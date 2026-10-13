@echo off
setlocal
rem DSD footing - drag a PDF onto this file. Output lands next to the input PDF.
rem ASCII only: Korean text in .bat breaks depending on console codepage (chcp).
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: drag a PDF onto run.bat, or run.bat "C:\path\report.pdf"
  if not defined FOOT_NOPAUSE pause
  exit /b 2
)
python foot.py "%~1"
set "FOOT_EXIT_CODE=%ERRORLEVEL%"
if not defined FOOT_NOPAUSE pause
exit /b %FOOT_EXIT_CODE%
