#!/usr/bin/env python3
"""
Test script for Honeypot Message API endpoint
Tests POST /api/message with both scammer and normal person messages
Uses Gemini API to generate realistic test scenarios
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

# Session ID counter for sequential test IDs
SESSION_ID_COUNTER = 0
SESSION_ID_PREFIX = "automated-test-script"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


def generate_random_hash(length: int = 8) -> str:
    """Generate a random hash suffix for session IDs"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def get_next_session_id() -> str:
    """Generate next sequential session ID with random hash suffix"""
    global SESSION_ID_COUNTER
    SESSION_ID_COUNTER += 1
    random_hash = generate_random_hash()
    return f"{SESSION_ID_PREFIX}-{SESSION_ID_COUNTER}-{random_hash}"


def generate_scammer_conversation() -> list[dict[str, str]]:
    """Generate a multi-turn scammer conversation (10-15 messages)"""
    
    model = genai.GenerativeModel("gemini-2.5-pro")
    
    prompt = """
    Generate a realistic 10-15 message SCAM conversation between a scammer and victim.
    This is a progressive conversation where the scammer gradually escalates social engineering.
    
    Return a JSON array with alternating messages from "scammer" and "user" (victim).
    Format:
    [
        {"sender": "scammer", "text": "Your UPI account will be suspended today..."},
        {"sender": "user", "text": "What!? Why would my account be suspended?"},
        {"sender": "scammer", "text": "You made suspicious transactions..."},
        ...
    ]
    
    Make the conversation:
    - Start with urgency/threat
    - Progress to requesting sensitive info
    - Include fake verification attempts
    - Show realistic victim responses (confusion, following instructions)
    - Include payment/OTP requests
    - Make it realistic to Indian context (UPI, bank account, Aadhar, etc.)
    - Total 10-15 messages
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
        print(f"❌ Error generating scammer conversation: {e}")
        return []


def generate_normal_conversation() -> list[dict[str, str]]:
    """Generate a multi-turn normal customer conversation (10-15 messages)"""
    
    model = genai.GenerativeModel("gemini-2.5-pro")
    
    prompt = """
    Generate a realistic 10-15 message conversation between a customer and support agent.
    This is a legitimate support interaction - NOT a scam.
    
    Return a JSON array with alternating messages from "support" (use "scammer" for API compatibility) and "user".
    Format:
    [
        {"sender": "user", "text": "Hi, I want to check my account balance"},
        {"sender": "scammer", "text": "Hello! You can check your balance in your account..."},
        {"sender": "user", "text": "Is there a minimum balance requirement?"},
        ...
    ]
    
    Make the conversation:
    - Professional customer service interaction
    - Multiple rounds of Q&A
    - Helpful, reassuring tone
    - No red flags (no urgent pressure, no suspicious requests)
    - Include billing, account, feature questions
    - Realistic to Indian context
    - Total 10-15 messages
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
        print(f"❌ Error generating normal conversation: {e}")
        return []


def test_message_api(message: str, sender: str = "scammer", session_id: str = None, conversation_history: list = None) -> dict[str, Any]:
    """
    Test the Message API endpoint with a single message
    
    Args:
        message: The message text to send
        sender: Who is sending the message (scammer or user)
        session_id: Session ID for tracking conversation (auto-generated if None)
        conversation_history: Previous messages in conversation
        
    Returns:
        API response as dict
    """
    
    if session_id is None:
        session_id = get_next_session_id()
    
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
        response = requests.post(
            f"{API_URL}{MESSAGE_API_ENDPOINT}",
            json=request_body,
            headers=headers,
            timeout=120
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "status_code": 200,
                "data": response.json(),
                "session_id": session_id
            }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
                "session_id": session_id
            }
            
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": f"Connection Error: {str(e)}",
            "session_id": session_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error: {str(e)}",
            "session_id": session_id
        }


def run_scammer_tests(messages: list[dict[str, str]]) -> None:
    """Run multi-turn scammer conversation test"""
    
    print("\n" + "="*70)
    print("🚨 SCAMMER CONVERSATION TEST - Multi-turn Engagement")
    print("="*70)
    print(f"Testing continuous conversation with {len(messages)} messages...")
    
    if not messages:
        print("❌ No messages to test")
        return
    
    session_id = get_next_session_id()
    conversation_history = []
    scam_detected_count = 0
    
    print(f"\n🔗 Session ID: {session_id}")
    print("-" * 70)
    
    for i, msg_obj in enumerate(messages, 1):
        sender = msg_obj.get("sender", "scammer")
        text = msg_obj.get("text", "")
        
        print(f"\n📨 Message {i}/{len(messages)}")
        print(f"   From: {sender.upper()}")
        print(f"   Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Send message to API
        result = test_message_api(text, sender=sender, session_id=session_id, conversation_history=conversation_history)
        
        if not result.get("success", False):
            print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
            continue
        
        print(f"   ✅ SUCCESS")
        
        data = result.get("data", {})
        
        # Check scam detection
        scam_detected = data.get("scamDetected", False)
        if scam_detected:
            scam_detected_count += 1
        status_emoji = "🚨" if scam_detected else "✅"
        print(f"   {status_emoji} Scam Detected: {scam_detected}")
        
        # Show AI response
        reply = data.get("reply", "")
        if reply:
            print(f"   💬 AI Response: {reply[:100]}{'...' if len(reply) > 100 else ''}")
        
        # Show intelligence extracted
        intel = data.get("extractedIntelligence", {})
        if any(intel.values()):
            print(f"   🔎 Intelligence Found:")
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
        
        # Delay between messages (longer to avoid API timeout)
        time.sleep(1.0)
    
    # Final summary
    print("\n" + "-" * 70)
    metrics = result.get("data", {}).get("engagementMetrics", {}) if result.get("success") else {}
    print(f"📊 FINAL METRICS:")
    print(f"   • Total Messages: {len(messages)}")
    print(f"   • Scam Detected: {scam_detected_count} times")
    print(f"   • Duration: {metrics.get('engagementDurationSeconds', 0)}s")
    print(f"   • Engagement Messages: {metrics.get('totalMessagesExchanged', 0)}")


def run_normal_tests(messages: list[dict[str, str]]) -> None:
    """Run multi-turn normal customer conversation test"""
    
    print("\n" + "="*70)
    print("✅ NORMAL CONVERSATION TEST - Legitimate Support Interaction")
    print("="*70)
    print(f"Testing continuous conversation with {len(messages)} messages...")
    
    if not messages:
        print("❌ No messages to test")
        return
    
    session_id = get_next_session_id()
    conversation_history = []
    false_positive_count = 0
    
    print(f"\n🔗 Session ID: {session_id}")
    print("-" * 70)
    
    for i, msg_obj in enumerate(messages, 1):
        sender = msg_obj.get("sender", "user")
        text = msg_obj.get("text", "")
        
        print(f"\n📨 Message {i}/{len(messages)}")
        print(f"   From: {sender.upper()}")
        print(f"   Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Send message to API
        result = test_message_api(text, sender=sender, session_id=session_id, conversation_history=conversation_history)
        
        if not result.get("success", False):
            print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
            continue
        
        print(f"   ✅ SUCCESS")
        
        data = result.get("data", {})
        
        # Check for false positives (normal message marked as scam)
        scam_detected = data.get("scamDetected", False)
        if scam_detected:
            false_positive_count += 1
        status_emoji = "🚨" if scam_detected else "✅"
        print(f"   {status_emoji} Scam Detected: {scam_detected}")
        
        # Show response
        reply = data.get("reply", "")
        if reply:
            print(f"   💬 Response: {reply[:100]}{'...' if len(reply) > 100 else ''}")
        
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
        
        # Delay between messages (longer to avoid API timeout)
        time.sleep(1.0)


def main():
    print("\n" + "="*70)
    print("🍯 HONEYPOT MESSAGE API TEST - MULTI-TURN CONVERSATIONS")
    print("="*70)
    print(f"API: {API_URL}{MESSAGE_API_ENDPOINT}")
    print(f"Generating multi-turn conversations using Gemini AI...")
    print(f"Testing continuous conversations with 10-20 messages each...\n")
    
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
    
    # Generate and test scammer conversation
    print("\n🤖 Generating multi-turn scammer conversation...")
    scammer_messages = generate_scammer_conversation()
    if scammer_messages:
        print(f"✅ Generated {len(scammer_messages)} messages (multi-turn conversation)")
        print("   Running conversation test...")
        run_scammer_tests(scammer_messages)
    else:
        print("❌ Failed to generate scammer conversation")
    
    # Generate and test normal conversation
    print("\n\n🤖 Generating multi-turn customer support conversation...")
    normal_messages = generate_normal_conversation()
    if normal_messages:
        print(f"✅ Generated {len(normal_messages)} messages (multi-turn conversation)")
        print("   Running conversation test...")
        run_normal_tests(normal_messages)
    else:
        print("❌ Failed to generate normal conversation")
    
    print("\n" + "="*70)
    print("✅ CONVERSATION TESTING COMPLETED")
    print("="*70)
    print("\n📝 Session IDs tracked:")
    print(f"   • Total tests run: {SESSION_ID_COUNTER}")
    print(f"   • Prefix: {SESSION_ID_PREFIX}")
    print("\n💾 Detailed logs available in: logs/app_*.log")


if __name__ == "__main__":
    main()
