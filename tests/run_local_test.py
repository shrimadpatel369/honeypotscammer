import subprocess
import time
import requests
import uuid
import os
import json
from dotenv import load_dotenv

load_dotenv()
print("Starting server...")
my_env = os.environ.copy()
my_env["ENV"] = "development"
server = subprocess.Popen([".venv/Scripts/python.exe", "-m", "uvicorn", "app.main:app", "--port", "8000"], env=my_env)
time.sleep(5)

try:
    session_id = str(uuid.uuid4())
    url = "http://127.0.0.1:8000/api/message"
    headers = {"X-API-Key": os.getenv("API_KEY", "Dm59xTVhENeQ2x2Jr9xt5qEpTYWbKhiYDkOuZ2rVdC63yMaWTg"), "Content-Type": "application/json"}
    payload = {
        "sessionId": session_id,
        "message": "Hi, I am calling from SBI. Share your 16 digit card number to 9876543210 immediately. Your account will be closed if not.",
        "testing": True
    }
    print(f"Sending payload...")
    resp = requests.post(url, json=payload, headers=headers)
    print(f"API Response: {resp.status_code}")
    print(f"API Body: {resp.text}")
    
    # Wait for background task to finish calling gemini and webhooking
    print("Waiting 10 seconds for asynchronous background processes to complete...")
    for i in range(10):
        time.sleep(1)
        print(f"Wait {i+1}/10...")
    
    if os.path.exists("mock_callback_payload.json"):
        with open("mock_callback_payload.json", "r") as f:
            data = json.load(f)
            print("\n========================================")
            print("✅ MOCK CALLBACK PAYLOAD SUCCESSFULLY GENERATED!")
            print("========================================")
            print(json.dumps(data, indent=2))
    else:
        print("\n❌ MOCK CALLBACK FILE NOT FOUND - Check server logs for errors")
finally:
    server.terminate()
    server.wait()
    print("Server stopped.")
