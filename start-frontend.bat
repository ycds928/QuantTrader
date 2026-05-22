@echo off
chcp 65001 >nul
setlocal EnableExtensions

echo ========================================
echo QuantFlow Frontend Starter
echo ========================================
echo.

set "ROOT_DIR=%~dp0"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

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
