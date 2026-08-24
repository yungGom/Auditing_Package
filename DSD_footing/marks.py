# -*- coding: utf-8 -*-
"""marks.json 직렬화 — 판정 결과를 픽셀이 아니라 데이터로 저장 (Phase 1: 판정/렌더 분리).

좌표는 pdfplumber 규약(좌상단 원점, top/bottom)으로 저장한다. reportlab의 하단 원점
변환은 render.py가 전담한다 — 이 파일은 좌표를 만들지 않고 받은 값을 그대로 담는다.
`marks.json`은 조서 첨부물이다: 도구가 무엇을 제안했고 회계사가 무엇을 바꿨는지가 남는다.
완전 오프라인.
"""
import hashlib, json, os

SCHEMA = "dsd-footing-marks/1"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mid(kind, check, page, table=None, row=None, col=None, extra=None):
    """결정론적 복합키. kind를 접두로 둔다 — check(A1/A2/A3/A5/C/D/F4/F6)만으로는
    같은 셀에 서로 다른 kind(예: C 대사의 circle·reftag·cross)가 겹칠 수 있다."""
    parts = [kind, check, f"p{page}"]
    if table is not None: parts.append(f"t{table}")
    if row is not None: parts.append(f"r{row}")
    if col is not None: parts.append(f"c{col}")
    if extra is not None: parts.append(str(extra))
    return ":".join(parts)


def box4(x0, top, x1, bottom):
    """4필드 box. slash 마크는 원래 좌표가 (x_end, top, bottom) 3필드뿐이라 x0=x1=x_end로
    채운다 — render.py가 kind='slash'일 때 x1을 쓰지 않으므로 무해하다.

    ⚠ 반올림하지 않는다. reportlab은 좌표를 자체 정밀도로 텍스트 포맷하므로, 저장 시
    값을 조금이라도 반올림하면 render.py가 원래와 다른 바이트를 만든다(R-1 위반 —
    실측 확인, 2026-08-14). pdfplumber가 준 값을 그대로 담는다."""
    return {"x0": x0, "top": top, "x1": x1, "bottom": bottom}


def build(source_pdf, marks, page_notes, run_meta, npages):
    marks_sorted = sorted(marks, key=lambda m: (m["page"], m["kind"], m["box"]["top"], m["box"]["x0"]))
    notes_sorted = sorted(page_notes, key=lambda n: (n["page"], n["seq"]))
    return {
        "schema": SCHEMA,
        "source": {"pdf": os.path.basename(source_pdf), "sha256": sha256_of(source_pdf), "pages": npages},
        "run": run_meta,
        "marks": marks_sorted,
        # page_notes: 스펙 예시 스키마 밖 확장 — 분할 의심 등 체크에 안 묶인 참고 문구.
        # R-1(바이트 동등)을 위해 marks와 같은 seq 축을 공유해 원래 그리기 순서를 보존한다.
        "page_notes": notes_sorted,
    }


def save(path, source_pdf, marks, page_notes, run_meta, npages):
    doc = build(source_pdf, marks, page_notes, run_meta, npages)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return doc


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
