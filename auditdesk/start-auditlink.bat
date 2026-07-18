@echo off
chcp 65001 >nul
title AuditLink v2
cd /d "%~dp0"

echo ============================================
echo    AuditLink v2 - launching...
echo ============================================
echo.

rem --- First run: create backend venv + install deps ---
if not exist "backend\.venv\Scripts\python.exe" (
  echo [setup] Creating backend environment ^(first run only^)...
  python -m venv "backend\.venv"
  "backend\.venv\Scripts\python.exe" -m pip install --upgrade pip -q
  "backend\.venv\Scripts\python.exe" -m pip install -q -r "backend\requirements.txt"
)

rem --- First run: install frontend packages ---
if not exist "frontend\node_modules" (
  echo [setup] Installing frontend packages ^(first run, a few minutes^)...
  pushd frontend
  call npm install
  popd
)

echo [1/2] Backend  -> http://localhost:8000
start "AuditLink Backend" /min cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/2] Frontend -> http://localhost:5173
start "AuditLink Frontend" /min cmd /k "cd frontend && npm run dev"

echo.
echo Opening browser shortly...
timeout /t 5 /nobreak >nul
start "" http://localhost:5173/

echo.
echo ============================================
echo   AuditLink is running.
echo   To stop: close the two minimized cmd windows.
echo ============================================
timeout /t 3 /nobreak >nul
exit
