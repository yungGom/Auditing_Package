@echo off
title Audit Toolbox

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo ==================================================
    echo   First run: Setting up environment [once only]
    echo ==================================================
    echo.
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo   ERROR: Python not found.
        echo   Install Python 3.8+ from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo       Done.
    echo.
    echo [2/3] Activating...
    call .venv\Scripts\activate.bat
    echo       Done.
    echo.
    echo [3/3] Installing packages [5-15 min for first time]...
    echo       (EasyOCR requires PyTorch ~ large download)
    pip install streamlit pandas openpyxl python-dateutil PyMuPDF easyocr pdf2image Pillow tqdm --quiet
    echo       Done.
    echo.
    echo ==================================================
    echo   Setup complete. Next time it starts instantly.
    echo ==================================================
    echo.
    echo   [NOTE] For PDF OCR, Poppler is also required.
    echo   If not installed, run in another command prompt:
    echo       winget install oschwartz10612.Poppler
    echo.
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo ==================================================
echo   Starting Audit Toolbox
echo   Browser: http://localhost:8501
echo   Quit: close this window or Ctrl+C
echo ==================================================
echo.
echo   [SECURITY] All data stays on this computer.
echo   localhost only. No external connections.
echo   (EasyOCR model: first-time download only)
echo.

streamlit run audit_toolbox.py --server.address localhost --server.port 8501 --browser.gatherUsageStats false --server.headless false

pause
