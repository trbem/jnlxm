@echo off
REM ESP-IDF Build Script for ESP32-S3
cd /d "C:\Users\admin\Desktop\jkxt\firmware"

REM Clean build directory
if exist build rmdir /s /q build

REM Export ESP-IDF environment
call "D:\app\Espressif\frameworks\esp-idf-v5.4.4\export.ps1"

REM Override CMake to use version 3.24
set PATH=D:\cmake-3.24.3\cmake-3.24.3-windows-x86_64\bin;%PATH%

REM Set target and build
python "D:\app\Espressif\frameworks\esp-idf-v5.4.4\tools\idf.py" set-target esp32s3
if %ERRORLEVEL% neq 0 exit /b 1

echo.
echo === Build completed ===
pause
