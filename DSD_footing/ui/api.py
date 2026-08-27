# -*- coding: utf-8 -*-
"""api — PyWebView JS 브리지. get_pdf() 하나만 노출한다.

읽는 파일은 app.py 실행 시 넘겨받은 경로 하나로 고정한다 — JS 쪽에 임의 경로를
읽을 수 있는 API를 열어주지 않는다(설계안_UI셸_U1.md §2). 완전 오프라인:
이 호출은 HTTP가 아니라 웹뷰 엔진의 네이티브 브리지(Windows/WebView2)를 타므로
개발자도구 Network 탭에 잡히지 않는다(설계안 §1 안 1).
"""
import base64
import os


class Api:
    def __init__(self, pdf_path):
        self._pdf_path = pdf_path

    def get_pdf(self):
        """→ {name, base64} 고정 파일 하나. 실패 시 {error: 사유}(조용히 빈 값 금지)."""
        try:
            with open(self._pdf_path, "rb") as f:
                data = f.read()
        except OSError as e:
            return {"error": f"파일을 열 수 없습니다: {e}"}
        return {"name": os.path.basename(self._pdf_path),
                "base64": base64.b64encode(data).decode("ascii")}
