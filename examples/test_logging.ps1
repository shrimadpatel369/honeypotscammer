# Test the logging system
# This script sends a test request and shows you where to find the logs

$API_URL = "http://localhost:8000"
$API_KEY = $env:API_KEY

if (-not $API_KEY) {
    Write-Host "Error: API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Please set it first: `$env:API_KEY = 'your-api-key'" -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Logging Test - Honeypot API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Create test request
$sessionId = "logging-test-$(Get-Date -Format 'yyyyMMddHHmmss')"
$body = @{
    sessionId = $sessionId
    message = @{
        sender = "scammer"
        text = "URGENT: Your bank account will be blocked today. Click here to verify: http://fake-bank.com/verify and send OTP to 9876543210"
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
    }
    conversationHistory = @()
    metadata = @{
        channel = "SMS"
        language = "English"
        locale = "IN"
    }
} | ConvertTo-Json -Depth 10

$headers = @{
    "Content-Type" = "application/json"
    "x-api-key" = $API_KEY
}

Write-Host "`n📤 Sending test request to API..." -ForegroundColor Green
Write-Host "Session ID: $sessionId" -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "$API_URL/api/v1/honeypot" -Method Post -Body $body -Headers $headers
    
    Write-Host "`n✅ Request successful!" -ForegroundColor Green
    Write-Host "Scam Detected: $($response.scamDetected)" -ForegroundColor $(if ($response.scamDetected) { "Red" } else { "Green" })
    Write-Host "Agent Reply: $($response.reply)" -ForegroundColor White
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "📋 Now check the logs:" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    $today = Get-Date -Format "yyyyMMdd"
    $logsDir = "logs"
    
    Write-Host "`n1. Application Log (Human Readable):" -ForegroundColor Yellow
    Write-Host "   File: logs\app_$today.log" -ForegroundColor White
    Write-Host "   Command: Get-Content logs\app_$today.log -Tail 100" -ForegroundColor Gray
    
    Write-Host "`n2. Request/Response Log (JSON):" -ForegroundColor Yellow
    Write-Host "   File: logs\requests_$today.log" -ForegroundColor White
    Write-Host "   Command: Get-Content logs\requests_$today.log | ConvertFrom-Json | ConvertTo-Json -Depth 10" -ForegroundColor Gray
    
    Write-Host "`n3. Search for your session:" -ForegroundColor Yellow
    Write-Host "   Command: Select-String -Path logs\*.log -Pattern '$sessionId'" -ForegroundColor Gray
    
    # Check if logs exist and show preview
    $appLog = "logs\app_$today.log"
    if (Test-Path $appLog) {
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "📄 Log Preview (Last 20 lines):" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Get-Content $appLog -Tail 20 | ForEach-Object {
            if ($_ -match "INCOMING TEST REQUEST|OUTGOING RESPONSE|GUVI CALLBACK") {
                Write-Host $_ -ForegroundColor Green
            } elseif ($_ -match "ERROR|Failed|❌") {
                Write-Host $_ -ForegroundColor Red
            } else {
                Write-Host $_
            }
        }
    } else {
        Write-Host "`n⚠️  Log file not found. Make sure the API is running." -ForegroundColor Yellow
    }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "✅ Test Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "`nThe hackathon provider's test requests will be logged the same way." -ForegroundColor White
    Write-Host "Check the logs to verify all test data is being captured." -ForegroundColor White
    
} catch {
    Write-Host "`n❌ Request failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nMake sure the API is running: docker-compose up -d" -ForegroundColor Yellow
}
