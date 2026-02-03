# Frontend Testing Guide

## 🌐 Access the Test UI

### Production (Live)
**URL**: https://honeypotscammer-136046240844.asia-south1.run.app

Simply open the URL in your browser - no installation needed!

### Local Development
**URL**: http://localhost:8000

Make sure your API server is running first:
```bash
# With Docker
docker-compose up -d

# Or locally
python -m uvicorn app.main:app --reload
```

## 🎨 How to Use the Test UI

### 1. **Start a New Session**
   - The UI automatically creates a session when you load the page
   - Click "🔄 New Session" to reset and start fresh

### 2. **Configure Test Parameters**
   - **Scam Type**: Select the type of scam to simulate
     - Bank Fraud
     - UPI Scam
     - Technical Support
     - Prize/Lottery
     - Phishing
     - Job Scam
     - Romance Scam
   
   - **Channel**: Choose the communication channel
     - SMS
     - WhatsApp
     - Telegram
     - Email

### 3. **Test with Quick Messages**
   Use the pre-configured quick test buttons for common scam scenarios:
   
   - **Bank Alert**: "Your bank account has been blocked..."
   - **Lottery Win**: "You have won Rs 5,00,000..."
   - **KYC Alert**: "Your KYC is not updated..."
   - **UPI Scam**: "Verify your UPI PIN for security update..."
   - **Tech Support**: "Microsoft support here..."

### 4. **Custom Messages**
   Type your own scammer messages in the input box to test specific scenarios

### 5. **Watch the AI Respond**
   - The AI agent will analyze the message
   - Generate a human-like response
   - Extract intelligence (URLs, accounts, etc.)
   - Continue the conversation naturally

### 6. **Monitor Statistics**
   The bottom panel shows:
   - **Messages Sent**: Number of scammer messages
   - **AI Responses**: Number of agent replies
   - **Session Duration**: How long the conversation has been active

## 🧪 Testing Scenarios

### Test 1: Bank Fraud Flow
```
1. Select "Bank Fraud" scam type
2. Click "Bank Alert" quick message
3. Follow the conversation flow
4. Watch how the AI:
   - Shows concern about the account
   - Asks clarifying questions
   - Tries to extract account numbers or links
   - Maintains a worried persona
```

### Test 2: UPI Scam Detection
```
1. Select "UPI Scam" type
2. Send: "Please verify your UPI PIN to complete KYC"
3. Observe how the AI:
   - Acts concerned but cautious
   - Asks "why" and "how"
   - Tries to get the scammer to reveal more
   - Never gives real information
```

### Test 3: Multi-turn Conversation
```
1. Start with any scam type
2. Continue the conversation for 10+ messages
3. Notice how the AI:
   - Changes personas based on message count
   - Adapts strategy (trust building → extraction)
   - Gradually becomes more cooperative
   - Eventually may end the conversation
```

### Test 4: Intelligence Extraction
```
1. In your scammer messages, include:
   - Phone numbers
   - Bank account numbers
   - UPI IDs
   - URLs/links
   - Email addresses
2. Check the API response (via /docs or logs)
3. Verify extracted intelligence in the metadata
```

## 🔍 Behind the Scenes

### What Happens When You Send a Message:

1. **Frontend** → Sends POST request to `/api/v1/messages/incoming`
2. **Scam Detector** → Analyzes if message is a scam
3. **AI Agent** → Generates human-like response
   - Selects appropriate persona
   - Uses RAG to retrieve training examples
   - Maintains conversation context
4. **Intelligence Extractor** → Finds URLs, accounts, etc.
5. **Response** → Returns to frontend with:
   - AI-generated reply
   - Should continue flag
   - Extracted intelligence
   - Confidence scores

### API Endpoint Used:
```
POST /api/v1/messages/incoming
```

### Request Format:
```json
{
  "sessionId": "test_1234567890",
  "text": "Your bank account has been blocked",
  "sender": "scammer",
  "metadata": {
    "channel": "SMS",
    "scamType": "bank_fraud",
    "language": "English",
    "locale": "IN"
  }
}
```

## 🐛 Troubleshooting

### Issue: "Connection Error" message
**Cause**: API server is not running or not accessible
**Solution**: 
- Check if server is running: `docker-compose ps`
- Check health endpoint: http://localhost:8000/health
- Verify no firewall blocking port 8000

### Issue: "API Error: Not Found"
**Cause**: Endpoint URL is incorrect
**Solution**: 
- Verify API_BASE URL in browser console (F12)
- Should be `http://localhost:8000/api/v1` locally
- Or production URL when deployed

### Issue: Slow responses (>5 seconds)
**Cause**: Gemini API or MongoDB connection slow
**Solution**:
- Check Gemini API quota
- Verify MongoDB connection
- Check server logs: `docker-compose logs -f api`

### Issue: AI responses are generic/not contextual
**Cause**: Training data might be limited
**Solution**:
- Add more training examples via `/api/v1/training/examples`
- See TRAINING_GUIDE.md for details

## 📊 Monitoring Your Tests

### View Detailed Logs
```bash
# Docker
docker-compose logs -f api

# Local
# Check logs/ directory for detailed logs
```

### Check API Documentation
Visit `/docs` endpoint for:
- Full API reference
- Try out endpoints directly
- View request/response schemas

### Database Inspection
All conversations are stored in MongoDB:
```javascript
// Collections:
- honeypot_sessions    // Session metadata
- honeypot_messages    // All messages
- training_examples    // Training data
- intelligence         // Extracted data
```

## 🎯 Advanced Testing

### Test with Postman/curl
For programmatic testing:

```bash
curl -X POST "https://honeypotscammer-136046240844.asia-south1.run.app/api/v1/messages/incoming" \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "sessionId": "test_123",
    "text": "Your account is blocked",
    "sender": "scammer",
    "metadata": {
      "channel": "SMS",
      "scamType": "bank_fraud"
    }
  }'
```

### Load Testing
See `examples/performance_test.ps1` for load testing scripts

### Custom Frontend
The test UI source is in `test_ui.html` - modify it for your needs!

## 📝 Notes

- Each session maintains its own conversation history
- AI responses vary based on conversation length
- Training examples improve response quality
- Rate limiting: 100 requests/minute (production)

## 🆘 Support

For issues or questions:
1. Check `/health` endpoint for system status
2. Review logs for error details
3. See API_REFERENCE.md for full documentation
4. Check IMPLEMENTATION_SUMMARY.md for architecture details

---

**Happy Testing! 🎉**
