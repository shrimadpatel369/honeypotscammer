# 🍯 Agentic Honey-Pot for Scam Detection & Intelligence Extraction

## � Live Demo

**🎨 Test Frontend**: [https://honeypotscammer-136046240844.asia-south1.run.app](https://honeypotscammer-136046240844.asia-south1.run.app)

**📖 API Documentation**: [https://honeypotscammer-136046240844.asia-south1.run.app/docs](https://honeypotscammer-136046240844.asia-south1.run.app/docs)

Try the interactive test UI to see the AI agent in action!

---

## �🌟 Premium Edition - Optimized for Minimum Latency

An AI-powered honeypot system that autonomously detects and engages with scammers to extract actionable intelligence. Built with premium Google Cloud services and optimized for production-grade performance.

## ⚡ Performance Features

- **Sub-second Response Times**: In-memory caching with 40-60% hit rate
- **Premium AI Model**: Google Gemini 2.0 Flash Thinking (latest model)
- **Cloud-Optimized MongoDB**: Connection pooling with 100 max connections
- **Auto-Scaling**: 1-100 instances on Cloud Run
- **High Throughput**: 50-100 requests/second per instance
- **Production-Grade**: Rate limiting, retry logic, health checks

## 🚀 Features

- **Real-time Scam Detection**: AI-powered detection of fraudulent messages
- **Autonomous AI Agent**: Multi-turn conversation handling with human-like responses
- **Multi-Lingual Support**: Native support for English + 9 Indian languages including **Hinglish** and **Gujarati-English** (transliterated)
- **Intelligence Extraction**: Automatic extraction of bank accounts, UPI IDs, phishing links, and more
- **RAG-Based Learning**: Import Kaggle datasets and auto-learn from conversations
- **Auto-Learning System**: Automatically improves from successful scam interactions
- **Training API**: Easy import of CSV/JSON datasets for better AI responses
- **Secure API**: API key authentication with rate limiting
- **MongoDB Storage**: Persistent session and intelligence storage
- **Google Gemini Integration**: Advanced AI capabilities for natural conversations
- **Production Ready**: Docker support, cloud deployment ready

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request (x-api-key)
       ▼
┌─────────────────────────────────────┐
│         FastAPI Gateway             │
│  ┌──────────────────────────────┐   │
│  │  Authentication Middleware   │   │
│  └──────────────────────────────┘   │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│      Scam Detection Service          │
│  ┌────────────────────────────────┐  │
│  │  Google Gemini AI Analysis     │  │
│  └────────────────────────────────┘  │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│      AI Agent Service                │
│  ┌────────────────────────────────┐  │
│  │  Multi-turn Conversation       │  │
│  │  Context Management            │  │
│  │  Human-like Responses          │  │
│  └────────────────────────────────┘  │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  Intelligence Extraction Service     │
│  ┌────────────────────────────────┐  │
│  │  Bank Accounts                 │  │
│  │  UPI IDs                       │  │
│  │  Phishing Links                │  │
│  │  Phone Numbers                 │  │
│  └────────────────────────────────┘  │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│        MongoDB Database              │
│  - Sessions                          │
│  - Conversations                     │
│  - Intelligence Data                 │
└──────────────────────────────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- MongoDB 6.0+
- Google Gemini API Key
- Docker (optional, for containerized deployment)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd honeypot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Run the application**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

6. **Optional: Import training data**
```bash
# Test the training system
.\examples\test_training.ps1

# Import your Kaggle datasets
curl -X POST "http://localhost:8000/training/import-csv" \
    -H "X-API-Key: your-api-key" \
    -F "file=@path/to/dataset.csv"
```

See **[RAG_SETUP.md](doc/RAG_SETUP.md)** for detailed training instructions.

### Docker Deployment

1. **Build and run with Docker Compose**
```bash
docker-compose up -d
```

2. **Access the API**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `API_KEY` | Your secret API key for authentication | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `MONGODB_URL` | MongoDB connection string | Yes |
| `MONGODB_DB_NAME` | Database name | Yes |
| `GUVI_CALLBACK_URL` | GUVI evaluation endpoint | Yes |
| `PORT` | Server port (default: 8000) | No |

## 📡 API Usage

### Endpoint
```
POST /api/v1/honeypot
```

### Authentication
```
x-api-key: YOUR_SECRET_API_KEY
Content-Type: application/json
```

### Request Format

**First Message (New Conversation)**
```json
{
  "sessionId": "wertyu-dfghj-ertyui",
  "message": {
    "sender": "scammer",
    "text": "Your bank account will be blocked today. Verify immediately.",
    "timestamp": "2026-01-21T10:15:30Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

**Follow-up Message**
```json
{
  "sessionId": "wertyu-dfghj-ertyui",
  "message": {
    "sender": "scammer",
    "text": "Share your UPI ID to avoid account suspension.",
    "timestamp": "2026-01-21T10:17:10Z"
  },
  "conversationHistory": [
    {
      "sender": "scammer",
      "text": "Your bank account will be blocked today. Verify immediately.",
      "timestamp": "2026-01-21T10:15:30Z"
    },
    {
      "sender": "user",
      "text": "Why will my account be blocked?",
      "timestamp": "2026-01-21T10:16:10Z"
    }
  ],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

### Response Format

```json
{
  "status": "success",
  "sessionId": "wertyu-dfghj-ertyui",
  "scamDetected": true,
  "reply": "Oh no! Why would my account be blocked? I didn't do anything wrong. What should I do?",
  "shouldContinue": true,
  "engagementMetrics": {
    "engagementDurationSeconds": 420,
    "totalMessagesExchanged": 18
  },
  "extractedIntelligence": {
    "bankAccounts": ["XXXX-XXXX-XXXX"],
    "upiIds": ["scammer@upi"],
    "phishingLinks": ["http://malicious-link.example"],
    "phoneNumbers": ["+91XXXXXXXXXX"],
    "suspiciousKeywords": ["urgent", "verify now", "account blocked"]
  },
  "agentNotes": "Scammer used urgency tactics and payment redirection"
}
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## 🚀 Google Cloud Deployment

### Using Cloud Run with GitHub Integration

1. **Push to GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Configure Cloud Run**
- Go to Google Cloud Console
- Navigate to Cloud Run
- Click "Create Service"
- Select "Continuously deploy from a repository"
- Connect your GitHub repository
- Set build type to "Dockerfile"
- Configure environment variables from `.env.example`

3. **Set Environment Variables in Cloud Run**
- Add all required variables from `.env.example`
- Use Secret Manager for sensitive data

### Manual Docker Deployment

```bash
# Build
docker build -t honeypot-api .

# Tag for GCR
docker tag honeypot-api gcr.io/YOUR_PROJECT_ID/honeypot-api

# Push
docker push gcr.io/YOUR_PROJECT_ID/honeypot-api

# Deploy
gcloud run deploy honeypot-api \
  --image gcr.io/YOUR_PROJECT_ID/honeypot-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 🔒 Security Features

- ✅ API Key Authentication
- ✅ CORS Configuration
- ✅ Request Validation
- ✅ Rate Limiting (100 req/min)
- ✅ Input Sanitization
- ✅ Secure MongoDB Connection

## 🎓 Training & Learning System

The honeypot includes a **RAG (Retrieval-Augmented Generation)** system that:

- ✅ **Import Kaggle datasets** (CSV/JSON) for training
- ✅ **Auto-learns** from successful scam conversations
- ✅ **Retrieves relevant examples** during AI response generation
- ✅ **No fine-tuning needed** - works immediately
- ✅ **Continuously improves** with each interaction

### Quick Start with Training

```powershell
# Test the training system
.\examples\test_training.ps1

# Import a Kaggle dataset
curl -X POST "http://localhost:8000/training/import-csv" \
    -H "X-API-Key: your-api-key" \
    -F "file=@examples/sample_scam_dataset.csv"

# Check statistics
curl -H "X-API-Key: your-api-key" \
    http://localhost:8000/training/stats
```

**📖 See [RAG_SETUP.md](doc/RAG_SETUP.md) for complete training guide**

## 📚 Documentation
- ✅ Rate Limiting
- ✅ Input Sanitization
- ✅ Secure Environment Variables
- ✅ MongoDB Connection Security

## 📚 Documentation

- **[Quick Start Guide](doc/QUICKSTART.md)** - Get started in 5 minutes
- **[Premium Optimization Guide](doc/PREMIUM_OPTIMIZATION.md)** - Performance tuning and best practices
- **[Hinglish & Transliterated Language Support](doc/HINGLISH_SUPPORT.md)** - Multi-lingual Indian language support
- **[Logging System](doc/LOGGING.md)** - Complete logging documentation and troubleshooting
- **[API Reference](doc/API_REFERENCE.md)** - Complete API documentation
- **[Deployment Guide](doc/DEPLOYMENT.md)** - Google Cloud deployment instructions
- **[API Docs (Interactive)](http://localhost:8000/docs)** - Swagger UI
- **[Examples](examples/)** - Sample requests and test scripts

## 📊 Monitoring & Logging

The application includes comprehensive logging:
- **Three log files**: Application logs, request/response logs, and error logs
- **Structured JSON**: All requests and responses logged in JSON format
- **Complete tracking**: Every test request from the hackathon provider is logged
- **GUVI callback logs**: Full payload and response tracking
- **Performance metrics**: Processing time for each request
- **Daily rotation**: New log files created automatically each day

See [Logging Documentation](doc/LOGGING.md) for details.

### Log Files Location
```
logs/
├── app_YYYYMMDD.log      # Human-readable application logs
├── requests_YYYYMMDD.log # JSON formatted request/response logs
└── errors_YYYYMMDD.log   # Errors only
```

### View Logs
```powershell
# Real-time monitoring
docker-compose logs -f api

# View log files
Get-Content logs\app_20260202.log -Tail 50

# Search for specific session
Select-String -Path logs\app_*.log -Pattern "session-123"
```
- Request/response logging
- Error tracking
- Performance metrics
- Session analytics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- GUVI Hackathon
- Google Gemini AI
- FastAPI Framework
- MongoDB

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

Built with ❤️ for the GUVI Hackathon
