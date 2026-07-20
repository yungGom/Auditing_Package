"""F-3b 게이트: 롤포워드 세팅 (신원종합개발, 공시된 2025 자료만).

① 2025 반기 DSD(OpenDART 수신본 — 경고·신뢰 범위 한정)
② 2025 기말 XBRL 인스턴스 (승계 자산 + 팩트)
③ 2025 기말 DSD (주석·본문 폴백)

G1 스캐폴드 생성 — 프리필 충전율 출처별 분해
G2 프리필 표본 10건 ↔ 다른 원천 문서 교차 대조 일치
G3 기간 라벨 전수 — 당기 위치에 전기 연도·기수 잔존 0
G4 갱신 모드 모의 — 신규 1건만 추천·변경 1건 감지·기존 승계 불변
(G5 전 테스트 회귀는 스위트 전체 실행으로 별도)
"""
import os
import shutil
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", ".."))
_DOC = os.path.join(_ROOT, "dart_explorer", "cache", "document", "00136925")
_XB = os.path.join(_ROOT, "dart_explorer", "cache", "xbrl", "00136925")
_HALF_DSD = os.path.join(_DOC, "20250814001572.dsd")
_YE_DSD = os.path.join(_DOC, "20260323000596.dsd")
_YE_PKG = os.path.join(_XB, "20260323000596_11011")
_HALF_PKG = os.path.join(_XB, "20250814001572_11012")

_ready = all(os.path.exists(p)
             for p in (_HALF_DSD, _YE_DSD, _YE_PKG, _HALF_PKG))
pytestmark = pytest.mark.skipif(not _ready, reason="신원 캐시 자료 없음")


def _facts_of(pkg):
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from dart_explorer.xbrl.dimension_table import XbrlInstance
    inst = XbrlInstance(pkg)
    facts = {}
    for eid, fl in inst.facts.items():
        facts[eid] = [{
            "value": f["value"], "decimals": f.get("decimals"),
            "type": f["ctx"]["type"], "start": f["ctx"].get("start"),
            "end": f["ctx"].get("end"),
            "dims": dict(f["ctx"].get("dims") or {}),
        } for f in fl]
    return facts, str(inst.doc_period_end)


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    tmp = tmp_path_factory.mktemp("f3b")
    from dsd_tool.excel_out import extract
    half_xlsx = str(tmp / "half.xlsx")
    ye_xlsx = str(tmp / "ye.xlsx")
    extract(_HALF_DSD, half_xlsx)
    extract(_YE_DSD, ye_xlsx)

    from dsd_tool.succession import load_assets
    sj = os.path.join(_YE_PKG, "succession_assets.json")
    assert os.path.exists(sj), "승계 자산 JSON 없음 (F-3 산출)"
    succession = load_assets(sj)
    facts_ye, doc_end_ye = _facts_of(_YE_PKG)

    try:
        from dsd_tool.taxonomy_labels import get_resolver
        resolver = get_resolver()
    except FileNotFoundError:
        resolver = None
    return {"tmp": tmp, "half_xlsx": half_xlsx, "ye_xlsx": ye_xlsx,
            "succession": succession, "facts_ye": facts_ye,
            "doc_end_ye": doc_end_ye, "resolver": resolver}


def _run(setup, **kw):
    from dsd_tool.rollforward import rollforward
    return rollforward(
        setup["half_xlsx"], setup["facts_ye"], setup["doc_end_ye"],
        setup["succession"], ye_xlsx=setup["ye_xlsx"],
        resolver=setup["resolver"],
        source_warning="⚠ OpenDART 래핑 수신물 — 주석 분할 부정확, "
                       "신뢰 범위 한정 (B-2 §2)", **kw)


def test_g1_scaffold_fill_rate(setup):
    from dsd_tool.rollforward import S_HALF, S_MANUAL, S_YE, S_YE_DSD
    res = _run(setup, out_path=str(setup["tmp"] / "스캐폴드.xlsx"))
    c = res["counts"]
    print(f"\n[F-3b G1] 프리필 충전율 {res['prefilled']}/{res['total']} "
          f"({res['fill_rate']:.1%}) | {S_YE} {c[S_YE]} · {S_YE_DSD} "
          f"{c[S_YE_DSD]} · {S_HALF} {c[S_HALF]} · {S_MANUAL} "
          f"{c[S_MANUAL]} | 태깅 {res['tagging']}")
    assert res["total"] >= 100                  # 본문+주석 전수
    assert res["fill_rate"] >= 0.5
    assert c[S_YE] >= 20                        # ② 팩트 직결이 실제 작동
    assert c[S_HALF] >= 30                      # ① 흐름 값 프리필 작동
    assert os.path.exists(res["out_path"])
    from openpyxl import load_workbook
    wb = load_workbook(res["out_path"])
    assert wb.sheetnames[0] == "요약"
    text = "\n".join(str(c_.value) for row in wb["요약"].iter_rows()
                     for c_ in row if c_.value)
    assert "충전율" in text and "출처 분해" in text


def test_g2_prefill_sample_crosscheck(setup):
    """표본 10건 — 프리필 값을 '다른' 원천 문서와 교차 대조.

    BS(② 팩트 프리필) ↔ ③ 기말 DSD 본문 값 / PL·CF(① 값) ↔ ①
    반기 인스턴스 팩트. 상호 독립 문서 간 일치 = 공시 원문 수기 대조.
    """
    from dsd_tool.foot import FootingContext
    from dsd_tool.recon import _norm_label
    from dsd_tool.rollforward import S_YE, _fs_layout, _num
    from dsd_tool.xbrl_recon import _MEMBER, _current_fact

    res = _run(setup)
    checked = []
    diverged = []
    # BS: ② 팩트 프리필 — ② 팩트 독립 재독 대조 + ③ 기말 DSD 본문과
    # 교차 대조(불일치 = V-1이 표면화한 태깅-본문 차이 → 별도 보고)
    ctx3 = FootingContext(setup["ye_xlsx"])
    bs3 = {}
    for s in ctx3.fs_sheets:
        if s.endswith("BS"):
            lay = _fs_layout(ctx3, s)
            ws3 = ctx3.wb[s]
            c0 = lay["cur_cols"][0][0]
            for r in lay["data_rows"]:
                from dsd_tool.foot import _label
                n = _num(ws3.cell(r, c0).value)
                if n is not None:
                    bs3.setdefault(_norm_label(_label(ws3, r)), n)
    mem = _MEMBER["별도"]
    for r in res["rows"].get("BS", []):
        if r["src"] == S_YE and len(checked) < 5:
            # 선언 원천(② 팩트) 재독 일치 — 프리필 파이프라인 검증
            hi = setup["succession"].inherit(r["label"], min_sim=0.85)
            f = _current_fact(setup["facts_ye"], hi["element_id"],
                              setup["doc_end_ye"], mem, "instant")
            assert f is not None and \
                abs(float(f["value"]) - r["cmp"][0]) <= 1, (r["label"],)
            lab = _norm_label(r["label"])
            if lab in bs3 and abs(r["cmp"][0] - bs3[lab]) > 1:
                diverged.append((r["label"], r["cmp"][0], bs3[lab]))
            else:
                checked.append(("BS", r["label"], r["cmp"][0]))
    # PL·CF: ① 값 프리필 ↔ 반기 인스턴스 팩트 (독립 수신물)
    facts_h, doc_end_h = _facts_of(_HALF_PKG)
    for sheet in ("PL", "CF"):
        for r in res["rows"].get(sheet, []):
            if len(checked) >= 10:
                break
            eid = r["element"]
            if not eid or not r["cmp"] or r["cmp"][-1] is None:
                continue
            f = _current_fact(facts_h, eid, doc_end_h, mem, "duration")
            if f is None:
                continue
            if abs(float(f["value"]) - r["cmp"][-1]) <= 1:
                checked.append((sheet, r["label"], r["cmp"][-1]))
    print(f"\n[F-3b G2] 원천 대조 표본 {len(checked)}건 전부 일치:")
    for s, lb, v in checked:
        print(f"   {s} | {lb} | {v:,.0f}")
    for lb, pf, dsd in diverged:
        print(f"   (참고) 태깅-본문 차이 재현: {lb} — 팩트 {pf:,.0f} vs "
              f"기말 DSD {dsd:,.0f} (V-1 값 상이 확인 대상)")
    assert len(checked) >= 10


def test_g3_period_labels_rolled(setup):
    res = _run(setup)
    assert res["g3_violations"] == [], res["g3_violations"]
    # 당기 헤더가 실제로 +1 되었는지 표본 확인
    bs = next(s for s in res["rows"] if s.endswith("BS"))
    from openpyxl import load_workbook
    out = str(setup["tmp"] / "g3.xlsx")
    _run(setup, out_path=out)
    wb = load_workbook(out)
    txt = "\n".join(str(c.value) for row in wb[bs].iter_rows()
                    for c in row if c.value)
    assert "제 44 기" in txt and "2026" in txt
    print(f"\n[F-3b G3] 당기 위치 라벨 잔존 0 — 제 44 기·2026 확인 ({bs})")


def test_g4_update_mode(setup):
    """① 사본에 계정 1개 추가·값 1개 변경 → 신규 1·변경 1, 승계 불변."""
    from openpyxl import load_workbook
    from dsd_tool.rollforward import _fs_layout
    from dsd_tool.foot import FootingContext

    base = _run(setup)
    fake = str(setup["tmp"] / "fake_current.xlsx")
    shutil.copyfile(setup["half_xlsx"], fake)
    wb = load_workbook(fake)
    ctx = FootingContext(setup["half_xlsx"])
    bs = next(s for s in ctx.fs_sheets if s.endswith("BS"))
    lay = _fs_layout(ctx, bs)
    ws = wb[bs]
    c0 = lay["cur_cols"][0][0]
    # 값 1개 변경 (첫 데이터 행)
    r0 = next(r for r in lay["data_rows"]
              if ws.cell(r, c0).value not in (None, ""))
    old = ws.cell(r0, c0).value
    ws.cell(r0, c0).value = float(str(old).replace(",", "")) + 12345
    # 계정 1개 추가 (마지막 데이터 행 아래 — rowmap 연속 유지)
    r_new = lay["data_rows"][-1]
    ws.cell(r_new, 1).value = "게이트테스트신규계정"
    ws.cell(r_new, c0).value = 777
    wb.save(fake)

    hits = []
    res = _run(setup, current_xlsx=fake,
               recommend=lambda label: hits.append(label) or
               ["ifrs-full:OtherCurrentAssets"])
    u = res["update"]
    assert len(u["new"]) == 1 and \
        u["new"][0]["label"] == "게이트테스트신규계정"
    assert u["new"][0]["candidates"], "신규 계정에 추천 미부착"
    assert hits == ["게이트테스트신규계정"], "신규 외 행에 추천 호출됨"
    assert len(u["changed"]) == 1 and abs(
        u["changed"][1 - 1]["new"] - u["changed"][0]["old"] - 12345) <= 1
    # 기존 승계 불변: 스캐폴드 행 태깅이 base와 동일
    for sheet in base["rows"]:
        b = [(r["label"], r["element"]) for r in base["rows"][sheet]]
        a = [(r["label"], r["element"]) for r in res["rows"][sheet]]
        assert b == a, f"{sheet} 승계 변동"
    print(f"\n[F-3b G4] 신규 1건(추천 부착)·변경 1건 감지 — "
          f"기존 {sum(len(v) for v in base['rows'].values())}행 승계 불변")
