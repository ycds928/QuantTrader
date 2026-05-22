@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"

if not exist "%BACKEND_DIR%\main.py" (
  echo [ERROR] Cannot find backend\main.py under "%ROOT_DIR%".
  goto :error
)

cd /d "%BACKEND_DIR%"

echo [INFO] Backend directory: %CD%
echo [INFO] THS client path uses backend default or existing THS_CLIENT_PATH env.
echo [INFO] Starting QuantFlow backend at http://127.0.0.1:8000
echo [INFO] Press Ctrl+C to stop.
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python was not found in PATH.
  goto :error
)

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
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
