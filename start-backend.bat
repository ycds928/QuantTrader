@echo off
chcp 65001 >nul
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "ROOT_DIR_MATCH=%ROOT_DIR:\=\\%"
title QuantFlow Backend - ACTIVE

if not exist "%BACKEND_DIR%\main.py" (
  echo [ERROR] Cannot find backend\main.py under "%ROOT_DIR%".
  goto :error
)

echo [INFO] Closing old QuantFlow backend startup windows...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $self=(Get-CimInstance Win32_Process -Filter \"ProcessId=$PID\"); $currentCmd=[int]$self.ParentProcessId; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cmd.exe' -and $_.ProcessId -ne $currentCmd -and $_.CommandLine -and $_.CommandLine -match 'start-backend\.bat' } | ForEach-Object { taskkill /PID $_.ProcessId /T /F | Out-Null }"

echo [INFO] Stopping existing QuantFlow backend processes on port 8000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $root='%ROOT_DIR_MATCH%'; $pids=@(); $pids += (Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess); $pids += (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ((($_.CommandLine -match 'uvicorn') -and ($_.CommandLine -match 'main:app')) -or ($_.CommandLine -match 'multiprocessing\.spawn')) -and ($_.CommandLine -match [regex]::Escape($root) -or $_.CommandLine -match 'QuantTrader' -or $_.CommandLine -match 'parent_pid=') } | Select-Object -ExpandProperty ProcessId); $pids | Sort-Object -Unique | ForEach-Object { if ($_ -and $_ -ne $PID) { taskkill /PID $_ /T /F 2>$null | Out-Null } }"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 1" >nul

cd /d "%BACKEND_DIR%"

echo [INFO] Backend directory: %CD%
echo [INFO] THS client path uses backend default or existing THS_CLIENT_PATH env.
if not defined TESSERACT_CMD (
  if exist "E:\Tesseract-OCR\tesseract.exe" set "TESSERACT_CMD=E:\Tesseract-OCR\tesseract.exe"
)
if defined TESSERACT_CMD (
  echo [INFO] Tesseract OCR: %TESSERACT_CMD%
) else (
  echo [WARN] Tesseract OCR not configured. Captcha OCR will fall back to manual input.
)
echo [INFO] Starting QuantFlow backend at http://127.0.0.1:8000
echo [INFO] Press Ctrl+C to stop.
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python was not found in PATH.
  goto :error
)

python -m uvicorn main:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
  echo [ERROR] Backend server exited with an error.
  goto :error
)

endlocal
exit /b 0

:error
echo.
echo [INFO] The window will stay open so you can read the error.
pause
endlocal
exit /b 1
