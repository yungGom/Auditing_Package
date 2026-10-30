# -*- coding: utf-8 -*-
"""ui/app.py — PyWebView 진입점. run.bat 시작 화면(설계안_run_시작화면.md)과
기존 개발용 직접 실행 방식을 모두 지원한다.

  python ui/app.py                              → 시작 화면(파일 선택/최근 목록)
  python ui/app.py <원본.pdf>                    → 시작 화면 표시 후 그 파일을 자동으로
                                                    고른 것과 동일하게 진행(§3~4 흐름 그대로 —
                                                    판단 파일 보호·경고도 똑같이 적용된다)
  python ui/app.py <원본>_틱마크.pdf              → 산출물 직접 열기(기존 개발 경로, 분석 없음)

foot.py/render.py/marks.py 등 판정·렌더 경로는 건드리지 않는다 — 산출물(오버레이
PDF·marks.json)을 읽고, foot.py는 subprocess로 그대로 부를 뿐 로직을 복제하지
않는다. 완전 오프라인: 로컬 정적 파일을 file://로 열고, PDF 바이트는 JS 브리지로
직접 넘긴다 — 서버를 띄우지 않는다(설계안_UI셸_U1.md §1 결정 A).

★ 시작 인자를 Python이 직접 처리하지 않고 api._startup_arg에 얹어 JS(start.js)가
  꺼내가게 한다(get_startup_arg) — 대화상자로 고른 경로와 완전히 같은 코드 경로
  (openPath)를 태우기 위함이다. 두 경로를 따로 두면 "CLI 인자로 열 때는 경고가
  안 뜬다" 같은 함정이 생긴다.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import webview  # noqa: E402
from api import Api  # noqa: E402


def _file_url(path):
    # file:// URL을 명시해야 한다 — 맨 경로를 주면 pywebview가 is_local_url()에 걸려
    # bottle 로컬 서버를 자동으로 띄운다(2026-08-26 실측, CLAUDE.md 결정 14).
    return "file:///" + path.replace(os.sep, "/")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg:
        arg = os.path.abspath(arg)
        if not os.path.isfile(arg):
            print(f"[오류] 파일이 없습니다: {arg}")
            sys.exit(2)

    api = Api()
    is_tick = bool(arg and arg.endswith("_틱마크.pdf"))
    start_url = _file_url(os.path.join(HERE, "web", "index.html" if is_tick else "start.html"))

    window = webview.create_window(
        "DSD 풋팅", url=start_url, js_api=api, width=1200, height=900, min_size=(600, 400),
    )
    api.bind_window(window)

    if is_tick:
        # 기존 개발 경로 그대로 — 분석 없이 산출물을 직접 연다(빠른 UI 반복 작업용).
        base = arg[: -len("_틱마크.pdf")]
        api._pdf_path = arg
        marks_path = base + "_marks.json"
        api._marks_path = marks_path if os.path.isfile(marks_path) else None
        api._review_path = base + "_판단.json"
    elif arg:
        api._startup_arg = arg  # start.js가 get_startup_arg()로 꺼내 openPath(arg)를 부른다

    # 분석 중 창이 닫히면 subprocess를 정리한다(설계안 §5) — 판단 파일은 foot.py가
    # 모르는 파일이라 여기서 손댈 이유가 없고, 실제로 건드리지 않는다.
    window.events.closing += lambda: api.cancel_analysis()

    webview.start()


if __name__ == "__main__":
    main()
