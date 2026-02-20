import requests
import time
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

API_KEY = os.getenv("API_KEY")
URL = "https://honeypotscammer-136046240844.asia-south2.run.app/api/v1/honeypot"

headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

session_id = str(uuid.uuid4())

payload = {
    "sessionId": session_id,
    "message": "Hello, I am calling from the SBI Bank fraud department. Your account is about to be suspended. Please verify your identity."
}

print(f"Testing URL: {URL}")
print(f"Session ID: {session_id}")
print(f"API Key Length: {len(API_KEY) if API_KEY else 0}")
print("Sending request...")

start = time.time()
try:
    response = requests.post(URL, json=payload, headers=headers, timeout=20.0)
    duration = time.time() - start
    
    print(f"\nResponse Time: {duration:.2f}s")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nResponse Match Successful!")
        print(f"Status: {data.get('status')}")
        print(f"Reply: {data.get('reply')}")
    else:
        print(f"Error Body: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")
