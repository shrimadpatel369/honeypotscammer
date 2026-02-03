# Quick Test: Training System
# Run this to test the RAG training system

$apiKey = "honey_pot_scam_detection_2026"
$baseUrl = "http://localhost:8000"

Write-Host "`n🎯 Testing AI Training & Learning System" -ForegroundColor Cyan
Write-Host "=" * 60

# 1. Upload sample training data
Write-Host "`n1️⃣  Uploading sample training examples..." -ForegroundColor Yellow

$trainingData = @{
    examples = @(
        @{
            scammer_message = "URGENT: Your SBI account has been compromised. Your account will be blocked in 2 hours."
            effective_response = "Which account? I have multiple accounts. Can you give me more details?"
            scam_type = "bank_phishing"
            notes = "Good deflection that asks for details"
        },
        @{
            scammer_message = "Congratulations! You have won 10 lakh rupees in lucky draw. Claim now!"
            effective_response = "Really? That's amazing! How did I win? What's the process?"
            scam_type = "lottery_scam"
            notes = "Shows interest to keep engagement"
        },
        @{
            scammer_message = "Your KYC is not updated. Update immediately or account blocked."
            effective_response = "I just updated it last month. Why again? Can you verify my details first?"
            scam_type = "kyc_scam"
            notes = "Shows skepticism but stays engaged"
        },
        @{
            scammer_message = "Click this link to verify your identity: bit.ly/verify123"
            effective_response = "I'm not comfortable clicking random links. Can you send it through official channel?"
            scam_type = "phishing_link"
            notes = "Cautious but doesn't shut down"
        },
        @{
            scammer_message = "Send OTP to verify your account now"
            effective_response = "What OTP? I didn't request anything. Why do you need it?"
            scam_type = "otp_phishing"
            notes = "Questions motive while staying in character"
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $uploadResult = Invoke-RestMethod -Uri "$baseUrl/training/upload" `
        -Method POST `
        -Headers @{"X-API-Key" = $apiKey} `
        -Body $trainingData `
        -ContentType "application/json"
    
    Write-Host "   ✅ Uploaded $($uploadResult.count) training examples" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Upload failed: $_" -ForegroundColor Red
}

# 2. Check training statistics
Write-Host "`n2️⃣  Checking training statistics..." -ForegroundColor Yellow

try {
    $stats = Invoke-RestMethod -Uri "$baseUrl/training/stats" `
        -Headers @{"X-API-Key" = $apiKey}
    
    Write-Host "   📊 Training Data:" -ForegroundColor Cyan
    Write-Host "      Total Examples: $($stats.statistics.total_examples)" -ForegroundColor White
    Write-Host "      Kaggle Imported: $($stats.statistics.kaggle_imported)" -ForegroundColor White
    Write-Host "      Live Learned: $($stats.statistics.live_learned)" -ForegroundColor White
} catch {
    Write-Host "   ❌ Stats failed: $_" -ForegroundColor Red
}

# 3. View training examples
Write-Host "`n3️⃣  Viewing stored examples..." -ForegroundColor Yellow

try {
    $examples = Invoke-RestMethod -Uri "$baseUrl/training/examples?limit=3" `
        -Headers @{"X-API-Key" = $apiKey}
    
    Write-Host "   📚 Sample Examples:" -ForegroundColor Cyan
    foreach ($ex in $examples.examples) {
        Write-Host "`n   Type: $($ex.scam_type)" -ForegroundColor Magenta
        Write-Host "   Scammer: $($ex.scammer_message.Substring(0, [Math]::Min(60, $ex.scammer_message.Length)))..." -ForegroundColor White
        if ($ex.effective_response) {
            Write-Host "   Response: $($ex.effective_response.Substring(0, [Math]::Min(60, $ex.effective_response.Length)))..." -ForegroundColor Green
        }
    }
} catch {
    Write-Host "   ❌ Examples retrieval failed: $_" -ForegroundColor Red
}

# 4. Test honeypot with training data
Write-Host "`n4️⃣  Testing honeypot (now uses training data!)..." -ForegroundColor Yellow

$testMessage = @{
    sessionId = "training-test-$(Get-Date -Format 'yyyyMMddHHmmss')"
    message = @{
        sender = "scammer"
        text = "URGENT: Your bank account has security issue. Verify immediately."
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
    }
    metadata = @{
        channel = "SMS"
        language = "English"
        locale = "IN"
    }
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/honeypot" `
        -Method POST `
        -Headers @{"X-API-Key" = $apiKey} `
        -Body $testMessage `
        -ContentType "application/json"
    
    Write-Host "`n   🤖 AI Response (with RAG training):" -ForegroundColor Cyan
    Write-Host "   $($response.reply)" -ForegroundColor Green
    Write-Host "`n   📈 Results:" -ForegroundColor Cyan
    Write-Host "      Scam Detected: $($response.scamDetected)" -ForegroundColor White
    Write-Host "      Should Continue: $($response.shouldContinue)" -ForegroundColor White
    Write-Host "      Session ID: $($response.sessionId)" -ForegroundColor White
} catch {
    Write-Host "   ❌ Test failed: $_" -ForegroundColor Red
}

Write-Host "`n" + "=" * 60
Write-Host "✨ Training system test complete!" -ForegroundColor Green
Write-Host "`n📖 See TRAINING_GUIDE.md for detailed instructions" -ForegroundColor Cyan
Write-Host "💡 Import your Kaggle datasets to improve AI responses" -ForegroundColor Cyan
Write-Host "`n🔄 System auto-learns from every successful conversation!" -ForegroundColor Yellow
