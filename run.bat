@echo off
cd /d "%~dp0"
title PDFMathTranslate (pdf2zh) Web UI

echo ======================================================================
echo          PDFMathTranslate (pdf2zh) - Dang khoi chay Giao dien Web
echo ======================================================================
echo.

if not exist ".venv\Scripts\python.exe" goto no_venv

echo [*] Kiem tra va giai phong cong ket noi neu can...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 7860 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [*] Dang khoi dong may chu Web UI...
echo [*] Trinh duyet web se tu dong mo tai: http://127.0.0.1:7860
echo [*] De dung chuong trinh, hay dong cua so nay hoac nhan Ctrl+C.
echo.

call ".venv\Scripts\python.exe" -m pdf2zh.pdf2zh -i
goto end

:no_venv
echo [LOI] Khong tim thay moi truong ao .venv!
echo Vui long kiem tra lai thu muc hoac cai dat lai moi truong.
echo.
pause
exit /b 1

:end
pause
