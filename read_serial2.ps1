Add-Type -AssemblyName System.IO.Ports

$port = New-Object System.IO.Ports.SerialPort "COM6", 115200, "None", 8, "One"
$port.DtrEnable = $true
$port.RtsEnable = $true
$port.Open()

# 等待连接稳定
Start-Sleep 2

# 刷新缓冲区
if ($port.BytesToRead -gt 0) {
    [void]$port.ReadExisting()
}

# 发送换行触发输出
$port.WriteLine("")

# 等待数据
Start-Sleep 5

# 读取所有数据
$output = ""
while ($port.BytesToRead -gt 0) {
    $output += $port.ReadExisting()
}

$port.Close()

Write-Host "=== Serial Output ==="
Write-Host $output
