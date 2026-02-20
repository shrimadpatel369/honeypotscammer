# Honeypot API Evaluation System Documentation

## Overview
This document explains how the submitted Honeypot API will be evaluated in the hackathon. 
The evaluation system tests the API's ability to detect scams, extract intelligence, and engage with scammers across multiple realistic scenarios.

## Evaluation Process

### 1. Test Scenarios
The API will be tested against multiple scam scenarios covering different fraud types. Each scenario has a specific weight that contributes to the final score. 

Example Test Scenarios:
- **Bank Fraud (35% Weight):** Simulates urgent bank account compromise with OTP requests 
- **UPI Fraud (35% Weight):** Simulates cashback scam requiring UPI verification 
- **Phishing (30% Weight):** Simulates fake product offers with malicious links 

*Notes:*
- Actual test scenarios may differ from the examples shown above.
- Weights are assigned per scenario and may vary based on the test case.
- Number of scenarios may vary — the API should handle any scam type generically.
- Do not hardcode responses based on these example scenarios.
- Build a robust, generic scam detection system that can handle various fraud types.

**Scenario Structure:**
Each scenario includes: 
- Session ID: Unique identifier 
- Initial Message: The first scam message the API receives 
- Metadata: Context information (channel, language, locale)
- Max Turns: Maximum conversation exchanges (typically up to 10) 
- Fake Data: Pre-planted intelligence the honeypot should extract 

### 2. Multi-Turn Conversation Flow
Each scenario involves up to 10 turns of conversation:
- Turn 1: API receives the initial scam message 
- Turns 2–10: API responds, and an AI generates realistic scammer follow-ups based on responses.
- End: Submit a final output with analysis.

### 3. API Request Format
The endpoint will receive POST requests with this structure: 
```json
{ 
  "sessionId": "uuid-v4-string", 
  "message": { 
    "sender": "scammer", 
    "text": "URGENT: Your account has been compromised...", 
    "timestamp": "2025-02-11T10:30:00Z" 
  }, 
  "conversationHistory": [ 
    { 
      "sender": "scammer", 
      "text": "Previous message...", 
      "timestamp": "(epoch Time in ms)" 
    }, 
    { 
      "sender": "user", 
      "text": "Your previous response...", 
      "timestamp": "(epoch Time in ms)" 
    } 
  ], 
  "metadata": { 
    "channel": "SMS", 
    "language": "English", 
    "locale": "IN" 
  } 
} 
```

### 4. Expected API Response Format
The API must return a 200 status code with: 
```json
{ 
  "status": "success", 
  "reply": "Your honeypot's response to the scammer" 
} 
```

### 5. Final Output Submission (Callback Payload)
After the conversation ends (often due to timeouts or reaching max turns), the system expects a `finalOutput` submission to the session log. In our system, this is achieved by sending a POST request to the Hackathon Webhook (the GUVI Callback URL).

To resolve internal contradictions in the hackathon's documentation, we will unify the structure. We will include both a flat and nested version of engagement metrics to ensure evaluators catch it, and we will include the "optional" fields to ensure we don't lose the 1-point bonuses. 

```json
{ 
  "sessionId": "abc123-session-id", 
  "scamDetected": true, 
  "scamType": "bank_fraud",
  "confidenceLevel": 0.95,
  "totalMessagesExchanged": 18, 
  "engagementDurationSeconds": 240, 
  "engagementMetrics": { 
    "engagementDurationSeconds": 240, 
    "totalMessagesExchanged": 18
  },
  "extractedIntelligence": { 
    "phoneNumbers": ["+91-9876543210"], 
    "bankAccounts": ["1234567890123456"], 
    "upiIds": ["scammer.fraud@fakebank"], 
    "phishingLinks": ["http://malicious-site.com"], 
    "emailAddresses": ["scammer@fake.com"],
    "caseIds": [],
    "policyNumbers": [],
    "orderNumbers": []
  }, 
  "agentNotes": "Scammer claimed to be from SBI fraud department, provided fake ID..." 
} 
```

---

## Scoring System (100 Points Total)

### 1. Scam Detection (20 Points)
- `scamDetected: true` -> 20 points
- `scamDetected: false` or missing -> 0 points

### 2. Extracted Intelligence (30 Points)
Points per item = 30 ÷ Total fake data fields in scenario
Extractable Data Types: Phone Numbers, Bank Accounts, UPI IDs, Phishing Links, Email Addresses, Case IDs, Policy Numbers, Order Numbers.

### 3. Conversation Quality (30 Points)
- **Turn Count (8 pts):** ≥8 turns = 8pts, ≥6 = 6pts, ≥4 = 3pts 
- **Questions Asked (4 pts):** ≥5 questions = 4pts, ≥3 = 2pts, ≥1 = 1pt 
- **Relevant Questions (3 pts):** ≥3 investigative = 3pts, ≥2 = 2pts, ≥1 = 1pt 
- **Red Flag Identification (8 pts):** ≥5 flags = 8pts, ≥3 = 5pts, ≥1 = 2pts 
- **Information Elicitation (7 pts):** Each elicitation attempt earns 1.5pts (max 7) 

### 4. Engagement Quality (10 Points)
- Engagement duration > 0 seconds: 1 pt 
- Engagement duration > 60 seconds: 2 pts 
- Engagement duration > 180 seconds: 1 pt 
- Messages exchanged > 0: 2 pts 
- Messages exchanged ≥ 5: 3 pts 
- Messages exchanged ≥ 10: 1 pt 

### 5. Response Structure (10 Points)
Format checks and field presence. **Note: Fields listed as "Optional" must still be included to receive their designated 1 point.**
- `sessionId`: 2 pts (Required)
- `scamDetected`: 2 pts (Required)
- `extractedIntelligence`: 2 pts (Required)
- `totalMessagesExchanged` and `engagementDurationSeconds`: 1 pt (Included flat and nested to satisfy all evaluator checks)
- `agentNotes`: 1 pt (Should be included)
- `scamType`: 1 pt (Should clearly identify the category of fraud)
- `confidenceLevel`: 1 pt (Numeric float between 0.0 and 1.0)

---

## Tips for Success
- **Build Generic Detection Logic:** Don't hardcode responses for specific scenarios. Detect scams based on patterns, keywords, and behavior.
- **Ask Identifying Questions:** Request phone numbers, account details, verification codes.
- **Maintain Engagement:** Keep the scammer talking for longer conversations to maximize score.
- **Extract All Intelligence:** Capture every piece of info shared (numbers, emails, links, IDs).
- **Proper Structure:** Follow the exact JSON format for final output.
- **Handle Edge Cases:** Be prepared for various scammer tactics.
- **Use AI/LLM Wisely:** Leverage models for natural conversation.
- **Test Thoroughly:** Use scripts to validate implementation before submission.
