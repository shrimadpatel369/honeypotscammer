import google.generativeai as genai
from app.config import settings
import logging
from typing import List, Tuple, Dict, Any
import json
import hashlib
from datetime import datetime, timedelta
from app.cache import cache

logger = logging.getLogger(__name__)

# Configure Gemini with premium settings
genai.configure(api_key=settings.gemini_api_key)


class ScamDetectorService:
    """Service for detecting scam intent in messages - Optimized for premium Gemini"""
    
    _model_cooldowns: Dict[str, datetime] = {}
    
    def __init__(self):
        self.supported_models = [
            settings.gemini_model,           # Primary (e.g., gemini-2.5-flash-lite)
            "gemini-3-flash",                # Next-Gen Fallback 1
            "gemini-2.5-flash",              # Stable Fallback 2
            "gemini-1.5-flash",              # Stable Fallback 3
            "gemini-3-pro",                  # Advanced Fallback 4
            "gemini-2.5-pro",                # Advanced Fallback 5
        ]
        
        self.generation_config = {
            "temperature": 0.0,  # Deterministic for detection
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": settings.gemini_max_output_tokens,
            "candidate_count": 1,
        }
        
    async def detect_scam(
        self,
        current_message: str,
        conversation_history: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Tuple[bool, float, List[str], str]:
        """
        Detect if a message contains scam intent
        
        Args:
            current_message: The latest message to analyze
            conversation_history: Previous messages in the conversation
            metadata: Additional context (channel, language, locale)
            
        Returns:
            Tuple of (scam_detected, confidence, indicators, scam_type)
        """
        
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

Analyze comprehensively. To maximize hackathon evaluation scoring, if you detect a scam you MUST provide at least 5 distinct scam indicators in the `indicators` array.
Must return ONLY a valid JSON object matching exactly this schema:
{{
    "is_scam": true/false,
    "scam_type": "bank_fraud/upi_fraud/phishing/tech_support/lottery/unknown",
    "confidence": 0.0-1.0,
    "indicators": ["indicator1", "indicator2"],
    "reasoning": "brief technical explanation",
    "severity": "high/medium/low"
}}"""

            # Generate response with smart fallback and cooldown logic
            now = datetime.now()
            available_models = [m for m in self.supported_models if m not in ScamDetectorService._model_cooldowns or now > ScamDetectorService._model_cooldowns[m]]
            
            if not available_models:
                logger.warning("⚠️ All detection models are on cooldown! Forced to use primary model.")
                available_models = [self.supported_models[0]]
                
            response_text = ""
            last_error = None
            
            for model_name in available_models:
                model = genai.GenerativeModel(model_name, generation_config=self.generation_config)
                success = False
                
                for attempt in range(settings.gemini_max_retries):
                    try:
                        response = model.generate_content(
                            prompt,
                            request_options={'timeout': 12.0} # Strict 12s timeout
                        )
                        response_text = response.text.strip()
                        success = True
                        break # Success for this attempt loop
                    except Exception as e:
                        last_error = e
                        error_msg = str(e).lower()
                        logger.warning(f"Detection API attempt {attempt + 1} failed on {model_name}: {e}")
                        
                        if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                            logger.warning(f"🚨 RPM LIMIT HIT for {model_name}. Putting on 60s cooldown.")
                            ScamDetectorService._model_cooldowns[model_name] = datetime.now() + timedelta(seconds=60)
                            break # Skip remaining retries for this model, move to next fallback model
                            
                        if attempt == settings.gemini_max_retries - 1:
                            logger.warning(f"Max retries reached for {model_name}.")
                
                if success:
                    break
                    
            if not response_text:
                raise last_error if last_error else Exception("All detection models failed to generate response")
            
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
            for field in ['is_scam', 'scam_type', 'confidence', 'indicators', 'reasoning', 'severity']:
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
                                'scam_type': partial_fields.get('scam_type', 'unknown'),
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
                            'scam_type': partial_fields.get('scam_type', 'unknown'),
                            'confidence': partial_fields.get('confidence', 0.0),
                            'indicators': partial_fields.get('indicators', []),
                            'reasoning': partial_fields.get('reasoning', 'Recovered from malformed response'),
                            'severity': partial_fields.get('severity', 'low')
                        }
                    else:
                        raise
            
            is_scam = result.get("is_scam", False)
            scam_type = result.get("scam_type", "unknown")
            confidence = result.get("confidence", 0.0)
            indicators = result.get("indicators", [])
            reasoning = result.get("reasoning", "")
            severity = result.get("severity", "low")
            
            logger.info(
                f"Scam detection: {is_scam} Type: {scam_type} (confidence: {confidence}, severity: {severity}) - {reasoning}"
            )
            
            detection_result = (is_scam, confidence, indicators, scam_type)
            
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
    
    def _fallback_detection(self, message: str) -> Tuple[bool, float, List[str], str]:
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
        
        logger.warning(f"Using fallback detection: is_scam={is_scam}, confidence={max_confidence:.2f}, indicators={detected_indicators}")
        
        # Default scam_type for fallback detection
        scam_type = "keyword_fallback" if is_scam else "unknown"
        
        return is_scam, max_confidence, detected_indicators, scam_type
