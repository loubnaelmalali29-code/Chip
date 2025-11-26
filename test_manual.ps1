# Manual Test Script for Chip
# Run each test one at a time

$baseUrl = "http://localhost:8000/api/v1/webhooks/loop"
$headers = @{"Content-Type"="application/json"}

Write-Host "`n=== Chip Manual Testing ===" -ForegroundColor Green
Write-Host "Make sure the server is running first!`n" -ForegroundColor Yellow

# Test 1: Normal message
Write-Host "Test 1: Normal message" -ForegroundColor Cyan
$body1 = @{
    alert_type = "message_inbound"
    text = "What challenges are available?"
    recipient = "+15551234567"
    message_id = "test1"
} | ConvertTo-Json
Invoke-WebRequest -Uri $baseUrl -Method POST -Headers $headers -Body $body1
Write-Host "`nPress Enter to continue to next test..." -ForegroundColor Yellow
Read-Host

# Test 2: Misspelling "challege"
Write-Host "`nTest 2: Misspelling 'challege'" -ForegroundColor Cyan
$body2 = @{
    alert_type = "message_inbound"
    text = "challege"
    recipient = "+15551234567"
    message_id = "test2"
} | ConvertTo-Json
Invoke-WebRequest -Uri $baseUrl -Method POST -Headers $headers -Body $body2
Write-Host "`nPress Enter to continue to next test..." -ForegroundColor Yellow
Read-Host

# Test 3: Misspelling "comunity"
Write-Host "`nTest 3: Misspelling 'comunity'" -ForegroundColor Cyan
$body3 = @{
    alert_type = "message_inbound"
    text = "comunity"
    recipient = "+15551234567"
    message_id = "test3"
} | ConvertTo-Json
Invoke-WebRequest -Uri $baseUrl -Method POST -Headers $headers -Body $body3
Write-Host "`nPress Enter to continue to next test..." -ForegroundColor Yellow
Read-Host

# Test 4: Multiple misspellings
Write-Host "`nTest 4: Multiple misspellings" -ForegroundColor Cyan
$body4 = @{
    alert_type = "message_inbound"
    text = "challege comunity"
    recipient = "+15551234567"
    message_id = "test4"
} | ConvertTo-Json
Invoke-WebRequest -Uri $baseUrl -Method POST -Headers $headers -Body $body4
Write-Host "`nPress Enter to continue to next test..." -ForegroundColor Yellow
Read-Host

# Test 5: Misspelling in sentence
Write-Host "`nTest 5: Misspelling in sentence" -ForegroundColor Cyan
$body5 = @{
    alert_type = "message_inbound"
    text = "What challeges are in the comunity?"
    recipient = "+15551234567"
    message_id = "test5"
} | ConvertTo-Json
Invoke-WebRequest -Uri $baseUrl -Method POST -Headers $headers -Body $body5

Write-Host "`n=== All tests complete! ===" -ForegroundColor Green
Write-Host "Check the server logs to see spelling corrections in action.`n" -ForegroundColor Yellow

