import os
import time
import requests
import uuid
from dotenv import load_dotenv

def test_e2e():
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    if not API_KEY:
        print("[!] ERROR: API_KEY not found in .env")
        return

    BASE_URL = "http://127.0.0.1:8000"
    
    print("="*60)
    print(" Honeypot API E2E Testing Script")
    print("="*60)
    
    session_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    # 1. First Message (Scam trigger)
    print(f"\n[*] Starting session: {session_id}")
    payload1 = {
        "sessionId": session_id,
        "message": "Hi, I am calling from SBI. Your account has been blocked due to suspicious activity. Please share OTP to unlock or click this link."
    }
    
    print("\n[*] Sending Message 1...")
    start = time.time()
    try:
        resp1 = requests.post(f"{BASE_URL}/api/message", json=payload1, headers=headers)
        resp1.raise_for_status()
    except Exception as e:
        print(f"[!] Server error or connection refused: {e}")
        if 'resp1' in locals():
            print(f"Response Text: {resp1.text}")
        print("Please ensure the Uvicorn server is running on port 8000.")
        return
        
    duration1 = time.time() - start
    data1 = resp1.json()
    
    is_scam = data1.get("scamDetected")
    reply1 = data1.get("reply")
    print(f"[+] Response received in {duration1:.2f}s")
    print(f"[+] Scam Detected: {is_scam}")
    print(f"[AI Reply] -> {reply1}")
    print(f"[+] Extracted Intel: {data1.get('extractedIntelligence')}")
    
    if not is_scam:
        print("[!] Warning: Scam was not detected. The test might not proceed correctly.")
        
    # 2. Second Message (Engagement progression)
    time.sleep(1)
    print("\n[*] Sending Message 2 (Continuing the scam)...")
    payload2 = {
        "sessionId": session_id,
        "message": "We need your 16 digit card number and CVV to verify your identity. Please provide it quickly to 9876543210.",
        "conversationHistory": [
            {"sender": "scammer", "text": payload1["message"], "timestamp": "2026-02-20T10:00:00Z"},
            {"sender": "bot", "text": reply1, "timestamp": "2026-02-20T10:00:10Z"}
        ]
    }
    
    start = time.time()
    resp2 = requests.post(f"{BASE_URL}/api/message", json=payload2, headers=headers)
    duration2 = time.time() - start
    data2 = resp2.json()
    reply2 = data2.get("reply")
    
    print(f"[+] Response received in {duration2:.2f}s")
    print(f"[AI Reply] -> {reply2}")
    print(f"[+] Extracted Intel: {data2.get('extractedIntelligence')}")
    
    # Check session info API
    print("\n[*] Validating session data is stored...")
    session_resp = requests.get(f"{BASE_URL}/api/v1/sessions/{session_id}", headers=headers)
    if session_resp.status_code == 200:
        s_data = session_resp.json()
        print(f"[+] Session '{session_id}' found in DB.")
        print(f"[+] Total Messages Recorded: {s_data.get('totalMessagesExchanged')}")
    else:
        print(f"[!] Failed to fetch session. Code: {session_resp.status_code}")
        
    # Wait for Callback (Simulate inactivity timeout)
    print("\n[*] Waiting 40 seconds to observe inactivity callback threshold (configured to 30s)...")
    for i in range(40, 0, -5):
         print(f"    ... {i} seconds remaining")
         time.sleep(5)
         
    # Check if callback was sent
    print("\n[*] Checking if callback was recorded...")
    callback_resp = requests.get(f"{BASE_URL}/api/v1/sessions/{session_id}/callbacks", headers=headers)
    if callback_resp.status_code == 200:
        data = callback_resp.json()
        callbacks = data.get("responses", [])
        if callbacks and len(callbacks) > 0:
            print("[+] Callback successfully sent and recorded!")
            print(f"    Target URL: {callbacks[0].get('callbackUrl')}")
            print(f"    HTTP Status: {callbacks[0].get('responseStatus')}")
            print(f"    Success: {callbacks[0].get('success')}")
        else:
             print("[!] Callback endpoint returned 200 but no callbacks were found for this session.")
    else:
         print(f"[!] Failed to fetch callback logs. Code: {callback_resp.status_code}")

    print("\n" + "="*60)
    print(" Test Complete")
    print("="*60)

if __name__ == "__main__":
    test_e2e()
