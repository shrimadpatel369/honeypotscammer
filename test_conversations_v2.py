#!/usr/bin/env python3
"""
Test script for Honeypot Message API endpoint - TWO SCENARIOS

SCENARIO 1: Scammer Initiating (Scammer → User Response)
- Test script imitates a SCAMMER sending messages
- Message API responds as a USER (victim)
- System should DETECT SCAM = True

SCENARIO 2: Normal User Interaction (User → User Response)
- Test script imitates a normal USER sending messages
- Message API responds as a USER (support/agent)
- System should DETECT SCAM = False (no false positives)

Each scenario runs in a SEPARATE SESSION
Requires x-api-key header authentication
"""

import json
import sys
from datetime import datetime, UTC
import requests
from typing import Any
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
import random
import string

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL", "http://localhost:8000")
MESSAGE_API_ENDPOINT = "/api/message"

# Session ID counters for each scenario
SCAMMER_SESSION_COUNTER = 0
USER_SESSION_COUNTER = 0

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


def generate_random_hash(length: int = 8) -> str:
    """Generate a random hash suffix for session IDs"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def get_scammer_session_id() -> str:
    """Generate session ID for SCENARIO 1 (Scammer Initiating)"""
    global SCAMMER_SESSION_COUNTER
    SCAMMER_SESSION_COUNTER += 1
    random_hash = generate_random_hash()
    return f"scenario-1-scammer-{SCAMMER_SESSION_COUNTER}-{random_hash}"


def get_user_session_id() -> str:
    """Generate session ID for SCENARIO 2 (Normal User)"""
    global USER_SESSION_COUNTER
    USER_SESSION_COUNTER += 1
    random_hash = generate_random_hash()
    return f"scenario-2-user-{USER_SESSION_COUNTER}-{random_hash}"


def generate_scammer_messages() -> list[dict[str, str]]:
    """
    SCENARIO 1: Generate scammer conversation (10-15 messages)
    These messages will be sent BY the test script (as scammer)
    The API will respond as the victim/user
    Scam detection should = TRUE
    """
    
    model = genai.GenerativeModel("gemini-2.5-pro")
    
    prompt = """
    Generate a realistic 10-15 message SCAM conversation where a scammer initiates contact.
    Return ONLY the scammer's messages (not the victim's responses - API will generate those).
    
    Return a JSON array with scammer messages only.
    Format:
    [
        {"sender": "scammer", "text": "Your UPI account will be suspended today..."},
        {"sender": "scammer", "text": "You made suspicious transactions..."},
        {"sender": "scammer", "text": "Please provide your bank details to verify..."},
        ...
    ]
    
    Make these messages:
    - Start with urgency/threat
    - Progress to requesting sensitive info
    - Include fake verification attempts
    - Include payment/OTP requests
    - Realistic to Indian context (UPI, bank account, Aadhar, etc.)
    - Total 10-15 messages
    - NO victim responses (only scammer messages)
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            messages = json.loads(json_str)
            return messages
        else:
            print(f"Could not find JSON in Gemini response")
            return []
    except Exception as e:
        print(f"❌ Error generating scammer messages: {e}")
        return []


def generate_user_messages() -> list[dict[str, str]]:
    """
    SCENARIO 2: Generate normal user conversation (10-15 messages)
    These messages will be sent BY the test script (as normal user)
    The API will respond as a support agent/user
    Scam detection should = FALSE (no false positives)
    """
    
    model = genai.GenerativeModel("gemini-2.5-pro")
    
    prompt = """
    Generate a realistic 10-15 message conversation where a normal customer initiates contact.
    Return ONLY the customer's messages (not the agent's responses - API will generate those).
    
    Return a JSON array with customer messages only.
    Format:
    [
        {"sender": "user", "text": "Hi, I have a question about my account..."},
        {"sender": "user", "text": "Can you help me with my billing?"},
        {"sender": "user", "text": "I want to upgrade my plan..."},
        ...
    ]
    
    Make these messages:
    - Professional customer service inquiries
    - Multiple rounds of Q&A
    - Questions about billing, account, features
    - NO red flags (no urgency, no suspicious requests)
    - Realistic to Indian context
    - Total 10-15 messages
    - NO agent/support responses (only customer messages)
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            messages = json.loads(json_str)
            return messages
        else:
            print(f"Could not find JSON in Gemini response")
            return []
    except Exception as e:
        print(f"❌ Error generating user messages: {e}")
        return []


def test_message_api(message: str, sender: str, session_id: str, conversation_history: list = None) -> dict[str, Any]:
    """
    Send a single message to the Message API endpoint
    
    Args:
        message: The message text to send
        sender: Who is sending ('scammer' or 'user')
        session_id: Session ID for tracking
        conversation_history: Previous messages in conversation
        
    Returns:
        API response as dict
    """
    
    if conversation_history is None:
        conversation_history = []
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Create request body for Message API
    request_body = {
        "sessionId": session_id,
        "message": {
            "sender": sender,
            "text": message,
            "timestamp": datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        },
        "conversationHistory": conversation_history,
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN"
        }
    }
    
    try:
        start_ts = time.time()
        response = requests.post(
            f"{API_URL}{MESSAGE_API_ENDPOINT}",
            json=request_body,
            headers=headers,
            timeout=120
        )
        elapsed = time.time() - start_ts
        response_ms = int(elapsed * 1000)

        if response.status_code == 200:
            return {
                "success": True,
                "status_code": 200,
                "data": response.json(),
                "session_id": session_id,
                "response_time_ms": response_ms
            }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
                "session_id": session_id,
                "response_time_ms": response_ms
            }

    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - start_ts if 'start_ts' in locals() else 0
        return {
            "success": False,
            "error": f"Connection Error: {str(e)}",
            "session_id": session_id,
            "response_time_ms": int(elapsed * 1000)
        }
    except Exception as e:
        elapsed = time.time() - start_ts if 'start_ts' in locals() else 0
        return {
            "success": False,
            "error": f"Error: {str(e)}",
            "session_id": session_id,
            "response_time_ms": int(elapsed * 1000)
        }


def run_scenario_1_scammer_initiating(messages: list[dict[str, str]]) -> None:
    """
    SCENARIO 1: Scammer Initiating
    - Test script sends SCAMMER messages
    - API responds as USER (victim)
    - Expected: scamDetected = TRUE
    - Expected: scamConfidence = HIGH
    """
    
    print("\n" + "="*80)
    print("🚨 SCENARIO 1: SCAMMER INITIATING (Scammer → User Response)")
    print("="*80)
    print(f"Testing: We are SCAMMER, API responds as VICTIM USER")
    print(f"Expected Result: scamDetected = TRUE (scam should be detected)")
    print(f"\nMessages to send: {len(messages)}\n")
    
    if not messages:
        print("❌ No messages to test")
        return
    
    session_id = get_scammer_session_id()
    conversation_history = []
    scam_detected_count = 0
    scam_confidence_sum = 0.0
    response_time_sum_ms = 0
    scenario_start = time.time()
    
    print(f"🔗 Session ID: {session_id}")
    print("-" * 80)
    
    for i, msg_obj in enumerate(messages, 1):
        sender = msg_obj.get("sender", "scammer")
        text = msg_obj.get("text", "")
        
        print(f"\n📨 Message {i}/{len(messages)} [SENT BY: SCAMMER]")
        print(f"   Text: {text[:80]}{'...' if len(text) > 80 else ''}")
        
        # Send message to API
        result = test_message_api(text, sender=sender, session_id=session_id, conversation_history=conversation_history)
        
        if not result.get("success", False):
            print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
            continue
        
        print(f"   ✅ SUCCESS")
        
        data = result.get("data", {})
        
        # Check scam detection
        scam_detected = data.get("scamDetected", False)
        scam_confidence = data.get("scamConfidence", 0.0)
        response_time = result.get("response_time_ms", 0)
        response_time_sum_ms += int(response_time or 0)
        
        if scam_detected:
            scam_detected_count += 1
            scam_confidence_sum += scam_confidence
        
        status_emoji = "🚨" if scam_detected else "⚠️"
        print(f"   {status_emoji} Scam Detected: {scam_detected} (Confidence: {scam_confidence:.2f})")
        print(f"   ⏱ Response Time: {response_time} ms")
        
        # Show AI response (API responding as user/victim)
        reply = data.get("reply", "")
        if reply:
            print(f"   💬 [API responds as USER]: {reply[:80]}{'...' if len(reply) > 80 else ''}")
        
        # Show intelligence extracted
        intel = data.get("extractedIntelligence", {})
        if any(intel.values()):
            print(f"   🔎 Intelligence Extracted:")
            for key, values in intel.items():
                if values:
                    print(f"      • {key}: {values}")
        
        # Update conversation history
        conversation_history.append({
            "sender": sender,
            "text": text,
            "timestamp": datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        })
        
        if reply:
            conversation_history.append({
                "sender": "user",
                "text": reply,
                "timestamp": datetime.now(UTC).isoformat().replace('+00:00', 'Z')
            })
        
        time.sleep(1.0)
    
    # Final summary for Scenario 1
    print("\n" + "-" * 80)
    print(f"📊 SCENARIO 1 RESULTS:")
    print(f"   • Total Scammer Messages Sent: {len(messages)}")
    print(f"   • Scam Detected Count: {scam_detected_count}")
    avg_confidence = scam_confidence_sum / max(1, scam_detected_count)
    avg_response_ms = response_time_sum_ms / max(1, len(messages))
    total_duration = time.time() - scenario_start
    print(f"   • Average Confidence: {avg_confidence:.2f}")
    print(f"   • Average Response Time: {avg_response_ms:.0f} ms")
    print(f"   • Total Scenario Duration: {int(total_duration)}s")
    print(f"   • ✅ Status: {'PASS - Scam detected correctly' if scam_detected_count > 0 else 'FAIL - Scam not detected'}")


def run_scenario_2_normal_user(messages: list[dict[str, str]]) -> None:
    """
    SCENARIO 2: Normal User Interaction
    - Test script sends USER (customer) messages
    - API responds as USER (support/agent)
    - Expected: scamDetected = FALSE
    - Expected: No false positives
    """
    
    print("\n\n" + "="*80)
    print("✅ SCENARIO 2: NORMAL USER INTERACTION (User → User Response)")
    print("="*80)
    print(f"Testing: We are NORMAL USER, API responds as SUPPORT AGENT")
    print(f"Expected Result: scamDetected = FALSE (should NOT flag as scam)")
    print(f"\nMessages to send: {len(messages)}\n")
    
    if not messages:
        print("❌ No messages to test")
        return
    
    session_id = get_user_session_id()
    conversation_history = []
    false_positive_count = 0
    response_time_sum_ms = 0
    scenario_start = time.time()
    
    print(f"🔗 Session ID: {session_id}")
    print("-" * 80)
    
    for i, msg_obj in enumerate(messages, 1):
        sender = msg_obj.get("sender", "user")
        text = msg_obj.get("text", "")
        
        print(f"\n📨 Message {i}/{len(messages)} [SENT BY: USER]")
        print(f"   Text: {text[:80]}{'...' if len(text) > 80 else ''}")
        
        # Send message to API
        result = test_message_api(text, sender=sender, session_id=session_id, conversation_history=conversation_history)
        
        if not result.get("success", False):
            print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
            continue
        
        print(f"   ✅ SUCCESS")
        
        data = result.get("data", {})
        
        # Check for false positives (normal message marked as scam)
        scam_detected = data.get("scamDetected", False)
        scam_confidence = data.get("scamConfidence", 0.0)
        response_time = result.get("response_time_ms", 0)
        response_time_sum_ms += int(response_time or 0)

        if scam_detected:
            false_positive_count += 1

        status_emoji = "🚨" if scam_detected else "✅"
        print(f"   {status_emoji} Scam Detected: {scam_detected} (Confidence: {scam_confidence:.2f})")
        print(f"   ⏱ Response Time: {response_time} ms")
        
        # Show API response (responding as support agent)
        reply = data.get("reply", "")
        if reply:
            print(f"   💬 [API responds as SUPPORT]: {reply[:80]}{'...' if len(reply) > 80 else ''}")
        
        # Update conversation history
        conversation_history.append({
            "sender": sender,
            "text": text,
            "timestamp": datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        })
        
        if reply:
            conversation_history.append({
                "sender": "scammer",
                "text": reply,
                "timestamp": datetime.now(UTC).isoformat().replace('+00:00', 'Z')
            })
        
        time.sleep(1.0)
    
    # Final summary for Scenario 2
    print("\n" + "-" * 80)
    print(f"📊 SCENARIO 2 RESULTS:")
    print(f"   • Total User Messages Sent: {len(messages)}")
    print(f"   • False Positives (incorrectly flagged as scam): {false_positive_count}")
    avg_response_ms = response_time_sum_ms / max(1, len(messages))
    total_duration = time.time() - scenario_start
    print(f"   • Average Response Time: {avg_response_ms:.0f} ms")
    print(f"   • Total Scenario Duration: {int(total_duration)}s")
    print(f"   • ✅ Status: {'PASS - No false positives' if false_positive_count == 0 else f'FAIL - {false_positive_count} false positives detected'}")


def main():
    print("\n" + "="*80)
    print("🍯 HONEYPOT MESSAGE API - TWO SCENARIO TEST SUITE")
    print("="*80)
    print(f"API Endpoint: {API_URL}{MESSAGE_API_ENDPOINT}")
    print(f"\nSCENARIO 1: Scammer Initiating (We send SCAMMER msgs, API responds as USER)")
    print(f"SCENARIO 2: Normal User (We send USER msgs, API responds as USER)")
    print(f"\nEach scenario will run in a SEPARATE SESSION\n")
    
    # Check if API is running
    try:
        start_time = time.time()
        response = requests.get(f"{API_URL}/docs", timeout=5)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ API is running (responded in {elapsed:.2f}s)")
        else:
            print(f"⚠️  API responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_URL}")
        print("💡 Start it with: uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"⚠️  API check failed: {e}")
    
    # ===== SCENARIO 1: Scammer Initiating =====
    print("\n\n🤖 Generating SCENARIO 1 messages (Scammer messages)...")
    scammer_messages = generate_scammer_messages()
    if scammer_messages:
        print(f"✅ Generated {len(scammer_messages)} scammer messages")
        run_scenario_1_scammer_initiating(scammer_messages)
    else:
        print("❌ Failed to generate scammer messages")
    
    # ===== SCENARIO 2: Normal User =====
    print("\n\n🤖 Generating SCENARIO 2 messages (Normal user messages)...")
    user_messages = generate_user_messages()
    if user_messages:
        print(f"✅ Generated {len(user_messages)} user messages")
        run_scenario_2_normal_user(user_messages)
    else:
        print("❌ Failed to generate user messages")
    
    # Final summary
    print("\n\n" + "="*80)
    print("✅ TEST SUITE COMPLETED")
    print("="*80)
    print(f"\n📊 SUMMARY:")
    print(f"   • Scenario 1 Sessions: {SCAMMER_SESSION_COUNTER}")
    print(f"   • Scenario 2 Sessions: {USER_SESSION_COUNTER}")
    print(f"   • Total Sessions Run: {SCAMMER_SESSION_COUNTER + USER_SESSION_COUNTER}")
    print(f"\n📝 Session Tracking:")
    print(f"   Scenario 1 prefix: scenario-1-scammer-*")
    print(f"   Scenario 2 prefix: scenario-2-user-*")
    print(f"\n💾 Detailed logs available in: logs/app_*.log")


if __name__ == "__main__":
    main()
