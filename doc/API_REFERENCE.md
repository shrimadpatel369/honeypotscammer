# API Reference

Complete API reference for the Honeypot Scam Detection API.

## Base URL

- **Local**: `http://localhost:8000`
- **Production**: `https://honeypotscammer-136046240844.asia-south1.run.app`

## Test Frontend

- **Local UI**: http://localhost:8000
- **Production UI**: https://honeypotscammer-136046240844.asia-south1.run.app
- **API Documentation**: https://honeypotscammer-136046240844.asia-south1.run.app/docs

## Authentication

All API endpoints (except `/`, `/health`, `/docs`) require API key authentication.

### Header
```
x-api-key: YOUR_SECRET_API_KEY
```

### Example
```bash
curl -H "x-api-key: your-secret-key" https://api.example.com/api/v1/honeypot
```

## Endpoints

### 1. Root Endpoint / Test Frontend

Serves the interactive test frontend UI for testing the AI agent.

**Endpoint**: `GET /`

**Authentication**: Not required

**Response**: HTML page with chat interface for testing scam detection

**Features**:
- Interactive chat interface
- Real-time AI agent responses
- Multiple scam type selection
- Quick test messages
- Session management

**Note**: If accessed via browser, returns the test UI. If you need API info as JSON, use `/health` endpoint.

---

### 2. Health Check

Check API and database health status.

**Endpoint**: `GET /health`

**Authentication**: Not required

**Response**:
```json
{
  "status": "healthy",
  "database": "healthy",
  "environment": "production"
}
```

**Status Codes**:
- `200`: All systems healthy
- `503`: Service degraded (database issue)

---

### 3. Process Message (Main Endpoint)

Process incoming messages for scam detection and engagement.

**Endpoint**: `POST /api/v1/honeypot`

**Authentication**: Required

**Request Body**:
```json
{
  "sessionId": "string",
  "message": {
    "sender": "scammer" | "user",
    "text": "string",
    "timestamp": "ISO-8601 datetime"
  },
  "conversationHistory": [
    {
      "sender": "scammer" | "user",
      "text": "string",
      "timestamp": "ISO-8601 datetime"
    }
  ],
  "metadata": {
    "channel": "SMS" | "WhatsApp" | "Email" | "Chat",
    "language": "string",
    "locale": "string"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "sessionId": "string",
  "scamDetected": boolean,
  "reply": "string",
  "shouldContinue": boolean,
  "engagementMetrics": {
    "engagementDurationSeconds": integer,
    "totalMessagesExchanged": integer
  },
  "extractedIntelligence": {
    "bankAccounts": ["string"],
    "upiIds": ["string"],
    "phishingLinks": ["string"],
    "phoneNumbers": ["string"],
    "suspiciousKeywords": ["string"]
  },
  "agentNotes": "string"
}
```

**Example Request**:
```bash
curl -X POST http://localhost:8000/api/v1/honeypot \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "sessionId": "session-123",
    "message": {
      "sender": "scammer",
      "text": "Your account will be blocked. Verify now.",
      "timestamp": "2026-02-02T10:00:00Z"
    },
    "conversationHistory": [],
    "metadata": {
      "channel": "SMS",
      "language": "English",
      "locale": "IN"
    }
  }'
```

**Status Codes**:
- `200`: Success
- `401`: Invalid/missing API key
- `422`: Validation error
- `500`: Server error

---

### 4. Get Session

Retrieve details of a specific session.

**Endpoint**: `GET /api/v1/sessions/{session_id}`

**Authentication**: Required

**Path Parameters**:
- `session_id` (string): Unique session identifier

**Response**:
```json
{
  "sessionId": "string",
  "scamDetected": boolean,
  "conversationHistory": [
    {
      "sender": "string",
      "text": "string",
      "timestamp": "string"
    }
  ],
  "extractedIntelligence": {
    "bankAccounts": ["string"],
    "upiIds": ["string"],
    "phishingLinks": ["string"],
    "phoneNumbers": ["string"],
    "suspiciousKeywords": ["string"]
  },
  "metadata": {},
  "startTime": "ISO-8601 datetime",
  "lastUpdateTime": "ISO-8601 datetime",
  "totalMessages": integer,
  "status": "active" | "completed" | "terminated",
  "agentNotes": "string"
}
```

**Example**:
```bash
curl -X GET http://localhost:8000/api/v1/sessions/session-123 \
  -H "x-api-key: your-api-key"
```

**Status Codes**:
- `200`: Success
- `401`: Invalid/missing API key
- `404`: Session not found

---

### 5. List Sessions

List all sessions with pagination and filtering.

**Endpoint**: `GET /api/v1/sessions`

**Authentication**: Required

**Query Parameters**:
- `limit` (integer, optional): Number of results to return (default: 10, max: 100)
- `skip` (integer, optional): Number of results to skip (default: 0)
- `scam_only` (boolean, optional): Filter for scam sessions only (default: false)

**Response**:
```json
{
  "total": integer,
  "limit": integer,
  "skip": integer,
  "sessions": [
    {
      "sessionId": "string",
      "scamDetected": boolean,
      "totalMessages": integer,
      "status": "string",
      "startTime": "string"
    }
  ]
}
```

**Example**:
```bash
# Get first 10 sessions
curl -X GET "http://localhost:8000/api/v1/sessions?limit=10" \
  -H "x-api-key: your-api-key"

# Get only scam sessions
curl -X GET "http://localhost:8000/api/v1/sessions?scam_only=true" \
  -H "x-api-key: your-api-key"

# Pagination
curl -X GET "http://localhost:8000/api/v1/sessions?limit=20&skip=40" \
  -H "x-api-key: your-api-key"
```

**Status Codes**:
- `200`: Success
- `401`: Invalid/missing API key

---

## Data Models

### Message
```typescript
{
  sender: "scammer" | "user",
  text: string,
  timestamp: string  // ISO-8601 format
}
```

### Metadata
```typescript
{
  channel?: "SMS" | "WhatsApp" | "Email" | "Chat",
  language?: string,
  locale?: string
}
```

### ExtractedIntelligence
```typescript
{
  bankAccounts: string[],
  upiIds: string[],
  phishingLinks: string[],
  phoneNumbers: string[],
  suspiciousKeywords: string[]
}
```

### EngagementMetrics
```typescript
{
  engagementDurationSeconds: number,
  totalMessagesExchanged: number
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing API key"
}
```

### 404 Not Found
```json
{
  "detail": "Session session-123 not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "sessionId"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "status": "error",
  "message": "An internal server error occurred",
  "detail": "Error details (only in debug mode)"
}
```

## Rate Limits

Currently, no rate limits are enforced. Consider implementing rate limiting for production use.

## Best Practices

1. **Session IDs**: Use unique, unpredictable session IDs
2. **Timestamps**: Always use ISO-8601 format with timezone
3. **Conversation History**: Include for better context (except first message)
4. **Error Handling**: Always check response status codes
5. **API Keys**: Keep them secure, rotate regularly

## Interactive Documentation

Visit `/docs` for interactive API documentation with Swagger UI:
```
http://localhost:8000/docs
```

Visit `/redoc` for alternative documentation:
```
http://localhost:8000/redoc
```

## Webhooks

The system automatically sends callbacks to GUVI evaluation endpoint when:
- Scam is detected
- Conversation is completed (status = "completed")
- Intelligence extraction is finished

**GUVI Callback**: `POST https://hackathon.guvi.in/api/updateHoneyPotFinalResult`

## SDKs and Client Libraries

### Python
```python
import httpx

API_URL = "http://localhost:8000"
API_KEY = "your-api-key"

async def process_message(session_id, message, history=[]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/api/v1/honeypot",
            json={
                "sessionId": session_id,
                "message": message,
                "conversationHistory": history
            },
            headers={"x-api-key": API_KEY}
        )
        return response.json()
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8000';
const API_KEY = 'your-api-key';

async function processMessage(sessionId, message, history = []) {
  const response = await axios.post(
    `${API_URL}/api/v1/honeypot`,
    {
      sessionId,
      message,
      conversationHistory: history
    },
    {
      headers: {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json'
      }
    }
  );
  return response.data;
}
```

## Support

For issues or questions:
- GitHub Issues: Create an issue
- Email: your-email@example.com
- Documentation: See README.md
