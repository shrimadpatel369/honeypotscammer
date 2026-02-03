"""Simple RAG-based Training Manager - Fast Implementation"""
from app.database import Database
import logging
from typing import List, Dict, Any
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)


class TrainingManager:
    """Lightweight training data manager using MongoDB for RAG"""
    
    async def store_examples(self, examples: List[Dict[str, Any]], source: str = "kaggle") -> bool:
        """Store training examples in MongoDB"""
        try:
            collection = Database.get_database().training_examples
            
            for example in examples:
                # Create unique ID from content
                example['_id'] = hashlib.md5(
                    json.dumps(example.get('scammer_message', '')[:100], sort_keys=True).encode()
                ).hexdigest()
                example['created_at'] = datetime.utcnow()
                example['source'] = source
                
                # Upsert to avoid duplicates
                await collection.update_one(
                    {'_id': example['_id']},
                    {'$set': example},
                    upsert=True
                )
            
            logger.info(f"✅ Stored {len(examples)} training examples (source: {source})")
            return True
        except Exception as e:
            logger.error(f"Error storing examples: {e}")
            return False
    
    async def get_relevant_examples(self, scam_type: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant examples for RAG"""
        try:
            collection = Database.get_database().training_examples
            
            query = {}
            if scam_type:
                query['scam_type'] = scam_type
            
            cursor = collection.find(query).sort('created_at', -1).limit(limit)
            examples = await cursor.to_list(length=limit)
            
            return examples
        except Exception as e:
            logger.error(f"Error retrieving examples: {e}")
            return []
    
    async def learn_from_session(self, session_data: Dict[str, Any]) -> bool:
        """Auto-learn from successful sessions"""
        try:
            if not session_data.get('scamDetected'):
                return False
            
            conversation = session_data.get('conversationHistory', [])
            intelligence = session_data.get('extractedIntelligence', {})
            
            # Calculate success score
            intel_count = sum([
                len(intelligence.get('bankAccounts', [])),
                len(intelligence.get('upiIds', [])),
                len(intelligence.get('phishingLinks', [])),
                len(intelligence.get('phoneNumbers', []))
            ])
            
            # Only learn from successful extractions
            if intel_count < 2 or len(conversation) < 3:
                return False
            
            # Extract patterns
            learned = []
            for i in range(0, len(conversation) - 1, 2):
                if i + 1 < len(conversation):
                    scammer = conversation[i]
                    agent = conversation[i + 1]
                    
                    if scammer.get('sender') == 'scammer' and agent.get('sender') == 'user':
                        learned.append({
                            'scammer_message': scammer.get('text', ''),
                            'effective_response': agent.get('text', ''),
                            'scam_type': session_data.get('scamType', 'learned'),
                            'intelligence_count': intel_count,
                            'notes': f"Learned from session {session_data.get('sessionId')}"
                        })
            
            if learned:
                await self.store_examples(learned, source='live_learning')
                logger.info(f"🎓 Learned {len(learned)} patterns from session {session_data.get('sessionId')}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error learning from session: {e}")
            return False
    
    async def import_kaggle_csv(self, file_path: str) -> Dict[str, Any]:
        """Import CSV dataset (common Kaggle format)"""
        try:
            import pandas as pd
            
            df = pd.read_csv(file_path)
            examples = []
            
            for _, row in df.iterrows():
                example = {
                    'scammer_message': str(row.get('text', row.get('message', ''))),
                    'scam_type': str(row.get('type', row.get('category', 'unknown'))),
                    'label': str(row.get('label', 'scam'))
                }
                examples.append(example)
            
            success = await self.store_examples(examples, source='kaggle')
            return {'success': success, 'count': len(examples)}
        except Exception as e:
            logger.error(f"CSV import error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def import_kaggle_json(self, file_path: str) -> Dict[str, Any]:
        """Import JSON dataset"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                examples = data
            else:
                examples = [data]
            
            success = await self.store_examples(examples, source='kaggle')
            return {'success': success, 'count': len(examples)}
        except Exception as e:
            logger.error(f"JSON import error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get training data stats"""
        try:
            collection = Database.get_database().training_examples
            
            total = await collection.count_documents({})
            kaggle = await collection.count_documents({'source': 'kaggle'})
            learned = await collection.count_documents({'source': 'live_learning'})
            
            return {
                'total_examples': total,
                'kaggle_imported': kaggle,
                'live_learned': learned
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {}


# Global instance
training_manager = TrainingManager()
