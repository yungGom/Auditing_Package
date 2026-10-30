@echo off
setlocal
rem DSD footing console launcher (no window) - drag a PDF onto this file. Output
rem lands next to the input PDF. The review window launcher is run.bat.
rem ASCII only: Korean text in .bat breaks depending on console codepage (chcp).
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: drag a PDF onto run_cli.bat, or run_cli.bat "C:\path\report.pdf"
  if not defined FOOT_NOPAUSE pause
  exit /b 2
)
python foot.py "%~1"
set "FOOT_EXIT_CODE=%ERRORLEVEL%"
if not defined FOOT_NOPAUSE pause
exit /b %FOOT_EXIT_CODE%
