"""dsd_workbench 오프라인 보증 테스트 (패치 A-1).

보안 원칙: 고객사 DSD를 다루는 이 앱에는 네트워크 코드가 일절 없어야 한다.
- requirements.txt에 네트워크 라이브러리 의존 금지
- 소스 전체에 네트워크 모듈 import 금지
"""
import os
import re

import pytest

_PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKBENCH_DIR = os.path.dirname(_PKG_DIR)

# 네트워크 통신에 쓰이는 모듈들 (표준 라이브러리 포함)
FORBIDDEN_MODULES = [
    "requests", "httpx", "aiohttp", "urllib3", "websockets", "websocket",
    "urllib.request", "urllib.parse", "http.client", "socket", "ftplib",
    "smtplib", "telnetlib", "xmlrpc",
]

_IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+([\w.]+)", re.MULTILINE)


def _source_files():
    for root, dirs, files in os.walk(_PKG_DIR):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "fixtures")]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def test_no_network_libs_in_requirements():
    req = os.path.join(_WORKBENCH_DIR, "requirements.txt")
    assert os.path.exists(req), "dsd_workbench/requirements.txt 없음"
    with open(req, encoding="utf-8") as f:
        lines = [ln.split("#")[0].strip().lower() for ln in f]
    deps = [ln for ln in lines if ln]
    for bad in ("requests", "httpx", "aiohttp", "urllib3", "websockets"):
        assert not any(d.startswith(bad) for d in deps), \
            f"네트워크 라이브러리 의존 발견: {bad}"


@pytest.mark.parametrize("path", list(_source_files()),
                         ids=lambda p: os.path.relpath(p, _PKG_DIR))
def test_no_network_imports(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    imported = set()
    for m in _IMPORT_RE.finditer(src):
        mod = m.group(1)
        imported.add(mod)
        imported.add(mod.split(".")[0])
    for bad in FORBIDDEN_MODULES:
        assert bad not in imported, \
            f"{os.path.basename(path)}: 네트워크 모듈 import 금지 위반 ({bad})"
