$port = New-Object System.IO.Ports.SerialPort "COM6", 921600, "None", 8, "One"
$port.Open()
Start-Sleep 3
$data = $port.ReadExisting()
$port.Close()
Write-Host "=== Serial Output ==="
Write-Host $data
