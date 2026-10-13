@echo off
cd /d "%~dp0"
title PDFMathTranslate Desktop Launcher

if exist "desktop\src-tauri\target\release\desktop.exe" (
    start "" /d "%~dp0" "desktop\src-tauri\target\release\desktop.exe"
    exit /b 0
)

echo [LOI] Khong tim thay file desktop.exe!
pause
exit /b 1
