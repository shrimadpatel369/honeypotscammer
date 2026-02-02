# Quick Start Guide

Get your Honeypot API up and running in minutes!

## 🚀 Quick Setup (5 minutes)

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd honeypot
```

### 2. Create Environment File
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual credentials
# Windows: notepad .env
# Linux/Mac: nano .env
```

Add your credentials:
```env
API_KEY=your-secret-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=honeypot_db
```

### 3. Option A: Run with Docker (Recommended)

**Prerequisites**: Docker and Docker Compose installed

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

Your API is now running at: `http://localhost:8000`

### 3. Option B: Run Locally

**Prerequisites**: Python 3.11+, MongoDB installed

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start MongoDB (in separate terminal)
mongod

# Run the application
uvicorn app.main:app --reload
```

Your API is now running at: `http://localhost:8000`

## 📖 Test Your API

### Using the Docs
Open your browser: `http://localhost:8000/docs`

### Using PowerShell (Windows)
```powershell
cd examples
.\test_api.ps1
```

### Using Bash (Linux/Mac)
```bash
cd examples
chmod +x test_api.sh
./test_api.sh
```

### Using cURL
```bash
# Health check
curl http://localhost:8000/health

# Test scam detection
curl -X POST http://localhost:8000/api/v1/honeypot \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-secret-api-key-here" \
  -d @examples/request_first_message.json
```

## 🎯 What's Next?

### For Development
- Modify [app/services/ai_agent.py](app/services/ai_agent.py) to change AI behavior
- Update [app/services/scam_detector.py](app/services/scam_detector.py) for detection logic
- Add new intelligence patterns in [app/services/intelligence_extractor.py](app/services/intelligence_extractor.py)

### For Production
- See [DEPLOYMENT.md](DEPLOYMENT.md) for Google Cloud deployment
- Set up monitoring and alerts
- Configure secret management
- Enable HTTPS

## 🔧 Common Commands

### Docker
```bash
# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart api

# Rebuild after code changes
docker-compose up -d --build
```

### Local Development
```bash
# Run with auto-reload
uvicorn app.main:app --reload

# Run in debug mode
uvicorn app.main:app --reload --log-level debug

# Run on different port
uvicorn app.main:app --port 8080
```

## 📊 View Your Data

### MongoDB
```bash
# Connect to MongoDB (Docker)
docker-compose exec mongodb mongosh honeypot_db

# View sessions
db.sessions.find().pretty()

# Count scam sessions
db.sessions.countDocuments({scamDetected: true})
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Windows: Find and kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

### MongoDB Connection Failed
```bash
# Check if MongoDB is running
# Docker:
docker-compose ps mongodb

# Local:
# Windows: Check Services
# Linux/Mac:
ps aux | grep mongo
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📚 Resources

- [Full README](../README.md) - Complete documentation
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Examples](../examples/) - Sample requests and scripts

## 💡 Tips

1. **Keep your API key secure** - Never commit `.env` to Git
2. **Use MongoDB Atlas** for production - Free tier available
3. **Monitor your Gemini API usage** - Set up billing alerts
4. **Test locally first** - Use the example scripts
5. **Check logs regularly** - `docker-compose logs -f api`

## 🆘 Get Help

- Check logs: `docker-compose logs api`
- Enable debug mode: Set `DEBUG=True` in `.env`
- View health status: `http://localhost:8000/health`
- Open an issue on GitHub

---

**Ready to deploy?** See [DEPLOYMENT.md](DEPLOYMENT.md) for Google Cloud instructions!
