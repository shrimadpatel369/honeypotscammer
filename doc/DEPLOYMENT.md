# Deployment Guide for Google Cloud

This guide explains how to deploy the Honeypot API to Google Cloud using Cloud Run with GitHub integration.

## Prerequisites

- Google Cloud account with billing enabled
- GitHub repository with the code
- gcloud CLI installed (optional, for manual deployment)

## Method 1: Cloud Run with GitHub Integration (Recommended)

### Step 1: Push Code to GitHub

```bash
# Initialize git repository (if not already)
git init

# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/honeypot-api.git

# Commit and push
git add .
git commit -m "Initial commit: Honeypot API"
git push -u origin main
```

### Step 2: Set up MongoDB Atlas (Managed MongoDB)

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster
3. Create a database user
4. Whitelist IP address: `0.0.0.0/0` (allow from anywhere for Cloud Run)
5. Get your connection string (should look like):
   ```
   mongodb+srv://username:password@cluster.mongodb.net/honeypot_db
   ```

### Step 3: Deploy to Cloud Run

1. **Go to Google Cloud Console**
   - Navigate to Cloud Run: https://console.cloud.google.com/run

2. **Create Service**
   - Click "Create Service"
   - Select "Continuously deploy from a repository (source or function)"

3. **Set up Cloud Build**
   - Click "Set up with Cloud Build"
   - Connect your GitHub repository
   - Select the repository containing your code
   - Select the branch (e.g., `main`)

4. **Build Configuration**
   - Build type: `Dockerfile`
   - Dockerfile path: `/Dockerfile`
   - Click "Save"

5. **Configure Service**
   - **Service name**: `honeypot-api`
   - **Region**: Choose closest to your users (e.g., `us-central1`, `asia-south1`)
   - **Authentication**: Allow unauthenticated invocations (API key auth is handled by your app)
   - **CPU allocation**: CPU is only allocated during request processing
   - **Minimum instances**: 0
   - **Maximum instances**: 10

6. **Configure Environment Variables**
   Click "Container, Variables & Secrets, Connections, Security" and add:

   ```
   API_KEY=your-secret-api-key-here
   GEMINI_API_KEY=your-gemini-api-key-here
   GEMINI_MODEL=gemini-2.0-flash-thinking-exp
   GEMINI_MAX_RETRIES=3
   GEMINI_TIMEOUT=30
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/
   MONGODB_DB_NAME=honeypot_db
   MONGODB_MAX_POOL_SIZE=100
   MONGODB_MIN_POOL_SIZE=10
   GUVI_CALLBACK_URL=https://hackathon.guvi.in/api/updateHoneyPotFinalResult
   ENV=production
   DEBUG=False
   HOST=0.0.0.0
   WORKERS=4
   ENABLE_CACHING=True
   CACHE_TTL=300
   RATE_LIMIT_PER_MINUTE=100
   ```

   **IMPORTANT**: 
   - **Do NOT set PORT** - Cloud Run automatically sets this (reserved variable)
   - Use Secret Manager for `API_KEY`, `GEMINI_API_KEY`, and `MONGODB_URL`:
     - Click "Reference a secret"
     - Create secrets for sensitive values

7. **Container Settings**
   - Port: `8000`
   - Memory: `512 MiB`
   - CPU: `1`
   - Timeout: `300` seconds
   - Maximum concurrent requests: `80`

8. **Deploy**
   - Click "Create"
   - Wait for deployment (5-10 minutes)
   - Get your service URL (e.g., `https://honeypot-api-xxxxx.run.app`)

### Step 4: Verify Deployment

```bash
# Test health endpoint
curl https://your-service-url.run.app/health

# Test API endpoint
curl -X POST https://your-service-url.run.app/api/v1/honeypot \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "sessionId": "test-001",
    "message": {
      "sender": "scammer",
      "text": "Your account is blocked",
      "timestamp": "2026-02-02T10:00:00Z"
    },
    "conversationHistory": []
  }'
```

## Method 2: Manual Deployment with Docker

### Build and Push to Google Container Registry

```bash
# Set your project ID
export PROJECT_ID=your-gcp-project-id

# Configure gcloud
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# Build and push Docker image
gcloud builds submit --tag gcr.io/$PROJECT_ID/honeypot-api

# Deploy to Cloud Run
gcloud run deploy honeypot-api \
  --image gcr.io/$PROJECT_ID/honeypot-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars="ENV=production,DEBUG=False" \
  --set-secrets="API_KEY=honeypot-api-key:latest,GEMINI_API_KEY=gemini-key:latest,MONGODB_URL=mongodb-url:latest"
```

## Continuous Deployment

Once set up with GitHub integration:

1. **Make changes to your code**
2. **Commit and push**:
   ```bash
   git add .
   git commit -m "Update: feature description"
   git push origin main
   ```
3. **Cloud Run automatically rebuilds and deploys**
   - Check Cloud Build history for build status
   - New version is automatically deployed
   - Zero-downtime deployment

## Monitoring & Logging

### View Logs
```bash
# Stream logs
gcloud run services logs tail honeypot-api --region us-central1

# View in Cloud Console
# Navigate to: Cloud Run > honeypot-api > Logs
```

### Monitor Metrics
- Cloud Console > Cloud Run > honeypot-api > Metrics
- Monitor: Request count, latency, CPU/Memory usage, errors

### Set up Alerts
- Cloud Console > Monitoring > Alerting
- Create alert policies for:
  - High error rate
  - High latency
  - High CPU/Memory usage

## Security Best Practices

### 1. Use Secret Manager
```bash
# Create secrets
echo -n "your-api-key" | gcloud secrets create honeypot-api-key --data-file=-
echo -n "your-gemini-key" | gcloud secrets create gemini-key --data-file=-
echo -n "mongodb-connection-string" | gcloud secrets create mongodb-url --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding honeypot-api-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2. Enable HTTPS Only
Cloud Run automatically provides HTTPS endpoints.

### 3. Set up VPC Connector (Optional)
For enhanced security with MongoDB in private network:
```bash
gcloud compute networks vpc-access connectors create honeypot-connector \
  --region us-central1 \
  --range 10.8.0.0/28
```

## Cost Optimization

### Cloud Run Pricing
- **Free tier**: 2 million requests/month
- **Compute**: Pay only when handling requests
- **Memory**: Based on GB-seconds
- **Requests**: After free tier

### Estimated Monthly Cost
For moderate usage (100K requests/month):
- Cloud Run: $5-10
- MongoDB Atlas (Free tier): $0
- **Total: ~$5-10/month**

## Troubleshooting

### Common Issues

1. **Build fails**
   - Check Dockerfile syntax
   - Verify all dependencies in requirements.txt
   - Check Cloud Build logs

2. **Container crashes**
   - Check environment variables are set
   - Verify MongoDB connection string
   - Check memory/CPU limits
   - View logs: `gcloud run services logs tail honeypot-api`

3. **API returns 500 errors**
   - Check application logs
   - Verify Gemini API key is valid
   - Check MongoDB connection

4. **Slow response times**
   - Increase memory allocation
   - Increase CPU allocation
   - Increase minimum instances to reduce cold starts

### Get Help
- Cloud Run documentation: https://cloud.google.com/run/docs
- Stack Overflow: Tag with `google-cloud-run`
- GitHub Issues: Create an issue in your repository

## Rolling Back

```bash
# List revisions
gcloud run revisions list --service honeypot-api --region us-central1

# Route traffic to previous revision
gcloud run services update-traffic honeypot-api \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```

## Cleanup

To delete all resources:
```bash
# Delete Cloud Run service
gcloud run services delete honeypot-api --region us-central1

# Delete Docker images
gcloud container images delete gcr.io/$PROJECT_ID/honeypot-api
```
