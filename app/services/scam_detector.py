import google.generativeai as genai
from app.config import settings
import logging
from typing import List, Tuple, Dict, Any
import json
import hashlib
from app.cache import cache

logger = logging.getLogger(__name__)

# Configure Gemini with premium settings
genai.configure(api_key=settings.gemini_api_key)


class ScamDetectorService:
    """Service for detecting scam intent in messages - Optimized for premium Gemini"""
    
    def __init__(self):
        # Use premium model with optimized generation config
        # Use a compact generation configuration for faster detection responses
        self.model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config={
                "temperature": 0.0,  # Deterministic for detection
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": settings.gemini_max_output_tokens,
                "candidate_count": 1,
            }
        )
        
    def _get_cache_key(self, message: str, history_length: int) -> str:
        """Generate cache key for scam detection"""
        content = f"{message}:{history_length}"
        return f"scam_detect:{hashlib.md5(content.encode()).hexdigest()}"
        
    async def detect_scam(
        self,
        current_message: str,
        conversation_history: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Tuple[bool, float, List[str]]:
        """
        Detect if a message contains scam intent with caching
        
        Args:
            current_message: The latest message to analyze
            conversation_history: Previous messages in the conversation
            metadata: Additional context (channel, language, locale)
            
        Returns:
            Tuple of (scam_detected, confidence, indicators)
        """
        # Check cache first for performance
        if settings.enable_caching:
            cache_key = self._get_cache_key(current_message, len(conversation_history))
            cached_result = await cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for scam detection")
                return cached_result
        
        try:
            # Build context from conversation history
            context = ""
            if conversation_history:
                context = "Previous conversation:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages for context
                    sender = msg.get("sender", "unknown")
                    text = msg.get("text", "")
                    context += f"{sender}: {text}\n"
            
            # Create detection prompt - optimized for premium model
            prompt = f"""You are an expert scam detection system with advanced pattern recognition. Analyze the message with high precision.

Channel: {metadata.get('channel', 'Unknown')}
Language: {metadata.get('language', 'Unknown')}
Locale: {metadata.get('locale', 'Unknown')}

IMPORTANT: Detect scams in ALL languages including Hinglish (Hindi written in English) and Gujarati-English (Gujarati written in English).

## TRANSLITERATED INDIAN LANGUAGES EXAMPLES:

HINGLISH SCAM EXAMPLES:
- "Aapka account block hone wala hai. Abhi OTP share karo" → SCAM (account threat + OTP request)
- "Tumhara card expire ho gaya. Link pe click karke update karo" → SCAM (urgency + link)
- "SBI bank se bol raha hun. Aapka KYC pending hai" → SCAM (impersonation + urgency)
- "Aapko 25 lakh ka prize mila hai" → SCAM (prize scam)
- "Account verify karne ke liye details bhejo" → SCAM (info request)

GUJARATI-ENGLISH SCAM EXAMPLES:
- "Tamaru account block thava walu che. Atyare OTP share karo" → SCAM (account threat + OTP)
- "Tamaro card expire thai gayo. Link par click kari update karo" → SCAM (urgency + link)
- "SBI bank thi bolu chu. Tamaru KYC pending che" → SCAM (impersonation + urgency)
- "Tamne 25 lakh no prize mali che" → SCAM (prize scam)
- "Account verify karva mate details mokalo" → SCAM (info request)

COMMON TRANSLITERATED KEYWORDS TO DETECT:
- Hindi/Hinglish: "aapka", "tumhara", "account", "bank", "OTP", "card", "block", "expire", "karo", "bhejo", "share"
- Gujarati-English: "tamaru", "tamaro", "account", "bank", "OTP", "card", "block", "expire", "karo", "mokalo", "share"

{context}

Current message to analyze: "{current_message}"

Scam indicators to check:
HIGH SEVERITY:
- Requests for OTP, PIN, CVV, passwords, or sensitive credentials (in ANY language)
- Threats of immediate account suspension/blocking
- Impersonation of banks, government, or trusted entities
- Requests for immediate money transfers or payments
- Sharing of suspicious payment links or account details

MEDIUM SEVERITY:
- Urgency and time pressure tactics
- Promises of prizes, refunds, or unrealistic offers
- Requests to click suspicious links
- Poor grammar in professional contexts
- Requests for personal information verification

Analyze comprehensively and respond ONLY with valid JSON:
{{
    "is_scam": true/false,
    "confidence": 0.0-1.0,
    "indicators": ["indicator1", "indicator2"],
    "reasoning": "brief technical explanation",
    "severity": "high/medium/low"
}}"""

            # Generate response with retry logic
            for attempt in range(settings.gemini_max_retries):
                try:
                    response = self.model.generate_content(
                        prompt,
                        request_options={'timeout': settings.gemini_timeout}
                    )
                    response_text = response.text.strip()
                    break
                except Exception as e:
                    if attempt == settings.gemini_max_retries - 1:
                        raise
                    logger.warning(f"Gemini API attempt {attempt + 1} failed: {e}")
                    continue
            
            # Parse JSON response - clean up markdown and trailing commas
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            # Fix common JSON issues: trailing commas, missing quotes
            import re
            # Remove trailing commas before ] or }
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            
            # ENHANCED: Try to extract partial JSON fields before parsing (same as ai_agent.py)
            partial_fields = {}
            for field in ['is_scam', 'confidence', 'indicators', 'reasoning', 'severity']:
                # Try to extract each field value
                if f'"{field}"' in response_text or f"'{field}'" in response_text:
                    # Boolean fields
                    if field == 'is_scam':
                        match = re.search(rf'["\']is_scam["\']\s*:\s*(true|false)', response_text, re.IGNORECASE)
                        if match:
                            partial_fields[field] = match.group(1).lower() == 'true'
                    # Float fields
                    elif field == 'confidence':
                        match = re.search(rf'["\']confidence["\']\s*:\s*([\d.]+)', response_text)
                        if match:
                            partial_fields[field] = float(match.group(1))
                    # Array fields
                    elif field == 'indicators':
                        match = re.search(rf'["\']indicators["\']\s*:\s*\[([^\]]*)', response_text)
                        if match:
                            # Extract array items
                            items = re.findall(r'["\']([^"\']+)["\']', match.group(1))
                            partial_fields[field] = items
                    # String fields
                    else:
                        match = re.search(rf'["\']' + field + rf'["\']\s*:\s*["\']([^"\']*)', response_text)
                        if match:
                            partial_fields[field] = match.group(1)
            
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)
                    response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError:
                        # RECOVERY: Use partial fields if we extracted any
                        if partial_fields:
                            logger.warning(f"⚠️ JSON truncated. Using {len(partial_fields)} extracted fields: {list(partial_fields.keys())}")
                            result = {
                                'is_scam': partial_fields.get('is_scam', False),
                                'confidence': partial_fields.get('confidence', 0.0),
                                'indicators': partial_fields.get('indicators', []),
                                'reasoning': partial_fields.get('reasoning', 'Recovered from truncated JSON'),
                                'severity': partial_fields.get('severity', 'low')
                            }
                        else:
                            raise
                else:
                    # FINAL RECOVERY: Use partial fields or raise
                    if partial_fields:
                        logger.warning(f"⚠️ No JSON structure found. Using {len(partial_fields)} extracted fields.")
                        result = {
                            'is_scam': partial_fields.get('is_scam', False),
                            'confidence': partial_fields.get('confidence', 0.0),
                            'indicators': partial_fields.get('indicators', []),
                            'reasoning': partial_fields.get('reasoning', 'Recovered from malformed response'),
                            'severity': partial_fields.get('severity', 'low')
                        }
                    else:
                        raise
            
            is_scam = result.get("is_scam", False)
            confidence = result.get("confidence", 0.0)
            indicators = result.get("indicators", [])
            reasoning = result.get("reasoning", "")
            severity = result.get("severity", "low")
            
            logger.info(
                f"Scam detection: {is_scam} (confidence: {confidence}, severity: {severity}) - {reasoning}"
            )
            
            detection_result = (is_scam, confidence, indicators)
            
            # Cache the result
            if settings.enable_caching:
                await cache.set(cache_key, detection_result, ttl=settings.cache_ttl)
            
            return detection_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            logger.error(f"Response text: {response_text}")
            # Fallback to keyword-based detection
            return self._fallback_detection(current_message)
        except Exception as e:
            logger.error(f"Error in scam detection: {str(e)}", exc_info=True)
            # Fallback to keyword-based detection
            return self._fallback_detection(current_message)
    
    def _fallback_detection(self, message: str) -> Tuple[bool, float, List[str]]:
        """Fallback keyword-based scam detection with multi-lingual support"""
        message_lower = message.lower()
        
        # High-priority scam keywords (almost certain scam)
        high_priority_keywords = {
            "share otp": 0.95,
            "share pin": 0.95,
            "share cvv": 0.95,
            "share password": 0.95,
            "account blocked": 0.9,
            "account suspended": 0.9,
            "account compromised": 0.9,
            "verify immediately": 0.85,
            "urgent": 0.7,
            # Hinglish keywords
            "otp share karo": 0.95,
            "otp bhejo": 0.95,
            "otp do": 0.95,
            "account block": 0.9,
            "card block": 0.9,
            "aapka account": 0.75,
            "tumhara account": 0.75,
            # Gujarati-English keywords
            "otp share karo": 0.95,
            "otp mokalo": 0.95,
            "account block": 0.9,
            "card block": 0.9,
            "tamaru account": 0.75,
            "tamaro card": 0.75,
        }
        
        # Medium-priority keywords
        medium_priority_keywords = {
            "click here": 0.6,
            "upi id": 0.65,
            "bank account": 0.6,
            "congratulations": 0.6,
            "won prize": 0.7,
            "refund": 0.55,
            "expire": 0.6,
            "suspend": 0.65,
            "blocked": 0.65,
            "verify": 0.55,
            "immediately": 0.6,
            # Hinglish keywords
            "link pe click": 0.7,
            "click karo": 0.7,
            "prize mila": 0.7,
            "jeet gaye": 0.7,
            "kyc pending": 0.65,
            "update karo": 0.6,
            "expire ho": 0.6,
            "band ho jayega": 0.65,
            # Gujarati-English keywords
            "link par click": 0.7,
            "click karo": 0.7,
            "prize mali": 0.7,
            "jiti gaya": 0.7,
            "kyc pending": 0.65,
            "update karo": 0.6,
            "expire thai": 0.6,
            "band thai jashe": 0.65,
        }
        
        detected_indicators = []
        max_confidence = 0.0
        
        # Check high priority first
        for keyword, confidence in high_priority_keywords.items():
            if keyword in message_lower:
                detected_indicators.append(keyword.replace(" ", "_"))
                max_confidence = max(max_confidence, confidence)
        
        # Check medium priority
        for keyword, confidence in medium_priority_keywords.items():
            if keyword in message_lower:
                detected_indicators.append(keyword.replace(" ", "_"))
                max_confidence = max(max_confidence, confidence)
        
        is_scam = max_confidence >= 0.6
        
        logger.warning(f"Using fallback detection: is_scam={is_scam}, confidence={max_confidence}, indicators={detected_indicators}")
        
        return is_scam, max_confidence, detected_indicators
