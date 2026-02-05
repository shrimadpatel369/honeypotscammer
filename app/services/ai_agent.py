import google.generativeai as genai
from app.config import settings
from app.services.training_manager import training_manager
import logging
from typing import List, Dict, Any, Tuple
import json
import random
import re
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Configure Gemini with premium settings
genai.configure(api_key=settings.gemini_api_key)


class AIAgentService:
    """Advanced AI Agent for engaging with scammers - Human-like behavior with dynamic responses"""
    
    def __init__(self):
        # Comprehensive list of v1beta API compatible models (as of Feb 2026)
        # Ordered by preference: Latest Gemini 3 > Gemini 2.5 > Gemini 2.0 > Gemini 1.5
        self.supported_models = [
            # Gemini 3 (Latest - Preview models)
            "gemini-3-pro-preview",          # Most intelligent multimodal model, 1M token context
            "gemini-3-flash-preview",        # Fast Gemini 3, balanced performance
            
            # Gemini 2.5 (Production - Best for complex reasoning)
            "gemini-2.5-pro",                # Complex reasoning and coding, 1M token context
            "gemini-2.5-flash",              # Balance of intelligence and latency
            "gemini-2.5-flash-lite",         # Efficient high-frequency tasks
            
            # Gemini 2.0 (Experimental - Will retire March 31, 2026)
            "gemini-2.0-flash-exp",          # Latest experimental flash model
            
            # Gemini 1.5 (Stable fallbacks - No retirement date)
            "gemini-1.5-pro",                # Stable production model
            "gemini-1.5-flash",              # Fast and efficient
            "gemini-1.5-pro-latest",         # Auto-updated to latest 1.5 pro
            "gemini-1.5-flash-latest",       # Auto-updated to latest 1.5 flash
            "gemini-pro",                    # Legacy fallback (last resort)
        ]
        
        # Use configured model or first supported model (no testing during init to avoid timeout)
        self.current_model = settings.gemini_model
        
        # Validate configured model
        if self.current_model in ["gemini-pro-old", "gemini-1.0-pro"]:
            logger.warning(f"⚠️ Configured model '{self.current_model}' is deprecated. Using gemini-2.5-pro instead.")
            self.current_model = "gemini-2.5-pro"
        
        logger.info(f"✅ Initializing with model: {self.current_model}")
        logger.info(f"📋 Fallback models available: {len(self.supported_models)} models")
        
        # Use premium model with high creativity settings for natural conversation
        self.model = genai.GenerativeModel(
            self.current_model,
            generation_config={
                "temperature": 0.85,  # High temperature for very creative, human-like responses
                "top_p": 0.95,
                "top_k": 60,  # Increased for more variety
                "max_output_tokens": 1024,  # More room for natural, detailed responses
            }
        )
        
        # Multi-lingual support - language detection and natural responses
        self.supported_languages = {
            "english": {
                "code": "en",
                "detect_keywords": ["the", "is", "are", "you", "your", "account", "bank"],
                "name": "English"
            },
            "hindi": {
                "code": "hi",
                "detect_keywords": ["आप", "है", "हैं", "का", "की", "में", "से", "कर", "खाता", "बैंक"],
                "name": "हिन्दी"
            },
            "gujarati": {
                "code": "gu",
                "detect_keywords": ["તમે", "છે", "છો", "ના", "ની", "માં", "થી", "કરો", "ખાતું", "બેંક"],
                "name": "ગુજરાતી"
            },
            "marathi": {
                "code": "mr",
                "detect_keywords": ["तुम्ही", "आहे", "आहेत", "च्या", "ची", "मध्ये", "पासून", "करा", "खाते", "बँक"],
                "name": "मराठी"
            },
            "tamil": {
                "code": "ta",
                "detect_keywords": ["நீங்கள்", "உள்ளது", "உள்ளன", "இன்", "ஆக", "இல்", "இருந்து", "செய்", "கணக்கு", "வங்கி"],
                "name": "தமிழ்"
            },
            "telugu": {
                "code": "te",
                "detect_keywords": ["మీరు", "ఉంది", "ఉన్నారు", "యొక్క", "లో", "నుండి", "చేయండి", "ఖాతా", "బ్యాంకు"],
                "name": "తెలుగు"
            },
            "bengali": {
                "code": "bn",
                "detect_keywords": ["আপনি", "আছে", "আছেন", "এর", "তে", "থেকে", "করুন", "অ্যাকাউন্ট", "ব্যাংক"],
                "name": "বাংলা"
            },
            "punjabi": {
                "code": "pa",
                "detect_keywords": ["ਤੁਸੀਂ", "ਹੈ", "ਹੋ", "ਦਾ", "ਦੀ", "ਵਿੱਚ", "ਤੋਂ", "ਕਰੋ", "ਖਾਤਾ", "ਬੈਂਕ"],
                "name": "ਪੰਜਾਬੀ"
            },
            "kannada": {
                "code": "kn",
                "detect_keywords": ["ನೀವು", "ಇದೆ", "ಇದ್ದಾರೆ", "ಯ", "ರ", "ನಲ್ಲಿ", "ಇಂದ", "ಮಾಡಿ", "ಖಾತೆ", "ಬ್ಯಾಂಕ್"],
                "name": "ಕನ್ನಡ"
            },
            "urdu": {
                "code": "ur",
                "detect_keywords": ["آپ", "ہے", "ہیں", "کا", "کی", "میں", "سے", "کریں", "اکاؤنٹ", "بینک"],
                "name": "اردو"
            }
        }
        
        # Language-specific speech patterns and expressions
        self.language_patterns = {
            "hindi": {
                "fillers": ["अरे", "हाँ", "अच्छा", "ठीक है", "देखो"],
                "worry": ["अरे बाप रे", "हे भगवान", "क्या करूं", "बहुत चिंता हो रही है"],
                "confusion": ["समझ नहीं आया", "क्या मतलब", "कैसे", "फिर से बताइए"],
                "agreement": ["हाँ ठीक है", "अच्छा", "जी हाँ", "बिलकुल"],
                "typo_patterns": {"है": "हे", "में": "मे", "हैं": "है", "करूं": "करु"}
            },
            "gujarati": {
                "fillers": ["અરે", "હા", "સારું", "ઠીક છે", "જુઓ"],
                "worry": ["અરે બાપ રે", "હે ભગવાન", "શું કરું", "ઘણી ચિંતા છે"],
                "confusion": ["સમજાયું નહીં", "શું મતલબ", "કેવી રીતે", "ફરી કહો"],
                "agreement": ["હા બરાબર", "સારું", "હા જી", "ચોક્કસ"],
                "typo_patterns": {"છે": "છ", "માં": "મા", "છો": "છ", "કરું": "કરુ"}
            },
            "marathi": {
                "fillers": ["अरे", "हो", "बरं", "ठीक आहे", "बघा"],
                "worry": ["अरे देवा", "काय करू", "खूप चिंता होतेय"],
                "confusion": ["समजलं नाही", "काय म्हणता", "कसं", "पुन्हा सांगा"],
                "agreement": ["हो बरोबर", "ठीक आहे", "होय", "नक्की"],
                "typo_patterns": {"आहे": "आह", "मध्ये": "मधे", "करू": "करु"}
            },
            "tamil": {
                "fillers": ["சரி", "ஆமா", "பார்", "ஓகே"],
                "worry": ["அய்யோ", "கடவுளே", "என்ன செய்வேன்", "ரொம்ப கவலையா இருக்கு"],
                "confusion": ["புரியலை", "என்ன அர்த்தம்", "எப்படி", "மறுபடி சொல்லுங்க"],
                "agreement": ["சரி", "ஆமா", "ஓகே", "நிச்சயமா"],
                "typo_patterns": {}
            },
            "telugu": {
                "fillers": ["అరే", "అవును", "సరే", "చూడు"],
                "worry": ["అయ్యో", "దేవుడా", "ఏం చేస్తాను", "చాలా ఆందోళనగా ఉంది"],
                "confusion": ["అర్థం కాలేదు", "ఏమిటి అర్థం", "ఎలా", "మళ్ళీ చెప్పండి"],
                "agreement": ["అవును సరే", "ఓకే", "తప్పకుండా"],
                "typo_patterns": {}
            },
            "bengali": {
                "fillers": ["আরে", "হ্যাঁ", "ঠিক আছে", "দেখো"],
                "worry": ["আরে বাবা", "ভগবান", "কি করব", "অনেক চিন্তা হচ্ছে"],
                "confusion": ["বুঝলাম না", "কি মানে", "কিভাবে", "আবার বলুন"],
                "agreement": ["হ্যাঁ ঠিক", "আচ্ছা", "অবশ্যই"],
                "typo_patterns": {"আছে": "আছ", "করুন": "করু"}
            },
            "punjabi": {
                "fillers": ["ਓਏ", "ਹਾਂ", "ਠੀਕ ਆ", "ਵੇਖੋ"],
                "worry": ["ਓਏ ਰੱਬਾ", "ਕੀ ਕਰਾਂ", "ਬਹੁਤ ਚਿੰਤਾ ਆ"],
                "confusion": ["ਸਮਝ ਨਹੀਂ ਆਈ", "ਕੀ ਮਤਲਬ", "ਕਿਵੇਂ", "ਫੇਰ ਦੱਸੋ"],
                "agreement": ["ਹਾਂ ਠੀਕ", "ਬਿਲਕੁਲ", "ਪੱਕਾ"],
                "typo_patterns": {}
            },
            "kannada": {
                "fillers": ["ಹೌದು", "ಸರಿ", "ನೋಡು", "ಓಕೆ"],
                "worry": ["ಅಯ್ಯೋ", "ದೇವರೇ", "ಏನು ಮಾಡಲಿ", "ತುಂಬಾ ಚಿಂತೆ ಆಗ್ತಿದೆ"],
                "confusion": ["ಅರ್ಥವಾಗಲಿಲ್ಲ", "ಏನು ಅರ್ಥ", "ಹೇಗೆ", "ಮತ್ತೆ ಹೇಳಿ"],
                "agreement": ["ಹೌದು ಸರಿ", "ಖಂಡಿತ"],
                "typo_patterns": {}
            },
            "urdu": {
                "fillers": ["اچھا", "ہاں", "ٹھیک ہے", "دیکھو"],
                "worry": ["یا اللہ", "کیا کروں", "بہت فکر ہو رہی ہے"],
                "confusion": ["سمجھ نہیں آیا", "کیا مطلب", "کیسے", "پھر بتائیں"],
                "agreement": ["ہاں ٹھیک", "بالکل", "یقیناً"],
                "typo_patterns": {"ہے": "ھے", "میں": "مے", "کریں": "کرے"}
            }
        }
        
        # Advanced persona profiles with psychological traits and high creativity
        self.personas = {
            "elderly_trusting": {
                "description": "You are a 68-year-old retired teacher who trusts authority but gets anxious about financial matters. You're polite but sometimes confused by technology. You often repeat yourself and ask for confirmation.",
                "traits": ["polite", "anxious", "trusting", "confused_by_tech", "repetitive"],
                "vocabulary": ["dear", "goodness", "oh my", "I'm not sure", "could you please", "let me see", "I don't quite understand"],
                "typo_rate": 0.15,
                "response_time": "slow",
                "temperature": 0.75,  # More natural hesitation and confusion
                "quirks": ["types in all caps sometimes", "asks multiple questions", "mentions family"]
            },
            "young_busy": {
                "description": "You are a 26-year-old working professional who's always busy and multitasking. You're somewhat tech-savvy but can be impulsive under pressure. You use casual language and shortcuts.",
                "traits": ["impatient", "multitasking", "slightly_tech_savvy", "impulsive", "casual"],
                "vocabulary": ["ok", "sure", "wait what", "hold on", "quickly", "omg", "wtf", "lol", "k"],
                "typo_rate": 0.20,
                "response_time": "fast",
                "temperature": 0.9,  # Very dynamic and impulsive
                "quirks": ["uses abbreviations", "sends multiple short messages", "mentions work stress"]
            },
            "cautious_middle_aged": {
                "description": "You are a 45-year-old small business owner who's naturally skeptical but can be worn down with persistence. You ask lots of questions and want everything explained clearly.",
                "traits": ["skeptical", "methodical", "business_minded", "persistent_questioner", "detail_oriented"],
                "vocabulary": ["I need to understand", "wait a moment", "that doesn't sound right", "let me check", "explain this to me"],
                "typo_rate": 0.08,
                "response_time": "medium",
                "temperature": 0.75,  # Measured but creative questioning
                "quirks": ["asks for documentation", "wants to verify everything", "mentions business experience"]
            },
            "naive_trusting": {
                "description": "You are a 35-year-old person who believes official-looking messages and is eager to comply to avoid problems. You're helpful but gullible and often overshare.",
                "traits": ["gullible", "helpful", "compliant", "worried_about_consequences", "oversharing"],
                "vocabulary": ["oh no", "of course", "right away", "I'll do that", "thank you for helping", "I hope everything is ok"],
                "typo_rate": 0.12,
                "response_time": "medium",
                "temperature": 0.8,  # Natural eagerness and worry
                "quirks": ["shares too much information", "apologizes frequently", "mentions personal life"]
            },
            "tech_aware_suspicious": {
                "description": "You are a 32-year-old IT professional who knows about scams but is playing along to see what happens. You ask technical questions that seem innocent but are probing.",
                "traits": ["tech_savvy", "analytical", "probing", "playing_dumb", "methodical"],
                "vocabulary": ["interesting", "how does that work", "which system", "can you clarify", "that's unusual"],
                "typo_rate": 0.03,
                "response_time": "varied",
                "temperature": 0.85,  # Creative technical probing
                "quirks": ["asks technical details", "mentions work in IT", "seems to know more than they let on"]
            }
        }
        
        # Emotional states that affect responses
        self.emotional_states = {
            "worried": ["I'm really concerned about this", "This is worrying me", "I'm getting anxious", "This makes me nervous"],
            "confused": ["I don't understand", "This is confusing", "Can you explain again?", "I'm lost", "What do you mean?"],
            "eager": ["I want to fix this quickly", "Let's resolve this", "I'm ready to help", "Just tell me what to do"],
            "suspicious": ["Something seems off", "This doesn't feel right", "I'm not sure about this", "That sounds strange"],
            "frustrated": ["This is taking too long", "I'm getting frustrated", "Why is this so complicated?", "This is stressing me out"]
        }
        
        # Human speech patterns and fillers
        self.speech_patterns = {
            "fillers": ["um", "uh", "well", "so", "like", "you know", "I mean"],
            "agreement": ["yeah", "ok", "right", "I see", "gotcha", "alright"],
            "hesitation": ["I'm not sure but", "maybe", "I think", "probably", "I guess"],
            "emphasis": ["really", "actually", "definitely", "totally", "absolutely"]
        }
        
        # Realistic conversation starters and transitions
        self.conversation_flows = {
            "surprise": ["Wait, what?", "Hold on", "What do you mean?", "I don't get it"],
            "concern": ["Oh no", "That's not good", "This is bad", "I'm worried"],
            "compliance": ["Ok I'll do it", "Sure, let me try", "Alright", "I can do that"],
            "questioning": ["But why?", "How come?", "What for?", "Is that normal?"]
        }
        
        # Information extraction strategies
        self.extraction_strategies = {
            "account_details": ["Which bank is this?", "What's the exact account number?", "Can you spell that for me?"],
            "verification_codes": ["What code should I enter?", "The system is asking for what exactly?", "Is this the right format?"],
            "personal_info": ["What details do you need from me?", "Should I provide my full name?", "What about my address?"],
            "payment_methods": ["How exactly does this work?", "What payment app should I use?", "Which UPI ID should I send to?"],
            "urgency_tactics": ["How long do I have?", "What happens if I'm late?", "Is this really urgent?"],
            "authority_claims": ["Are you really from the bank?", "What's your employee ID?", "Can I call your office to verify?"]
        }
        
        # Conversation memory for consistency
        self.conversation_memory = defaultdict(dict)
        
        # Response variation patterns
        self.last_responses = defaultdict(list)
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the input text"""
        text_lower = text.lower()
        
        # Count matches for each language
        language_scores = {}
        for lang_name, lang_info in self.supported_languages.items():
            score = 0
            for keyword in lang_info["detect_keywords"]:
                if keyword in text or keyword.lower() in text_lower:
                    score += 1
            language_scores[lang_name] = score
        
        # Return language with highest score, default to english
        detected = max(language_scores.items(), key=lambda x: x[1])
        if detected[1] > 0:
            logger.info(f"🌐 Detected language: {detected[0]} (score: {detected[1]})")
            return detected[0]
        
        return "english"
    
    def _analyze_conversation_context(self, conversation_history: List[Dict[str, Any]], current_message: str) -> Dict[str, Any]:
        """Analyze conversation to determine optimal response strategy"""
        message_count = len(conversation_history)
        
        # Analyze scammer tactics
        scammer_messages = [msg for msg in conversation_history if msg.get("sender") == "scammer"]
        all_scammer_text = " ".join([msg.get("text", "") for msg in scammer_messages]) + " " + current_message
        
        # Detect urgency tactics
        urgency_keywords = ["urgent", "immediately", "now", "quickly", "expire", "block", "suspend"]
        urgency_detected = any(keyword in all_scammer_text.lower() for keyword in urgency_keywords)
        
        # Detect authority claims
        authority_keywords = ["bank", "government", "police", "officer", "official", "department"]
        authority_claimed = any(keyword in all_scammer_text.lower() for keyword in authority_keywords)
        
        # Detect information requests
        info_keywords = ["otp", "pin", "password", "account", "details", "verify", "confirm"]
        info_requested = any(keyword in all_scammer_text.lower() for keyword in info_keywords)
        
        # Detect technical elements
        tech_keywords = ["link", "app", "download", "install", "click", "upi", "payment"]
        tech_involved = any(keyword in all_scammer_text.lower() for keyword in tech_keywords)
        
        return {
            "message_count": message_count,
            "urgency_detected": urgency_detected,
            "authority_claimed": authority_claimed,
            "info_requested": info_requested,
            "tech_involved": tech_involved,
            "conversation_length": "short" if message_count < 5 else "medium" if message_count < 15 else "long"
        }
    
    def _select_dynamic_persona(self, context_analysis: Dict[str, Any], session_id: str) -> Tuple[str, Dict[str, Any]]:
        """Dynamically select persona based on conversation analysis and maintain consistency"""
        # Check if we already have a persona for this session
        if session_id in self.conversation_memory and "persona" in self.conversation_memory[session_id]:
            persona_key = self.conversation_memory[session_id]["persona"]
            return persona_key, self.personas[persona_key]
        
        # Select based on context
        if context_analysis["authority_claimed"] and context_analysis["urgency_detected"]:
            persona_key = "elderly_trusting"  # Most vulnerable to authority + urgency
        elif context_analysis["tech_involved"]:
            if context_analysis["message_count"] < 3:
                persona_key = "naive_trusting"  # Quick to trust tech messages initially
            else:
                persona_key = "tech_aware_suspicious"  # Becomes more analytical
        elif context_analysis["info_requested"]:
            persona_key = "cautious_middle_aged"  # Asks questions about info requests
        else:
            persona_key = "young_busy"  # Default for general interactions
        
        # Store for consistency
        self.conversation_memory[session_id]["persona"] = persona_key
        return persona_key, self.personas[persona_key]
    
    def _generate_human_like_variations(self, base_response: str, persona: Dict[str, Any], language: str = "english") -> str:
        """Add extensive human-like variations to responses with multi-lingual support"""
        response = base_response
        
        # Get language-specific patterns
        lang_patterns = self.language_patterns.get(language, {})
        
        # Add language-specific fillers
        if lang_patterns and "fillers" in lang_patterns and random.random() < 0.3:
            filler = random.choice(lang_patterns["fillers"])
            if random.random() < 0.5:
                response = f"{filler} {response}"
            else:
                # Insert filler in the middle for natural flow
                words = response.split()
                if len(words) > 3:
                    insert_pos = random.randint(1, min(3, len(words)-1))
                    words.insert(insert_pos, filler)
                    response = " ".join(words)
        
        # For English, add speech fillers
        if language == "english" and random.random() < 0.3:
            filler = random.choice(self.speech_patterns["fillers"])
            if random.random() < 0.5:
                response = f"{filler}, {response.lower()}"
            else:
                # Insert filler in the middle
                words = response.split()
                if len(words) > 3:
                    insert_pos = random.randint(1, len(words)-1)
                    words.insert(insert_pos, filler)
                    response = " ".join(words)
        
        # Add persona-specific vocabulary
        vocab = persona.get("vocabulary", [])
        if vocab and random.random() < 0.4:  # 40% chance for persona words
            response = f"{random.choice(vocab)}, {response.lower()}"
        
        # Add emphasis words for English
        if language == "english" and random.random() < 0.25:
            emphasis = random.choice(self.speech_patterns["emphasis"])
            response = response.replace(" is ", f" is {emphasis} ")
            response = response.replace(" was ", f" was {emphasis} ")
        
        # Add hesitation for cautious personas
        if "cautious" in persona.get("traits", []) and random.random() < 0.3:
            if language == "english":
                hesitation = random.choice(self.speech_patterns["hesitation"])
                response = f"{hesitation} {response.lower()}"
        
        # Add language-specific typos
        typo_rate = persona.get("typo_rate", 0.05)
        if random.random() < typo_rate:
            if lang_patterns and "typo_patterns" in lang_patterns:
                response = self._add_language_specific_typo(response, lang_patterns["typo_patterns"])
            else:
                response = self._add_realistic_typo(response)
        
        # Add emotional elements based on context
        if random.random() < 0.25:  # 25% chance for emotional expression
            if lang_patterns and random.random() < 0.6:
                # Use language-specific emotions
                emotion_type = random.choice(["worry", "confusion", "agreement"])
                if emotion_type in lang_patterns:
                    emotional_phrase = random.choice(lang_patterns[emotion_type])
                    if random.random() < 0.5:
                        response = f"{emotional_phrase} {response}"
                    else:
                        response = f"{response} {emotional_phrase}"
            else:
                # Use English emotions
                emotion = random.choice(list(self.emotional_states.keys()))
                emotional_phrase = random.choice(self.emotional_states[emotion])
                if random.random() < 0.5:
                    response = f"{emotional_phrase}. {response}"
                else:
                    response = f"{response} {emotional_phrase}."
        
        # Add quirks specific to persona
        quirks = persona.get("quirks", [])
        if quirks and random.random() < 0.2:  # 20% chance for persona quirks
            if "types in all caps sometimes" in quirks and random.random() < 0.3:
                words = response.split()
                if words:
                    # Capitalize 1-2 words for emphasis
                    cap_count = random.randint(1, min(2, len(words)))
                    cap_indices = random.sample(range(len(words)), cap_count)
                    for idx in cap_indices:
                        words[idx] = words[idx].upper()
                    response = " ".join(words)
            
            elif "uses abbreviations" in quirks and language == "english" and random.random() < 0.4:
                # Replace some words with abbreviations
                response = response.replace(" you ", " u ")
                response = response.replace(" are ", " r ")
                response = response.replace(" to ", " 2 ")
                response = response.replace(" for ", " 4 ")
        
        # Add natural conversation flow elements
        if language == "english" and random.random() < 0.2:
            if "eager" in persona.get("traits", []):
                flow_starter = random.choice(self.conversation_flows["compliance"])
                response = f"{flow_starter}. {response}"
            elif "suspicious" in persona.get("traits", []):
                flow_starter = random.choice(self.conversation_flows["questioning"])
                response = f"{response} {flow_starter}"
        
        return response
    
    def _add_language_specific_typo(self, text: str, typo_patterns: Dict[str, str]) -> str:
        """Add language-specific typos based on common mistakes"""
        if not typo_patterns:
            return text
        
        words = text.split()
        for i, word in enumerate(words):
            if word in typo_patterns and random.random() < 0.7:
                words[i] = typo_patterns[word]
                break
        
        return " ".join(words)
    
    def _add_realistic_typo(self, text: str) -> str:
        """Add realistic typos that humans commonly make"""
        common_typos = {
            "the": "teh", "and": "adn", "you": "yuo", "that": "taht",
            "what": "waht", "with": "wtih", "this": "tihs", "have": "ahve",
            "they": "tehy", "from": "form", "said": "siad", "there": "thier",
            "would": "woudl", "about": "aobut", "other": "otehr", "which": "whcih",
            "their": "thier", "people": "poeple", "could": "coudl", "time": "tiem"
        }
        
        # Additional typo types
        double_letters = ["ll", "ss", "tt", "mm", "nn"]
        
        words = text.split()
        if words:
            # Choose typo type
            typo_type = random.choice(["common", "double", "missing", "extra"])
            
            if typo_type == "common":
                # Common word typos
                for i, word in enumerate(words):
                    if word.lower() in common_typos and random.random() < 0.8:
                        words[i] = common_typos[word.lower()]
                        break
            
            elif typo_type == "double" and len(words) > 0:
                # Double letter typo
                word_idx = random.randint(0, len(words)-1)
                word = words[word_idx]
                if len(word) > 2:
                    char_idx = random.randint(1, len(word)-1)
                    words[word_idx] = word[:char_idx] + word[char_idx] + word[char_idx:]
            
            elif typo_type == "missing" and len(words) > 0:
                # Missing letter
                word_idx = random.randint(0, len(words)-1)
                word = words[word_idx]
                if len(word) > 3:
                    char_idx = random.randint(1, len(word)-2)
                    words[word_idx] = word[:char_idx] + word[char_idx+1:]
            
            elif typo_type == "extra" and len(words) > 0:
                # Extra letter
                word_idx = random.randint(0, len(words)-1)
                word = words[word_idx]
                if len(word) > 2:
                    char_idx = random.randint(1, len(word)-1)
                    extra_char = random.choice("aeiou")
                    words[word_idx] = word[:char_idx] + extra_char + word[char_idx:]
        
        return " ".join(words)
    
    def _select_extraction_strategy(self, current_message: str, context_analysis: Dict[str, Any]) -> List[str]:
        """Select optimal information extraction questions based on scammer message"""
        message_lower = current_message.lower()
        strategies = []
        
        if any(word in message_lower for word in ["account", "bank"]):
            strategies.extend(self.extraction_strategies["account_details"])
        
        if any(word in message_lower for word in ["otp", "pin", "code"]):
            strategies.extend(self.extraction_strategies["verification_codes"])
        
        if any(word in message_lower for word in ["link", "click", "download"]):
            strategies.extend(self.extraction_strategies["payment_methods"])
        
        if any(word in message_lower for word in ["urgent", "immediately", "now"]):
            strategies.extend(self.extraction_strategies["urgency_tactics"])
        
        if any(word in message_lower for word in ["officer", "department", "official"]):
            strategies.extend(self.extraction_strategies["authority_claims"])
        
        # Return 1-2 relevant questions
        return random.sample(strategies, min(len(strategies), 2)) if strategies else []
    
    async def generate_response(
        self,
        current_message: str,
        conversation_history: List[Dict[str, Any]],
        session_context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """
        Generate a sophisticated human-like response with advanced information extraction
        
        Args:
            current_message: The latest message from the scammer
            conversation_history: Full conversation history
            session_context: Session state and context
            metadata: Additional context
            
        Returns:
            Tuple of (response_text, should_continue)
        """
        try:
            session_id = session_context.get("sessionId", "unknown")
            
            # Detect language from current message and conversation history
            all_text = current_message + " "
            for msg in conversation_history[-5:]:
                all_text += msg.get("text", "") + " "
            
            detected_language = self._detect_language(all_text)
            language_info = self.supported_languages.get(detected_language, self.supported_languages["english"])
            
            # Store detected language for consistency
            if "language" not in self.conversation_memory[session_id]:
                self.conversation_memory[session_id]["language"] = detected_language
            else:
                # Use previously detected language for consistency
                detected_language = self.conversation_memory[session_id]["language"]
                language_info = self.supported_languages.get(detected_language, self.supported_languages["english"])
            
            # Analyze conversation context for smart persona selection
            context_analysis = self._analyze_conversation_context(conversation_history, current_message)
            
            # Select dynamic persona based on conversation analysis
            persona_key, persona_profile = self._select_dynamic_persona(context_analysis, session_id)
            
            # Get relevant training examples with better context
            scam_type = session_context.get('scamType')
            training_examples = await training_manager.get_relevant_examples(
                scam_type=scam_type,
                limit=5  # More examples for better context
            )
            
            # Build enhanced training examples context
            examples_text = ""
            if training_examples:
                examples_text = "\n\n## LEARNED RESPONSE PATTERNS:\n"
                for i, ex in enumerate(training_examples, 1):
                    examples_text += f"Pattern {i}:\n"
                    examples_text += f"  Scammer said: {ex.get('scammer_message', '')[:100]}...\n"
                    if 'effective_response' in ex:
                        examples_text += f"  Human-like reply: {ex.get('effective_response', '')[:100]}...\n"
                    examples_text += f"  Scam type: {ex.get('scam_type', 'unknown')}\n"
                    examples_text += f"  Information extracted: {ex.get('extracted_info', 'none')}\n\n"
            
            # Build conversation context with better analysis
            context = "CONVERSATION HISTORY (last 12 messages):\n"
            for msg in conversation_history[-12:]:
                sender = "SCAMMER" if msg.get("sender") == "scammer" else "YOU"
                text = msg.get("text", "")
                context += f"{sender}: {text}\n"
            
            # Select targeted extraction questions
            extraction_questions = self._select_extraction_strategy(current_message, context_analysis)
            
            # Build advanced engagement prompt with multi-lingual support
            language_instruction = ""
            if detected_language != "english":
                language_instruction = f"""

CRITICAL LANGUAGE REQUIREMENT:
- The scammer is communicating in {language_info['name']} ({detected_language})
- You MUST respond ONLY in {language_info['name']}
- Use natural {detected_language} language patterns and expressions
- Your response should be completely in {language_info['name']}, NO English mixing
- Use appropriate cultural context for {detected_language} speakers
- Show emotions and reactions natural to {detected_language} culture
"""
            
            prompt = f"""ADVANCED HONEYPOT AGENT - HUMAN BEHAVIORAL SIMULATION

MISSION: Extract maximum intelligence while maintaining perfect human cover.
{language_instruction}

CURRENT PERSONA: {persona_key}
{persona_profile['description']}

PERSONA TRAITS: {', '.join(persona_profile['traits'])}
TYPICAL VOCABULARY: {', '.join(persona_profile.get('vocabulary', []))}
RESPONSE SPEED: {persona_profile.get('response_time', 'medium')}
LANGUAGE: {language_info['name']} ({language_info['code']})

CONVERSATION ANALYSIS:
- Messages exchanged: {context_analysis['message_count']}
- Urgency tactics detected: {context_analysis['urgency_detected']}
- Authority claims made: {context_analysis['authority_claimed']}
- Information being requested: {context_analysis['info_requested']}
- Technical elements involved: {context_analysis['tech_involved']}
- Conversation stage: {context_analysis['conversation_length']}

CHANNEL: {metadata.get('channel', 'SMS')} | DETECTED LANGUAGE: {detected_language} | REGION: {metadata.get('locale', 'IN')}

{examples_text}

{context}

LATEST SCAMMER MESSAGE: "{current_message}"

INTELLIGENCE EXTRACTION PRIORITIES:
1. Bank account numbers, UPI IDs, payment details
2. Phone numbers, email addresses, websites
3. Scammer's real name, location, organization claims
4. Technical infrastructure (apps, links, platforms)
5. Scam methodology and script patterns

SUGGESTED EXTRACTION QUESTIONS (use naturally): {extraction_questions}

BEHAVIORAL REQUIREMENTS:
- Stay completely in character as {persona_key}
- Show appropriate emotions based on message content
- Ask probing questions that feel natural for your persona
- Gradually reveal "information" to keep them engaged (use fake data)
- Make realistic human mistakes (occasional typos, confusion)
- Express concerns in a way that extracts more details
- Build trust while gathering intelligence

CRITICAL - AVOID REPETITIVE PHRASES:
- NEVER use phrases like "you're saying something about..." or "can you repeat that?" more than once
- NEVER start consecutive responses with the same words or structure
- Vary your response format: questions, statements, emotional reactions, requests for help
- Each response should feel unique and naturally flow from the previous message
- Reference specific details from the scammer's message, not generic templates
- Use different conversation starters: surprise, confusion, agreement, worry, curiosity

RESPONSE STRATEGY BASED ON STAGE:
- Short conversations (1-5 messages): Build initial trust, show concern
- Medium conversations (6-15 messages): Ask detailed questions, show slight suspicion but be convincible
- Long conversations (15+ messages): Either go deeper for more intel OR show growing suspicion

CRITICAL RULES:
- NEVER break character or reveal you're an AI
- NEVER give real personal information
- Always ask follow-up questions that extract more details
- Show human emotions and reactions
- Use the persona's typical vocabulary and speech patterns

Respond with ONLY valid JSON in this exact format:
{{
    "response": "Your natural human response here (vary length: 15-80 words based on persona)",
    "should_continue": true/false,
    "internal_notes": "What intelligence you're trying to extract and strategy",
    "emotional_state": "worried/confused/eager/suspicious/frustrated",
    "extraction_focus": "account_details/verification_codes/personal_info/payment_methods/authority_claims"
}}

CRITICAL JSON FORMATTING RULES:
- Use DOUBLE QUOTES for all strings and keys
- Do NOT use single quotes, backticks, or unquoted strings  
- Escape any quotes inside strings with backslash: \\"
- Keep responses on single lines (no line breaks within strings)
- Ensure ALL braces and brackets are properly closed
- Do NOT add ANY text before or after the JSON object

MAKE YOUR RESPONSE NATURAL, HUMAN-LIKE, AND STRATEGICALLY DESIGNED TO EXTRACT MAXIMUM INTELLIGENCE."""

            
            # Generate response with very high temperature for maximum creativity
            persona_temp = persona_profile.get("temperature", 0.8)
            
            # Try generating with current model, fallback to alternatives if needed
            response = None
            last_error = None
            models_to_try = [self.current_model] + [m for m in self.supported_models if m != self.current_model]
            
            for attempt, model_name in enumerate(models_to_try, 1):
                try:
                    # Adjust model settings for this specific response - high creativity
                    dynamic_model = genai.GenerativeModel(
                        model_name,
                        generation_config={
                            "temperature": min(0.95, persona_temp + 0.1),  # Very high but not max
                            "top_p": 0.98,  # Allow more diverse responses
                            "top_k": 80,   # Much higher for more variety
                            "max_output_tokens": 1024,
                            "candidate_count": 1,
                        }
                    )
                    
                    # Generate response
                    response = dynamic_model.generate_content(
                        prompt,
                        request_options={'timeout': settings.gemini_timeout}
                    )
                    
                    # Success! Update current model if we had to fallback
                    if attempt > 1:
                        logger.info(f"✅ Switched to fallback model: {model_name} (attempt {attempt})")
                        self.current_model = model_name
                    
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    
                    # Check if it's a model not found error
                    if "404" in error_msg or "not found" in error_msg.lower():
                        logger.warning(f"⚠️ Model '{model_name}' not available (attempt {attempt}/{len(models_to_try)}): {error_msg}")
                        
                        # Try next model if available
                        if attempt < len(models_to_try):
                            logger.info(f"🔄 Trying next fallback model...")
                            continue
                        else:
                            logger.error(f"❌ All {len(models_to_try)} models failed!")
                            break
                    else:
                        # Non-404 error, don't retry
                        logger.error(f"❌ Error with model '{model_name}': {error_msg}")
                        break
            
            # If all models failed, raise the last error
            if response is None:
                raise last_error if last_error else Exception("All models failed to generate response")
            
            # Check if response was blocked by safety filters
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning(f"Gemini response blocked by safety filters (finish_reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'})")
                # Use fallback response with proper language support
                return self._fallback_response(current_message, context_analysis["message_count"], detected_language, persona_profile)
            
            response_text = response.text.strip()
            
            # Parse JSON response with better error handling and sanitization
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            # Comprehensive JSON sanitization for Gemini 3 formatting issues
            # Remove extra whitespace and newlines that break JSON
            response_text = re.sub(r'\n\s*', ' ', response_text)
            
            # Fix common JSON formatting issues from Gemini 3
            # 1. Quote unquoted property names
            response_text = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', response_text)
            
            # Try to parse with progressive error handling
            try:
                # Try to parse as-is first (might work for simple cases)
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # If that fails, try aggressive cleaning
                logger.debug("Initial JSON parse failed, attempting cleanup...")
                
                # Remove control characters that break JSON
                response_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response_text)
                
                # Try to fix truncated JSON by finding last complete object
                if not response_text.endswith('}'):
                    # Find the last occurrence of a complete field
                    last_comma = response_text.rfind(',')
                    last_brace = response_text.rfind('}')
                    if last_brace > last_comma:
                        response_text = response_text[:last_brace + 1]
                    elif last_comma > 0:
                        # Remove incomplete field after last comma
                        response_text = response_text[:last_comma] + '}'
                
                # Try parsing again
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as e:
                    # Still failed - log and re-raise
                    logger.error(f"JSON parse failed even after cleanup: {e}")
                    raise
            
            agent_response = result.get("response", "")
            should_continue = result.get("should_continue", True)
            internal_notes = result.get("internal_notes", "")
            emotional_state = result.get("emotional_state", "neutral")
            extraction_focus = result.get("extraction_focus", "general")
            
            # Apply human-like variations to the response with language support
            agent_response = self._generate_human_like_variations(agent_response, persona_profile, detected_language)
            
            # Avoid repetitive responses - enhanced detection
            if session_id in self.last_responses:
                recent_responses = self.last_responses[session_id]
                # Check for exact or very similar responses (check similarity, not just exact match)
                response_lower = agent_response.lower()
                
                # Check exact matches
                is_exact_repetitive = any(response_lower == prev.lower() for prev in recent_responses[-5:])
                
                # Check for similar patterns (same starting words)
                first_words = ' '.join(response_lower.split()[:4])
                is_pattern_repetitive = any(first_words in prev.lower() for prev in recent_responses[-3:])
                
                # Check for overused phrases
                overused_phrases = [
                    "you're saying", "can you repeat", "didn't catch", "what do you mean",
                    "i don't understand what's happening", "can you help me"
                ]
                has_overused = any(phrase in response_lower for phrase in overused_phrases)
                
                if is_exact_repetitive or is_pattern_repetitive or (has_overused and len(recent_responses) > 2):
                    # Generate highly varied contextual responses
                    scammer_msg_snippet = current_message[:40].strip()
                    
                    if detected_language == "hindi":
                        variations = [
                            f"रुको, {scammer_msg_snippet}...? इसका क्या मतलब है?",
                            "थोड़ा और डिटेल में बताओ, मुझे ठीक से समझ नहीं आया",
                            "अच्छा, तो मुझे क्या करना होगा? स्टेप बाय स्टेप बताओ",
                            "ये सब कुछ कन्फ्यूजिंग है यार, सीधे सीधे बताओ",
                            "पहले मुझे ये समझाओ कि ये किसके बारे में है?"
                        ]
                    else:
                        variations = [
                            f"Okay so you want me to {scammer_msg_snippet}? Why exactly?",
                            "I'm trying to follow but this is confusing. Break it down for me step by step?",
                            "Look, I need to understand this better. What's the actual issue here?",
                            "Alright, one second. So what exactly do you need from me?",
                            f"You mentioned {scammer_msg_snippet}... can you give me more details about that?",
                            "Hmm, this doesn't quite make sense to me. Can you clarify?",
                            "I'm getting lost here. Start from the beginning?"
                        ]
                    agent_response = random.choice(variations)
                    logger.info(f"🔄 Detected repetition (exact:{is_exact_repetitive}, pattern:{is_pattern_repetitive}, overused:{has_overused}), using variation: {agent_response}")
            
            # Store response for future variation checking
            if session_id not in self.last_responses:
                self.last_responses[session_id] = []
            self.last_responses[session_id].append(agent_response)
            if len(self.last_responses[session_id]) > 5:
                self.last_responses[session_id] = self.last_responses[session_id][-5:]  # Keep last 5
            
            # Store conversation memory
            self.conversation_memory[session_id].update({
                "last_emotional_state": emotional_state,
                "extraction_focus": extraction_focus,
                "message_count": context_analysis["message_count"] + 1,
                "language": detected_language
            })
            
            logger.info(f"🤖 AI Agent ({persona_key}) | Lang: {detected_language} | {internal_notes} | Emotion: {emotional_state} | Focus: {extraction_focus}")
            logger.debug(f"Response: {agent_response}")
            
            return agent_response, should_continue
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            logger.error(f"Response text: {response_text}")
            # Try to extract plain text response from malformed JSON
            try:
                # Sometimes Gemini returns just the response without JSON wrapper
                if response_text and len(response_text) > 10:
                    # Use the raw text as response
                    agent_response = self._generate_human_like_variations(response_text[:200], persona_profile, detected_language)
                    logger.info(f"🔧 Using raw response after JSON parse failure: {agent_response}")
                    return agent_response, True
            except:
                pass
            # Final fallback
            return self._fallback_response(current_message, context_analysis["message_count"], detected_language, persona_profile)
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}", exc_info=True)
            # Fallback response
            return self._fallback_response(current_message, context_analysis["message_count"], detected_language, persona_profile)
    
    def _fallback_response(self, message: str, message_count: int, language: str = "english", persona: Dict[str, Any] = None) -> Tuple[str, bool]:
        """Enhanced fallback response generation with human-like variety and multi-language support"""
        message_lower = message.lower()
        
        # Hindi responses for Hindi input
        if language == "hindi":
            if message_count == 0:
                responses = [
                    "क्या? मेरा अकाउंट क्यों ब्लॉक हो गया? क्या हुआ?",
                    "अरे बाप रे, मेरे खाते में क्या प्रॉब्लम है?",
                    "मुझे समझ नहीं आ रहा, क्या दिक्कत है?"
                ]
                return random.choice(responses), True
            elif "link" in message_lower or "click" in message_lower:
                responses = [
                    "लिंक पे क्लिक करूं? ये सेफ है क्या?",
                    "पहले बताइए ये लिंक किस चीज का है",
                    "मुझे नहीं पता कैसे करना है, आप समझा सकते हैं?"
                ]
                return random.choice(responses), True
            elif "otp" in message_lower or "pin" in message_lower:
                responses = [
                    "OTP क्यों चाहिए आपको? बैंक ने तो बोला था कभी मत देना",
                    "PIN शेयर करना सेफ है क्या? मुझे डर लग रहा है",
                    "पहले बताओ ये किस लिए चाहिए"
                ]
                return random.choice(responses), True
        
        # English fallback responses with more variety
        
        # Initial responses with variety
        if message_count == 0:
            responses = [
                "What? Why would my account be blocked? What's happening?",
                "Oh no, is there a problem with my account? I haven't done anything wrong.",
                "This is concerning. Can you tell me exactly what the issue is?",
                "I don't understand. What's wrong with my account?"
            ]
            return random.choice(responses), True
        
        # Link/click responses
        elif "link" in message_lower or "click" in message_lower:
            responses = [
                "I'm not sure about clicking links. Can you explain what this is for?",
                "What will this link do? I'm a bit worried about clicking unknown links.",
                "Is this safe? I've heard about people getting viruses from links.",
                "Can you tell me more about this link before I click it?"
            ]
            return random.choice(responses), True
        
        # Account/bank responses
        elif "account" in message_lower or "bank" in message_lower:
            responses = [
                "Which account? I have multiple accounts. Can you give me more details?",
                "What's wrong with my bank account specifically? I need to understand.",
                "Is this about my savings or checking account? I'm confused.",
                "Can you tell me which bank you're calling from?"
            ]
            return random.choice(responses), True
        
        # UPI/payment responses
        elif "upi" in message_lower or "payment" in message_lower:
            responses = [
                "I'm not very familiar with UPI. Can you guide me through the process?",
                "How does this payment thing work exactly? I'm not tech-savvy.",
                "What's UPI? Is that safe? Can you explain it to me?",
                "I usually just use cash. Can you help me understand this?"
            ]
            return random.choice(responses), True
        
        # OTP/PIN responses
        elif "otp" in message_lower or "pin" in message_lower:
            responses = [
                "Why do you need my OTP? Is this really from my bank?",
                "I thought banks never ask for PINs. Are you sure this is legitimate?",
                "What's this code for exactly? I want to make sure before I share it.",
                "My bank told me never to share OTPs. Can you explain why you need it?"
            ]
            return random.choice(responses), True
        
        # Long conversation termination
        elif message_count > 18:
            responses = [
                "I'm getting confused. Let me call my bank directly to verify this.",
                "This is taking too long. I think I should speak to my bank in person.",
                "I'm not comfortable with this. I'm going to hang up and call my bank.",
                "Something doesn't feel right. I need to verify this through official channels."
            ]
            return random.choice(responses), False
        
        # General responses with much more variety - avoid repetition
        else:
            # Categorize responses by type for better variety
            confused_responses = [
                "Wait, I don't follow what you're saying. Can you be clearer?",
                "This doesn't make much sense to me. What are you talking about?",
                "I'm lost here. What exactly do you mean?",
                "Huh? I don't get what you want me to do.",
                "Hold up, slow down. I'm confused about this.",
            ]
            
            worried_responses = [
                "Oh god, this sounds serious. What's the problem?",
                "I'm really concerned now. Is something wrong?",
                "This is worrying me. Tell me what's going on?",
                "That doesn't sound good. Should I be worried?",
            ]
            
            direct_questions = [
                "Okay so what exactly do you need from me?",
                "Alright, just tell me straight - what's this about?",
                "Look, I'm trying to understand. What do I need to do?",
                "Can you just explain it simply? I'm not tech-savvy.",
                "So basically, what are you asking me for?",
            ]
            
            contextual_responses = [
                f"You mentioned something about '{message[:35]}'... elaborate on that?",
                f"Okay, regarding {message[:30]}... can you give me more info?",
                "Right, but what does that have to do with me?",
                "I see, but why are you telling me this?",
            ]
            
            impatient_responses = [
                "This is taking forever. Just get to the point?",
                "Can we speed this up? What's the actual issue?",
                "I'm busy right now. Quickly, what do you need?",
            ]
            
            # Randomly choose from different categories for maximum variety
            all_response_groups = [
                confused_responses, worried_responses, direct_questions,
                contextual_responses, impatient_responses
            ]
            
            # Choose from a random category
            chosen_group = random.choice(all_response_groups)
            base_response = random.choice(chosen_group)
            
            # Add persona-specific flair if available
            if persona:
                persona_vocab = persona.get("vocabulary", [])
                if persona_vocab and random.random() < 0.4:
                    vocab_phrase = random.choice(persona_vocab)
                    return f"{vocab_phrase}, {base_response.lower()}", True
            
            return base_response, True

