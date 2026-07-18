"""/api/fs — 로컬 파일 선택 (OS 대화상자, 로컬 앱 전용)."""
import json
import subprocess
import sys

from fastapi import APIRouter

router = APIRouter()

_PICK_SCRIPT = r"""
import json, sys
import tkinter as tk
from tkinter import filedialog
root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
path = filedialog.askopenfilename(
    title="DSD 파일 선택",
    filetypes=[("DSD/XML", "*.dsd *.xml"), ("모든 파일", "*.*")])
print(json.dumps({"path": path or None}))
"""


@router.post("/open")
def open_path(body: dict):
    """로컬 파일을 OS 기본 프로그램으로 열기 (엑셀 열기 버튼)."""
    import os
    path = body.get("path") or ""
    if not os.path.exists(path):
        return {"ok": False, "error": f"파일 없음: {path}"}
    os.startfile(path)                          # Windows 로컬 앱 전용
    return {"ok": True}


@router.post("/pick")
def pick():
    """OS 파일 선택 대화상자 (서버 스레드 밖 별도 프로세스 — Tk 격리)."""
    out = subprocess.run([sys.executable, "-c", _PICK_SCRIPT],
                         capture_output=True, text=True, timeout=300)
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"path": None, "error": out.stderr[-300:]}


_SAVE_SCRIPT = r"""
import json, sys
import tkinter as tk
from tkinter import filedialog
root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
path = filedialog.asksaveasfilename(
    title="저장 위치 선택", initialfile=sys.argv[1] if len(sys.argv) > 1 else "",
    defaultextension=".dsd",
    filetypes=[("DSD", "*.dsd"), ("모든 파일", "*.*")])
print(json.dumps({"path": path or None}))
"""


@router.post("/save-pick")
def save_pick(body: dict = None):
    """OS 저장 위치 대화상자 — 제안 파일명 지정 가능."""
    suggest = (body or {}).get("suggest") or ""
    out = subprocess.run([sys.executable, "-c", _SAVE_SCRIPT, suggest],
                         capture_output=True, text=True, timeout=300)
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"path": None, "error": out.stderr[-300:]}
