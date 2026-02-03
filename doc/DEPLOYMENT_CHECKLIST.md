# Deployment Checklist

After committing and pushing code changes, follow this checklist to ensure the frontend is accessible.

## ✅ Pre-Deployment Checklist

- [ ] `test_ui.html` exists in root directory
- [ ] `Dockerfile` includes `COPY test_ui.html .`
- [ ] `app/main.py` has root route serving the HTML file
- [ ] Environment variables are set in Google Cloud Run
- [ ] API key is configured

## 🚀 Deployment Steps

### 1. Commit and Push
```bash
git add .
git commit -m "Add test UI and frontend serving"
git push origin main
```

### 2. Build and Deploy to Google Cloud Run
```bash
# Build the Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/honeypot-api

# Deploy to Cloud Run
gcloud run deploy honeypotscammer \
  --image gcr.io/YOUR_PROJECT_ID/honeypot-api \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 100 \
  --min-instances 1 \
  --set-env-vars="GEMINI_API_KEY=your-key,MONGODB_URL=your-url"
```

### 3. Verify Deployment

After deployment completes, you'll get a service URL like:
```
https://honeypotscammer-136046240844.asia-south1.run.app
```

## 🧪 Post-Deployment Testing

### Test 1: Frontend Access
```bash
# Open in browser
https://honeypotscammer-136046240844.asia-south1.run.app
```
**Expected**: Should see the test UI with chat interface

### Test 2: Health Check
```bash
curl https://honeypotscammer-136046240844.asia-south1.run.app/health
```
**Expected**: JSON response with status

### Test 3: API Documentation
```bash
# Open in browser
https://honeypotscammer-136046240844.asia-south1.run.app/docs
```
**Expected**: Swagger UI with API documentation

### Test 4: Send Test Message
Use the frontend UI or curl:
```bash
curl -X POST \
  "https://honeypotscammer-136046240844.asia-south1.run.app/api/v1/messages/incoming" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test_123",
    "text": "Your bank account has been blocked",
    "sender": "scammer",
    "metadata": {"channel": "SMS", "scamType": "bank_fraud"}
  }'
```
**Expected**: JSON response with AI-generated reply

## 🔧 Troubleshooting

### Issue: 404 Not Found on root URL

**Possible Causes:**
1. `test_ui.html` not copied in Dockerfile
2. File path mismatch in main.py
3. Deployment used old image

**Solution:**
```bash
# Check Dockerfile has:
COPY test_ui.html .

# Rebuild and redeploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/honeypot-api
gcloud run deploy honeypotscammer --image gcr.io/YOUR_PROJECT_ID/honeypot-api
```

### Issue: Frontend loads but API calls fail

**Possible Causes:**
1. CORS not configured
2. API endpoints not accessible
3. Authentication required but not provided

**Solution:**
```bash
# Check Cloud Run logs
gcloud run logs read honeypotscammer --limit 50

# Verify CORS settings in main.py
# Should allow origins from your domain
```

### Issue: Service URL changed after deployment

**What to do:**
1. Get new URL: `gcloud run services describe honeypotscammer`
2. Update documentation with new URL
3. Update README.md, QUICKSTART.md, API_REFERENCE.md
4. Commit and push documentation updates (no need to redeploy)

## 📝 Files Modified for Frontend

1. **test_ui.html** - Frontend interface (NEW)
2. **Dockerfile** - Added COPY test_ui.html (MODIFIED)
3. **app/main.py** - Root route serves HTML (ALREADY EXISTS)
4. **doc/FRONTEND_TESTING.md** - Testing guide (NEW)
5. **doc/DEPLOYMENT_CHECKLIST.md** - This file (NEW)

## 🌐 URLs to Update in Documentation

After deployment, update these files with your actual service URL:

- [ ] README.md - Live Demo section
- [ ] doc/QUICKSTART.md - Production URL
- [ ] doc/API_REFERENCE.md - Base URL
- [ ] doc/FRONTEND_TESTING.md - Production URL

**Find and replace:**
```
OLD: https://honeypotscammer-136046240844.asia-south1.run.app
NEW: <your-actual-service-url>
```

## ✨ Success Criteria

Deployment is successful when:
- ✅ Root URL shows test UI
- ✅ /docs shows API documentation
- ✅ /health returns healthy status
- ✅ Test message through UI gets AI response
- ✅ All quick test buttons work
- ✅ Session statistics update correctly
- ✅ No CORS errors in browser console

## 🎉 Next Steps

After successful deployment:
1. Share the frontend URL with testers
2. Monitor logs for any errors
3. Check performance metrics in Google Cloud Console
4. Add more training examples for better AI responses
5. Test different scam scenarios

---

**Current Deployment:**
- Service: honeypotscammer
- Region: asia-south1
- URL: https://honeypotscammer-136046240844.asia-south1.run.app

**Last Updated:** February 3, 2026
