import asyncio
from datetime import datetime, timedelta, timezone
from app.database import Database
from app.utils.callback import send_guvi_callback
import logging

logger = logging.getLogger(__name__)


class CallbackMonitor:
    """Background service to monitor inactive sessions and auto-send callbacks"""
    
    def __init__(self):
        self.check_interval = 30  # Check every 30 seconds for faster response
        self.inactivity_threshold = 90  # 1.5 minutes of inactivity (fast for evaluators)
        self.is_running = False
        self.task = None
    
    async def start(self):
        """Start the background monitoring task"""
        if self.is_running:
            logger.warning("Callback monitor already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info(f"✅ Callback monitor started (check every {self.check_interval}s, inactivity threshold: {self.inactivity_threshold}s)")
    
    async def stop(self):
        """Stop the background monitoring task"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Callback monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                await self._check_inactive_sessions()
            except Exception as e:
                logger.error(f"Error in callback monitor loop: {e}", exc_info=True)
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)
    
    async def _check_inactive_sessions(self):
        """Check for inactive sessions that need callbacks"""
        try:
            sessions_collection = Database.get_sessions_collection()
            now = datetime.now(timezone.utc)
            inactivity_cutoff = now - timedelta(seconds=self.inactivity_threshold)
            
            # Find sessions that:
            # 1. Have scam detected
            # 2. Haven't had callback sent yet
            # 3. Last update was more than 5 minutes ago
            # 4. Are still in 'active' status
            query = {
                "scamDetected": True,
                "callbackSent": {"$ne": True},  # Not sent yet
                "status": "active",
                "lastUpdateTime": {"$lt": inactivity_cutoff}
            }
            
            stale_sessions = await sessions_collection.find(query).to_list(length=100)
            
            if stale_sessions:
                logger.info(f"🔍 Found {len(stale_sessions)} inactive sessions requiring callbacks")
            
            for session in stale_sessions:
                session_id = session.get("sessionId")
                
                try:
                    logger.info(f"⏰ Auto-sending callback for inactive session: {session_id}")
                    
                    # Calculate or get engagement metrics
                    engagement_metrics = session.get("engagementMetrics")
                    
                    if not engagement_metrics:
                        # Fallback calculation if not saved in session
                        try:
                            start_time = session.get("startTime")
                            last_update = session.get("lastUpdateTime")
                            duration = 0
                            
                            if start_time and last_update:
                                # Handle string timestamps
                                if isinstance(start_time, str):
                                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                if isinstance(last_update, str):
                                    last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                                
                                # Ensure timezone awareness
                                if start_time.tzinfo is None:
                                    start_time = start_time.replace(tzinfo=timezone.utc)
                                if last_update.tzinfo is None:
                                    last_update = last_update.replace(tzinfo=timezone.utc)
                                    
                                duration = max(0, int((last_update - start_time).total_seconds()))
                                
                            engagement_metrics = {
                                "engagementDurationSeconds": duration,
                                "totalMessagesExchanged": session.get("totalMessages", 0)
                            }
                        except Exception as metric_error:
                            logger.error(f"Error calculating metrics for inactive session: {metric_error}")
                            engagement_metrics = {
                                "engagementDurationSeconds": 0,
                                "totalMessagesExchanged": session.get("totalMessages", 0)
                            }
                    
                    # Send callback
                    callback_success = await send_guvi_callback(
                        session_id=session_id,
                        scam_detected=session.get("scamDetected", False),
                        total_messages=session.get("totalMessages", 0),
                        extracted_intelligence=session.get("extractedIntelligence", {}),
                        engagement_metrics=engagement_metrics,
                        agent_notes=session.get("agentNotes", "")
                    )
                    
                    if callback_success:
                        # Mark callback as sent
                        await sessions_collection.update_one(
                            {"sessionId": session_id},
                            {
                                "$set": {
                                    "callbackSent": True,
                                    "callbackSentTime": now,
                                    "status": "completed"
                                }
                            }
                        )
                        logger.info(f"✅ Auto-callback sent successfully for session {session_id}")
                    else:
                        logger.error(f"❌ Auto-callback failed for session {session_id}")
                
                except Exception as e:
                    logger.error(f"Error sending auto-callback for session {session_id}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error checking inactive sessions: {e}", exc_info=True)


# Global instance
callback_monitor = CallbackMonitor()