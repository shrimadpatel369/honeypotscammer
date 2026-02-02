# Performance Test Script
# Tests the API performance and measures latency

$API_URL = "http://localhost:8000"
$API_KEY = $env:API_KEY

if (-not $API_KEY) {
    Write-Host "Error: API_KEY environment variable not set" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Honeypot API Performance Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n1. Health Check with Cache Stats" -ForegroundColor Green
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$response = Invoke-RestMethod -Uri "$API_URL/health" -Method Get
$stopwatch.Stop()
Write-Host "Response Time: $($stopwatch.ElapsedMilliseconds)ms" -ForegroundColor Yellow
$response | ConvertTo-Json -Depth 10

# Test 2: First Request (Cache Miss)
Write-Host "`n2. First Request - Scam Detection (Cache Miss Expected)" -ForegroundColor Green
$body = @{
    sessionId = "perf-test-$(Get-Date -Format 'yyyyMMddHHmmss')"
    message = @{
        sender = "scammer"
        text = "Your bank account will be blocked. Share OTP immediately."
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

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$response = Invoke-RestMethod -Uri "$API_URL/api/v1/honeypot" -Method Post -Body $body -Headers $headers
$stopwatch.Stop()
Write-Host "Response Time: $($stopwatch.ElapsedMilliseconds)ms" -ForegroundColor Yellow
Write-Host "Scam Detected: $($response.scamDetected)" -ForegroundColor $(if ($response.scamDetected) { "Red" } else { "Green" })
Write-Host "Reply: $($response.reply)" -ForegroundColor White

# Test 3: Second Request (Cache Hit Expected)
Write-Host "`n3. Similar Request - Scam Detection (Cache Hit Expected)" -ForegroundColor Green
$body2 = @{
    sessionId = "perf-test-$(Get-Date -Format 'yyyyMMddHHmmss')-2"
    message = @{
        sender = "scammer"
        text = "Your bank account will be blocked. Share OTP immediately."
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
    }
    conversationHistory = @()
    metadata = @{
        channel = "SMS"
        language = "English"
        locale = "IN"
    }
} | ConvertTo-Json -Depth 10

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$response2 = Invoke-RestMethod -Uri "$API_URL/api/v1/honeypot" -Method Post -Body $body2 -Headers $headers
$stopwatch.Stop()
Write-Host "Response Time: $($stopwatch.ElapsedMilliseconds)ms" -ForegroundColor Yellow
Write-Host "Scam Detected: $($response2.scamDetected)" -ForegroundColor $(if ($response2.scamDetected) { "Red" } else { "Green" })

# Test 4: Multiple Parallel Requests
Write-Host "`n4. Parallel Requests (10 concurrent)" -ForegroundColor Green
$jobs = @()
$stopwatchParallel = [System.Diagnostics.Stopwatch]::StartNew()

for ($i = 1; $i -le 10; $i++) {
    $sessionId = "perf-parallel-$i-$(Get-Date -Format 'yyyyMMddHHmmss')"
    $testBody = @{
        sessionId = $sessionId
        message = @{
            sender = "scammer"
            text = "Test message $i - Your account needs verification"
            timestamp = (Get-Date).ToUniversalTime().ToString("o")
        }
        conversationHistory = @()
        metadata = @{
            channel = "SMS"
            language = "English"
            locale = "IN"
        }
    } | ConvertTo-Json -Depth 10
    
    $job = Start-Job -ScriptBlock {
        param($url, $headers, $body)
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -Headers $headers
            $sw.Stop()
            return @{
                success = $true
                time = $sw.ElapsedMilliseconds
                scamDetected = $response.scamDetected
            }
        } catch {
            $sw.Stop()
            return @{
                success = $false
                time = $sw.ElapsedMilliseconds
                error = $_.Exception.Message
            }
        }
    } -ArgumentList "$API_URL/api/v1/honeypot", $headers, $testBody
    
    $jobs += $job
}

# Wait for all jobs to complete
$results = $jobs | Wait-Job | Receive-Job
$stopwatchParallel.Stop()

Write-Host "Total Time: $($stopwatchParallel.ElapsedMilliseconds)ms" -ForegroundColor Yellow
Write-Host "Successful Requests: $(($results | Where-Object { $_.success }).Count)/10" -ForegroundColor Green
$avgTime = ($results | Where-Object { $_.success } | Measure-Object -Property time -Average).Average
Write-Host "Average Response Time: $([math]::Round($avgTime, 2))ms" -ForegroundColor Yellow
$minTime = ($results | Where-Object { $_.success } | Measure-Object -Property time -Minimum).Minimum
$maxTime = ($results | Where-Object { $_.success } | Measure-Object -Property time -Maximum).Maximum
Write-Host "Min: $($minTime)ms, Max: $($maxTime)ms" -ForegroundColor White

# Clean up jobs
$jobs | Remove-Job

# Test 5: Cache Stats After Tests
Write-Host "`n5. Final Cache Statistics" -ForegroundColor Green
$response = Invoke-RestMethod -Uri "$API_URL/health" -Method Get
Write-Host "Cache Hit Rate: $($response.cache.hit_rate)" -ForegroundColor $(if ([int]$response.cache.hit_rate.Replace('%','') -gt 50) { "Green" } else { "Yellow" })
Write-Host "Total Requests: $($response.cache.total_requests)" -ForegroundColor White
Write-Host "Cache Hits: $($response.cache.hits)" -ForegroundColor Green
Write-Host "Cache Misses: $($response.cache.misses)" -ForegroundColor Yellow
Write-Host "Cache Size: $($response.cache.size)/$($response.cache.max_size)" -ForegroundColor White

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Performance Test Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
