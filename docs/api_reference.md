# API Reference

## Honeypot Core Endpoint

### `POST /api/v1/honeypot`
Handles incoming messages from potential scammers and returns an AI-generated response.

#### Headers
- `X-API-Key` (Required): Authentication key assigned to the application.

#### Request Body
```json
{
  "sessionId": "string (UUID)",
  "message": {
    "sender": "scammer",
    "text": "string (The actual message from the scammer)",
    "timestamp": "ISO 8601 string"
  },
  "conversationHistory": [
    // Array of previous message objects (optional but recommended)
  ],
  "metadata": {
    "channel": "string (e.g. SMS, WhatsApp)",
    "language": "string",
    "locale": "string",
    "simulation": "boolean"
  }
}
```

#### Response
```json
{
  "status": "success",
  "reply": "string (The AI's generated response to the scammer)"
}
```

---

## Server Health Endpoints

### `GET /health`
Basic healthcheck to determine if the server is live and capable of serving internal responses.
**Response**: `{ "status": "healthy" }`

### `GET /api/system/status`
Comprehensive system metrics check. Reports on AI model availability, MongoDB connectivity, and background system cache locks.
**Response**:
```json
{
  "status": "online",
  "database": "connected",
  "ai_models_status": {
      "gemini-2.5-flash-lite": "available",
      "gemini-3-pro": "ratelimited"
  },
  "uptime": "seconds"
}
```

---

## Local Webhook (Testing Only)

### `POST /api/v1/mock-callback`
A local listener testing interface for capturing the final scoring payloads dumped by the application when `GUVI_CALLBACK_URL="http://127.0.0.1:8000/api/v1/mock-callback"` is set in `.env`. Responds with a simple `200 OK`.
