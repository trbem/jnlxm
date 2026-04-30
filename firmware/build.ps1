# 编译ESP-IDF固件
$env:PATH = "D:\app\Espressif\tools\xtensa-esp-elf\esp-14.2.0_20260121\xtensa-esp-elf\bin;D:\app\Espressif\tools\cmake\3.30.2\bin;D:\app\Espressif\tools\ninja\1.12.1;D:\app\Espressif\tools\idf-exe\1.0.3;D:\app\Espressif\python_env\idf5.4_py3.14_env\Scripts;D:\app\Espressif\tools\idf-git\2.44.0\cmd;C:\WINDOWS\system32;C:\WINDOWS"
$env:IDF_PATH = "D:\app\Espressif\frameworks\esp-idf-v5.4.4"
$env:IDF_PYTHON_ENV_PATH = "D:\app\Espressif\python_env\idf5.4_py3.14_env"
$env:IDF_TOOLS_PATH = "D:\app\Espressif"

Write-Host "PATH:" $env:PATH
Write-Host "IDF_PATH:" $env:IDF_PATH

Set-Location "c:\Users\admin\Desktop\jkxt\firmware"
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue

& python D:\app\Espressif\frameworks\esp-idf-v5.4.4\tools\idf.py set-target esp32s3
