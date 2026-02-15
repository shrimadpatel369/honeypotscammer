#!/usr/bin/env pwsh
# PowerShell script to test Hinglish language support
# Run from the project root: ./examples/test_hinglish.ps1

Write-Host "`n==============================================================" -ForegroundColor Cyan
Write-Host "Testing Hinglish & Gujarati-English Language Support" -ForegroundColor Cyan
Write-Host "==============================================================`n" -ForegroundColor Cyan

$BASE_URL = "http://localhost:8000"
$API_KEY = $env:API_KEY

if (-not $API_KEY) {
    Write-Host "❌ ERROR: API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Set it with: `$env:API_KEY = 'your-api-key'" -ForegroundColor Yellow
    exit 1
}

function Test-ScamDetection {
    param(
        [string]$Language,
        [string]$Message,
        [string]$Description
    )
    
    Write-Host "`n--------------------------------------------------" -ForegroundColor Yellow
    Write-Host "Test: $Description" -ForegroundColor Yellow
    Write-Host "Language: $Language" -ForegroundColor Yellow
    Write-Host "Message: `"$Message`"" -ForegroundColor White
    
    $Body = @{
        message = $Message
        sender = "scammer"
        channel = "SMS"
        metadata = @{
            language = $Language
            locale = "IN"
        }
    } | ConvertTo-Json -Depth 10
    
    try {
        $Response = Invoke-RestMethod -Uri "$BASE_URL/v1/webhook" `
            -Method Post `
            -Headers @{
                "x-api-key" = $API_KEY
                "Content-Type" = "application/json"
            } `
            -Body $Body
        
        Write-Host "`n📊 Response:" -ForegroundColor Green
        Write-Host "  Session ID: $($Response.sessionId)" -ForegroundColor Gray
        Write-Host "  Scam Detected: $($Response.analysis.scam_detected)" -ForegroundColor $(if ($Response.analysis.scam_detected) { "Red" } else { "Green" })
        Write-Host "  Confidence: $($Response.analysis.confidence)" -ForegroundColor Gray
        Write-Host "  AI Response: '$($Response.agent_response)'" -ForegroundColor Cyan
        
        if ($Response.intelligence.length -gt 0) {
            Write-Host "`n  🔍 Intelligence Extracted:" -ForegroundColor Magenta
            foreach ($intel in $Response.intelligence) {
                Write-Host "    - $($intel.type): $($intel.value)" -ForegroundColor Gray
            }
        }
        
    } catch {
        Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test 1: Hinglish Bank Scam
Test-ScamDetection `
    -Language "hinglish" `
    -Message "Aapka account block hone wala hai. Abhi OTP share karo." `
    -Description "Bank Account Threat + OTP Request (Hinglish)"

# Test 2: Hinglish Prize Scam
Test-ScamDetection `
    -Language "hinglish" `
    -Message "Congratulations! Aapko 25 lakh ka prize mila hai. Details ke liye is link pe click karo: bit.ly/prize123" `
    -Description "Prize Scam with Link (Hinglish)"

# Test 3: Hinglish KYC Scam
Test-ScamDetection `
    -Language "hinglish" `
    -Message "Urgent! Aapka SBI KYC pending hai. 24 ghante me complete nahi kiya to account band ho jayega." `
    -Description "KYC + Urgency Tactic (Hinglish)"

# Test 4: Gujarati-English Bank Scam
Test-ScamDetection `
    -Language "gujarati_english" `
    -Message "Tamaru account block thava walu che. Atyare OTP share karo." `
    -Description "Bank Account Threat + OTP Request (Gujarati-English)"

# Test 5: Gujarati-English Prize Scam
Test-ScamDetection `
    -Language "gujarati_english" `
    -Message "Congratulations! Tamne 25 lakh no prize mali che. Details mate aa link par click karo." `
    -Description "Prize Scam (Gujarati-English)"

# Test 6: Multi-turn Hinglish Conversation
Write-Host "`n==============================================================`n" -ForegroundColor Cyan
Write-Host "Multi-turn Hinglish Conversation Test" -ForegroundColor Cyan
Write-Host "==============================================================`n" -ForegroundColor Cyan

$SessionId = ""

# Message 1
Write-Host "👤 Scammer: Aapka account me suspicious activity detect hui hai" -ForegroundColor Yellow
$Body1 = @{
    message = "Aapka account me suspicious activity detect hui hai"
    sender = "scammer"
    channel = "WhatsApp"
    metadata = @{
        language = "hinglish"
        locale = "IN"
    }
} | ConvertTo-Json

$Response1 = Invoke-RestMethod -Uri "$BASE_URL/v1/webhook" `
    -Method Post `
    -Headers @{
        "x-api-key" = $API_KEY
        "Content-Type" = "application/json"
    } `
    -Body $Body1

$SessionId = $Response1.sessionId
Write-Host "🤖 AI (Victim): $($Response1.agent_response)" -ForegroundColor Cyan

# Message 2
Start-Sleep -Seconds 2
Write-Host "`n👤 Scammer: Haan, aapka card ka details chahiye verification ke liye" -ForegroundColor Yellow
$Body2 = @{
    message = "Haan, aapka card ka details chahiye verification ke liye"
    sender = "scammer"
    channel = "WhatsApp"
    sessionId = $SessionId
    metadata = @{
        language = "hinglish"
        locale = "IN"
    }
} | ConvertTo-Json

$Response2 = Invoke-RestMethod -Uri "$BASE_URL/v1/webhook" `
    -Method Post `
    -Headers @{
        "x-api-key" = $API_KEY
        "Content-Type" = "application/json"
    } `
    -Body $Body2

Write-Host "🤖 AI (Victim): $($Response2.agent_response)" -ForegroundColor Cyan

# Message 3
Start-Sleep -Seconds 2
Write-Host "`n👤 Scammer: Bank se bol raha hun. OTP bhejo jaldi" -ForegroundColor Yellow
$Body3 = @{
    message = "Bank se bol raha hun. OTP bhejo jaldi"
    sender = "scammer"
    channel = "WhatsApp"
    sessionId = $SessionId
    metadata = @{
        language = "hinglish"
        locale = "IN"
    }
} | ConvertTo-Json

$Response3 = Invoke-RestMethod -Uri "$BASE_URL/v1/webhook" `
    -Method Post `
    -Headers @{
        "x-api-key" = $API_KEY
        "Content-Type" = "application/json"
    } `
    -Body $Body3

Write-Host "🤖 AI (Victim): $($Response3.agent_response)" -ForegroundColor Cyan

Write-Host "`n==============================================================`n" -ForegroundColor Green
Write-Host "✅ Hinglish & Gujarati-English Testing Complete!" -ForegroundColor Green
Write-Host "==============================================================`n" -ForegroundColor Green

Write-Host "📝 Summary:" -ForegroundColor Yellow
Write-Host "  - Tested scam detection in transliterated Indian languages" -ForegroundColor Gray
Write-Host "  - Tested AI responses in Hinglish and Gujarati-English" -ForegroundColor Gray
Write-Host "  - Tested multi-turn conversation handling" -ForegroundColor Gray
Write-Host "`n  See doc/HINGLISH_SUPPORT.md for more details`n" -ForegroundColor Cyan
