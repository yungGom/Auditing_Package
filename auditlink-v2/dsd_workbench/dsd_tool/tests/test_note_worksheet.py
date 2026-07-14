"""F-2 게이트: 주석 워크시트.

1. role 배정 일치율 85%+ (삼성 기공시사 — 인스턴스 실제 role이 정답지)
2. 표→차원 매핑 벤치마크 (최초 실행 = 기준선, 결과 보고)
3. 상태 4종(Design v2): 표준 / 표준 사용 권장 / 확장 필요 / 수동 확인
"""
import os
import re

import pytest

from dsd_tool.excel_out import extract
from dsd_tool.foot import FootingContext
from dsd_tool.mapping import (STATE_EXTENSION, STATE_MANUAL,
                              STATE_PREFER_STANDARD, STATE_STANDARD,
                              classify_suggestion)
from dsd_tool.note_worksheet import NoteAssets, _classify_column

_SAMSUNG_DSD = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "real",
    "[삼성전자(주)]_2025_[감사보고서].dsd")
_SAMSUNG_XBRL = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "dart_explorer", "cache",
    "xbrl", "00126380", "20260310002820_11011")
_ASSETS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "dart_explorer", "corpus")

_ready = (os.path.exists(_SAMSUNG_DSD) and os.path.isdir(_SAMSUNG_XBRL) and
          os.path.exists(os.path.join(_ASSETS_DIR, "standard_roles.json")))


# ---------------------------------------------------------------------------
# 상태 4종 판정 (Design v2 추천 카드 일치)
# ---------------------------------------------------------------------------

def test_classify_suggestion_states():
    top = {"sim": 0.9, "element_id": "x", "std_label": "", "score": 0.8,
           "n_companies": 5, "n_same_induty": 0, "evidence": ""}
    # 정상 표준 후보
    assert classify_suggestion(
        {"verdict": "후보", "candidates": [top],
         "similar_extensions": []})[0] == STATE_STANDARD
    # 함정 재해석: 확장 실증 + 고유사 표준 → 표준 사용 권장
    weak = dict(top, sim=0.5)
    state, t = classify_suggestion(
        {"verdict": "적합 표준 없음", "candidates": [weak],
         "similar_extensions": [{"label": "y", "n_companies": 3,
                                 "sim": 0.9}]})
    assert state == STATE_PREFER_STANDARD and t is weak
    # 확장 실증만
    assert classify_suggestion(
        {"verdict": "적합 표준 없음", "candidates": [dict(top, sim=0.2)],
         "similar_extensions": [{"label": "y", "n_companies": 3,
                                 "sim": 0.9}]})[0] == STATE_EXTENSION
    # 신호 없음
    assert classify_suggestion(
        {"verdict": "적합 표준 없음", "candidates": [],
         "similar_extensions": []})[0] == STATE_MANUAL


def test_classify_column():
    assert _classify_column("제 57 (당) 기") == "기간"
    assert _classify_column("기초 장부금액") == "증감(기초)"
    assert _classify_column("취득") == "증감(취득)"
    assert _classify_column("장부금액") == "항목"
    assert _classify_column("") == "빈칸"


# ---------------------------------------------------------------------------
# 게이트 1: role 배정 일치율 85%+ (삼성 인스턴스 정답지)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ready, reason="삼성 페어 또는 표준 자산 없음")
def test_gate1_role_assignment(tmp_path):
    import sys
    explorer_root = os.path.abspath(os.path.join(_ASSETS_DIR, "..", ".."))
    if explorer_root not in sys.path:
        sys.path.insert(0, explorer_root)
    from dart_explorer.xbrl.taxonomy import TaxonomyPackage

    answer = {}
    for _uri, definition, _pl in TaxonomyPackage(_SAMSUNG_XBRL).roles():
        m = re.match(r"^\[(D8\d{5})\]\s*(\d+)\.", definition)
        if m and m.group(1).endswith("5"):          # 별도
            answer[m.group(2)] = m.group(1)
    assert len(answer) >= 25

    xlsx = str(tmp_path / "s.xlsx")
    extract(_SAMSUNG_DSD, xlsx)
    ctx = FootingContext(xlsx)
    assets = NoteAssets()

    hit1 = hit3 = total = 0
    for sheet in ctx.note_sheets:
        title = str(ctx.wb[sheet].cell(1, 1).value or "")
        num = re.match(r"^(\d+)\.", title)
        truth = answer.get(num.group(1)) if num else None
        if truth is None:
            continue
        total += 1
        cands = assets.assign_role(title)
        got = cands[0]["code"] if cands and cands[0]["sim"] >= 0.4 else None
        hit1 += int(got == truth)
        hit3 += int(truth in [c["code"] for c in cands])
    rate1, rate3 = hit1 / total, hit3 / total
    print(f"\n[게이트 F-2] role 배정 Top-1 {rate1:.1%} / Top-3 {rate3:.1%} "
          f"(n={total})")
    assert rate1 >= 0.85, f"role 배정 {rate1:.1%} < 85%"


# ---------------------------------------------------------------------------
# 게이트 2: 표→차원 매핑 벤치마크 (스팟체크: 유형자산 클래스 → member)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 게이트 3: 행 라우팅 침묵 누락 0 + 3지표 벤치마크 (삼성 홀드아웃)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ready, reason="삼성 페어 또는 표준 자산 없음")
def test_gate3_routing_and_benchmark():
    """[1] 모든 주석 표 행은 a(element)/b(member)/c(manual) 중 하나로
    라우팅 — 침묵 누락 0 (자동화 경계 명시 원칙).
    [2] 3지표(분류 정확도·member 매칭률·element 매핑률 Top-4) 산출 =
    F-2 공식 벤치마크. member 매칭률에 게이트 기준 없음 — 첫 유효
    벤치마크이므로 기준은 결과 보고 후 확정."""
    from dsd_tool.note_eval import benchmark
    rep = benchmark(_SAMSUNG_DSD, "00126380", _SAMSUNG_XBRL)

    # [1] 라우팅 전수성
    assert rep["silent_missing"] == 0
    assert set(rep["routes"]) <= {"member", "element", "manual"}
    assert rep["rows_total"] == sum(rep["routes"].values()) >= 400

    # [2] 지표 산출 가능성 (수치 자체는 벤치마크 — 게이트 아님)
    c = rep["classification"]
    assert c["n"] >= 100 and c["accuracy"] is not None
    assert rep["element"]["n"] >= 50
    print(f"\n[F-2 벤치마크] 행 {rep['rows_total']} 라우팅 {rep['routes']} | "
          f"분류 정확도 {c['accuracy']:.1%} (기권 {c['abstain']}) | "
          f"member {rep['member']['hit']}/{rep['member']['eligible']} | "
          f"element Top-4 {rep['element']['top4']}/{rep['element']['n']}")


@pytest.mark.skipif(not _ready, reason="삼성 페어 또는 표준 자산 없음")
def test_gate2_dimension_mapping_spotcheck():
    from dsd_tool.note_worksheet import match_member
    assets = NoteAssets()
    axes = assets.role_axes("D822105")               # 유형자산 (별도)
    assert any("ClassesOfPropertyPlantAndEquipment" in a["axis"]
               for a in axes)
    for label, want in [("토지", "LandMember"),
                        ("건물", "BuildingsMember"),
                        ("기계장치", "MachineryMember"),
                        ("건설중인자산", "ConstructionInProgressMember")]:
        hit = match_member(axes, label)
        assert hit and want in hit[1], (label, hit)
        assert "ClassesOfPropertyPlantAndEquipment" in hit[0]
