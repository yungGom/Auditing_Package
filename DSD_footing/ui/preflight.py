# -*- coding: utf-8 -*-
"""run.bat이 UI를 띄우기 전에 부르는 의존성 점검. 막연히 "실행 안 됨"이 아니라
어느 패키지가 없는지 이름으로 콕 집어 알려준다 — 동료가 "안 돼요"라고 했을 때
개발자가 원격으로 원인을 짐작하지 않게 하기 위함(2026-08-29, run.bat 설계안).

성공 시 아무것도 출력하지 않고 종료코드 0 — run.bat이 조용히 다음 단계로 넘어간다.
"""
import importlib
import sys

# (표시 이름, import 이름, requirements.txt에 적힌 이름) — pywebview는 배포명과
# import명이 다르다(pip install pywebview → import webview).
DEPS = [
    ("pdfplumber", "pdfplumber", "pdfplumber"),
    ("pypdf", "pypdf", "pypdf"),
    ("reportlab", "reportlab", "reportlab"),
    ("openpyxl", "openpyxl", "openpyxl"),
    ("pywebview", "webview", "pywebview"),
]


def main():
    missing = []
    for display, modname, pipname in DEPS:
        try:
            importlib.import_module(modname)
        except ImportError:
            missing.append((display, pipname))

    if not missing:
        return 0

    print("=" * 60)
    print("[오류] 다음 라이브러리가 설치되어 있지 않습니다:")
    for display, _ in missing:
        print(f"  - {display}")
    print()
    print("설치 방법 (이 폴더에서):")
    print(f"  {sys.executable} -m pip install -r requirements.txt")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
