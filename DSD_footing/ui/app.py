# -*- coding: utf-8 -*-
"""ui/app.py — U-1 진입점. PyWebView 창을 띄우고 지정한 PDF를 pdf.js로 보여준다.

foot.py/render.py/marks.py 등 판정·렌더 경로는 건드리지 않는다 — 산출물(오버레이
PDF)을 읽기만 한다. 완전 오프라인: 로컬 정적 파일을 file://로 열고, PDF 바이트는
JS 브리지(api.Api.get_pdf)로 직접 넘긴다 — 서버를 띄우지 않는다(설계안_UI셸_U1.md
§1 결정 A, 게이트 5 "네트워크 요청 0건"이 포트를 아예 안 여는 것을 뜻한다는
확인에 따름, 2026-08-26).

사용:
  python ui/app.py <오버레이_PDF.pdf>
  예) python ui/app.py "samples/[조선내화]반기연결검토보고서(2026.08.13)_틱마크.pdf"

개발 시 실제 창(WebView2)에 Playwright를 CDP로 붙이려면 다음 환경변수를 켠다
(배포본에는 없음 — 설계안 §4-1):
  set WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import webview  # noqa: E402
from api import Api  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("사용법: python ui/app.py <오버레이_PDF.pdf>")
        sys.exit(2)
    pdf_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(pdf_path):
        print(f"[오류] 파일이 없습니다: {pdf_path}")
        sys.exit(2)

    index_html = os.path.join(HERE, "web", "index.html")
    # file:// URL을 명시해야 한다 — 맨 경로를 주면 pywebview가 is_local_url()에 걸려
    # bottle 로컬 서버를 자동으로 띄운다(실측: 127.0.0.1:포트가 LISTENING으로 열림).
    # js_api 호출은 file:// 모드에서도 WebView2의 네이티브 postMessage 브리지를 타서
    # 동작한다 — 서버가 필요한 건 자산 서빙 쪽이지 브리지 쪽이 아니다(설계안 §1 결정 A,
    # 게이트 5 "포트를 아예 안 연다"를 satisfy하려면 이 경로가 맞다, 2026-08-26 실측 확인).
    index_url = "file:///" + index_html.replace(os.sep, "/")

    # marks.json 경로 역산 — foot.py 명명 규칙(<원본>_틱마크.pdf / <원본>_marks.json,
    # 같은 <원본> 베이스)에서 접미사만 바꿔 찾는다. U-2 설계안 §1.
    SUFFIX = "_틱마크.pdf"
    marks_path = None
    review_path = None
    if pdf_path.endswith(SUFFIX):
        base = pdf_path[: -len(SUFFIX)]
        candidate = base + "_marks.json"
        if os.path.isfile(candidate):
            marks_path = candidate
        # 판단 파일 — marks.json을 덮어쓰지 않는다. foot.py를 다시 돌리면 marks.json이
        # 통째로 재생성되므로, 같은 파일에 담으면 재분석 한 번에 판단이 전부 사라진다
        # (되돌릴 방법이 없는 사고, U-6 설계안 §1). 없으면 첫 판단 때 만들어진다.
        review_path = base + "_판단.json"

    api = Api(pdf_path, marks_path, review_path)
    webview.create_window(
        f"DSD 풋팅 — {os.path.basename(pdf_path)}",
        url=index_url, js_api=api, width=1200, height=900, min_size=(600, 400),
    )
    webview.start()


if __name__ == "__main__":
    main()
