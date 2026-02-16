import httpx
from app.config import settings
from typing import Dict, Any
import logging
from datetime import datetime
from app.database import Database

logger = logging.getLogger(__name__)


async def send_guvi_callback(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    extracted_intelligence: Dict[str, Any],
    engagement_metrics: Dict[str, int],
    agent_notes: str
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
        total_messages: Total number of messages exchanged
        extracted_intelligence: All extracted intelligence
        engagement_metrics: Metrics about engagement duration and quantity
        agent_notes: Summary of scammer behavior
        
    Returns:
        True if callback was successful, False otherwise
    """
    try:
        # Log function invocation
        logger.info(f"🔔 GUVI callback function triggered for session: {session_id}")
        logger.debug(f"Callback params - scam_detected: {scam_detected}, metrics: {engagement_metrics}")
        
        # ✅ ONLY send callback if scam is confirmed
        if not scam_detected:
            logger.info(f"⏭️ Skipping GUVI callback for session {session_id} - No scam detected")
            return True  # Return True since this is expected behavior
        
        # Validate sufficient engagement
        if total_messages < 3:
            logger.warning(
                f"⚠️ Session {session_id} has insufficient messages ({total_messages}), "
                "but sending callback anyway since scam was detected"
            )
        
        payload = {
            "sessionId": session_id,
            "scamDetected": scam_detected,
            "totalMessagesExchanged": total_messages,
            "engagementMetrics": engagement_metrics,
            "extractedIntelligence": {
                "bankAccounts": extracted_intelligence.get("bankAccounts", []),
                "upiIds": extracted_intelligence.get("upiIds", []),
                "phishingLinks": extracted_intelligence.get("phishingLinks", []),
                "phoneNumbers": extracted_intelligence.get("phoneNumbers", []),
                "emailAddresses": extracted_intelligence.get("emailAddresses", []),
                "suspiciousKeywords": extracted_intelligence.get("suspiciousKeywords", [])
            },
            "agentNotes": agent_notes
        }
        
        logger.info("="*80)
        logger.info(f"📡 SENDING GUVI CALLBACK - Session: {session_id}")
        logger.info("="*80)
        logger.info(f"✅ Scam Confirmed - Sufficient Engagement Complete")
        logger.info(f"Endpoint: {settings.guvi_callback_url}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Scam Detected: {scam_detected}")
        logger.info(f"Total Messages: {total_messages}")
        logger.info(f"Intelligence Summary:")
        logger.info(f"  - Bank Accounts: {len(payload['extractedIntelligence']['bankAccounts'])}")
        logger.info(f"  - UPI IDs: {len(payload['extractedIntelligence']['upiIds'])}")
        logger.info(f"  - Phishing Links: {len(payload['extractedIntelligence']['phishingLinks'])}")
        logger.info(f"  - Phone Numbers: {len(payload['extractedIntelligence']['phoneNumbers'])}")
        logger.info(f"  - Keywords: {len(payload['extractedIntelligence']['suspiciousKeywords'])}")
        logger.info(f"Agent Notes: {agent_notes}")
        logger.info("Full Payload:")
        
        import json
        logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
        logger.debug(f"Callback payload: {payload}")
        
        logger.info("🚀 Preparing to send HTTP POST request to GUVI callback endpoint")
        logger.debug(f"GUVI Callback URL: {settings.guvi_callback_url}")
        
        async with httpx.AsyncClient() as client:
            logger.info(f"📤 Sending POST request with scam intelligence data for session {session_id}")
            response = await client.post(
                settings.guvi_callback_url,
                json=payload,
                timeout=10.0,
                headers={
                    "Content-Type": "application/json"
                }
            )
            
            logger.info(f"📨 Received response from GUVI callback endpoint")
            logger.info(f"Response Body: {response.text}")
            logger.info("="*80)
            
            # Save callback response to MongoDB
            success = response.status_code == 200
            callback_response_doc = {
                "sessionId": session_id,
                "callbackUrl": settings.guvi_callback_url,
                "sentPayload": payload,
                "responseStatus": response.status_code,
                "responseBody": response.text,
                "sentTime": datetime.utcnow(),
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
