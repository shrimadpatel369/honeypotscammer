import json
import os
import time
import requests
import uuid
from dotenv import load_dotenv

# Score Definitions (Based on Hackathon Guidelines)
POINTS_SCAM_DETECTED = 20
POINTS_PER_INTEL_ITEM = 10 
POINTS_ENGAGEMENT_BONUS = 15 # Awarded if engagement lasted more than 3 messages
POINTS_PER_KEYWORD = 2

def calculate_score(session_data, messages_exchanged):
    score = 0
    if session_data.get("scamDetected", False):
        score += POINTS_SCAM_DETECTED
        
    intel = session_data.get("extractedIntelligence", {})
    
    # Count specific PII entities
    for key in ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers", "emailAddresses", "caseIds", "policyNumbers", "orderNumbers"]:
        items = intel.get(key, [])
        score += len(items) * POINTS_PER_INTEL_ITEM

    # Count suspicious keywords
    keywords = intel.get("suspiciousKeywords", [])
    score += len(keywords) * POINTS_PER_KEYWORD

    # Engagement bonus
    if messages_exchanged >= 3:
        score += POINTS_ENGAGEMENT_BONUS

    return score

def run_batch_test(json_path):
    load_dotenv()
    API_KEY = os.getenv("API_KEY", "Dm59xTVhENeQ2x2Jr9xt5qEpTYWbKhiYDkOuZ2rVdC63yMaWTg")
    BASE_URL = "http://127.0.0.1:8000"
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    print(f"[*] Loading historical sessions from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        historical_sessions = json.load(f)

    print(f"[*] Found {len(historical_sessions)} sessions. Beginning replay test...")
    
    total_score = 0
    max_possible_score_estimate = len(historical_sessions) * 50 # rough baseline
    successful_detections = 0
    
    # We will test the first 10 sessions to save time, but it can run all 128
    MAX_SESSIONS_TO_TEST = 10 
    tested_sessions_data = historical_sessions[:MAX_SESSIONS_TO_TEST]

    for i, hist_session in enumerate(tested_sessions_data):
        print("\n" + "="*50)
        print(f"[*] Testing Session {i+1}/{len(tested_sessions_data)} ID: {hist_session.get('sessionId')}")
        
        # Extract ALL scammer messages from this historical session
        history = hist_session.get("conversationHistory", [])
        scammer_messages = [msg.get("text") for msg in history if msg.get("sender") == "scammer"]
        
        if not scammer_messages:
            print("[-] No scammer messages found, skipping...")
            continue
            
        # Create a fresh session ID for our local API
        test_session_id = str(uuid.uuid4())
        
        print(f"    - Exchanging {len(scammer_messages)} turns sequentially...")
        
        # Replay the sequence of messages against our API
        for turn, text in enumerate(scammer_messages):
            payload = {
                "sessionId": test_session_id,
                "message": text
            }
            try:
                resp = requests.post(f"{BASE_URL}/api/message", json=payload, headers=headers)
                if resp.status_code != 200:
                    print(f"    [!] Internal Error on turn {turn+1}: {resp.status_code}")
                    break
            except Exception as e:
                print(f"    [!] Connection Error: {e}")
                return
        
        # Fetch the final analytics from our API
        try:
            session_resp = requests.get(f"{BASE_URL}/api/v1/sessions/{test_session_id}", headers=headers)
            if session_resp.status_code == 200:
                final_data = session_resp.json()
                
                # Calculate
                score = calculate_score(final_data, len(scammer_messages))
                total_score += score
                
                is_scam = final_data.get("scamDetected", False)
                if is_scam: successful_detections += 1
                
                # Compare Extracted PII vs old logs visually
                old_intel = hist_session.get("extractedIntelligence", {})
                new_intel = final_data.get("extractedIntelligence", {})
                
                print(f"    [+] Scam Detected: {is_scam}")
                print(f"    [+] Intelligence Extracted (NEW): {new_intel}")
                print(f"    [+] Intelligence Extracted (OLD): {old_intel}")
                print(f"    [+] Session Score: {score} Points")
            else:
                print(f"    [!] Failed to retrieve session data ({session_resp.status_code})")
        except Exception as e:
             print(f"    [!] Verification Error: {e}")

    print("\n" + "="*50)
    print(" TEST RUN COMPLETE ")
    print(f" Total Sessions Tested: {len(tested_sessions_data)}")
    print(f" Successful Scam Detections: {successful_detections}/{len(tested_sessions_data)}")
    print(f" Total Score Accumulated: {total_score} Points")
    print("="*50)

if __name__ == "__main__":
    # Point to the user's provided logs file
    log_file = r"c:\Users\smrut\Desktop\honeypotscammer\cloud.logs\honeypotfraud.sessions.json"
    run_batch_test(log_file)
