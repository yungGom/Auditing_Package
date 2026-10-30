# -*- coding: utf-8 -*-
"""marks.json 직렬화 — 판정 결과를 픽셀이 아니라 데이터로 저장 (Phase 1: 판정/렌더 분리).

좌표는 pdfplumber 규약(좌상단 원점, top/bottom)으로 저장한다. reportlab의 하단 원점
변환은 render.py가 전담한다 — 이 파일은 좌표를 만들지 않고 받은 값을 그대로 담는다.
`marks.json`은 조서 첨부물이다: 도구가 무엇을 제안했고 회계사가 무엇을 바꿨는지가 남는다.
완전 오프라인.
"""
import hashlib, json, os

SCHEMA = "dsd-footing-marks/2"

# rev.2가 말하는 "검토 항목(mark)" = 회계사가 판단 버튼을 누르는 대상.
# 나머지(체크·사선·원·태그·조판지적)는 지면에 그려지기만 하는 표시라 annotations로 나눈다.
# 실측 근거(조선내화 반기 307건): 검토 항목 8 / 그리기 전용 299 — 한 배열에 두면
# 화면 카운터가 조용히 307로 부푼다(설계안_marks_스키마_v2.md 1절, 2026-08-25 승인).
REVIEW_KINDS = ("cross", "question")

# 좌표 규약 — box는 pdfplumber 원본(반올림 금지, R-1 전제), bbox는 화면용 파생이다.
# 둘 다 좌상단 원점으로 통일한다: 변환을 넣는 순간 R-1 함정 1(반올림/재계산 오차)에
# 걸리므로, bbox는 뺄셈 2회만으로 만든다.
COORD_SPACE = "pdfplumber-topleft"


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


def type_of(m):
    """rev.2 type — "diff" | "unverified".

    C 레퍼 미성립(kind=cross, check=C)은 "금액이 틀렸다"가 아니라 "본표 금액을 주석에서
    찾지 못했다"이다. 주석 세분 표시·단위 상이·미수록 공시관행이 대부분이고 전부 정상
    공시라, diff로 세면 '차이 N건' 카운터에 정상 건이 섞인다 → unverified
    (회계사 판단, 2026-08-25). 지면 글리프(✗)는 R-1 때문에 이번 라운드에서 바꾸지 않는다.
    """
    if m["kind"] == "question":
        return "unverified"
    if (m.get("source") or {}).get("check") == "C":
        return "unverified"
    return "diff"


def bbox4(box):
    """box(x0/top/x1/bottom) → rev.2 bbox [x, y, w, h]. 좌상단 원점 유지(COORD_SPACE)."""
    return [box["x0"], box["top"], box["x1"] - box["x0"], box["bottom"] - box["top"]]


def _counts(review, annots):
    kinds = {}
    for a in annots:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
    return {
        "ok":         kinds.get("tick", 0),
        "diff":       sum(1 for m in review if m.get("type") == "diff"),
        "unverified": sum(1 for m in review if m.get("type") == "unverified"),
        "recon":      kinds.get("circle", 0) + kinds.get("reftag", 0),
        "prose":      kinds.get("slash", 0),
        "typo":       kinds.get("flagword", 0) + kinds.get("gapx", 0),
    }


def build(source_pdf, marks, page_notes, run_meta, npages, document=None):
    _key = lambda m: (m["page"], m["kind"], m["box"]["top"], m["box"]["x0"])
    review = sorted([m for m in marks if m["kind"] in REVIEW_KINDS], key=_key)
    annots = sorted([m for m in marks if m["kind"] not in REVIEW_KINDS], key=_key)
    for m in review:
        m.setdefault("type", type_of(m))
        m.setdefault("bbox", bbox4(m["box"]))
        # anchor_bbox: 링을 그릴 원본 숫자 영역. A·B·L2 계열은 마크가 이미 금액 셀에
        # 찍히므로 bbox와 같은 값이다(설계안 2절).
        m.setdefault("anchor_bbox", m["bbox"])
    notes_sorted = sorted(page_notes, key=lambda n: (n["page"], n["seq"]))
    doc = dict(document or {})
    doc.setdefault("page_count", npages)
    doc.setdefault("coordinate_space", COORD_SPACE)
    doc["counts"] = _counts(review, annots)
    return {
        "schema": SCHEMA,
        "source": {"pdf": os.path.basename(source_pdf), "sha256": sha256_of(source_pdf), "pages": npages},
        "run": run_meta,
        "document": doc,
        "marks": review,
        # annotations: 그리기 전용(체크·사선·원·레퍼태그·조판지적). 렌더러는 marks와
        # 합쳐 seq 순으로 재생한다 — 배열이 나뉘어도 그리기 순서는 seq가 지킨다(R-1).
        "annotations": annots,
        # page_notes: 스펙 예시 스키마 밖 확장 — 분할 의심 등 체크에 안 묶인 참고 문구.
        # R-1(바이트 동등)을 위해 marks와 같은 seq 축을 공유해 원래 그리기 순서를 보존한다.
        "page_notes": notes_sorted,
    }


def drawables(doc):
    """렌더 대상 전량 — marks(검토 항목) + annotations(그리기 전용). v1 문서도 읽는다."""
    return list(doc.get("marks", [])) + list(doc.get("annotations", []))


def save(path, source_pdf, marks, page_notes, run_meta, npages, document=None):
    doc = build(source_pdf, marks, page_notes, run_meta, npages, document)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return doc


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
