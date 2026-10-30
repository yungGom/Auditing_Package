# -*- coding: utf-8 -*-
"""l2_marks — L2 표간 대사 결과(쌍 목록) → marks.json v2 마크(그룹 1건 + counterparts).

쌍 단위로 그대로 내보내면 같은 사안이 목록에 여러 건으로 뜬다(지분법손익 = IS 하나에
주석 둘 → 2행). 회계사 입장에서 하나의 사안이므로 **그룹 단위로 묶는다**
(설계안_marks_스키마_v2.md 5절, 2026-08-25 승인):

    1. (canonical_label, period_key)로 그룹        → 조선내화 반기 11쌍 = 10그룹
    2. 그룹 안에서 기준(A) 1개 선정
         1순위  본표(BS/IS/CI/SCE/CF)가 있으면 본표
         2순위  동급이면 (page, bbox.top) 오름차순
    3. 기준 = 마크 1건, 나머지 전원 = counterparts[]

★ 쌍마다 기준을 뽑으면 안 된다: 3중 불일치에서 마크가 2건으로 쪼개져 카운터가
  다시 부푼다(지분법손익은 주석6·주석17이 서로 같아 쌍이 2개로 끝났을 뿐, 셋이 서로
  달랐다면 쌍 3개 → 마크 2건이 됐다).

완전 오프라인.
"""
import re

STMT_IDS = ("BS", "IS", "CI", "SCE", "CF")
# rev.2 태그 규약. 자본변동표는 내부 table_id가 SCE, 화면·지면 표기는 CE로 통일
# (2026-08-25, 지면 레퍼 태그도 refmap.STMT_TAG에서 "/CE"로 변경 — 의도적 드로잉
# 변경, render_gate.py --update로 골든 재기록됨).
TAG = {"BS": "BS", "IS": "IS", "CI": "CI", "SCE": "CE", "CF": "CF"}


def stmt_of(table_id):
    """table_id → 본표 코드 또는 None. 'n9-t1.b2' 같은 주석 표는 None."""
    base = (table_id or "").split(".")[0].split("-")[0]
    return base if base in STMT_IDS else None


def tag_of(table_id):
    """counterparts[].tag — 본표는 rev.2 코드, 주석은 '주{번호}'.
    ⚠ rev.2 태그 열거에 주석이 없다(본표 5종만). 화면 좌측 칩을 비우지 않으려면
    무언가는 필요해 주석 번호를 쓴다 — 승인 필요 항목."""
    st = stmt_of(table_id)
    if st:
        return TAG[st]
    m = re.match(r"n(\d+)", table_id or "")
    return f"주{m.group(1)}" if m else None


def _side(rec, which):
    """finding 한쪽(A/B)을 표 단위 dict로 편다."""
    s = "a" if which == "A" else "b"
    return dict(table_id=rec[f"table_{s}"], value=rec[f"value_{s}"], won=rec[f"won_{s}"],
                page=rec[f"page_{s}"], bbox=rec[f"bbox_{s}"], sign=rec[f"sign_{s}"],
                raw=rec.get(f"raw_{s}"), mult=rec.get(f"mult_{s}"),
                table_seq=rec.get(f"tseq_{s}"))


def group(findings):
    """쌍 목록 → [{key, tables:{table_id: side}}] · 표 단위로 펼쳐 중복 제거."""
    groups = {}
    for r in findings:
        k = (r["canonical_label"], r["period_key"])
        g = groups.setdefault(k, {"label": r["canonical_label"], "period": r["period_key"],
                                  "column_key": r.get("column_key"), "tables": {}})
        for w in ("A", "B"):
            s = _side(r, w)
            g["tables"].setdefault(s["table_id"], s)
    return list(groups.values())


def pick_base(tables):
    """기준(A) 선정 — 본표 우선, 동급이면 (page, bbox.top).
    bbox는 pdfplumber 튜플 (x0, top, x1, bottom)이라 top은 [1]이다."""
    def rank(tid):
        s = tables[tid]
        top = (s["bbox"][1] if s.get("bbox") else 0.0)
        return (0 if stmt_of(tid) else 1, s["page"], top, tid)
    return sorted(tables, key=rank)[0]


def _fmt(side):
    """원문 표기 우선, 없으면 표시 단위 숫자로 되살린다."""
    if side.get("raw"):
        return side["raw"]
    v = side["value"]
    s = f"{abs(v):,.0f}"
    return f"({s})" if v < 0 else s


def build(findings, l2_class, label_of, seq_of_page, run_ts, mid, box4, bbox4):
    """→ 마크 리스트. 호출부(final.py)가 marks.py의 id·좌표 헬퍼를 넘겨준다.

    label_of   : side dict(page·table_seq 보유) → 사람이 읽는 표 이름(없으면 None)
    seq_of_page: page → 그 페이지에서 이미 쓴 seq 개수(그 뒤에 이어 붙인다)
    """
    out = []
    used = dict(seq_of_page)
    for g in sorted(group(findings), key=lambda x: -max(
            abs(s["won"] - t["won"]) for s in x["tables"].values() for t in x["tables"].values())):
        tables = g["tables"]
        if len(tables) < 2:
            continue
        base_id = pick_base(tables)
        base = tables[base_id]
        if not base.get("bbox"):
            continue                      # 좌표 없는 기준은 지면에 찍을 수 없다
        cps = []
        for tid, s in sorted(tables.items(), key=lambda kv: (kv[1]["page"], kv[0])):
            if tid == base_id:
                continue
            cps.append(dict(tag=tag_of(tid), label=label_of(s) or tid,
                            amount=_fmt(s), page=s["page"], mark_id=None,
                            sign_flipped=(s["sign"] != 1),
                            table_id=tid, delta=f"{s['won'] - base['won']:+,.0f}"))
        pg = base["page"]
        seq = used.get(pg, 0); used[pg] = seq + 1
        worst = max(abs(s["won"] - base["won"]) for s in tables.values())
        out.append(dict(
            id=mid("cross", "L2", pg, extra=f"{g['label']}:{g['period']}"),
            seq=seq, page=pg, kind="cross",
            box=box4(*base["bbox"]),
            text=f"{cps[0]['delta']} p{cps[0]['page']}" if cps else None,
            source=dict(check="L2", table=None, row=None, col=None, label=g["label"]),
            verdict="DIFF" if l2_class == "confirmed" else None,
            evidence=dict(period=g["period"], tables=sorted(tables), worst_diff=worst,
                          unit_mult=base.get("mult")),
            table_label=label_of(base), account=g["label"], level="L2",
            shown_value=_fmt(base), computed_value=None,
            delta=(f"{cps[0]['delta']}" if cps else None),
            formula=("표간 대사 — 같은 항목이 다른 표에서 다른 금액으로 표시됩니다"
                     if l2_class == "confirmed"
                     else "표간 대사 — 같아야 하는지 판단된 적 없는 조합입니다"),
            operands=[], counterparts=cps,
            l2_class=l2_class, column_key=g.get("column_key"), paper_no=None,
            comment=None, verified_at=run_ts, reviewed_at=None, reviewed_by=None,
            origin="tool", status="pending", note=None))
    return out
