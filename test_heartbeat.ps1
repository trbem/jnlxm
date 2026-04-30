# 测试心跳API - 需要有效的device_token
# 由于设备已注册，我们先查询现有设备

# 测试获取设备配置
Write-Host "=== 测试获取设备配置 ==="
try {
    $config = Invoke-RestMethod -Uri 'http://localhost:8000/api/device/config' -Method GET
    $config | ConvertTo-Json
} catch {
    Write-Host "配置API错误: $_"
}

Write-Host ""
Write-Host "=== 测试心跳 (需要token) ==="
Write-Host "设备已注册，心跳API需要device_token"
Write-Host "请在ESP32日志中查看实际的device_token"
