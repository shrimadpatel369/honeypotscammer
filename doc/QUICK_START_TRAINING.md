# 🎯 RAG Training System - Quick Reference

## ⚡ 5-Minute Setup

```powershell
# 1. Install pandas
pip install pandas

# 2. Test the system
.\examples\test_training.ps1

# 3. Import sample data
curl -X POST "http://localhost:8000/training/import-csv" `
    -H "X-API-Key: honey_pot_scam_detection_2026" `
    -F "file=@examples/sample_scam_dataset.csv"

# Done! System now learns automatically ✅
```

## 📊 Quick Commands

### Import Kaggle CSV
```powershell
curl -X POST "http://localhost:8000/training/import-csv" `
    -H "X-API-Key: honey_pot_scam_detection_2026" `
    -F "file=@C:\path\to\dataset.csv"
```

### View Statistics
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/training/stats" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"}
```

### View Examples
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/training/examples?limit=10" `
    -Headers @{"X-API-Key" = "honey_pot_scam_detection_2026"}
```

## 🎁 What You Get

✅ **AI learns from Kaggle datasets**  
✅ **Auto-learns from conversations**  
✅ **Better, more natural responses**  
✅ **No fine-tuning needed**  
✅ **Works in 5 minutes**  

## 📖 Full Docs

- **Quick Start**: [RAG_SETUP.md](RAG_SETUP.md)
- **Detailed Guide**: [TRAINING_GUIDE.md](TRAINING_GUIDE.md)
- **Implementation**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

## 🚀 Perfect for Feb 5th Deadline!

No complex setup, no fine-tuning, just import and go! 🎉
