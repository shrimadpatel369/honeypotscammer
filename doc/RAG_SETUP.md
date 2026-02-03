# 🎓 RAG-Based AI Training System - Quick Start

## What is RAG?

**RAG (Retrieval-Augmented Generation)** is a technique that enhances AI responses by:
1. **Retrieving** relevant examples from a database
2. **Augmenting** the AI prompt with these examples
3. **Generating** better, context-aware responses

Perfect for your 2-day timeline! ⚡

## Why RAG Over Fine-Tuning?

| Feature | RAG (Our System) | Fine-Tuning |
|---------|------------------|-------------|
| Setup Time | ✅ 10 minutes | ❌ 2-3 days |
| Infrastructure | ✅ Just MongoDB | ❌ Vertex AI, GPUs |
| Cost | ✅ $0 extra | ❌ $$$$ |
| Updates | ✅ Real-time | ❌ Re-train needed |
| Learning | ✅ Auto from conversations | ❌ Manual |

## System Architecture

```
User Message → Scam Detector → AI Agent
                                   ↓
                              RAG System:
                              1. Query MongoDB
                              2. Retrieve 3-5 examples
                              3. Add to prompt
                                   ↓
                              Gemini API → Smart Response
                                   ↓
                              MongoDB (Save for future learning)
```

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```powershell
pip install pandas
```

### Step 2: Test with Sample Data

```powershell
# Run the test script
.\examples\test_training.ps1
```

This will:
- Upload 5 sample training examples
- Show statistics
- Test the AI with training data
- Demonstrate auto-learning

### Step 3: Import Your Kaggle Dataset

```powershell
# We've included a sample dataset
curl -X POST "http://localhost:8000/training/import-csv" `
    -H "X-API-Key: honey_pot_scam_detection_2026" `
    -F "file=@examples/sample_scam_dataset.csv"
```

### Step 4: Verify

```powershell
# Check stats
Invoke-RestMethod -Uri "http://localhost:8000/training/stats" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"}
```

## Import Your Kaggle Datasets

### Recommended Datasets

1. **SMS Spam Collection**
   - URL: https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset
   - Format: CSV with 'v2' (text) column

2. **Phishing Emails Dataset**
   - URL: https://www.kaggle.com/datasets/subhajournal/phishingemails
   - Format: CSV with email text

3. **Scam Text Messages**
   - URL: https://www.kaggle.com/datasets/thedevastator/identifying-scam-text-messages
   - Format: CSV

### Import Commands

```powershell
# CSV Import
curl -X POST "http://localhost:8000/training/import-csv" `
    -H "X-API-Key: honey_pot_scam_detection_2026" `
    -F "file=@C:\path\to\your\dataset.csv"

# JSON Import
curl -X POST "http://localhost:8000/training/import-json" `
    -H "X-API-Key: honey_pot_scam_detection_2026" `
    -F "file=@C:\path\to\your\dataset.json"
```

## How Auto-Learning Works

Every time a conversation completes successfully:

1. **Success Check**: Did we extract intelligence? (accounts, links, etc.)
2. **Pattern Extraction**: Extract scammer messages & effective responses
3. **Storage**: Save to MongoDB as new training examples
4. **Future Use**: Used for similar scams automatically

**No manual work needed!** 🎉

## API Endpoints

### 1. Upload Training Data

```powershell
POST /training/upload
{
  "examples": [
    {
      "scammer_message": "Your account is blocked",
      "effective_response": "Which account?",
      "scam_type": "bank_phishing"
    }
  ]
}
```

### 2. Import CSV Dataset

```powershell
POST /training/import-csv
Content-Type: multipart/form-data
file: your_dataset.csv
```

### 3. Import JSON Dataset

```powershell
POST /training/import-json
Content-Type: multipart/form-data
file: your_dataset.json
```

### 4. Get Statistics

```powershell
GET /training/stats
```

Response:
```json
{
  "statistics": {
    "total_examples": 125,
    "kaggle_imported": 100,
    "live_learned": 25
  }
}
```

### 5. View Examples

```powershell
GET /training/examples?scam_type=bank_phishing&limit=10
```

## CSV Format Requirements

Your CSV should have these columns (flexible names):

| Column Options | Description |
|----------------|-------------|
| `text` or `message` | The scam message text |
| `type` or `category` | Scam type (e.g., "bank_phishing") |
| `label` | Usually "scam" or "legitimate" |

Example:
```csv
text,type,label
"Your account is blocked",bank_phishing,scam
"Win prize now!",lottery_scam,scam
```

## JSON Format Requirements

```json
[
  {
    "scammer_message": "Text here",
    "scam_type": "type here",
    "notes": "optional notes"
  }
]
```

## Monitoring & Optimization

### Check What AI is Learning

```powershell
# View recent learned patterns
Invoke-RestMethod -Uri "http://localhost:8000/training/examples?limit=20" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"}
```

### Monitor Statistics

```powershell
# Check training growth
Invoke-RestMethod -Uri "http://localhost:8000/training/stats" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"}
```

### View Logs

```powershell
# Check if training examples are being used
# Look for: "Retrieved X relevant examples"
Get-Content logs/app.log -Tail 50 | Select-String "training|learned"
```

## Performance Tips

### 1. Quality Over Quantity
- 50-100 good examples better than 10,000 poor ones
- Include diverse scam types
- Add effective responses if available

### 2. Scam Type Categorization
Good categories:
- `bank_phishing`
- `lottery_scam`
- `kyc_scam`
- `otp_phishing`
- `prize_scam`
- `loan_scam`
- `tax_scam`

### 3. Regular Monitoring
```powershell
# Daily check
./examples/test_training.ps1
```

## Benefits You'll See

✅ **Better Responses**: AI learns from real scam patterns  
✅ **More Natural**: Responses match successful engagement strategies  
✅ **Adaptive**: System improves with each conversation  
✅ **No Maintenance**: Auto-learning handles everything  
✅ **Fast Setup**: Ready in minutes, not days  

## Troubleshooting

### CSV Import Fails

**Issue**: "Error parsing CSV"

**Solution**:
```powershell
# Check encoding (should be UTF-8)
# Verify columns exist: text, type, label
# Remove special characters
```

### No Improvement in Responses

**Issue**: AI not using training data

**Check**:
```powershell
# 1. Verify examples stored
Invoke-RestMethod -Uri "http://localhost:8000/training/stats" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"}

# 2. Check scam_type matches
# If dataset has "phishing", sessions should detect "phishing" too
```

### Pandas Not Found

```powershell
pip install pandas
```

## Example: Complete Workflow

```powershell
# 1. Start server
docker-compose up

# 2. Import Kaggle dataset
curl -X POST "http://localhost:8000/training/import-csv" `
    -H "X-API-Key: honey_pot_scam_detection_2026" `
    -F "file=@C:\datasets\scam_sms.csv"

# 3. Check stats
Invoke-RestMethod -Uri "http://localhost:8000/training/stats" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"}

# 4. Test honeypot
.\examples\test_api.ps1

# 5. System auto-learns from successful tests!

# 6. Check learned patterns
Invoke-RestMethod -Uri "http://localhost:8000/training/examples?limit=10" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"} | 
    ConvertTo-Json -Depth 10
```

## What Happens During a Scam Conversation?

1. **Scammer sends message**: "Your account is blocked"
2. **RAG System activates**:
   - Searches MongoDB for similar messages
   - Finds 3-5 relevant examples
   - Retrieves effective response patterns
3. **AI Agent generates response**:
   - Uses persona (elderly, young, cautious, naive)
   - Includes training examples in prompt
   - Generates natural, engaging response
4. **Intelligence extracted**: Accounts, links, phone numbers
5. **Auto-learning**:
   - If intelligence extracted successfully
   - Saves conversation patterns
   - Available for future use

## Next Steps

1. ✅ **Test the system**: Run `test_training.ps1`
2. ✅ **Import sample data**: Use provided CSV
3. ✅ **Import your Kaggle datasets**: Download and import
4. ✅ **Monitor results**: Check stats and logs
5. ✅ **Let it learn**: System improves automatically

## Support

- **API Docs**: http://localhost:8000/docs
- **Training Guide**: See TRAINING_GUIDE.md
- **Example Scripts**: Check examples/ folder

---

**Ready to go!** 🚀

The system is designed for speed and simplicity. Perfect for your Feb 5th deadline!
