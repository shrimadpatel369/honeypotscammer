# PowerShell test script for the Honeypot API
# Run this script from the project root directory

# Load environment variables from .env file
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Variable -Name $name -Value $value -Scope Script
        }
    }
} else {
    Write-Host "Error: .env file not found" -ForegroundColor Red
    exit 1
}

$API_URL = "http://localhost:8000"
$API_KEY = $env:API_KEY

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Honeypot API Test Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`nTest 1: Health Check" -ForegroundColor Green
$response = Invoke-RestMethod -Uri "$API_URL/health" -Method Get
$response | ConvertTo-Json -Depth 10

# Test 2: First Message (Scam Detection)
Write-Host "`nTest 2: First Message (Scam Detection)" -ForegroundColor Green
$body = Get-Content "examples\request_first_message.json" -Raw
$headers = @{
    "Content-Type" = "application/json"
    "x-api-key" = $API_KEY
}

$response = Invoke-RestMethod -Uri "$API_URL/api/v1/honeypot" -Method Post -Body $body -Headers $headers
$response | ConvertTo-Json -Depth 10

$sessionId = $response.sessionId
Write-Host "`nSession ID: $sessionId" -ForegroundColor Yellow

# Test 3: Follow-up Message
Write-Host "`nTest 3: Follow-up Message" -ForegroundColor Green
$body = Get-Content "examples\request_followup_message.json" -Raw
$response = Invoke-RestMethod -Uri "$API_URL/api/v1/honeypot" -Method Post -Body $body -Headers $headers
$response | ConvertTo-Json -Depth 10

# Test 4: Get Session Details
Write-Host "`nTest 4: Get Session Details" -ForegroundColor Green
$response = Invoke-RestMethod -Uri "$API_URL/api/v1/sessions/$sessionId" -Method Get -Headers @{"x-api-key" = $API_KEY}
$response | ConvertTo-Json -Depth 10

# Test 5: List All Sessions
Write-Host "`nTest 5: List All Sessions" -ForegroundColor Green
$response = Invoke-RestMethod -Uri "$API_URL/api/v1/sessions?limit=5" -Method Get -Headers @{"x-api-key" = $API_KEY}
$response | ConvertTo-Json -Depth 10

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "All tests completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
