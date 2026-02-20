import httpx
from app.config import settings
from typing import Dict, Any
import logging
from datetime import datetime, timezone
from app.database import Database

logger = logging.getLogger(__name__)

# ─── Persistent HTTP client for callbacks (reuses TCP connections) ───
_callback_client = httpx.AsyncClient(timeout=10.0)


async def send_guvi_callback(
    session_id: str,
    scam_detected: bool,
    scam_type: str,
    confidence_level: float,
    total_messages: int,
    extracted_intelligence: Dict[str, Any],
    engagement_metrics: Dict[str, int],
    agent_notes: str,
    testing_mode: bool = False
) -> bool:
    """
    Send final result callback to GUVI evaluation endpoint
    
    ⚠️ ONLY SENDS WHEN:
    1. Scam intent is confirmed (scam_detected = True)
    2. AI Agent has completed sufficient engagement
    3. Intelligence extraction is finished
    
    Args:
        session_id: Unique session identifier
        scam_detected: Whether scam was detected
        scam_type: Predicted scam type
        confidence_level: Model confidence level
        total_messages: Total number of messages exchanged
        extracted_intelligence: All extracted intelligence
        engagement_metrics: Metrics about engagement duration and quantity
        agent_notes: Summary of scammer behavior
        
    Returns:
        True if callback was successful, False otherwise
    """
    try:
        # Log function invocation
        logger.info(f"[HONEYPOT-APP] 🔔 GUVI callback function triggered for session: {session_id}")
        logger.debug(f"[HONEYPOT-APP] Callback params - scam_detected: {scam_detected}, testing_mode: {testing_mode}")
        
        # ✅ ONLY send callback if scam is confirmed
        if not scam_detected and not testing_mode:
            logger.info(f"[HONEYPOT-APP] ⏭️ Skipping GUVI callback for session {session_id} - No scam detected")
            return True  # Return True since this is expected behavior
        
        # Validate sufficient engagement
        if total_messages < 3 and not testing_mode:
            logger.warning(
                f"[HONEYPOT-APP] ⚠️ Session {session_id} has insufficient messages ({total_messages}), "
                "but sending callback anyway since scam was detected"
            )
        
        payload = {
            "sessionId": session_id,
            "scamDetected": scam_detected,
            "scamType": scam_type,
            "confidenceLevel": confidence_level,
            "totalMessagesExchanged": total_messages,
            "engagementDurationSeconds": engagement_metrics.get("engagementDurationSeconds", 0),
            "engagementMetrics": engagement_metrics,
            "extractedIntelligence": {
                "bankAccounts": extracted_intelligence.get("bankAccounts", []),
                "upiIds": extracted_intelligence.get("upiIds", []),
                "phishingLinks": extracted_intelligence.get("phishingLinks", []),
                "phoneNumbers": extracted_intelligence.get("phoneNumbers", []),
                "emailAddresses": extracted_intelligence.get("emailAddresses", []),
                "suspiciousKeywords": extracted_intelligence.get("suspiciousKeywords", []),
                "caseIds": extracted_intelligence.get("caseIds", []),
                "policyNumbers": extracted_intelligence.get("policyNumbers", []),
                "orderNumbers": extracted_intelligence.get("orderNumbers", [])
            },
            "agentNotes": agent_notes
        }
        
        logger.info("[HONEYPOT-APP] " + "="*80)
        logger.info(f"[HONEYPOT-APP] 📡 SENDING GUVI CALLBACK - Session: {session_id}")
        logger.info("[HONEYPOT-APP] " + "="*80)
        
        target_url = settings.guvi_callback_url
        if testing_mode:
            # Re-route to our own backend test endpoint to prove execution without polluting evaluator db
            target_url = "http://localhost:8000/api/v1/mock-callback"
            if settings.env == "production":
                target_url = "https://honeypotscammer-136046240844.asia-south2.run.app/api/v1/mock-callback"
        
        logger.info(f"[HONEYPOT-APP] ✅ Scam Confirmed - Sufficient Engagement Complete")
        logger.info(f"[HONEYPOT-APP] Endpoint: {target_url} (Testing Mode: {testing_mode})")
        logger.info(f"[HONEYPOT-APP] Session ID: {session_id}")
        logger.info(f"[HONEYPOT-APP] Scam Detected: {scam_detected}")
        logger.info(f"[HONEYPOT-APP] Total Messages: {total_messages}")
        logger.info(f"[HONEYPOT-APP] Intelligence Summary:")
        logger.info(f"[HONEYPOT-APP]   - Bank Accounts: {len(payload['extractedIntelligence']['bankAccounts'])}")
        logger.info(f"[HONEYPOT-APP]   - Phone Numbers: {len(payload['extractedIntelligence']['phoneNumbers'])}")
        
        import json
        logger.info(f"[HONEYPOT-APP] Full Payload: {json.dumps(payload)}")
        logger.debug(f"Callback payload: {payload}")
        
        logger.info("[HONEYPOT-APP] 🚀 Preparing to send HTTP POST request to GUVI callback endpoint")
        logger.debug(f"[HONEYPOT-APP] Target URL: {target_url}")
        
        logger.info(f"[HONEYPOT-APP] 📤 Sending POST request with scam intelligence data for session {session_id}")
        response = await _callback_client.post(
            target_url,
            json=payload,
            headers={
                "Content-Type": "application/json"
            }
        )
        
        logger.info(f"[HONEYPOT-APP] 📨 Received response from GUVI callback endpoint")
        logger.info(f"[HONEYPOT-APP] Response Body: {response.text}")
        logger.info("[HONEYPOT-APP] " + "="*80)
        
        # Save callback response to MongoDB
        success = response.status_code == 200
        callback_response_doc = {
            "sessionId": session_id,
            "callbackUrl": settings.guvi_callback_url,
            "sentPayload": payload,
            "responseStatus": response.status_code,
            "responseBody": response.text,
            "sentTime": datetime.now(timezone.utc),
            "success": success,
            "error": None if success else f"HTTP {response.status_code}"
        }
        
        try:
            callbacks_collection = Database.get_callbacks_collection()
            result = await callbacks_collection.insert_one(callback_response_doc)
            logger.info(f"💾 Callback response saved to MongoDB with ID: {result.inserted_id}")
        except Exception as db_error:
            logger.error(f"⚠️ Failed to save callback response to MongoDB: {str(db_error)}", exc_info=True)
        
        if success:
            logger.info(f"✅ Successfully sent GUVI callback for session {session_id}")
            return True
        else:
            logger.error(
                f"❌ GUVI callback failed for session {session_id}: "
                f"Status {response.status_code}, Response: {response.text}"
            )
            return False
                
    except httpx.TimeoutException:
        logger.error(f"⏱️ GUVI callback timeout for session {session_id}")
        return False
    except Exception as e:
        logger.error(f"❌ Error sending GUVI callback for session {session_id}: {str(e)}", exc_info=True)
        return False


async def get_callback_response(session_id: str) -> Dict[str, Any]:
    """
    Retrieve callback response from MongoDB for a specific session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Dictionary containing callback response or empty dict if not found
    """
    try:
        callbacks_collection = Database.get_callbacks_collection()
        callback_doc = await callbacks_collection.find_one(
            {"sessionId": session_id},
            sort=[("sentTime", -1)]  # Get the most recent callback
        )
        
        if callback_doc:
            # Remove MongoDB internal _id for API response
            callback_doc.pop("_id", None)
            return callback_doc
        else:
            logger.info(f"No callback response found for session {session_id}")
            return {}
    except Exception as e:
        logger.error(f"Error retrieving callback response for session {session_id}: {str(e)}", exc_info=True)
        return {}


async def get_all_callback_responses(session_id: str) -> list:
    """
    Retrieve all callback responses from MongoDB for a specific session
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of callback responses sorted by sent time (newest first)
    """
    try:
        callbacks_collection = Database.get_callbacks_collection()
        callback_docs = await callbacks_collection.find(
            {"sessionId": session_id}
        ).sort("sentTime", -1).to_list(length=None)
        
        # Remove MongoDB internal _id for API response
        for doc in callback_docs:
            doc.pop("_id", None)
        
        return callback_docs
    except Exception as e:
        logger.error(f"Error retrieving callback responses for session {session_id}: {str(e)}", exc_info=True)
        return []
