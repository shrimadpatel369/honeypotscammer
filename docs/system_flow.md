# Honeypot System Flow Details

This document provides a deep dive into the inner workings of the Honeypot Scam Detection API, specifically detailing the lifecycle of a message, how the webhook callback is triggered, and the mechanics of the scam detection engine.

---

## 1. The Message API Flow (`POST /api/v1/honeypot`)

Every interaction with the scammer follows a strict, stateful pipeline to ensure memory is preserved and intelligence is extracted continuously. 

1. **Ingestion & Validation**: The incoming JSON payload is validated through Pydantic (`HoneypotRequest`). The `sessionId` is extracted to identify if this is a new or ongoing conversation.
2. **State Restoration (In-Memory Fast-Path)**: The system queries the local RAM `CacheService` for the `sessionId`. 
   - If found, the historical conversation context is loaded instantly (0ms latency).
   - If it misses, it falls back to MongoDB, mounts the session into the RAM Cache (`3600s TTL`), and proceeds. This drastically reduces NoSQL read/write overheads.
3. **Deferred Scam Detection (Turn 2+)**: Scam evaluation is explicitly deferred until the conversation reaches Turn 2. Single-word openers (e.g. "Hi", "Hello") lack sufficient context for accurate categorization. By waiting until the second message is received, Gemini is able to confidently extract the intent and evaluate `scamDetected`.
4. **Intelligence Extraction**: The raw message is passed through the `IntelligenceExtractorService`, which uses regex to passively strip any IOCs (Bank Accounts, UPI IDs, links) hidden in the text.
5. **AI Engagement (Zero-Latency Fast Path)**: The `AIAgentService` kicks in. It dynamically adjusts its Gemini model tier (e.g. `3-pro or 2.5-pro, 3-flash or 2.5-flash, 2.5-flash-lite or 1.5-flash`) and its memory token limits based on how deep the conversation is. It then generates a manipulative, stalling response to keep the scammer hooked.
6. **State Persistence (Background Thread)**: The AI's reply is returned synchronously to the client as an HTTP 200 response the instant it generates natively. Meanwhile, the actual Intelligence Extraction heuristics, database IO, local Cache writes, and Callback Saturation Checks are pushed into a fully isolated FastAPI `BackgroundTasks` queue. This guarantees that `POST /api/v1/honeypot` maintains 0ms latency from blocking logic.

---

## 2. When & How is the Callback Triggered?

The Hacker/Evaluator needs the final collected intelligence (the 100-point payload json) sent to the `GUVI_CALLBACK_URL`. Our system triggers this payload generation in two specific ways to guarantee delivery:

### Primary Trigger (Dynamic Scoring Saturation)
At the end of the Message API Flow, the background worker checks if the session has saturated the max Hackathon grading rubric. Because sending the webhook too early (even with the 16-message minimum) forfeits data extraction points, the system prioritizes *Intelligence Gathering* over raw limits. 

The payload is constructed and fired asynchronously using `httpx` to the `GUVI_CALLBACK_URL` when ONE of the following three tiers is met:

**Tier 1: Optimal Extraction (Primary Goal)**
- **Rule 1**: The base Engagement points are secured (>= 16 Msgs AND >= 180s).
- **Rule 2**: The AI has asked **5 or more** parsed questions over the course of the dialogue.
- **Rule 3**: The Scam Detector has identified **5 or more** distinct Red Flags.
*(Note: Because the "Maximum Intelligence Points" varies wildly based on the specific evaluator scenario, the system relies on the Tier 2 4-turn Repetition Fallback to mathematically deduce when all available PII has been exhausted)*

**Tier 2: Repetition Fallback (The Scammer Gave Up)**
- **Rule 1**: The base Engagement points are secured (>= 16 Msgs AND >= 180s).
- **Rule 2**: The AI extracted at least *something*, but the scammer has failed to provide any new data points for the last **4 turns**, marking the session as an unrecoverable loop. 
- **Rule 3**: Or, the AI natively determined it cannot extract further data and returned an empty string.

**Tier 3: Infinite Loop Hard Limit (Fail-safe)**
- The system prevents deadlocked server sessions by strictly terminating and submitting ANY interaction that exceeds **30 Messages** or **300 Seconds**, regardless of what intelligence was pulled.

### Secondary Fallback Trigger (Asynchronous Timeout)
What if the scammer just stops responding at Turn 5? The API would never get hit again, and the callback would never fire.
To prevent this, the `CallbackMonitor` runs continuously in the background using `asyncio`.
- Every **30 seconds**, it scans MongoDB.
- It searches for `active` sessions where `lastUpdateTime` was more than **90 seconds** ago.
- If it finds a stale session where the scammer gave up or the evaluator stopped sending requests, the monitor forcefully pulls the data, marks the session as `completed`, and fires the payload to the `GUVI_CALLBACK_URL`. 

This guarantees that NO intelligence is ever lost, and the Hackathon webhook is *always* hit.

---

## 3. How Scam Detection Works

The `ScamDetectorService` is optimized to be the fastest, most rigid component of the machine. It operates at the very beginning of a new session to determine **if** we even want to waste AI tokens talking to the sender.

1. **The Model Matrix**: It defaults to using `gemini-2.5-flash-lite`, configuring it with a strict temperature of `0.0`. This ensures it generates deterministic, mathematical output rather than creative writing.
2. **Context Passing**: It takes the raw text and compares it against explicit "Red Flag" prompt indicators (e.g., sense of urgency, requesting OTPs, threatening account closure).
3. **Multi-Lingual Processing**: The prompt guarantees the AI can process romanized localized phrases like "account block ho jayega" (Hinglish).
4. **JSON Serialization**: It outputs a strictly formatted JSON array containing `is_scam`, a floating point `confidenceLevel` (e.g. 0.95), and the `scamType` (e.g. "bank_fraud"). 
5. **Fallback Safety**: If the Gemini API drops the connection or flags a `429 Rate Limit` during this process, the `_model_cooldowns` memory lock excludes the exhausted model for 60-seconds. The detector instantly routes to the next tier (`gemini-3-flash` -> `gemini-2.5-flash` -> `gemini-1.5-flash`). If every single API endpoint suffers an outage simultaneously, the detector finally collapses down into a Lightning Keyword heuristics search (looking for hardcoded trigger words like "OTP" or "Winner") guaranteeing the application never throws an Internal Server Exception on the Evaluator's monitor.
