import httpx
from app.config import settings
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def send_guvi_callback(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    extracted_intelligence: Dict[str, Any],
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
        agent_notes: Summary of scammer behavior
        
    Returns:
        True if callback was successful, False otherwise
    """
    try:
        # Log function invocation
        logger.info(f"🔔 GUVI callback function triggered for session: {session_id}")
        logger.debug(f"Callback params - scam_detected: {scam_detected}, total_messages: {total_messages}")
        
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
            "extractedIntelligence": {
                "bankAccounts": extracted_intelligence.get("bankAccounts", []),
                "upiIds": extracted_intelligence.get("upiIds", []),
                "phishingLinks": extracted_intelligence.get("phishingLinks", []),
                "phoneNumbers": extracted_intelligence.get("phoneNumbers", []),
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
            
            if response.status_code == 200:
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
