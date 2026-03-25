@echo off
title AuditLink Launcher
cd /d "C:\Users\moonyong\Auditing_Package\auditlink"

echo ========================================
echo   AuditLink 시작 중...
echo ========================================
echo.

:: 백엔드 서버 (새 cmd 창)
echo [1/2] 백엔드 서버 시작 (port 8000)...
start "AuditLink Backend" cmd /k "cd /d C:\Users\moonyong\Auditing_Package\auditlink && python -m uvicorn backend.main:app --port 8000"

:: 프론트엔드 개발 서버 (새 cmd 창)
echo [2/2] 프론트엔드 서버 시작 (port 5173)...
start "AuditLink Frontend" cmd /k "cd /d C:\Users\moonyong\Auditing_Package\auditlink && npm run dev"

:: 3초 대기 후 브라우저 오픈
echo.
echo 3초 후 브라우저를 엽니다...
timeout /t 3 /nobreak >nul
start http://localhost:5173/

echo.
echo ========================================
echo   AuditLink가 실행되었습니다.
echo   - 백엔드: http://localhost:8000
echo   - 프론트엔드: http://localhost:5173
echo   종료하려면 각 cmd 창을 닫으세요.
echo ========================================
