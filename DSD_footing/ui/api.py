# -*- coding: utf-8 -*-
"""api — PyWebView JS 브리지. get_pdf()/get_marks() 두 개만 노출한다.

읽는 파일은 app.py 실행 시 넘겨받은 경로로 고정한다 — JS 쪽에 임의 경로를
읽을 수 있는 API를 열어주지 않는다(설계안_UI셸_U1.md §2). 완전 오프라인:
이 호출은 HTTP가 아니라 웹뷰 엔진의 네이티브 브리지(Windows/WebView2)를 타므로
개발자도구 Network 탭에 잡히지 않는다(설계안 §1 안 1).
"""
import base64
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _atomic_write(path, text):
    """임시 파일에 쓰고 os.replace로 교체한다. 같은 파일에 직접 쓰면 쓰는 도중 앱이
    죽었을 때 반쯤 쓰인 JSON이 남아 **판단을 전부 잃는다**(U-6 승인 조건)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class Api:
    def __init__(self, pdf_path, marks_path=None, review_path=None):
        self._pdf_path = pdf_path
        self._marks_path = marks_path
        self._review_path = review_path
        self._doc = None            # marks.json 원문 캐시 (읽기 전용)
        self._judgments = {}        # 메모리 사본 — 파일이 원본이다

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
        self._doc = doc
        res = {"marks": doc.get("marks", []),
               "counts": doc.get("document", {}).get("counts", {})}
        # 저장된 판단을 얹어 보낸다. 실패는 조용히 넘기지 않는다 — 판단이 사라진 것처럼
        # 보이면 회계사가 다시 검토하게 되고, 그건 조서 신뢰의 문제다.
        rv = self._load_review(doc)
        if rv.get("error"):
            res["review_error"] = rv["error"]
        else:
            self._judgments = rv.get("judgments", {})
            applied, missing = 0, []
            ids = {m["id"] for m in res["marks"]}
            for mid, j in self._judgments.items():
                if mid not in ids:
                    missing.append(mid); continue
                applied += 1
            for m in res["marks"]:
                j = self._judgments.get(m["id"])
                if j:
                    m["status"] = j.get("status", m.get("status"))
                    m["comment"] = j.get("comment")
                    m["reviewed_at"] = j.get("reviewed_at")
                    m["reviewed_by"] = j.get("reviewed_by")
            res["review"] = {"applied": applied, "missing": missing,
                             "reviewer": rv.get("reviewer") or ""}
        return res

    # ── 판단 파일 ────────────────────────────────────────────────────
    def _load_review(self, doc):
        """판단 파일을 읽는다. 원본 PDF가 다르면 **적용하지 않고 멈춘다** —
        무시하고 열면 회계사가 '판단이 사라졌다'고 오해한다(U-6 승인 조건)."""
        if not self._review_path or not os.path.isfile(self._review_path):
            return {"judgments": {}}
        try:
            with open(self._review_path, encoding="utf-8") as f:
                rv = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            return {"error": f"판단 파일을 읽을 수 없습니다: {e}"}
        want = (doc.get("source") or {}).get("sha256")
        got = rv.get("source_sha256")
        if want and got and want != got:
            return {"error": ("판단 파일이 다른 PDF의 것입니다 — 적용하지 않았습니다.\n"
                              f"판단 파일이 기록한 원본: {rv.get('source_pdf') or '(파일명 없음)'}\n"
                              f"지금 연 PDF: {(doc.get('source') or {}).get('pdf') or '(알 수 없음)'}\n"
                              f"파일 경로: {self._review_path}")}
        return rv

    def save_judgment(self, mark_id, status, comment=None):
        """판단 1건을 즉시 파일에 쓴다. 쓰는 대상은 판단 파일뿐 — marks.json·PDF에는
        절대 쓰지 않는다(분석 산출물은 UI가 손대지 않는다는 U-1 이래의 경계)."""
        if not self._review_path:
            return {"error": "판단을 저장할 경로가 없습니다."}
        if self._doc is None:
            return {"error": "marks.json을 아직 읽지 않았습니다."}
        self._judgments[mark_id] = {
            "status": status,
            "comment": (comment or "").strip() or None,
            "reviewed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "reviewed_by": self.get_reviewer().get("reviewer") or None,
        }
        src = self._doc.get("source") or {}
        payload = {
            "schema": "dsd-footing-review/1",
            "source_pdf": src.get("pdf"),
            "source_sha256": src.get("sha256"),
            "marks_run": (self._doc.get("run") or {}).get("run_ts"),
            "reviewer": self.get_reviewer().get("reviewer") or "",
            "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "judgments": self._judgments,
        }
        try:
            _atomic_write(self._review_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            return {"error": f"판단을 저장하지 못했습니다: {e}"}
        return {"ok": True, "saved": len(self._judgments), "path": self._review_path}

    # ── 검토자 ───────────────────────────────────────────────────────
    def get_reviewer(self):
        """ui/config.json에 이름 하나만 둔다. 인증이 아니라 '누가 검토했는지'다.
        이 파일은 .gitignore 대상 — 사람 이름이 저장소에 들어가면 안 된다."""
        try:
            with open(CONFIG, encoding="utf-8") as f:
                return {"reviewer": (json.load(f).get("reviewer") or "").strip()}
        except (OSError, json.JSONDecodeError):
            return {"reviewer": ""}

    def set_reviewer(self, name):
        name = (name or "").strip()
        if not name:
            return {"error": "이름을 입력하십시오."}
        try:
            _atomic_write(CONFIG, json.dumps({"reviewer": name}, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            return {"error": f"설정을 저장하지 못했습니다: {e}"}
        return {"ok": True, "reviewer": name}

    # ── 최종 출력 ────────────────────────────────────────────────────
    def export_final(self):
        """판단을 반영한 <원본>_검토완료.pdf. 원본 marks.json은 읽기만 하고,
        status를 반영한 **사본**을 render_all에 넘긴다."""
        import copy, render, summary
        if self._doc is None:
            return {"error": "marks.json을 아직 읽지 않았습니다."}
        base = self._pdf_path[:-len("_틱마크.pdf")] if self._pdf_path.endswith("_틱마크.pdf") \
            else os.path.splitext(self._pdf_path)[0]
        src_pdf = base + ".pdf"
        if not os.path.isfile(src_pdf):
            return {"error": f"원본 PDF를 찾을 수 없습니다: {src_pdf}"}
        out = base + "_검토완료.pdf"
        try:
            doc = copy.deepcopy(self._doc)
            for m in doc.get("marks", []):
                j = self._judgments.get(m["id"])
                if j: m["status"] = j.get("status", m.get("status"))
            tick = base + "_틱마크.pdf"
            render.render_all(src_pdf, doc, tick + ".tmp_final", quiet=True)
            t = summary.append_to(tick + ".tmp_final", doc, self._judgments,
                                  self.get_reviewer().get("reviewer"), out)
            os.remove(tick + ".tmp_final")
        except Exception as e:
            return {"error": f"출력에 실패했습니다: {type(e).__name__}: {e}"}
        return {"ok": True, "path": out, "pending": t["pending"],
                "approved": t["approved"], "removed": t["removed"], "total": t["total"]}

    def export_errors_snippet(self):
        """'차이 아님'으로 판정한 항목을 ERRORS.json 형식 문자열로 만든다.
        ★ 자동 반영이 아니라 복사 편의다. task를 비워 내보내므로 그대로 붙여넣으면
        C안 로더가 'task 없음'으로 거부한다 — 복사만으로는 선언이 성립하지 않는다."""
        if self._doc is None:
            return {"error": "marks.json을 아직 읽지 않았습니다."}
        import errors as errmod
        out = []
        for m in self._doc.get("marks", []):
            j = self._judgments.get(m["id"]) or {}
            if j.get("status") != "removed" or m.get("level") == "L2":
                continue
            ev = m.get("evidence") or {}
            if ev.get("disp") is None or ev.get("diff") is None:
                continue
            out.append({
                "key": errmod.l1_key(m["page"], (m.get("source") or {}).get("check"),
                                     ev["disp"], ev["diff"]),
                "account": m.get("account") or "",
                "reason": j.get("comment") or "",
                "task": "",
            })
        return {"ok": True, "count": len(out),
                "text": json.dumps(out, ensure_ascii=False, indent=2)}

    def get_glyph_offsets(self):
        """→ ui/glyph_offsets.json 내용. UI 히트영역의 **유일한 출처**다 —
        값을 JS에 복제하지 않는 이유와 게이트(glyph_gate.py)는 그 파일 주석 참고."""
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glyph_offsets.json")
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            return {"error": f"glyph_offsets.json을 읽을 수 없습니다: {e}"}
