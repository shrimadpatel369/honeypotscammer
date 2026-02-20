# Honeypot Scam Detection API

## Description
This project implements an intelligent Honeypot API designed to detect scams, extract intelligence, and engage scammers in realistic conversations. The system uses advanced AI models to simulate human personas, analyze conversation context, and extract critical information like bank accounts, UPI IDs, and phishing links. It is built to handle various scam scenarios including Bank Fraud, UPI Fraud, and Phishing attempts.

## Tech Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: MongoDB (via Motor for async)
- **AI/LLM**: Google Gemini Pro (via `google-generativeai`)
- **Key Libraries**: 
  - `pydantic` for data validation
  - `slowapi` for rate limiting
  - `httpx` for async HTTP requests

## Setup Instructions

1.  **Clone the repository**
    ```bash
    git clone <your-repo-url>
    cd honeypot-api
    ```

2.  **Create a virtual environment**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set environment variables**
    - Copy `.env.example` to `.env`
    - Fill in your ONLY these 5 explicitly required variables: `API_KEY`, `MONGODB_URL`, `MONGODB_DB_NAME`, `GEMINI_API_KEY`, and `GUVI_CALLBACK_URL`.
    - Note: All other timeout, model, and port settings are hardcoded into `app/config.py` for submission stability.
    ```bash
    cp .env.example .env
    ```

5.  **Run the application**
    ```bash
    python -m app.main
    # Or using uvicorn directly:
    uvicorn app.main:app --reload
    ```

## API Endpoint
- **URL**: `https://<your-deployed-domain>/api/v1/honeypot`
- **Method**: `POST`
- **Authentication**: `x-api-key` header (optional, configured in `.env`)
- **Root URL**: `https://<your-deployed-domain>/` serves a testing UI.

## Approach

### Scam Detection & Scoring Extraction
The system employs a multi-layered approach to detect scams and natively formats them for the Hackathon Evaluation metrics:
1. **Keyword Analysis**: Scans messages for high-confidence urgency markers ("OTP", "block", "prize") which can act as a sub-10ms fallback detection.
2. **Contextual Analysis (Gemini Flash-Lite)**: The AI agent assigns a `confidenceLevel` float and categorizes the interaction into a `scamType` (e.g. `bank_fraud`, `phishing`).
3. **Information Elicitation**: Generates dynamic prompts with forced directives to stall hackers for `>8 Turns` and natively ask `>5 Questions`.

### Intelligence Extraction
To gather actionable intelligence and maximize Extracted Data Points (30 pts):
1.  **Entity Regex Extraction**: Natively extracts Phone numbers, UPI IDs, Bank accounts, URLs, Case IDs, Order Numbers, and Policy Numbers immediately as the scammer blurts them out.
2.  **Conversation Probing**: The AI persona implicitly targets 5+ 'Red Flags' (e.g., "Why would a bank need my OTP?").
3.  **Webhook Compliance**: The auto-generated GUVI webhook payload cleanly structures flat `engagementDurationSeconds` properties alongside the nested `engagementMetrics` object to ensure parsers from the evaluation engine do not miss them.

### Engagement Strategy
The honeypot maintains engagement through:
1.  **Dynamic Personas**: Simulates various human profiles (e.g., "Elderly Trusting", "Busy Professional", "Skeptical User") to match the scammer's tactic.
2.  **Realistic Latency**: Introduces natural delays and "typing" behaviors.
3.  **Adaptive Responses**: The AI adjusts its tone and hesitation level based on the scammer's aggression, appearing vulnerable to keep the scammer hooked.

### Engagement Metrics
The system tracks and reports:
- **Duration**: Total time the scammer was kept engaged.
- **Message Count**: Number of turns in the conversation.
- These metrics are sent in the final callback to quantify the "time wasted" for the scammer.
