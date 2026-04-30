# 测试心跳API
$token = "043ed95356538e90ddb1dfa15f3d8cd56d6f2b3fc2f6d636f5fb996f3d50d6df"
$body = "device_token=$token"

Write-Host "=== 测试心跳 ==="
try {
    $result = Invoke-RestMethod -Uri 'http://localhost:8000/api/device/heartbeat' -Method POST -ContentType 'application/x-www-form-urlencoded' -Body $body
    Write-Host "心跳成功!"
    $result | ConvertTo-Json
} catch {
    Write-Host "心跳失败: $_"
}

Write-Host ""
Write-Host "=== 后端API测试完成 ==="
Write-Host "后端服务运行在 http://localhost:8000"
Write-Host "设备Token: $token"
