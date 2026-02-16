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
    - Fill in your API keys (Gemini API Key is required) and MongoDB connection string.
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

### Scam Detection
The system employs a multi-layered approach to detect scams:
1.  **Keyword Analysis**: Scans messages for urgency markers ("immediate", "block", "expire") and financial keywords.
2.  **Contextual Analysis**: The AI agent analyzes the conversation history to detect patterns of manipulation, authority claims, and unparalleled urgency.
3.  **Heuristic Scoring**: Calculates a scam probability score based on the presence of known scam indicators.

### Intelligence Extraction
To gather actionable intelligence, the system:
1.  **Entity Extraction**: Uses Regex and NLP techniques to identify phone numbers, UPI IDs, bank accounts, and URLs.
2.  **Conversation Probing**: The AI persona asks targeted questions (e.g., "Which bank?", "Can I have payment details?") to elicit specific information from the scammer.
3.  **Structured Logging**: All extracted data is structured and stored in the session log for analysis.

### Engagement Strategy
The honeypot maintains engagement through:
1.  **Dynamic Personas**: Simulates various human profiles (e.g., "Elderly Trusting", "Busy Professional", "Skeptical User") to match the scammer's tactic.
2.  **Realistic Latency**: Introduces natural delays and "typing" behaviors.
3.  **Adaptive Responses**: The AI adjusts its tone and hesitation level based on the scammer's aggression, appearing vulnerable to keep the scammer hooked.
