@echo off
chcp 65001 >nul
title AuditDesk 실행기
cd /d "%~dp0"

rem ── 프런트 빌드 확인 ─────────────────────────────────────────────
if not exist "auditdesk\static\index.html" (
    echo [안내] 프런트 빌드가 없습니다. 최초 1회 빌드를 실행합니다...
    pushd webui
    call npm install --no-fund --no-audit
    call npm run build
    popd
)

rem ── 이미 실행 중이면 브라우저만 연다 ─────────────────────────────
powershell -NoProfile -Command "try{Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8710/api/status/overview -TimeoutSec 1|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if %errorlevel%==0 goto open

rem ── 서버 기동 (창을 닫으면 서버 종료) ────────────────────────────
start "AuditDesk 서버 (localhost:8710) — 이 창을 닫으면 종료됩니다" cmd /k "chcp 65001 >nul && python -m auditdesk --port 8710"

rem ── 기동 대기 (최대 30초) 후 브라우저 열기 ───────────────────────
powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){try{Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8710/api/status/overview -TimeoutSec 1|Out-Null;exit 0}catch{Start-Sleep -Milliseconds 500}};exit 1" >nul 2>&1
if not %errorlevel%==0 (
    echo [오류] 서버가 30초 내에 기동하지 않았습니다 — 서버 창의 메시지를 확인하세요.
    pause
    exit /b 1
)

:open
start "" http://127.0.0.1:8710/
exit /b 0
