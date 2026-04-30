$port = New-Object System.IO.Ports.SerialPort "COM6", 115200
$port.ReadTimeout = 3000
$port.WriteLine("")

Start-Sleep 2

$output = ""
try {
    while ($port.BytesToRead -gt 0) {
        $output += $port.ReadExisting()
    }
} catch {}

$port.Close()

Write-Host "=== Output ==="
Write-Host $output
