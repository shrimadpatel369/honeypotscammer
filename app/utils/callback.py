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
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.guvi_callback_url,
                json=payload,
                timeout=10.0,
                headers={
                    "Content-Type": "application/json"
                }
            )
            
            logger.info(f"GUVI Callback Response - Status: {response.status_code}")
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
