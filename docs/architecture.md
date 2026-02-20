# Honeypot API Architecture

## System Design
Our Honeypot system is built around a dynamic, asynchronous event-driven architecture using **FastAPI** to ensure low-latency responses (under the strict 30s threshold).

### Core Components:
1. **API Gateway (`app/main.py`)**: Handles the core POST webhook and orchestrates the flow of data.
2. **Intent Engine (`app/services/scam_detector.py`)**: Uses Google's efficient **Gemini 2.5 Flash-Lite** to analyze the conversational context and assign a `confidenceLevel` string and `scamType` categorization within sub-seconds.
3. **Persona Engine (`app/services/ai_agent.py`)**: Once an interaction flags high confidence for malicious intent, this engine assumes one of several dynamic personas (e.g., Tech-Illiterate Senior, Busy Professional) designed to perfectly counter the `scamType` identified.
4. **Intelligence Extractor (`app/services/intelligence_extractor.py`)**: A parallel processing service that uses Regex and NLP heuristics to comb through the scammer's messages and extract Entity data (Bank Accounts, Phone Numbers, UPI IDs, Order Numbers).
5. **Callback Monitor (`app/services/callback_monitor.py`)**: Runs asynchronously in the background. It measures Engagement Durations and Turn Counts. Once a threshold is met or the conversation terminates, it fires the `finalOutput` payload.

## State Management
We utilize **MongoDB** via `Motor` for non-blocking asynchronous database transactions. This allows the system to instantaneously track and recall:
- The full `conversationHistory` array for context windowing.
- Rolling aggregation of `engagementMetrics` to ensure we hit maximum points for long durations.
- The evolving state of `extractedIntelligence` so the AI knows what data points it still needs to elicit.

## Optimization Strategies
- **Dynamic Model Degradation**: We leverage `gemini-2.5-flash-lite` for the fastest Turn 1-3 detections to guarantee < 15s responses, avoiding the 30s timeout failure penalty.
- **Rule-Based Prioritization**: Known scam indicators ("OTP", "cvv") map directly to a high `confidenceLevel` via heuristic dictionaries before the LLM is even invoked, saving crucial bandwidth and reducing processing time to < 0.1s. 
- **Prompt Engineering for Maximum Scoring**: The core System Prompts explicitly instruct the LLM to target the exact metrics evaluated in the Hackathon: (1) Ask 5+ questions, (2) Keep engagement > 8 turns, (3) Extract 5+ specific Red Flags.
