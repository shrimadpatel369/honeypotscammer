from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import time
from pathlib import Path

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
from app.services.training_manager import training_manager
from app.utils.callback import send_guvi_callback
from app.cache import cache
from app.routes import training
from app.logger import (
    setup_logging,
    log_request,
    log_response,
    log_error,
    mask_sensitive_data
)

# Configure logging
setup_logging(debug=settings.debug)
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

# Register training routes
app.include_router(training.router)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with full details"""
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}"
    
    # Capture request details
    path = request.url.path
    method = request.method
    client_ip = get_remote_address(request)
    
    # Get headers (mask sensitive data)
    headers = dict(request.headers)
    masked_headers = mask_sensitive_data(headers)
    
    # Log request start
    logger.info(
        f"Request START: {method} {path} | Client: {client_ip} | "
        f"User-Agent: {headers.get('user-agent', 'unknown')}"
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request END: {method} {path} | Status: {response.status_code} | "
            f"Time: {process_time:.3f}s | Client: {client_ip}"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request FAILED: {method} {path} | Error: {str(e)} | "
            f"Time: {process_time:.3f}s | Client: {client_ip}",
            exc_info=True
        )
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
async def root():
    """Serve the test UI frontend"""
    test_ui_path = Path(__file__).parent.parent / "test_ui.html"
    if test_ui_path.exists():
        return FileResponse(test_ui_path)
    return {"message": "Honeypot API is running", "version": "2.0.0", "docs": "/docs"}

@app.get("/health")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def health_check(request: Request):
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
    "/api/message",
    response_model=HoneypotResponse,
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def message_endpoint(request: Request):
    """
    Main endpoint for hackathon - accepts messages as per specification
    Logs raw request first, then validates
    """
    # Log raw request body first
    try:
        raw_body = await request.body()
        logger.info(f"🔍 RAW REQUEST RECEIVED - Content-Type: {request.headers.get('content-type')}")
        logger.info(f"Raw Body: {raw_body.decode('utf-8')}")
        
        # Parse and validate
        body_json = await request.json()
        logger.info(f"Parsed JSON: {body_json}")
        
        honeypot_request = HoneypotRequest(**body_json)
        return await honeypot_endpoint(request, honeypot_request)
    except Exception as e:
        logger.error(f"❌ REQUEST VALIDATION FAILED: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request format: {str(e)}"
        )


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
        request: FastAPI request object
        honeypot_request: HoneypotRequest with message and conversation history
        
    Returns:
        HoneypotResponse with detection results and AI agent reply
    """
    start_time = time.time()
    session_id = honeypot_request.sessionId
    
    # Log incoming request with full details
    logger.info("="*80)
    logger.info(f"🔍 INCOMING TEST REQUEST - Session: {session_id}")
    logger.info("="*80)
    
    # Log request headers (masked)
    headers = dict(request.headers)
    masked_headers = mask_sensitive_data(headers)
    logger.info(f"Request Headers: {masked_headers}")
    
    # Log request body details
    request_body = honeypot_request.model_dump()
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Channel: {honeypot_request.metadata.channel if honeypot_request.metadata else 'Unknown'}")
    logger.info(f"Language: {honeypot_request.metadata.language if honeypot_request.metadata else 'Unknown'}")
    logger.info(f"Message Sender: {honeypot_request.message.sender}")
    logger.info(f"Message Text: {honeypot_request.message.text}")
    logger.info(f"Message Timestamp: {honeypot_request.message.timestamp}")
    logger.info(f"Conversation History Length: {len(honeypot_request.conversationHistory)}")
    
    if honeypot_request.conversationHistory:
        logger.info("Conversation History:")
        for idx, msg in enumerate(honeypot_request.conversationHistory, 1):
            logger.info(f"  [{idx}] {msg.sender}: {msg.text}")
    
    # Log structured request data
    log_request(
        session_id=session_id,
        request_data=request_body,
        masked_headers=masked_headers
    )
    
    try:
        logger.info(f"📊 Processing request for session: {session_id}")
        
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
        from datetime import timezone
        start_time_session = session["startTime"]
        if isinstance(start_time_session, str):
            from datetime import datetime
            start_time_session = datetime.fromisoformat(start_time_session.replace('Z', '+00:00'))
        
        # Ensure both timestamps are timezone-aware (UTC)
        current_timestamp = honeypot_request.message.timestamp
        if current_timestamp.tzinfo is None:
            current_timestamp = current_timestamp.replace(tzinfo=timezone.utc)
        if start_time_session.tzinfo is None:
            start_time_session = start_time_session.replace(tzinfo=timezone.utc)
        
        # Calculate duration, handle negative durations
        duration_seconds = max(0, int((current_timestamp - start_time_session).total_seconds()))
        
        engagement_metrics = {
            "engagementDurationSeconds": duration_seconds,
            "totalMessagesExchanged": session["totalMessages"]
        }
        
        # Check if conversation should end
        if not should_continue or session["totalMessages"] >= 30:  # Max 30 messages
            session["status"] = "completed"
            logger.info(f"Session {honeypot_request.sessionId} completed")
            
            # Auto-learn from successful session
            if session["scamDetected"]:
                try:
                    await training_manager.learn_from_session(session)
                    logger.info(f"🎓 Learning completed for session {honeypot_request.sessionId}")
                except Exception as learn_error:
                    logger.error(f"Learning error: {learn_error}")
            
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
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
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
        
        # Log response details
        logger.info("="*80)
        logger.info(f"📤 OUTGOING RESPONSE - Session: {honeypot_request.sessionId}")
        logger.info("="*80)
        logger.info(f"Status: {response.status}")
        logger.info(f"Scam Detected: {response.scamDetected}")
        logger.info(f"Should Continue: {response.shouldContinue}")
        logger.info(f"Agent Reply: {response.reply}")
        logger.info(f"Total Messages: {response.engagementMetrics.totalMessagesExchanged}")
        logger.info(f"Duration: {response.engagementMetrics.engagementDurationSeconds}s")
        logger.info(f"Intelligence Extracted:")
        logger.info(f"  - Bank Accounts: {len(response.extractedIntelligence.bankAccounts)}")
        logger.info(f"  - UPI IDs: {len(response.extractedIntelligence.upiIds)}")
        logger.info(f"  - Phishing Links: {len(response.extractedIntelligence.phishingLinks)}")
        logger.info(f"  - Phone Numbers: {len(response.extractedIntelligence.phoneNumbers)}")
        logger.info(f"  - Keywords: {len(response.extractedIntelligence.suspiciousKeywords)}")
        logger.info(f"Agent Notes: {response.agentNotes}")
        logger.info(f"Processing Time: {processing_time:.2f}ms")
        logger.info("="*80)
        
        # Log structured response data
        log_response(
            session_id=honeypot_request.sessionId,
            response_data=response.model_dump(),
            duration_ms=processing_time,
            status_code=200
        )
        
        logger.info(f"✅ Successfully processed request for session {honeypot_request.sessionId}")
        return response
        
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(f"❌ Error processing honeypot request for session {honeypot_request.sessionId}: {str(e)}", exc_info=True)
        
        # Log error details
        log_error(
            session_id=honeypot_request.sessionId,
            error_message=str(e),
            error_details={
                "exception_type": type(e).__name__,
                "duration_ms": processing_time
            }
        )
        
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
