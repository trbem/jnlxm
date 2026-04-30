$body = @{
    device_name = "ESP32-S3-EYE-001"
    device_type = "ESP32-S3-EYE"
} | ConvertTo-Json

Write-Host "=== 测试设备注册 ==="
try {
    $result = Invoke-RestMethod -Uri 'http://localhost:8000/api/device/register' -Method POST -ContentType 'application/json' -Body $body
    Write-Host "注册成功!"
    Write-Host "Device ID: $($result.device_id)"
    Write-Host "Device Token: $($result.device_token)"
    
    # 保存token到文件供后续使用
    $result.device_token | Out-File "c:\Users\admin\Desktop\jkxt\device_token.txt"
    Write-Host "Token已保存到 device_token.txt"
} catch {
    $errorDetail = $_.Exception.Response
    if ($errorDetail) {
        $reader = [System.IO.StreamReader]::new($errorDetail.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        $reader.Close()
        Write-Host "注册失败: $responseBody"
    } else {
        Write-Host "注册失败: $_"
    }
}
