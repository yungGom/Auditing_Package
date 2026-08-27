# -*- coding: utf-8 -*-
"""api — PyWebView JS 브리지. get_pdf()/get_marks() 두 개만 노출한다.

읽는 파일은 app.py 실행 시 넘겨받은 경로로 고정한다 — JS 쪽에 임의 경로를
읽을 수 있는 API를 열어주지 않는다(설계안_UI셸_U1.md §2). 완전 오프라인:
이 호출은 HTTP가 아니라 웹뷰 엔진의 네이티브 브리지(Windows/WebView2)를 타므로
개발자도구 Network 탭에 잡히지 않는다(설계안 §1 안 1).
"""
import base64
import json
import os


class Api:
    def __init__(self, pdf_path, marks_path=None):
        self._pdf_path = pdf_path
        self._marks_path = marks_path

    def get_pdf(self):
        """→ {name, base64} 고정 파일 하나. 실패 시 {error: 사유}(조용히 빈 값 금지)."""
        try:
            with open(self._pdf_path, "rb") as f:
                data = f.read()
        except OSError as e:
            return {"error": f"파일을 열 수 없습니다: {e}"}
        return {"name": os.path.basename(self._pdf_path),
                "base64": base64.b64encode(data).decode("ascii")}

    def get_marks(self):
        """→ {marks, counts}. annotations[]는 여기서부터 걸러 JS로 아예 보내지 않는다 —
        U-2 요구("annotations는 목록에 넣지 않는다")를 렌더 단계가 아니라 전송 단계에서
        지킨다(가장 강한 보장: 브라우저 메모리에 annotations가 존재조차 하지 않음).
        marks.json이 없으면(구형 산출물, 또는 foot.py 밖에서 만든 PDF) {error: 사유}."""
        if not self._marks_path:
            return {"error": "이 PDF는 foot.py 산출물이 아닙니다(파일명이 _틱마크.pdf로 끝나지 않음)."}
        try:
            with open(self._marks_path, encoding="utf-8") as f:
                doc = json.load(f)
        except OSError as e:
            return {"error": f"marks.json을 열 수 없습니다: {e}"}
        except json.JSONDecodeError as e:
            return {"error": f"marks.json 형식이 올바르지 않습니다: {e}"}
        return {"marks": doc.get("marks", []), "counts": doc.get("document", {}).get("counts", {})}
