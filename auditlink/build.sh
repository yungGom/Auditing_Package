#!/usr/bin/env bash
# ============================================================
#  AuditLink Build Script (macOS / Linux)
#  1. Install Python dependencies
#  2. Build React frontend
#  3. Package as single binary via PyInstaller
# ============================================================
set -e

echo "[1/4] Installing Python dependencies..."
pip install fastapi uvicorn pywebview pyinstaller aiosqlite

echo "[2/4] Installing Node.js dependencies..."
npm install

echo "[3/4] Building React frontend..."
npm run build

echo "[4/4] Packaging with PyInstaller..."
pyinstaller auditlink.spec --noconfirm

echo ""
echo "============================================================"
echo "  Build complete!"
echo "  Output: dist/AuditLink"
echo "============================================================"
