"""UI-6 게이트: 금지어 grep 강제 — 패치 ID·영문 모듈명의 UI 노출 금지.

검사 면: ① webui/src/*.tsx 문자열 리터럴·JSX 텍스트
        ② 산출물 라이터(py)의 한국어 문자열 리터럴 (docstring 제외)
        ③ docs/USER_GUIDE.md
허용 목록: 코드 식별자·주석·내부 로그·GATES.json·docs/ 스펙 문서·
AI_Footing(법인 산출물 형식 고유명)·element/QName 표기.
기준: docs/GLOSSARY.md
"""
import ast
import glob
import io
import os
import re

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", ".."))
_BAN_ID = re.compile(r"(?<![A-Za-z0-9가-힣_])(?:UI|[A-Z]{1,2})-\d[0-9a-z]*")
_BAN_WORDS = ("Workbench", "Studio", "Explorer", "TOOLKIT", "워크벤치",
              "스튜디오")
_ALLOW = ("AI_Footing",)

# 산출물을 쓰는 모듈 (사용자에게 보이는 문자열 발생 지점)
_WRITER_MODULES = ("xbrl_recon.py", "rollforward.py", "recon.py",
                   "foot_excel.py", "worksheet.py", "note_worksheet.py",
                   "excel_out.py")


def _violations(chunks, where):
    out = []
    for text in chunks:
        for a in _ALLOW:
            text = text.replace(a, "")
        for m in _BAN_ID.finditer(text):
            out.append((where, m.group(0), text.strip()[:60]))
        for w in _BAN_WORDS:
            if w in text:
                out.append((where, w, text.strip()[:60]))
    return out


def _tsx_chunks(path):
    """주석 제거 후 문자열 리터럴 + JSX 텍스트 노드만."""
    s = io.open(path, encoding="utf-8").read()
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"^\s*(import|export|\})[^\n]*from[^\n]*$", "", s,
               flags=re.M)                      # 모듈 경로는 식별자 영역
    chunks = re.findall(r'"([^"\n]*)"|\'([^\'\n]*)\'|`([^`]*)`', s)
    flat = [a or b or c for a, b, c in chunks]
    flat += re.findall(r">([^<>{}]*[가-힣][^<>{}]*)<", s)
    return flat


def _py_korean_literals(path):
    """docstring 제외, 한국어 포함 문자열 리터럴."""
    src = io.open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                docstrings.add(id(node.body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings \
                and re.search(r"[가-힣]", node.value):
            out.append(node.value)
    return out


def test_webui_no_banned_terms():
    files = glob.glob(os.path.join(_ROOT, "webui", "src", "*.tsx"))
    assert files
    bad = []
    for f in files:
        bad += _violations(_tsx_chunks(f), os.path.basename(f))
    assert not bad, bad[:10]


def test_excel_writers_no_banned_terms():
    bad = []
    for fn in _WRITER_MODULES:
        p = os.path.join(_ROOT, "dsd_workbench", "dsd_tool", fn)
        bad += _violations(_py_korean_literals(p), fn)
    assert not bad, bad[:10]


def test_user_guide_no_banned_terms():
    p = os.path.join(_ROOT, "docs", "USER_GUIDE.md")
    if not os.path.exists(p):
        pytest.skip("USER_GUIDE 없음")
    lines = io.open(p, encoding="utf-8").read().splitlines()
    bad = _violations(lines, "USER_GUIDE.md")
    assert not bad, bad[:10]
