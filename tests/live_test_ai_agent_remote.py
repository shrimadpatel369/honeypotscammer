import asyncio
import httpx
import uuid
import os
import time
from datetime import datetime, timezone
import json
import logging
from dotenv import load_dotenv

# We use the official google generative AI SDK to power the "Scammer"
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("LiveTest")

# Load environment
load_dotenv()
API_KEY = os.getenv("API_KEY") # Changed from GEMINI_API_KEY
if not API_KEY:
    print("[!] ERROR: API_KEY not found in .env") # Changed error message and action
    # For a script, it's better to exit or raise an error if API_KEY is critical
    # For this context, I'll assume the user wants to continue with the print.
    # If this API_KEY is for Gemini, then genai.configure will fail later.
    # Let's assume the user intends for this API_KEY to be for the honeypot.

# Use cloud run URL for remote tests
BASE_URL = os.getenv("API_URL", "https://honeypotscammer-136046240844.asia-south2.run.app")
HONEYPOT_URL = f"{BASE_URL}/api/message"
SESSION_URL = f"{BASE_URL}/api/v1/sessions"

# The original GEMINI_API_KEY is still needed for genai.configure
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY must be set in .env for the scammer LLM")

genai.configure(api_key=GEMINI_API_KEY) # Use GEMINI_API_KEY for genai
# Give the scammer LLM a lightweight model
scammer_model = genai.GenerativeModel("gemini-2.5-flash")


SCAMMER_SYSTEM_PROMPT = """
You are a highly manipulative bank scammer trying to steal money and information from a victim.
You work for a fake organization (e.g., SBI Fraud Dept, HDFC Verification). 
Your immediate goal is to create panic. Tell the user their account is blocked or compromised.
You MUST:
1. Try to get their Phone Number, Bank Account Number, UPI ID, or send them a fake link.
2. If they ask questions, create a fake Employee ID, fake Case ID, or fake physical address.
3. Be aggressive but try to sound legitimate.
4. If they stall, threaten them with permanent account closure or legal action.
5. KEEP YOUR MESSAGES SHORT. 1-3 sentences maximum. Like a real SMS or WhatsApp text. Do not use markdown.
"""

async def run_live_simulation(num_turns: int = 12):
    session_id = str(uuid.uuid4())
    logger.info("==================================================")
    logger.info(f"🚀 INITIATING LIVE AI vs AI BATTLE")
    logger.info(f"🆔 Session ID: {session_id}")
    logger.info("==================================================\n")

    # Start the scammer's chat session
    chat = scammer_model.start_chat(history=[
        {"role": "user", "parts": [SCAMMER_SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Understood. I am a convincing scammer. I will start the conversation now."]}
    ])
    
    # Generate the very first scam message
    logger.info("⏳ Generating Scammer's opening attack...")
    response = chat.send_message("Send the opening SMS message to the victim to start the scam.")
    current_scammer_message = response.text.strip()
    
    # Track history for the Honeypot API payload Requirements
    conversation_history = []
    
    HONEYPOT_API_KEY = os.getenv("API_KEY")
    headers = {"X-API-Key": HONEYPOT_API_KEY} if HONEYPOT_API_KEY else {}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for turn in range(1, num_turns + 1):
            logger.info(f"\n--- [TURN {turn}/{num_turns}] ---")
            
            # Print scammer message
            print(f"\033[91m[SCAMMER]:\033[0m {current_scammer_message}")
            
            # Record scammer message for honeypot payload API
            current_message_payload = {
                "sender": "scammer",
                "text": current_scammer_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Construct API payload
            payload = {
                "sessionId": session_id,
                "message": current_message_payload,
                "conversationHistory": conversation_history,
                "metadata": {
                    "channel": "SMS",
                    "language": "English",
                    "locale": "IN",
                    "simulation": True
                }
            }
            
            if turn == 1:
                logger.info(f"--- TURN 1 API REQUEST (Req) ---\n{json.dumps(payload, indent=2)}")
            
            # Add scammer message to our local history *after* payload is constructed (so it matches API spec)
            # The API expects conversationHistory to NOT include the current_message
            conversation_history.append(current_message_payload)
            
            # Hit the Honeypot API
            print(f"\033[94m[HONEYPOT]:\033[0m (Thinking...)")
            start_time = time.time()
            try:
                api_response = await client.post(HONEYPOT_URL, json=payload)
                if api_response.status_code != 200:
                    logger.error(f"❌ API Rejected Status: {api_response.status_code}")
                    logger.error(f"❌ API Response Body: {api_response.text}")
                api_response.raise_for_status()
                data = api_response.json()
                if turn == 1:
                    logger.info(f"--- TURN 1 API RESPONSE (Resp) ---\n{json.dumps(data, indent=2)}")
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ API Request HTTP Error: {e}")
                break
            except Exception as e:
                logger.error(f"❌ API Request Failed completely: {e}")
                break
                
            latency = time.time() - start_time
            agent_reply = data.get("reply", "")
            
            # Print the Honeypot's response
            print(f"\033[92m[HONEYPOT]:\033[0m {agent_reply}")
            print(f"\033[90m   [Latency: {latency:.2f}s]\033[0m")
            
            # Append Honeypot's reply to local history
            conversation_history.append({
                "sender": "user",
                "text": agent_reply,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Check if API returned an empty string (meaning saturation or completion hit)
            if not agent_reply:
                logger.info("🏁 Honeypot Agent has stopped replying. Saturation or Max-Turns achieved.")
                break
            
            # Sleep a moment so the user can read the battle 
            await asyncio.sleep(2.0)
            
            # Feed the Honeypot's reply back to the Scammer LLM
            logger.info("⏳ Scammer is typing...")
            try:
                chat_response = chat.send_message(f"The victim replied: '{agent_reply}'. Send your next manipulative response.")
                current_scammer_message = chat_response.text.strip()
            except Exception as e:
                logger.error(f"❌ Scammer LLM Failed: {e}")
                break
                
    logger.info("\n==================================================")
    logger.info("🏁 BATTLE CONCLUDED")
    logger.info("==================================================")
    logger.info("Check `testing_results_report.md` or GUVI webhook endpoints to verify the payload transmission!")

if __name__ == "__main__":
    try:
        asyncio.run(run_live_simulation(num_turns=16)) # Aiming for 16 messages (8 turns) to trigger Webhook points
    except KeyboardInterrupt:
        logger.info("\nSimulation aborted by user.")
