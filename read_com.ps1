$port = New-Object System.IO.Ports.SerialPort "COM6", 115200
$port.ReadTimeout = 5000
try {
    $port.Open()
    Start-Sleep 2
    
    # 读取所有可用数据
    $output = ""
    try {
        while ($true) {
            $char = $port.ReadChar()
            $output += $char
        }
    } catch {
        # 超时或结束
    }
    
    $port.Close()
    Write-Host "=== Serial Output ==="
    Write-Host $output
} catch {
    Write-Host "Error: $_"
}
