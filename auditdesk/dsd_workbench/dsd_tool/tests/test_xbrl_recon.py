"""V-1 게이트: DSD ↔ XBRL 인스턴스 대사 (신원종합개발 왕복).

G1: DSD·인스턴스 모두 보유 건 — 본문 대조율 리포트 (매칭률·판정 분포)
G2: 변조 — 인스턴스 팩트 1개 값 수정 → 해당 행만 FALSE(값 상이) 전환
"""
import copy
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", ".."))
_PKG = os.path.join(_ROOT, "dart_explorer", "cache", "xbrl", "00136925",
                    "20260323000596_11011")
_DSD = os.path.join(os.path.dirname(__file__), "..", "fixtures", "real",
                    "[(주)티에스넥스젠]_2025_[반기검토보고서].dsd")
# 신원 DSD는 fixtures에 없음 — 신원 인스턴스 왕복은 래핑 수신물로 수행
# (본문 값은 동일 공시 원천 — 주석 분할 부정확 경고 대상이지만 본문 스코프)

_ready = os.path.isdir(_PKG)
pytestmark = pytest.mark.skipif(not _ready, reason="신원 패키지 없음")


def _facts_and_more():
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from dart_explorer.xbrl.corpus import _element_roles
    from dart_explorer.xbrl.dimension_table import XbrlInstance
    inst = XbrlInstance(_PKG)
    facts = {}
    for eid, fl in inst.facts.items():
        facts[eid] = [{
            "value": f["value"], "decimals": f.get("decimals"),
            "type": f["ctx"]["type"], "start": f["ctx"].get("start"),
            "end": f["ctx"].get("end"),
            "dims": dict(f["ctx"].get("dims") or {}),
        } for f in fl]
    roles = _element_roles(_PKG)
    body = {e for e, rs in roles.items()
            if any(r[:2] in ("D2", "D3", "D4", "D5", "D6") for r in rs)}
    return facts, inst.doc_period_end, body


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    """신원 공시원본(document.xml 캐시) 래핑 → extract + 승계 자산."""
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    tmp = tmp_path_factory.mktemp("v1")
    # 공시원본 캐시 (UI-5 게이트에서 수신됨) — 없으면 스킵
    doc_dsd = os.path.join(_ROOT, "dart_explorer", "cache", "document",
                           "00136925", "20260323000596.dsd")
    if not os.path.exists(doc_dsd):
        pytest.skip("신원 공시원본 캐시 없음 (UI-5 게이트 산출)")
    from dsd_tool.excel_out import extract
    xlsx = str(tmp / "신원.xlsx")
    extract(doc_dsd, xlsx)

    sj = os.path.join(_PKG, "succession_assets.json")
    assert os.path.exists(sj), "승계 자산 JSON 없음 (F-3 게이트 산출)"
    from dsd_tool.succession import load_assets
    succession = load_assets(sj)
    facts, doc_end, body = _facts_and_more()
    return {"xlsx": xlsx, "succession": succession, "facts": facts,
            "doc_end": doc_end, "body": body, "tmp": tmp}


def test_g1_roundtrip_report(setup):
    from dsd_tool.xbrl_recon import xbrl_recon
    res = xbrl_recon(
        setup["xlsx"], setup["facts"], setup["doc_end"],
        succession=setup["succession"], body_elements=setup["body"],
        out_path=str(setup["tmp"] / "대사.xlsx"),
        source_warning="⚠ OpenDART 래핑 수신물 — 참고용")
    c = res["counts"]
    print(f"\n[V-1 G1] 본문 대조율 {res['matched']}/{res['total']} "
          f"({res['match_rate']:.1%}) | 일치 {c['일치']} · 값 상이 "
          f"{c['값 상이']} · 태깅 누락 {c['태깅 누락']} · 인스턴스에만 "
          f"{res['only_instance']} · 매핑 없음 {c['매핑 없음']} | "
          f"허용오차 {res['tolerance']}")
    assert res["total"] >= 40                   # 본문 전수 대사 수행
    assert res["match_rate"] >= 0.5             # 붕괴 방지 하한
    assert c["일치"] >= 20
    assert os.path.exists(res["out_path"])
    # A-5 규격: 요약 + 시트별 상세 + FALSE 하이라이트 열 구성
    from openpyxl import load_workbook
    wb = load_workbook(res["out_path"])
    assert wb.sheetnames[0] == "요약"
    text = "\n".join(str(cell.value) for row in wb["요약"].iter_rows()
                     for cell in row if cell.value)
    assert "대조율" in text and "판정 분포" in text and "허용오차" in text


def test_g2_tamper_detection(setup):
    """인스턴스 팩트 1개 값 +1 변조 → 해당 행만 값 상이, 나머지 불변."""
    from dsd_tool.xbrl_recon import xbrl_recon

    base = xbrl_recon(setup["xlsx"], setup["facts"], setup["doc_end"],
                      succession=setup["succession"],
                      body_elements=setup["body"])
    # 일치 판정 행 하나 고름 → 그 element의 당기 팩트 값 변조
    target = None
    for sheet, rows in base["rows"].items():
        for r in rows:
            if r["verdict"] == "일치" and r["fact"]:
                target = (sheet, r)
                break
        if target:
            break
    assert target
    sheet, row = target
    facts2 = copy.deepcopy(setup["facts"])
    tampered = 0
    for f in facts2[row["element"]]:
        if f.get("end") == str(setup["doc_end"]) and \
                not [a for a in (f.get("dims") or {})
                     if a != "ifrs-full_ConsolidatedAndSeparate"
                     "FinancialStatementsAxis"]:
            f["value"] = str(float(f["value"]) + 1_000_000)
            tampered += 1
    assert tampered

    after = xbrl_recon(setup["xlsx"], facts2, setup["doc_end"],
                       succession=setup["succession"],
                       body_elements=setup["body"])

    def verdicts(res):
        return {(s, r["row"]): r["verdict"]
                for s, rows in res["rows"].items() for r in rows}
    vb, va = verdicts(base), verdicts(after)
    changed = {k for k in vb if vb[k] != va[k]}
    # 변조 element를 참조하는 행만 전환 (같은 element 중복 행 허용)
    assert changed, "변조가 판정에 반영되지 않음"
    for k in changed:
        assert va[k] == "값 상이", (k, vb[k], va[k])
        s, rn = k
        r_after = next(r for r in after["rows"][s] if r["row"] == rn)
        assert r_after["element"] == row["element"], \
            "변조 element 외 행이 전환됨"
    print(f"\n[V-1 G2] 변조 1건(+1,000,000) → 전환 {len(changed)}행 "
          f"(전부 대상 element) · 나머지 {len(vb) - len(changed)}행 불변")
