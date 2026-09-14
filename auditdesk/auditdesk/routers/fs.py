"""/api/fs — 로컬 파일 선택 (OS 대화상자, 로컬 앱 전용)."""
import json
import subprocess
import sys

from fastapi import APIRouter, HTTPException

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
    if not isinstance(path, str) or not path.strip():
        raise HTTPException(422, "열 파일의 경로를 지정하세요")
    if not os.path.exists(path):
        raise HTTPException(404, "파일을 찾을 수 없습니다 — 파일 위치를 확인하세요")
    try:
        os.startfile(path)                      # Windows 로컬 앱 전용
    except OSError:
        raise HTTPException(409, "파일을 열 수 없습니다 — 접근 권한과 기본 프로그램 설정을 확인하세요") from None
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
