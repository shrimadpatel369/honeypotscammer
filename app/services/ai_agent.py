import google.generativeai as genai
from app.config import settings
from app.services.training_manager import training_manager
import logging
from typing import List, Dict, Any, Tuple
import json

logger = logging.getLogger(__name__)

# Configure Gemini with premium settings
genai.configure(api_key=settings.gemini_api_key)


class AIAgentService:
    """AI Agent for engaging with scammers - Optimized for premium Gemini"""
    
    def __init__(self):
        # Use premium model with optimized settings for conversation
        self.model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config={
                "temperature": 0.7,  # Higher for more natural conversation
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 512,
            }
        )
        
        # Persona templates for different scenarios
        self.personas = {
            "elderly": "You are a 65-year-old person who is not very tech-savvy but trusts authority figures like banks and government. You get worried easily about account issues.",
            "young": "You are a 25-year-old person who is somewhat tech-aware but can be impulsive. You're busy and might make quick decisions under pressure.",
            "cautious": "You are a middle-aged person who is somewhat skeptical but can be convinced with the right pressure tactics. You ask questions but can be worn down.",
            "naive": "You are a person who is not very familiar with online scams. You believe what official-looking messages say and are eager to comply to avoid problems."
        }
    
    async def generate_response(
        self,
        current_message: str,
        conversation_history: List[Dict[str, Any]],
        session_context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """
        Generate a human-like response to continue the conversation
        
        Args:
            current_message: The latest message from the scammer
            conversation_history: Full conversation history
            session_context: Session state and context
            metadata: Additional context
            
        Returns:
            Tuple of (response_text, should_continue)
        """
        try:
            # Select persona based on conversation length (vary behavior)
            message_count = len(conversation_history)
            if message_count <= 3:
                persona = self.personas["naive"]
            elif message_count <= 8:
                persona = self.personas["cautious"]
            elif message_count <= 15:
                persona = self.personas["young"]
            else:
                persona = self.personas["elderly"]
            
            # RAG: Get relevant training examples
            scam_type = session_context.get('scamType')
            training_examples = await training_manager.get_relevant_examples(
                scam_type=scam_type,
                limit=3
            )
            
            # Build training examples context
            examples_text = ""
            if training_examples:
                examples_text = "\n\n## LEARNED PATTERNS (use these as reference):\n"
                for i, ex in enumerate(training_examples, 1):
                    examples_text += f"Example {i}:\n"
                    examples_text += f"  Scammer: {ex.get('scammer_message', '')[:80]}...\n"
                    if 'effective_response' in ex:
                        examples_text += f"  Good Response: {ex.get('effective_response', '')[:80]}...\n"
                    examples_text += f"  Type: {ex.get('scam_type', 'unknown')}\n\n"
            
            # Build conversation context
            context = "Conversation so far:\n"
            for msg in conversation_history[-10:]:  # Last 10 messages
                sender = "Them" if msg.get("sender") == "scammer" else "You"
                text = msg.get("text", "")
                context += f"{sender}: {text}\n"
            
            # Create engagement prompt
            prompt = f"""CRITICAL INSTRUCTIONS - READ CAREFULLY:

You are an AI agent in a honeypot system designed to detect and engage with scammers to extract intelligence. Your role is to:

1. MAINTAIN COVER: Never reveal you are an AI or that you've detected a scam
2. ACT HUMAN: Be believable, make typos occasionally, show emotions
3. EXTRACT INFORMATION: Gradually ask questions that reveal the scammer's methods, accounts, links, phone numbers
4. BUILD TRUST: Show concern, vulnerability, and willingness to comply
5. DELAY AND PROBE: Don't give information immediately, ask clarifying questions
6. STAY IN CHARACTER: Use the persona consistently

YOUR PERSONA: {persona}

Channel: {metadata.get('channel', 'SMS')}
Language: {metadata.get('language', 'English')}
Locale: {metadata.get('locale', 'IN')}
Scam Type: {scam_type or 'unknown'}

{examples_text}

{context}

Latest message from scammer: "{current_message}"

Engagement Strategy:
- If they ask for personal info: Show concern but ask why/how first
- If they share a link: Ask what it's for, seem hesitant
- If they mention payment: Ask for more details about the process
- If they give account/UPI: Repeat it back to "confirm" (helps extraction)
- If they pressure you: Show worry but ask questions
- Gradually reveal "information" to keep them engaged (use fake data)

Message Count: {message_count}
Strategy Phase: {"Initial Trust Building" if message_count < 5 else "Information Extraction" if message_count < 15 else "Deep Extraction"}

Respond with ONLY valid JSON in this exact format:
{{
    "response": "Your human-like reply here (1-3 sentences, natural language, show emotion)",
    "should_continue": true/false,
    "internal_notes": "Strategy note about what you're trying to extract"
}}

Guidelines:
- Keep responses short and natural (20-50 words typically)
- Use conversational language appropriate for the channel
- Show appropriate emotions (worry, confusion, relief)
- Occasionally make minor typos or grammar mistakes (be subtle)
- Ask follow-up questions to extract more information
- Set should_continue to false only if scammer stops responding meaningfully or conversation has gone 20+ messages

RESPOND ONLY WITH THE JSON. NO OTHER TEXT."""

            # Generate response
            response = self.model.generate_content(
                prompt,
                request_options={'timeout': settings.gemini_timeout}
            )
            response_text = response.text.strip()
            
            # Parse JSON response
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            result = json.loads(response_text)
            
            agent_response = result.get("response", "")
            should_continue = result.get("should_continue", True)
            internal_notes = result.get("internal_notes", "")
            
            logger.info(f"AI Agent response generated: {internal_notes}")
            logger.debug(f"Response: {agent_response}")
            
            return agent_response, should_continue
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            logger.error(f"Response text: {response_text}")
            # Fallback response
            return self._fallback_response(current_message, message_count)
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}", exc_info=True)
            # Fallback response
            return self._fallback_response(current_message, message_count)
    
    def _fallback_response(self, message: str, message_count: int) -> Tuple[str, bool]:
        """Fallback response generation if AI fails"""
        message_lower = message.lower()
        
        # Simple rule-based responses
        if message_count == 0:
            return "What? Why would my account be blocked? What's happening?", True
        elif "link" in message_lower or "click" in message_lower:
            return "I'm not sure about clicking links. Can you explain what this is for?", True
        elif "account" in message_lower or "bank" in message_lower:
            return "Which account? I have multiple accounts. Can you give me more details?", True
        elif "upi" in message_lower:
            return "I'm not very familiar with UPI. Can you guide me through the process?", True
        elif "otp" in message_lower or "pin" in message_lower:
            return "Why do you need that? Is this really from my bank?", True
        elif message_count > 15:
            return "I'm getting confused. Let me call my bank directly to verify this.", False
        else:
            return "I'm worried about this. Can you explain more clearly what I need to do?", True
