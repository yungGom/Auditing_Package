"""F-2 벤치마크: 주석 표 행 라우팅·차원 매핑 재측정 (홀드아웃).

지표 정의 (확정, 2026-07-14):
- 분류 정확도: 행 라우팅(a 항목/b member/c 수동)이 정답지와 일치하는 비율.
  정답지 = 홀드아웃사 인스턴스 실적 — 라벨→element 사용(usages) +
  문맥의 xbrldi:explicitMember 사용(인스턴스 파일 직접 파싱, 파일 경계 유지).
  수동 확인 라우팅은 오답이 아니라 기권(abstain)으로 별도 집계.
- member 매칭률: 분모 = 축 배정 표의 행 중 정답이 member인 행,
  적중 = member 라우팅 + member id 일치.
- element 매핑률: 분모 = element 라우팅 행 중 정답 element가 있는 행,
  적중 = Top-4 내 정답 포함 (D-3b 게이트와 동일 기준).

member 매칭률에는 게이트 기준을 걸지 않는다 — 이 재측정이 첫 유효
벤치마크이며 기준은 결과 보고 후 확정한다.

주: NoteAssets의 role 실증 빈도(role_corps)에는 홀드아웃 제외가 없다
(수백 사 중 1사 — 빈도 가중에만 미치는 미세 누수, element/member
추천 자체는 MappingCorpus(exclude_corps)로 차단됨).
"""
import collections
import glob
import os
import sqlite3
import tempfile
import xml.etree.ElementTree as ET

from openpyxl import Workbook

from .excel_out import extract
from .foot import FootingContext
from .mapping import DEFAULT_CORPUS, MappingCorpus, normalize
from .note_worksheet import (ROUTE_ELEMENT, ROUTE_MANUAL, ROUTE_MEMBER,
                             NoteAssets, build_note_sheets)

_XBRLDI = "http://xbrl.org/2006/xbrldi"


def _element_answer(db_path, corp_code):
    """홀드아웃사 (정규화 라벨) → {element_id} — usages 실적."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    ans = collections.defaultdict(set)
    for eid, label in con.execute(
            "SELECT element_id, label_ko FROM usages WHERE corp_code = ? "
            "AND element_id NOT LIKE 'dart-gcd%'", (corp_code,)):
        qn = normalize((label or "").strip())
        if len(qn) >= 2:
            ans[qn].add(eid)
    con.close()
    return ans


def _member_answer(instance_dir, assets):
    """인스턴스 문맥에서 실제 사용된 member → {정규화 라벨: member_id}.

    인스턴스(.xbrl)의 xbrldi:explicitMember만 읽는다 — 파일 교환 경계.
    라벨은 표준 하이퍼큐브(standard_hypercubes.json)의 member 라벨.
    """
    used = set()
    for path in glob.glob(os.path.join(instance_dir, "*.xbrl")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for m in root.iter(f"{{{_XBRLDI}}}explicitMember"):
            used.add((m.text or "").strip().replace(":", "_"))
    mid_label = {}
    for axes in assets.hypercubes.values():
        for a in axes:
            for mid, lb in a["members"]:
                mid_label.setdefault(mid, lb)
    ans = {}
    for mid in used:
        lb = mid_label.get(mid)
        if lb:
            ans.setdefault(normalize(lb), mid)
    return ans


def benchmark(dsd_path, corp_code, instance_dir, db_path=None,
              induty=None, prefer_consol="별도", progress=None):
    """홀드아웃 1사 재측정. 3지표 리포트 dict 반환 (F-2 공식 벤치마크)."""
    db_path = db_path or DEFAULT_CORPUS
    assets = NoteAssets(db_path=db_path)
    corpus = MappingCorpus(db_path, exclude_corps={corp_code})  # 누수 방지
    with tempfile.TemporaryDirectory(prefix="notebench_") as tmp:
        xlsx = os.path.join(tmp, "홀드아웃.xlsx")
        extract(dsd_path, xlsx)
        ctx = FootingContext(xlsx)
        res = build_note_sheets(Workbook(), ctx, corpus, assets,
                                induty=induty, prefer_consol=prefer_consol,
                                progress=progress)

    elem_ans = _element_answer(db_path, corp_code)
    member_ans = _member_answer(instance_dir, assets)

    def truth_of(label):
        qn = normalize(label)
        if qn in member_ans:
            return ROUTE_MEMBER, member_ans[qn]
        if qn in elem_ans:
            return ROUTE_ELEMENT, elem_ans[qn]
        return None, None

    rows = res["rows_detail"]
    confusion = collections.Counter()
    known = unknown = abstain = correct = 0
    mem_eligible = mem_hit = mem_route_only = mem_unassigned = 0
    el_n = el_top4 = 0
    misses = []
    for d in rows:
        tclass, tval = truth_of(d["label"])
        if tclass is None:
            unknown += 1
            continue
        known += 1
        confusion[(tclass, d["route"])] += 1
        if d["route"] == ROUTE_MANUAL:
            abstain += 1
        elif d["route"] == tclass:
            correct += 1

        if tclass == ROUTE_MEMBER and d["axis"]:
            mem_eligible += 1
            if d["route"] == ROUTE_MEMBER:
                mem_route_only += 1
                if (d["member_id"] or "").replace(":", "_") == tval:
                    mem_hit += 1
        elif tclass == ROUTE_MEMBER:
            mem_unassigned += 1        # 축 미배정 표의 member 행 (라우팅 미스)

        if tclass == ROUTE_ELEMENT and d["route"] == ROUTE_ELEMENT:
            el_n += 1
            if tval & set(d["cand_ids"]):
                el_top4 += 1
            elif len(misses) < 30:
                misses.append({"sheet": d["sheet"], "label": d["label"],
                               "truth": sorted(tval)[:2],
                               "got": d["cand_ids"]})

    def _rate(a, b):
        return round(a / b, 4) if b else None

    return {
        "corp_code": corp_code,
        "rows_total": len(rows),
        "routes": dict(res["routes"]),
        "silent_missing": len(rows) - sum(res["routes"].values()),
        "truth": {"known": known, "unknown": unknown},
        "classification": {
            "n": known, "correct": correct, "abstain": abstain,
            "accuracy": _rate(correct, known),
            "confusion": {f"{t}->{r}": n
                          for (t, r), n in sorted(confusion.items())}},
        "member": {"eligible": mem_eligible, "routed": mem_route_only,
                   "hit": mem_hit, "rate": _rate(mem_hit, mem_eligible),
                   "in_unassigned_tables": mem_unassigned},
        "element": {"n": el_n, "top4": el_top4,
                    "rate": _rate(el_top4, el_n)},
        "misses": misses,
        "roles_assigned": sum(1 for v in res["roles"].values()
                              if v["assigned"]),
        "roles_total": len(res["roles"]),
    }
