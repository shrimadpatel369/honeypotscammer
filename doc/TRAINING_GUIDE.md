# Kaggle Dataset Import Guide

## Quick Import Your Datasets

### 1. Manual Upload via API

```powershell
# Upload manual examples
$data = @{
    examples = @(
        @{
            scammer_message = "URGENT: Your SBI account has been compromised. Click here to verify: bit.ly/fake"
            effective_response = "Which account? I have multiple accounts. Can you give me more details?"
            scam_type = "bank_phishing"
            notes = "Good response that asks for clarification and keeps engagement"
        },
        @{
            scammer_message = "Congratulations! You won 10 lakh rupees. Send us your account details"
            effective_response = "Really? How did I win? What do I need to do?"
            scam_type = "lottery_scam"
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:8000/training/upload" `
    -Method POST `
    -Headers @{"X-API-Key" = "your-api-key-here"} `
    -Body $data `
    -ContentType "application/json"
```

### 2. Import CSV Dataset

```powershell
# Import Kaggle CSV (e.g., scam_messages.csv)
curl -X POST "http://localhost:8000/training/import-csv" `
    -H "X-API-Key: your-api-key-here" `
    -F "file=@path/to/your/kaggle_dataset.csv"
```

Expected CSV format:
```csv
text,type,label
"Your account is blocked",bank_phishing,scam
"Win iPhone now!",prize_scam,scam
"KYC update required",bank_phishing,scam
```

### 3. Import JSON Dataset

```powershell
# Import Kaggle JSON
curl -X POST "http://localhost:8000/training/import-json" `
    -H "X-API-Key: your-api-key-here" `
    -F "file=@path/to/dataset.json"
```

Expected JSON format:
```json
[
  {
    "scammer_message": "Your account will be blocked",
    "scam_type": "bank_phishing"
  },
  {
    "scammer_message": "Claim your prize",
    "scam_type": "lottery"
  }
]
```

### 4. Check Training Stats

```powershell
# View statistics
Invoke-RestMethod -Uri "http://localhost:8000/training/stats" `
    -Headers @{"X-API-Key" = "your-api-key-here"}
```

### 5. View Training Examples

```powershell
# See what's been learned
Invoke-RestMethod -Uri "http://localhost:8000/training/examples?limit=10" `
    -Headers @{"X-API-Key" = "your-api-key-here"}
```

## Popular Kaggle Datasets for Scam Detection

1. **SMS Spam Collection**: https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset
2. **Phishing Emails**: https://www.kaggle.com/datasets/subhajournal/phishingemails
3. **Scam Text Messages**: https://www.kaggle.com/datasets/thedevastator/identifying-scam-text-messages
4. **Indian Scam SMS**: Search Kaggle for "indian sms scam" or "banking fraud sms"

## How It Works (RAG System)

1. **Store**: Upload your Kaggle datasets → Stored in MongoDB
2. **Retrieve**: When AI agent gets a message → Retrieves 3-5 similar examples
3. **Augment**: Examples added to AI prompt → Better context for responses
4. **Generate**: AI creates response based on learned patterns
5. **Learn**: System auto-learns from successful conversations

## Auto-Learning

The system automatically learns from successful sessions:
- Extracts scammer patterns
- Records effective responses
- Builds knowledge base over time
- No manual intervention needed!

## Benefits

✅ **Fast**: No fine-tuning, works immediately  
✅ **Simple**: Just upload datasets, system handles rest  
✅ **Adaptive**: Learns from real interactions  
✅ **Cost-effective**: Uses existing Gemini API  
✅ **Scalable**: MongoDB stores unlimited examples  

## Example Workflow

```powershell
# 1. Import your Kaggle dataset
curl -X POST "http://localhost:8000/training/import-csv" `
    -H "X-API-Key: honey_pot_scam_detection_2026" `
    -F "file=@C:\datasets\scam_messages.csv"

# 2. Check stats
Invoke-RestMethod -Uri "http://localhost:8000/training/stats" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"}

# 3. Test honeypot (it now uses training data!)
$testData = @{
    message = "Your SBI account is blocked"
    sessionId = "test-123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/honeypot" `
    -Method POST `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"} `
    -Body $testData `
    -ContentType "application/json"
```

## Tips for Best Results

1. **Quality over Quantity**: Better to have 100 good examples than 10,000 poor ones
2. **Diverse Types**: Include various scam types (banking, lottery, tech support, etc.)
3. **Include Responses**: If your dataset has victim responses, include them
4. **Regular Updates**: System learns from live sessions automatically
5. **Review Learned Patterns**: Check `/training/examples` to see what AI learned

## Troubleshooting

**CSV Import Fails?**
- Check column names: `text`, `message`, `type`, `category`, `label`
- Ensure UTF-8 encoding
- Remove special characters if needed

**JSON Import Issues?**
- Validate JSON format
- Must be array of objects or single object
- Check for syntax errors

**Not Seeing Improvement?**
- Import more examples (aim for 50+ per scam type)
- Check if examples are being used: `/training/stats`
- Review examples quality: `/training/examples`
