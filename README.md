# Honeypot Scam Detection API 🍯🤖

An intelligent, AI-driven Honeypot API designed to detect, engage, and extract intelligence from active scammers in real-time. Built specifically for the GUVI AI Hackathon, this server leverages Google's advanced Gemini models to simulate realistic human personas, stall attackers for extensive durations, and natively extract high-value Indicators of Compromise (IOCs) like Bank Accounts, UPI IDs, and Phishing Links.

## 📖 Documentation
Detailed technical documentation has been separated into dedicated files to maintain a clean root repository:
- [System Architecture & Flow Design](docs/architecture.md)
- [API Reference & Payload Schemas](docs/api_reference.md)

## 🛠️ Tech Stack
- **Language/Framework**: Python 3.10+, FastAPI, Uvicorn (ASGI)
- **Database**: MongoDB (motor async driver)
- **Key Libraries**: Pydantic, HTTPX, google-generativeai
- **LLM/AI Models**: `gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`

## 🔌 API Endpoint
- **URL**: `https://<your-deployed-url>.com/api/message` (or `/api/v1/honeypot`)
- **Method**: `POST`
- **Authentication**: `x-api-key` header

## 🧠 Approach

### How we detect scams
We leverage a rapid-fire Gemini LLM (`gemini-2.5-flash-lite`) exclusively on the 2nd conversational turn. The background detector parses the initial message and the user's intent to identify high-risk indicators (threats, urgency, requests for PII) and immediately flags the session. Once flagged, the detection engine caches the result and bypasses itself on future turns to drastically minimize latency.

### How we extract intelligence
Intelligence is extracted organically via a robust RegEx engine combined with explicit AI Persona prompting. The conversational bot is explicitly instructed to end every message with a question targeted at acquiring 1 of 8 specific entities (Phone Numbers, Bank Accounts, UPI IDs, Phishing Links, Email Addresses, Case IDs, Policy Numbers, Order Numbers). The background processor then parses these entities synchronously upon every response.

### How we maintain engagement
Our proxy LLM adopts highly realistic human personas (e.g., confused senior, angry customer) and utilizes progressive context windowing. To prevent repetition or dead-ends, the AI is explicitly instructed to *always* ask a question and naturally stall by asking for procedural clarifications. The system utilizes background workers to guarantee near-zero latency, keeping scammers hooked with immediate replies.

## 🚀 Key Features
- **Dynamic AI Rotation**: Seamlessly rotates between `gemini-2.5-flash-lite`, `gemini-2.5-flash`, and `gemini-2.5-pro` with an automatic 60-second cooldown memory cache if Rate Limits (429) are encountered.
- **Context Preservation**: Dynamically scales conversational memory token limits upward (1000->2000->4000) based on turn depth to prevent hallucination looping.
- **Extraction Engine**: Robust regex heuristics pipeline capable of parsing Bank Accounts, Phishing Links, Phone Numbers, and dynamically stripping Case IDs without relying on LLM parsing limitations.
- **Hackathon Hardened**: Guarantees a 100-point maximum metric output by forcing `>16 message` saturation interactions and perfectly formatting the nested Pydantic GUI Telemetry JSON string.

## 📁 Project Structure
```
honeypotscammer/
├── app/                      # Application Source Code
│   ├── services/             # Core Logic (AI Agent, Scam Detector, Regex Extractor)
│   ├── utils/                # Webhook Callbacks & Monitors
│   ├── models.py             # Pydantic Schemas
│   └── main.py               # FastAPI Initializer
├── docs/                     # Technical System Documentation
│   ├── api_reference.md
│   └── architecture.md
├── tests/                    # Testing & Simulation Scripts
│   ├── live_test_ai_agent.py # Real-time Scammer vs Honeypot AI Simulator
│   ├── batch_test_rig.py     # Bulk CSV metric evaluator
│   └── test_e2e.py           # Unit validations
├── .env.example              # Environment Variable Template
└── requirements.txt          # Python Dependencies
```

## 🛠️ Quick Start

### 1. Installation
Clone the repository and install the dependencies:
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and fill in the required keys.
Note: You MUST provide `GEMINI_API_KEY` for the system to generate intelligent responses. 
```bash
API_KEY=your_secure_authentication_key
GEMINI_API_KEY=AIzaSy...
MONGODB_URL=mongodb://user:pass@host:27017/db
MONGODB_DB_NAME=honeypotfraud
GUVI_CALLBACK_URL=https://hackathon.guvi.in/api/updateHoneyPotFinalResult
```

### 3. Run the API Server
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
*The Interactive Testing UI is accessible at `http://localhost:8000/`.*

### 4. Run the Live AI Simulator (Testing)
Located in the `/tests` directory, this script spawns a dedicated LLM instructed to play the role of a scammer and attacks your local Honeypot API in real-time to generate a full 16-turn scored Webhook payload:
```bash
python tests/live_test_ai_agent.py
```
