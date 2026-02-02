# Logging System Documentation

## Overview

The Honeypot API includes comprehensive logging to track all incoming test requests, responses, and system operations. This is essential for debugging and verifying test results with the hackathon provider.

## Log Files Location

All logs are stored in the `logs/` directory:

```
logs/
├── app_YYYYMMDD.log         # General application logs (human-readable)
├── requests_YYYYMMDD.log    # All API requests/responses (JSON format)
└── errors_YYYYMMDD.log      # Errors and exceptions only
```

New log files are created daily with the date in the filename.

## Log Types

### 1. Application Logs (`app_YYYYMMDD.log`)

Human-readable format for general application events:

```
[2026-02-02 10:15:30] INFO     | app.main | 🔍 INCOMING TEST REQUEST - Session: test-001
[2026-02-02 10:15:30] INFO     | app.main | Session ID: test-001
[2026-02-02 10:15:30] INFO     | app.main | Message Text: Your bank account will be blocked
[2026-02-02 10:15:31] INFO     | app.main | ✅ Successfully processed request for session test-001
```

### 2. Request/Response Logs (`requests_YYYYMMDD.log`)

Structured JSON format with complete request/response data:

```json
{
  "timestamp": "2026-02-02T10:15:30.123Z",
  "level": "INFO",
  "logger": "api.requests",
  "message": "Incoming Request - Session: test-001",
  "session_id": "test-001",
  "request": {
    "headers": {
      "x-api-key": "abc1****xyz9",
      "content-type": "application/json"
    },
    "body": {
      "sessionId": "test-001",
      "message": {
        "sender": "scammer",
        "text": "Your bank account will be blocked",
        "timestamp": "2026-02-02T10:15:30Z"
      },
      "conversationHistory": [],
      "metadata": {
        "channel": "SMS",
        "language": "English",
        "locale": "IN"
      }
    }
  }
}
```

### 3. Error Logs (`errors_YYYYMMDD.log`)

Only errors and exceptions:

```
[2026-02-02 10:20:15] ERROR    | app.main | ❌ Error processing request - Connection timeout
```

## What Gets Logged

### Incoming Requests
- **Session ID**: Unique identifier for the conversation
- **Headers**: All HTTP headers (API keys are masked)
- **Message Details**:
  - Sender (scammer/user)
  - Message text
  - Timestamp
- **Conversation History**: All previous messages
- **Metadata**: Channel, language, locale

### Processing Details
- **Scam Detection**: Results and confidence scores
- **AI Agent**: Generated responses and reasoning
- **Intelligence Extraction**: Extracted data (accounts, links, etc.)
- **Database Operations**: Session updates

### Outgoing Responses
- **Status**: Success/failure
- **Scam Detection Result**: Boolean and confidence
- **Agent Reply**: Generated conversation response
- **Engagement Metrics**: Duration and message count
- **Extracted Intelligence**: All collected data
- **Processing Time**: Total time in milliseconds

### GUVI Callbacks
- **Endpoint**: Callback URL
- **Full Payload**: Complete data sent to GUVI
- **Response**: Status code and response body
- **Intelligence Summary**: Count of each intelligence type

## Viewing Logs

### Real-time Monitoring (Console)
```powershell
# View live logs
docker-compose logs -f api

# Or if running locally
uvicorn app.main:app --reload
```

### Reading Log Files

#### Application Logs (Human-Readable)
```powershell
# View entire log
Get-Content logs\app_20260202.log

# Tail last 50 lines
Get-Content logs\app_20260202.log -Tail 50

# Follow new entries
Get-Content logs\app_20260202.log -Wait

# Search for specific session
Select-String -Path logs\app_20260202.log -Pattern "test-001"
```

#### Request Logs (JSON)
```powershell
# Parse JSON logs
Get-Content logs\requests_20260202.log | ForEach-Object {
    $_ | ConvertFrom-Json
} | Format-List

# Filter by session ID
Get-Content logs\requests_20260202.log | ForEach-Object {
    $obj = $_ | ConvertFrom-Json
    if ($obj.session_id -eq "test-001") { $obj | ConvertTo-Json -Depth 10 }
}
```

#### Linux/Mac
```bash
# View application logs
tail -f logs/app_20260202.log

# View request logs
tail -f logs/requests_20260202.log

# Parse JSON logs
cat logs/requests_20260202.log | jq '.'

# Filter by session
cat logs/requests_20260202.log | jq 'select(.session_id == "test-001")'
```

## Log Formats

### Incoming Request Log Example
```
================================================================================
🔍 INCOMING TEST REQUEST - Session: test-session-001
================================================================================
Request Headers: {'content-type': 'application/json', 'x-api-key': 'abc1****xyz9'}
Session ID: test-session-001
Channel: SMS
Language: English
Message Sender: scammer
Message Text: Your bank account will be blocked today. Verify immediately.
Message Timestamp: 2026-02-02T10:15:30Z
Conversation History Length: 0
================================================================================
```

### Outgoing Response Log Example
```
================================================================================
📤 OUTGOING RESPONSE - Session: test-session-001
================================================================================
Status: success
Scam Detected: True
Should Continue: True
Agent Reply: Oh no! Why would my account be blocked? I didn't do anything wrong.
Total Messages: 1
Duration: 0s
Intelligence Extracted:
  - Bank Accounts: 0
  - UPI IDs: 0
  - Phishing Links: 0
  - Phone Numbers: 0
  - Keywords: 3
Agent Notes: urgency tactics, account blocked, verify immediately
Processing Time: 523.45ms
================================================================================
```

### GUVI Callback Log Example
```
================================================================================
📡 SENDING GUVI CALLBACK - Session: test-session-001
================================================================================
Endpoint: https://hackathon.guvi.in/api/updateHoneyPotFinalResult
Session ID: test-session-001
Scam Detected: True
Total Messages: 5
Intelligence Summary:
  - Bank Accounts: 1
  - UPI IDs: 2
  - Phishing Links: 1
  - Phone Numbers: 1
  - Keywords: 8
Agent Notes: Scammer used urgency tactics, requested UPI payment
Full Payload:
{
  "sessionId": "test-session-001",
  "scamDetected": true,
  "totalMessagesExchanged": 5,
  "extractedIntelligence": {
    "bankAccounts": ["1234567890"],
    "upiIds": ["scammer@upi", "fraud@paytm"],
    "phishingLinks": ["http://fake-bank.com"],
    "phoneNumbers": ["+919876543210"],
    "suspiciousKeywords": ["urgent", "blocked", "verify", ...]
  },
  "agentNotes": "Scammer used urgency tactics, requested UPI payment"
}
GUVI Callback Response - Status: 200
Response Body: {"status": "success"}
================================================================================
```

## Security & Privacy

### API Key Masking
API keys in logs are automatically masked:
- Original: `abc123xyz789`
- Logged: `abc1****xyz9`

### What's NOT Logged
- Full API keys
- Sensitive credentials
- Internal system paths (in production mode)

### What IS Logged
- All test request data (needed for verification)
- All message content (as per hackathon requirements)
- Intelligence extracted (for evaluation)

## Troubleshooting with Logs

### Find Failed Requests
```powershell
# Search for errors
Select-String -Path logs\app_*.log -Pattern "ERROR"

# Search for failed sessions
Select-String -Path logs\app_*.log -Pattern "❌"
```

### Check Specific Session
```powershell
# View all logs for a session
Select-String -Path logs\app_*.log -Pattern "session-123"
```

### Verify GUVI Callbacks
```powershell
# Check callback logs
Select-String -Path logs\app_*.log -Pattern "GUVI CALLBACK"
```

### Performance Analysis
```powershell
# Find slow requests (> 1 second)
Select-String -Path logs\app_*.log -Pattern "Processing Time: [1-9]\d{3,}\.\d+ms"
```

## Log Rotation

Logs automatically rotate daily. Old log files are kept indefinitely by default.

### Manual Cleanup
```powershell
# Delete logs older than 7 days
Get-ChildItem logs\*.log | Where-Object { 
    $_.LastWriteTime -lt (Get-Date).AddDays(-7) 
} | Remove-Item
```

### Automated Cleanup (Optional)
Add to your deployment script or cron job:
```bash
find logs/ -name "*.log" -mtime +7 -delete
```

## Best Practices

1. **Monitor Logs Regularly**: Check for errors and performance issues
2. **Archive Important Tests**: Save logs from test sessions with the provider
3. **Share Logs for Debugging**: Send relevant log excerpts when reporting issues
4. **Check GUVI Callbacks**: Verify callback success in logs
5. **Performance Tracking**: Monitor processing times

## Example: Verifying Test Results

When the hackathon provider tests your endpoint:

1. **Check incoming request**:
   ```powershell
   Select-String -Path logs\app_*.log -Pattern "INCOMING TEST REQUEST"
   ```

2. **Verify processing**:
   ```powershell
   Select-String -Path logs\app_*.log -Pattern "Successfully processed"
   ```

3. **Check GUVI callback**:
   ```powershell
   Select-String -Path logs\app_*.log -Pattern "SENDING GUVI CALLBACK"
   ```

4. **Extract full session data**:
   ```powershell
   $sessionId = "test-session-001"
   Select-String -Path logs\requests_*.log -Pattern $sessionId
   ```

## Integration with Monitoring

Logs can be integrated with monitoring services:
- **Google Cloud Logging**: Automatic integration on Cloud Run
- **ELK Stack**: Parse JSON logs with Logstash
- **Datadog/New Relic**: Use file-based log ingestion

---

All logs follow industry standards for structured logging and are designed to help you verify and debug your honeypot implementation with the hackathon evaluation system.
