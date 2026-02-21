from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime, timezone, UTC
import logging
import time
import asyncio
from pathlib import Path


from app.config import settings
from app.database import Database, init_indexes
from app.models import HoneypotRequest, HoneypotResponse, GuviCallbackPayload
from app.auth import verify_api_key
from app.services.scam_detector import ScamDetectorService
from app.services.ai_agent import AIAgentService
from app.services.intelligence_extractor import IntelligenceExtractorService
from app.services.training_manager import training_manager
from app.services.callback_monitor import callback_monitor
from app.utils.callback import send_guvi_callback, get_callback_response, get_all_callback_responses
from app.cache import cache

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

# ─── Singleton service instances (avoid re-creation per request) ───
_scam_detector = ScamDetectorService()
_ai_agent = AIAgentService()
_intelligence_extractor = IntelligenceExtractorService()




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting application...")
    await Database.connect_db()
    await init_indexes()
    
    # Start callback monitor for auto-callbacks on inactive sessions
    await callback_monitor.start()
    
    logger.info(f"Application startup complete - Using {settings.gemini_model}")
    logger.info(f"MongoDB pool: {settings.mongodb_min_pool_size}-{settings.mongodb_max_pool_size} connections")
    logger.info(f"Caching: {'Enabled' if settings.enable_caching else 'Disabled'}")
    logger.info(f"Callback monitor: Active (1.5min inactivity threshold)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await callback_monitor.stop()
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


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register training routes



# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with full details"""
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}"
    
    # Capture request details
    path = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "unknown"
    
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

@app.post("/api/v1/mock-callback")
async def mock_callback(payload: GuviCallbackPayload):
    """Internal mock endpoint to capture the final callback payload for testing"""
    import json
    with open("mock_callback_payload.json", "w") as f:
        json.dump(payload.model_dump(), f, indent=2)
    logger.info(f"Mock Callback Received for session {payload.sessionId}")
    return {"status": "success", "message": "Callback captured"}

# Routes
@app.get("/")
async def root():
    """Serve the test UI frontend"""
    test_ui_path = Path(__file__).parent.parent / "tests" / "test_ui.html"
    if test_ui_path.exists():
        return FileResponse(test_ui_path)
    return {"message": "Honeypot API is running", "version": "2.0.0", "docs": "/docs"}

@app.get("/health")
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
async def message_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Main endpoint for hackathon - accepts messages as per specification
    Logs raw request first, then validates
    """
    # Log raw request body first
    try:
        raw_body = await request.body()
        logger.info(f"[HONEYPOT-APP] 🔍 RAW REQUEST RECEIVED - Content-Type: {request.headers.get('content-type')}")
        logger.info(f"[HONEYPOT-APP] Raw Body: {raw_body.decode('utf-8')}")
        
        # Parse and validate
        body_json = await request.json()
        logger.info(f"[HONEYPOT-APP] Parsed JSON: {body_json}")
        
        honeypot_request = HoneypotRequest(**body_json)
        return await honeypot_endpoint(request, honeypot_request, background_tasks)
    except Exception as e:
        logger.error(f"❌ REQUEST VALIDATION FAILED: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request format: {str(e)}"
        )





from app.utils.callback import send_guvi_callback

async def process_background_tasks(
    honeypot_request: HoneypotRequest,
    session: dict,
    all_messages: list,
    agent_reply: str,
    should_continue: bool
):
    """Offloads heavy analytical and database operations out of the critical response path."""
    try:
        scam_detector = _scam_detector
        intelligence_extractor = _intelligence_extractor
        sessions_collection = Database.get_sessions_collection()
        cache_key = f"session_{honeypot_request.sessionId}"
        
        # 1. Deferred Scam Detection 
        scam_detected = session.get("scamDetected", False)
        scam_indicators = []
        scam_type = session.get("scamType", "unknown")
        scam_confidence = session.get("confidenceLevel", 0.0)
        
        if not scam_detected and len(all_messages) >= 2:
            logger.info(f"[DETECTION] 🔍 Running scam detection for session {honeypot_request.sessionId} (msgs: {len(all_messages)})")
            detected, confidence, indicators, s_type = await scam_detector.detect_scam(
                current_message=honeypot_request.message.text,
                conversation_history=[msg.model_dump() for msg in all_messages],
                metadata=honeypot_request.metadata.model_dump() if honeypot_request.metadata else {}
            )
            if detected:
                session["scamDetected"] = True
                session["scamType"] = s_type
                session["confidenceLevel"] = confidence
                scam_indicators = indicators
                logger.info(f"[DETECTION] 🚨 SCAM DETECTED in session {honeypot_request.sessionId} — type={s_type}, confidence={confidence:.2f}, indicators={indicators}")
            else:
                logger.info(f"[DETECTION] ✅ No scam detected in session {honeypot_request.sessionId} (confidence={confidence:.2f})")
        elif scam_detected:
            logger.info(f"[DETECTION] ⏭️ Skipping detection for {honeypot_request.sessionId} — already detected as {scam_type} ({scam_confidence:.2f})")
        else:
            logger.info(f"[DETECTION] ⏭️ Skipping detection for {honeypot_request.sessionId} — not enough messages ({len(all_messages)})")
                
        # 2. Intelligence Extraction
        extracted_intelligence = await intelligence_extractor.extract_intelligence(
            conversation_history=[msg.model_dump() for msg in all_messages],
            current_extraction=session.get("extractedIntelligence", {})
        )
        intel_summary = {k: len(v) for k, v in extracted_intelligence.items() if isinstance(v, list) and len(v) > 0}
        logger.info(f"[INTEL] 📊 Extraction for {honeypot_request.sessionId}: {intel_summary if intel_summary else 'no items found'}")
        
        # 3. Synchronize Session State
        # NOTE: We NO LONGER store conversationHistory in memory/MongoDB to save massive amounts of space.
        # The evaluator's request payload already provides the full history on every request.
        session["extractedIntelligence"] = extracted_intelligence
        session["lastUpdateTime"] = honeypot_request.message.timestamp
        session["totalMessages"] = len(all_messages) + 1  # Including the AI's reply
        
        # Track conversation quality metrics (Questions Asked)
        if agent_reply and "?" in agent_reply:
            session["questionsAsked"] = session.get("questionsAsked", 0) + agent_reply.count("?")
        
        if scam_indicators:
            session["agentNotes"] = f"{session.get('agentNotes', '')} | {', '.join(scam_indicators)}"
            session["redFlagCount"] = session.get("redFlagCount", 0) + len(scam_indicators)
            
        # 4. Engagement Metrics Calculation
        start_time_session = session["startTime"]
        if isinstance(start_time_session, str):
            start_time_session = datetime.fromisoformat(start_time_session.replace('Z', '+00:00'))
            
        current_timestamp = honeypot_request.message.timestamp
        if current_timestamp.tzinfo is None:
            current_timestamp = current_timestamp.replace(tzinfo=timezone.utc)
        if start_time_session.tzinfo is None:
            start_time_session = start_time_session.replace(tzinfo=timezone.utc)
            
        duration_seconds = max(0, int((current_timestamp - start_time_session).total_seconds()))
        engagement_metrics = {
            "engagementDurationSeconds": duration_seconds,
            "totalMessagesExchanged": session["totalMessages"]
        }
        session["engagementMetrics"] = engagement_metrics
        
        # 5. Dynamic Scoring & Saturation Callbacks
        # Priority 1: Maximize Intelligence Extraction (Exclude keywords as they don't score intel points)
        intel_count = sum(len(v) for k, v in extracted_intelligence.items() if isinstance(v, list) and k != 'suspiciousKeywords')
        
        # Track intelligence growth to detect repetitive loops
        previous_intel_count = session.get("lastIntelCount", 0)
        if intel_count > previous_intel_count:
            session["turnsSinceLastIntel"] = 0
            session["lastIntelCount"] = intel_count
        else:
            session["turnsSinceLastIntel"] = session.get("turnsSinceLastIntel", 0) + 1
            
        # Priority 2: Base Hackathon Engagement Rules
        # - Turn Count (8 pts): >= 8 turns (16 msgs)
        # - Messages exchanged >= 10 points: >= 10 msgs 
        # - Engagement duration > 180 seconds: > 180s
        has_min_engagement = (session["totalMessages"] >= 16 and duration_seconds > 180)
        
        # Priority 3: Have we satisfied all Maximum Evaluation Criteria?
        # - Red Flag Identification (8 pts): >= 5 flags
        # - Information Elicitation (7 pts): Each earns 1.5 pts -> evaluated via `intel_count`
        # - Questions Asked (4 pts): >= 5 questions
        red_flag_count = session.get("redFlagCount", 0)
        questions_asked = session.get("questionsAsked", 0)
        
        has_max_red_flags = (red_flag_count >= 5)
        has_max_questions = (questions_asked >= 5)
        
        # We don't know the exact max intel points for the evaluator's specific scenario, 
        # so we rely strongly on the 'repetition' fallback to know when they've given up.
        is_repetitive = (intel_count > 0 and session["turnsSinceLastIntel"] >= 4)
        
        # Optimal Saturation Trigger: Base engagement met AND (hit maximum points OR scammer gave up)
        is_optimal_saturation = has_min_engagement and ((has_max_questions and has_max_red_flags) or is_repetitive)
        
        # Infinite Loop Hard Limit Fallback (Ensures we never get trapped)
        is_hard_limit = (session["totalMessages"] >= 30 or duration_seconds >= 300)
        
        if (not should_continue or is_optimal_saturation or is_hard_limit or session.get("testingMode")):
            session["status"] = "completed"
            
            if is_optimal_saturation:
                logger.info(f"[HONEYPOT-APP] 🏆 Optimal Scoring Saturation Hit for {honeypot_request.sessionId} (Data: {intel_count}, Msgs: {session['totalMessages']})")
            elif is_hard_limit:
                logger.warning(f"[HONEYPOT-APP] ⚠️ Hard Limit Fallback Hit for {honeypot_request.sessionId} (Msgs: {session['totalMessages']}, Secs: {duration_seconds})")
            elif session.get("testingMode"):
                logger.info(f"[HONEYPOT-APP] 🧪 Testing Mode Active - Pre-emptively terminating session {honeypot_request.sessionId} to fire webhook immediately.")
            else:
                logger.info(f"[HONEYPOT-APP] Session {honeypot_request.sessionId} completed (AI Terminal state)")
                
            try:
                await training_manager.learn_from_session(session)
            except Exception as e:
                logger.error(f"Background learning error: {e}")
                
            if not session.get("callbackSent", False):
                logger.info(f"[CALLBACK] 📡 Initiating callback for session {honeypot_request.sessionId} — "
                           f"scamDetected={session['scamDetected']}, type={session.get('scamType','unknown')}, "
                           f"confidence={session.get('confidenceLevel',0):.2f}, msgs={session['totalMessages']}, "
                           f"duration={duration_seconds}s, testing={session.get('testingMode', False)}")
                # ─── ATOMIC CALLBACK-ONCE GUARD ───
                # Optimistically mark as sent immediately to prevent re-entry
                # from concurrent background tasks or callback monitor
                session["callbackSent"] = True
                
                # Atomic DB guard: only proceed if DB also confirms not yet sent
                try:
                    lock_result = await sessions_collection.find_one_and_update(
                        {"sessionId": honeypot_request.sessionId, "callbackSent": {"$ne": True}},
                        {"$set": {"callbackSent": True}},
                        return_document=False  # returns the ORIGINAL doc (before update)
                    )
                    # If lock_result is None, another process already sent the callback
                    if lock_result is None:
                        # Check if session even exists in DB
                        existing = await sessions_collection.find_one({"sessionId": honeypot_request.sessionId})
                        if existing and existing.get("callbackSent"):
                            logger.info(f"🔒 Callback already sent for {honeypot_request.sessionId} (DB guard). Skipping duplicate.")
                            # Still need to save session and purge cache
                            await sessions_collection.update_one(
                                {"sessionId": honeypot_request.sessionId},
                                {"$set": session},
                                upsert=True
                            )
                            await cache.delete(cache_key)
                            return  # Exit early, callback already sent
                        # If session doesn't exist yet in DB, proceed (first write)
                except Exception as db_lock_err:
                    logger.warning(f"⚠️ DB callback lock check failed (DB may be unavailable): {db_lock_err}")
                    # Proceed anyway — the in-memory flag is our fallback guard
                
                success = await send_guvi_callback(
                    session_id=honeypot_request.sessionId,
                    scam_detected=session["scamDetected"],
                    scam_type=session.get("scamType", "unknown"),
                    confidence_level=session.get("confidenceLevel", 0.0),
                    total_messages=session["totalMessages"],
                    extracted_intelligence=session.get("extractedIntelligence", {}),
                    engagement_metrics=engagement_metrics,
                    agent_notes=session.get("agentNotes", ""),
                    testing_mode=session.get("testingMode", False)
                )
                if success:
                    session["callbackSentTime"] = honeypot_request.message.timestamp.isoformat()
                    
                    # Store the exact payload parameters we fired off
                    session["finalCallbackPayload"] = {
                        "scamDetected": session["scamDetected"],
                        "scamType": session.get("scamType", "unknown"),
                        "confidenceLevel": session.get("confidenceLevel", 0.0),
                        "totalMessagesExchanged": session["totalMessages"],
                        "extractedIntelligence": session.get("extractedIntelligence", {}),
                        "engagementMetrics": engagement_metrics,
                        "agentNotes": session.get("agentNotes", "")
                    }
                    
                    # Store the completed session into MongoDB
                    await sessions_collection.update_one(
                        {"sessionId": honeypot_request.sessionId},
                        {"$set": session},
                        upsert=True
                    )
                    logger.info(f"💾 Permanently saved completed session {honeypot_request.sessionId} to MongoDB with full history")
                    
                    # Purge from RAM Cache since evaluation is permanently over
                    await cache.delete(cache_key)
                    logger.info(f"🧹 Purged completed session {honeypot_request.sessionId} from RAM Cache")
                else:
                    # Callback failed — reset the flag so it can be retried
                    session["callbackSent"] = False
                    try:
                        await sessions_collection.update_one(
                            {"sessionId": honeypot_request.sessionId},
                            {"$set": {"callbackSent": False}},
                        )
                    except Exception:
                        pass
                    logger.error(f"❌ Callback failed for {honeypot_request.sessionId} — flag reset for retry")
                        
        # 6. Push to DB and Cache (Only if not completed & purged)
        if session.get("status") != "completed" or not session.get("callbackSent"):
            await cache.set(cache_key, session, ttl=3600)
            
            # Ensure conversationHistory never pollutes the MongoDB document during active flight to save DB I/O bandwidth
            session.pop("conversationHistory", None) 
            await sessions_collection.update_one(
                {"sessionId": honeypot_request.sessionId},
                {"$set": session},
                upsert=True
            )
        logger.info(f"✅ Background processing finished for session {honeypot_request.sessionId}")
    except Exception as e:
        logger.error(f"❌ Error in background process for session {honeypot_request.sessionId}: {e}", exc_info=True)


@app.post(
    "/api/v1/honeypot",
    response_model=HoneypotResponse,
    dependencies=[Depends(verify_api_key)]
)
async def honeypot_endpoint(request: Request, honeypot_request: HoneypotRequest, background_tasks: BackgroundTasks):
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
        
        # Use singleton services (module-level instances)
        ai_agent = _ai_agent
        
        # Get or create session from memory cache first, fallback to DB
        sessions_collection = Database.get_sessions_collection()
        cache_key = f"session_{honeypot_request.sessionId}"
        
        session = await cache.get(cache_key)
        if not session:
            logger.info(f"Cache miss for {honeypot_request.sessionId}, checking MongoDB...")
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
                "startTime": honeypot_request.message.timestamp.isoformat(),
                "lastUpdateTime": honeypot_request.message.timestamp.isoformat(),
                "totalMessages": 1,
                "status": "active",
                "testingMode": honeypot_request.testing,
                "agentNotes": "",
                "scamType": "unknown",
                "confidenceLevel": 0.0,
                "callbackSent": False  # Track callback status
            }
        
        # Add current message to history
        all_messages = honeypot_request.conversationHistory + [honeypot_request.message]
        
        # Zero-Blocking Fast Path: Instantly Generate AI Agent Response
        # We process LLM engagement first using raw history to minimize latency.
        agent_reply, should_continue = await ai_agent.generate_response(
            current_message=honeypot_request.message.text,
            conversation_history=[msg.model_dump() for msg in all_messages],
            session_context=session,
            metadata=honeypot_request.metadata.model_dump() if honeypot_request.metadata else {}
        )
        logger.info(f"AI agent synchronously generated response for session {honeypot_request.sessionId}")
        
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
            logger.info(f"Scam Detected: {session['scamDetected']} for session {honeypot_request.sessionId}")
            logger.info(f"Session Callback Sent ? {session.get('callbackSent', False)}")
            
            if session["scamDetected"] and not session.get("callbackSent", False):
                logger.info(f"Preparing to send GUVI callback for session {honeypot_request.sessionId}")
                callback_success = await send_guvi_callback(
                    session_id=honeypot_request.sessionId,
                    scam_detected=session["scamDetected"],
                    total_messages=session["totalMessages"],
                    extracted_intelligence=session.get("extractedIntelligence", {}),
                    engagement_metrics=engagement_metrics,
                    agent_notes=session.get("agentNotes", "")
                )
                if callback_success:
                    session["callbackSent"] = True
                    session["callbackSentTime"] = honeypot_request.message.timestamp.isoformat()
                    logger.info(f"Successfully sent GUVI callback for session {honeypot_request.sessionId}")
                    
                    # Learn from successful session for future improvements
                    try:
                        await training_manager.learn_from_session(session)
                        logger.info(f"🎓 Session data queued for live learning: {honeypot_request.sessionId}")
                    except Exception as e:
                        logger.error(f"Failed to learn from session: {e}")
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
        
        # Prepare response (Hackathon schema format)
        response = HoneypotResponse(
            status="success",
            reply=agent_reply if agent_reply else ""
        )
        
        # Log response details
        logger.info("="*80)
        logger.info(f"📤 OUTGOING RESPONSE - Session: {honeypot_request.sessionId}")
        logger.info("="*80)
        logger.info(f"Status: {response.status}")
        logger.info(f"Agent Reply: {response.reply}")
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


@app.get("/api/v1/sessions/{session_id}/callback")
async def get_session_callback(session_id: str, api_key: str = Depends(verify_api_key)):
    """Get the latest callback response for a session"""
    callback_response = await get_callback_response(session_id)
    
    if not callback_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No callback response found for session {session_id}"
        )
    
    return callback_response


@app.get("/api/v1/sessions/{session_id}/callbacks")
async def get_session_callbacks(session_id: str, api_key: str = Depends(verify_api_key)):
    """Get all callback responses for a session"""
    callback_responses = await get_all_callback_responses(session_id)
    
    return {
        "sessionId": session_id,
        "count": len(callback_responses),
        "responses": callback_responses
    }


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
