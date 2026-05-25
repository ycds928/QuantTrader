@echo off
chcp 65001 >nul
setlocal EnableExtensions

echo ========================================
echo QuantFlow Frontend Starter
echo ========================================
echo.

set "ROOT_DIR=%~dp0"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "ROOT_DIR_MATCH=%ROOT_DIR:\=\\%"
title QuantFlow Frontend - ACTIVE

echo [INFO] Root directory: %ROOT_DIR%
echo [INFO] Frontend directory: %FRONTEND_DIR%
echo.

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] Cannot find frontend\package.json.
  echo [ERROR] Please run this bat from the QuantTrader project root.
  goto END
)

cd /d "%FRONTEND_DIR%"
if errorlevel 1 (
  echo [ERROR] Failed to enter frontend directory.
  goto END
)

echo [INFO] Closing old QuantFlow frontend startup windows...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $self=(Get-CimInstance Win32_Process -Filter \"ProcessId=$PID\"); $currentCmd=[int]$self.ParentProcessId; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cmd.exe' -and $_.ProcessId -ne $currentCmd -and $_.CommandLine -and ($_.CommandLine -match 'start-frontend\.bat' -or $_.CommandLine -match 'start-frontend\.cmd') } | ForEach-Object { taskkill /PID $_.ProcessId /T /F | Out-Null }"

echo [INFO] Stopping existing QuantFlow frontend processes on port 5000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $root='%ROOT_DIR_MATCH%'; $pids=@(); $pids += (Get-NetTCPConnection -LocalPort 5000 | Select-Object -ExpandProperty OwningProcess); $pids += (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'vite' -or $_.CommandLine -match 'pnpm dev') -and ($_.CommandLine -match [regex]::Escape($root) -or $_.CommandLine -match 'QuantTrader') } | Select-Object -ExpandProperty ProcessId); $pids | Sort-Object -Unique | ForEach-Object { if ($_ -and $_ -ne $PID) { taskkill /PID $_ /T /F 2>$null | Out-Null } }"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 1" >nul

where pnpm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] pnpm was not found in PATH.
  echo [HELP] Install pnpm first:
  echo        npm install -g pnpm
  goto END
)

if not exist "node_modules" (
  echo [WARN] node_modules not found. Installing dependencies...
  call pnpm install
  if errorlevel 1 (
    echo [ERROR] pnpm install failed.
    goto END
  )
)

echo [INFO] Starting frontend at:
echo        http://localhost:5000/account
echo.
echo [INFO] Press Ctrl+C to stop the server.
echo.

call pnpm dev --host 0.0.0.0 --port 5000

echo.
echo [WARN] Frontend server has stopped or exited.

:END
echo.
echo ========================================
echo Press any key to close this window.
echo ========================================
pause >nul
endlocal
