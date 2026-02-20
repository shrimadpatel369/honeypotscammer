# Honeypot Scam Detection System - Architecture

## High-Level Flow
The Honeypot Scam Detection system is an AI-powered intercept layer designed to detect, engage, and extract intelligence from active scammers in real-time. 

### Data Flow Pipeline
1. **Ingestion**: The system receives a message from an external client (e.g., SMS, WhatsApp, Web) via the `POST /api/message` endpoint.
2. **Context Resolution**: The request is routed to the `HoneypotRouter`. It checks the `sessionId` against the local MongoDB instance to restore the entire conversational memory and extraction state.
3. **Scam Detection (Initial Pass)**: If the session is new, the message is sent to `ScamDetectorService` to evaluate if the message exhibits fraudulent intent.
    - Uses Gemini-2.5-Flash-Lite (default) for high-speed pattern recognition.
    - Evaluates against localized languages (Hinglish, Gujarati, Tamil, etc.).
4. **Active Engagement**: The `AIAgentService` impersonates a vulnerable target to respond to the scammer.
    - Rotates between `gemini-2.5-flash-lite`, `gemini-3-flash`, and `gemini-3-pro` dynamically based on conversation depth and API Rate Limit (`429`) cooldowns.
    - Built-in prompt engineering forces the AI to extract specific details over an extended 16+ message span without repeating itself.
5. **Intelligence Extraction**: The `IntelligenceExtractorService` uses targeted Regex heuristics to passively strip high-value IOCs (Indicators of Compromise) like `UPI IDs`, `Bank Accounts`, `URLs`, and `Phone Numbers` from the scammer's raw inputs.
6. **Telemetry Callback**: Once the conversation hits the max Hackathon Scoring criteria (16+ expected messages, >180s duration) OR the AI determines it cannot extract any further intelligence, the loop is terminated. A comprehensive `GuviCallbackPayload` is generated and asynchronously POSTed to the external evaluator webhook.

## Microservices Breakdown

### 1. `app/services/scam_detector.py`
Optimized for the lowest-latency decision making. It uses a strictly deterministic temperature (`0.0`) to guarantee that its JSON output parses correctly every time. It uses memory-based models cooldown caching for automatic 429 backoff logic.

### 2. `app/services/ai_agent.py`
The core conversational engine. Built with advanced Memory Context scaling:
- **Truncation Prevention**: Scales its token generation limit dynamically based on turn depth (1000 -> 2000 -> 4000 tokens).
- **Memory Preservation**: Preserves up to 30 messages of conversational history to stop fallback repetitions.
- **RPM Hardening**: Features a 60-second lockout dictionary for models that trip Google's API limits, safely bypassing throttling.

### 3. `app/services/intelligence_extractor.py`
A robust Regex parsing engine designed to extract 9 specific categories of indicators natively, mapping formats like IBAN accounts, US Phone formatting, specific `@paytm` UPI signatures, and case ticket IDs without relying on LLM hallucination.

### 4. `app/utils/callback.py`
Listens for the completion of the chat limits (`session["totalMessages"] >= 16 and duration_seconds > 180`), and formats the extracted data dynamically into the 100-point metric payload string. It reliably HTTP POSTs the data to the configured GUVI backend endpoint.
