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
              "스튜디오",
              # UI-7 확장: 내부 동작·마크업 용어의 사용자 노출 금지
              "repack", "dry-run", "diff", "게이트", "&cr;",
              # UI-9 확장: 언어 내부값 표기의 사용자 노출 금지
              "null", "undefined", "None")
# UI-7: G1·G2 등 내부 점검 ID (한국어 노출 문자열 한정 검사)
_BAN_G_RE = re.compile(r"(?<![A-Za-z0-9가-힣_])G\d(?![0-9A-Za-z])")
_ALLOW = ("AI_Footing",)
# 명령줄 예시는 코드 식별자 영역 (GLOSSARY 허용 목록)
_ALLOW_CHUNK = ("python -m dsd_tool",)

# 산출물을 쓰는 모듈 (사용자에게 보이는 문자열 발생 지점)
_WRITER_MODULES = ("xbrl_recon.py", "rollforward.py", "recon.py",
                   "foot_excel.py", "worksheet.py", "note_worksheet.py",
                   "excel_out.py")


def _violations(chunks, where):
    out = []
    for text in chunks:
        # UI-7: 사용자 노출 한국어 문자열만 검사 — 식별자·URL·색상 등
        # 비한국어 리터럴은 코드 영역 (허용 목록)
        if not re.search(r"[가-힣]", text):
            continue
        if any(a in text for a in _ALLOW_CHUNK):
            continue
        for a in _ALLOW:
            text = text.replace(a, "")
        for m in _BAN_ID.finditer(text):
            out.append((where, m.group(0), text.strip()[:60]))
        for m in _BAN_G_RE.finditer(text):
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


def test_routers_no_banned_terms():
    """UI-7: 라우터 오류 메시지·라벨(화면 노출)도 3면 검사에 포함."""
    bad = []
    for fn in ("workbench.py", "studio.py", "explorer.py"):
        p = os.path.join(_ROOT, "auditdesk", "routers", fn)
        if not os.path.exists(p):
            continue
        bad += _violations(_py_korean_literals(p), fn)
    assert not bad, bad[:10]


def test_user_guide_no_banned_terms():
    p = os.path.join(_ROOT, "docs", "USER_GUIDE.md")
    if not os.path.exists(p):
        pytest.skip("USER_GUIDE 없음")
    lines = io.open(p, encoding="utf-8").read().splitlines()
    bad = _violations(lines, "USER_GUIDE.md")
    assert not bad, bad[:10]
