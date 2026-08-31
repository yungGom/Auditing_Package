@echo off
rem DSD footing launcher. Run with no argument to get the start screen (open a
rem report, pick from recents). Drag a PDF onto this file (or pass a path) to
rem skip the start screen and go straight into that report.
rem ASCII only: Korean text in .bat breaks depending on console codepage (chcp
rem 65001 has an offset bug in cmd.exe -- see the run.bat design doc in the repo root).
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH.
  echo Install Python 3.10+ and make sure "python" works from this folder.
  pause
  exit /b 2
)

python ui\preflight.py
if errorlevel 1 (
  pause
  exit /b 2
)

rem Once the UI window is up, this console should not get in the way, but it
rem must not disappear either -- an unhandled exception prints here, and a
rem hidden (pythonw.exe) console would swallow it silently. Minimize instead.
start /min "" python ui\app.py %*
