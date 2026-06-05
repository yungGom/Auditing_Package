@echo off
title ICFR Flowchart Generator
cd /d "C:\Users\moonyong\dev\Auditing_Package\flowchart"

echo.
echo  ============================================
echo   ICFR Flowchart Generator - DEV Server
echo  ============================================
echo.
echo   서버 시작 중...
echo   브라우저에서 아래 주소로 접속하세요:
echo.
echo       http://localhost:5173/
echo.
echo   종료하려면 이 창에서 Ctrl+C 를 누르세요.
echo  ============================================
echo.

start "" "http://localhost:5173/"
npm run dev
