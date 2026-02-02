from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import Database, init_indexes
from app.models import HoneypotRequest, HoneypotResponse
from app.auth import verify_api_key
from app.services.scam_detector import ScamDetectorService
from app.services.ai_agent import AIAgentService
from app.services.intelligence_extractor import IntelligenceExtractorService
from app.utils.callback import send_guvi_callback
from app.cache import cache

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting application...")
    await Database.connect_db()
    await init_indexes()
    logger.info(f"Application startup complete - Using {settings.gemini_model}")
    logger.info(f"MongoDB pool: {settings.mongodb_min_pool_size}-{settings.mongodb_max_pool_size} connections")
    logger.info(f"Caching: {'Enabled' if settings.enable_caching else 'Disabled'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await Database.close_db()
    await cache.clear()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered honeypot system for scam detection and intelligence extraction - Premium Edition",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - Error: {str(e)}")
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An internal server error occurred",
            "detail": str(exc) if settings.debug else "Internal server error"
        }
    )


# Routes
@app.get("/")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def root(request: Request):
    """Root endpoint - health check"""
    return {
        "status": "online",
        "service": settings.app_name,
        "version": "2.0.0",
        "environment": settings.env,
        "model": settings.gemini_model,
        "cache_enabled": settings.enable_caching
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    try:
        # Check database connection
        db = Database.get_database()
        await db.command('ping')
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Get cache stats
    cache_stats = cache.get_stats() if settings.enable_caching else {"status": "disabled"}
    
    health_status = {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "cache": cache_stats,
        "environment": settings.env,
        "model": settings.gemini_model
    }
    
    status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=health_status, status_code=status_code)


@app.post(
    "/api/v1/honeypot",
    response_model=HoneypotResponse,
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def honeypot_endpoint(request: Request, honeypot_request: HoneypotRequest):
    """
    Main honeypot endpoint for scam detection and engagement
    
    This endpoint:
    1. Receives incoming messages
    2. Detects scam intent
    3. Activates AI agent for engagement
    4. Extracts intelligence
    5. Returns structured response
    6. Sends final callback to GUVI when conversation completes
    
    Args:
        request: HoneypotRequest with message and conversation history
        
    Returns:
        HoneypotResponse with detection results and AI agent reply
    """
    try:
        logger.info(f"Processing request for session: {honeypot_request.sessionId}")
        start_time = time.time()
        
        # Initialize services
        scam_detector = ScamDetectorService()
        ai_agent = AIAgentService()
        intelligence_extractor = IntelligenceExtractorService()
        
        # Get or create session from database
        sessions_collection = Database.get_sessions_collection()
        session = await sessions_collection.find_one({"sessionId": honeypot_request.sessionId})
        
        if session is None:
            # First message - create new session
            logger.info(f"Creating new session: {honeypot_request.sessionId}")
            session = {
                "sessionId": honeypot_request.sessionId,
                "scamDetected": False,
                "conversationHistory": [],
                "extractedIntelligence": {
                    "bankAccounts": [],
                    "upiIds": [],
                    "phishingLinks": [],
                    "phoneNumbers": [],
                    "suspiciousKeywords": []
                },
                "metadata": honeypot_request.metadata.model_dump() if honeypot_request.metadata else {},
                "startTime": honeypot_request.message.timestamp,
                "lastUpdateTime": honeypot_request.message.timestamp,
                "totalMessages": 0,
                "status": "active",
                "agentNotes": ""
            }
        
        # Add current message to history
        all_messages = honeypot_request.conversationHistory + [honeypot_request.message]
        
        # Detect scam intent
        scam_detected, scam_confidence, scam_indicators = await scam_detector.detect_scam(
            current_message=honeypot_request.message.text,
            conversation_history=[msg.model_dump() for msg in honeypot_request.conversationHistory],
            metadata=honeypot_request.metadata.model_dump() if honeypot_request.metadata else {}
        )
        
        # Update session with scam detection
        if scam_detected and not session["scamDetected"]:
            session["scamDetected"] = True
            logger.info(f"Scam detected in session {honeypot_request.sessionId} with confidence {scam_confidence}")
        
        # Generate AI agent response (if scam detected)
        agent_reply = ""
        should_continue = True
        
        if scam_detected:
            agent_reply, should_continue = await ai_agent.generate_response(
                current_message=honeypot_request.message.text,
                conversation_history=[msg.model_dump() for msg in all_messages],
                session_context=session,
                metadata=honeypot_request.metadata.model_dump() if honeypot_request.metadata else {}
            )
            logger.info(f"AI agent generated response for session {honeypot_request.sessionId}")
        
        # Extract intelligence from conversation
        extracted_intelligence = await intelligence_extractor.extract_intelligence(
            conversation_history=[msg.model_dump() for msg in all_messages],
            current_extraction=session["extractedIntelligence"]
        )
        
        # Update session
        session["conversationHistory"] = [msg.model_dump() for msg in all_messages]
        if agent_reply:
            session["conversationHistory"].append({
                "sender": "user",
                "text": agent_reply,
                "timestamp": honeypot_request.message.timestamp.isoformat()
            })
        
        session["extractedIntelligence"] = extracted_intelligence
        session["lastUpdateTime"] = honeypot_request.message.timestamp
        session["totalMessages"] = len(session["conversationHistory"])
        
        # Update agent notes
        if scam_indicators:
            session["agentNotes"] = f"{session['agentNotes']} | {', '.join(scam_indicators)}"
        
        # Calculate engagement metrics
        start_time_session = session["startTime"]
        if isinstance(start_time_session, str):
            from datetime import datetime
            start_time_session = datetime.fromisoformat(start_time_session.replace('Z', '+00:00'))
        
        duration_seconds = int((honeypot_request.message.timestamp - start_time_session).total_seconds())
        
        engagement_metrics = {
            "engagementDurationSeconds": duration_seconds,
            "totalMessagesExchanged": session["totalMessages"]
        }
        
        # Check if conversation should end
        if not should_continue or session["totalMessages"] >= 30:  # Max 30 messages
            session["status"] = "completed"
            logger.info(f"Session {honeypot_request.sessionId} completed")
            
            # Send final callback to GUVI
            if session["scamDetected"]:
                callback_success = await send_guvi_callback(
                    session_id=honeypot_request.sessionId,
                    scam_detected=session["scamDetected"],
                    total_messages=session["totalMessages"],
                    extracted_intelligence=extracted_intelligence,
                    agent_notes=session["agentNotes"].strip(" |")
                )
                if callback_success:
                    logger.info(f"Successfully sent GUVI callback for session {honeypot_request.sessionId}")
                else:
                    logger.error(f"Failed to send GUVI callback for session {honeypot_request.sessionId}")
        
        # Save session to database
        await sessions_collection.update_one(
            {"sessionId": honeypot_request.sessionId},
            {"$set": session},
            upsert=True
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Request processed in {processing_time:.3f}s for session {honeypot_request.sessionId}")
        
        # Prepare response
        response = HoneypotResponse(
            status="success",
            sessionId=honeypot_request.sessionId,
            scamDetected=session["scamDetected"],
            reply=agent_reply if agent_reply else None,
            shouldContinue=should_continue and session["status"] == "active",
            engagementMetrics=engagement_metrics,
            extractedIntelligence=extracted_intelligence,
            agentNotes=session["agentNotes"].strip(" |")
        )
        
        logger.info(f"Successfully processed request for session {honeypot_request.sessionId}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing honeypot request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process request: {str(e)}"
        )


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str, api_key: str = Depends(verify_api_key)):
    """Get session details by ID"""
    sessions_collection = Database.get_sessions_collection()
    session = await sessions_collection.find_one({"sessionId": session_id})
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # Remove MongoDB _id field
    session.pop("_id", None)
    return session


@app.get("/api/v1/sessions")
async def list_sessions(
    limit: int = 10,
    skip: int = 0,
    scam_only: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """List all sessions with pagination"""
    sessions_collection = Database.get_sessions_collection()
    
    query = {"scamDetected": True} if scam_only else {}
    
    sessions = await sessions_collection.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    # Remove MongoDB _id field
    for session in sessions:
        session.pop("_id", None)
    
    total = await sessions_collection.count_documents(query)
    
    return {
        "total": total,
        "limit": limit,
        "skip": skip,
        "sessions": sessions
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
