$body = @{
    device_name = "ESP32-S3-EYE-001"
    device_type = "ESP32-S3-EYE"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri 'http://localhost:8000/api/device/register' -Method POST -ContentType 'application/json' -Body $body
Write-Host "=== Device Register Response ==="
$result | ConvertTo-Json
