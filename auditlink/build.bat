@echo off
REM ============================================================
REM  AuditLink Build Script (Windows)
REM  1. Install Python dependencies
REM  2. Build React frontend
REM  3. Package as single EXE via PyInstaller
REM ============================================================

echo [1/4] Installing Python dependencies...
pip install fastapi uvicorn pywebview pyinstaller aiosqlite
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)

echo [2/4] Installing Node.js dependencies...
call npm install
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install Node.js dependencies
    pause
    exit /b 1
)

echo [3/4] Building React frontend...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERROR: React build failed
    pause
    exit /b 1
)

echo [4/4] Packaging with PyInstaller...
pyinstaller auditlink.spec --noconfirm
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Build complete!
echo  Output: dist\AuditLink.exe
echo ============================================================
echo.
pause
