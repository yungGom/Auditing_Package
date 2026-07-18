"""D-2 게이트: 차원 표 렌더러 (단계별).

1. 축 0개 — BS 본문 표 재현 (행=element, 열=기간)
2. 축 1개 — 신원 자본변동표: 축 컨텍스트 16개 전수 배치, DART 뷰어식
   (member 열 + [합계]=default, 기간 블록 분리)
3. 축 2개 중첩 — 삼성 유형자산(D822100): 이미지1 형식 (배치 육안 대조는 수동)
4. def.xml 아크롤 체인 + 연결/별도 필터 축 + 서브롤(a/b/c) 병합
"""
import os

import pytest

from dart_explorer.xbrl.dimension_table import (FILTER_AXIS, HypercubeDef,
                                                RoleTable, XbrlInstance,
                                                _base_code, _role_code,
                                                render_dimension_tables)
from dart_explorer.xbrl.taxonomy import TaxonomyPackage

_SHINWON = os.path.join(
    r"C:\Users\moonyong\OneDrive - 서현회계법인\바탕 화면\XBRL",
    "신원종합개발", "[신원종합개발]반기보고서_IFRS(원문XBRL)(2025.08.14)")
_SAMSUNG = os.path.join(
    os.path.dirname(__file__), "..", "cache", "xbrl", "00126380",
    "20260310002820_11011")

_CE_AXIS = "ifrs-full_ComponentsOfEquityAxis"


def test_role_code_helpers():
    assert _role_code("http://x/role-D822100b") == "D822100b"
    assert _base_code("D822100b") == "D822100"
    assert _base_code("D610005") == "D610005"


@pytest.mark.skipif(not os.path.isdir(_SHINWON), reason="신원 패키지 없음")
class TestShinwon:
    @pytest.fixture(scope="class")
    def parts(self):
        pkg = TaxonomyPackage(_SHINWON)
        inst = XbrlInstance(_SHINWON)
        cube = HypercubeDef(_SHINWON)
        tables = {}
        for uri, definition, pl in pkg.roles():
            tables[definition.split("]")[0].strip("[")] = \
                RoleTable(pkg, inst, cube, uri, definition, pl)
        return pkg, inst, tables

    def test_gate1_flat_bs(self, parts):
        """게이트 1 (축 0개): BS 본문 표 — 행=element, 열=기간."""
        pkg, inst, tables = parts
        bs = tables["D210005"]
        assert len(bs.sections) == 1
        sec = bs.sections[0]
        assert sec.axes == []                     # 연결/별도 축은 필터로 접힘
        # 유동자산 당기말 값 = 인스턴스 팩트와 일치
        block = ("instant", "2025-06-30", "2025-06-30")
        f = sec.cell("ifrs-full_CurrentAssets", block, {})
        assert f and float(f["value"]) == 166606680498.0
        f_prev = sec.cell("ifrs-full_CurrentAssets",
                          ("instant", "2024-12-31", "2024-12-31"), {})
        assert f_prev and float(f_prev["value"]) == 157470837553.0

    def test_gate2_one_axis_ce(self, parts):
        """게이트 2 (축 1개): 자본변동표 — 축 컨텍스트 16개 전수 배치."""
        pkg, inst, tables = parts
        ce = tables["D610005"]
        assert len(ce.sections) == 1
        sec = ce.sections[0]
        assert [a["axis"] for a in sec.axes] == [_CE_AXIS]
        assert len(sec.axes[0]["members"]) == 4   # 자본금/잉여금/기타/이익잉여금
        assert len(sec.blocks) == 2               # 당기·전기 (누적만)

        # 인스턴스의 CE 축 컨텍스트 16개의 팩트가 표 셀로 전부 조회되는가
        placed_ctx = set()
        for cid, facts in sec.facts.items():
            for f in facts:
                m = f["ctx"]["dims"].get(_CE_AXIS)
                if m is None:
                    continue
                hit = any(
                    sec.cell(cid, b, {_CE_AXIS: m}) is not None
                    for b in sec.blocks if sec._in_block(f["ctx"], b))
                assert hit, (cid, f["ctx"])
                placed_ctx.add(id(f["ctx"]))
        assert len(placed_ctx) == 16              # 스펙 명시: 축 컨텍스트 16개

        # [합계] 열 = default(EquityMember) 팩트: 당기 기초자본 합계
        cur = sec.blocks[0]
        total = sec.cell("dart_EquityAtBeginningOfPeriod", cur, {})
        assert total and float(total["value"]) == 106997656933.0
        # member 열: 이익잉여금 기초
        rem = sec.cell("dart_EquityAtBeginningOfPeriod", cur,
                       {_CE_AXIS: "ifrs-full_RetainedEarningsMember"})
        assert rem and float(rem["value"]) == 45204228305.0

    def test_render_excel(self, parts, tmp_path):
        res = render_dimension_tables(_SHINWON, str(tmp_path / "신원.xlsx"))
        assert len(res["roles"]) == 4
        by_code = {r["definition"].split("]")[0].strip("["): r
                   for r in res["roles"]}
        assert by_code["D210005"]["axes"] == 0
        assert by_code["D610005"]["axes"] == 1


@pytest.mark.skipif(not os.path.isdir(_SAMSUNG), reason="삼성 캐시 없음")
class TestSamsung:
    @pytest.fixture(scope="class")
    def rendered(self, tmp_path_factory):
        out = str(tmp_path_factory.mktemp("dim") / "삼성.xlsx")
        return render_dimension_tables(_SAMSUNG, out)

    def test_consolidated_filter(self, rendered):
        """연결/별도 축은 열로 분화되지 않는다 (role별 필터)."""
        by_code = {r["definition"].split("]")[0].strip("["): r
                   for r in rendered["roles"]}
        assert by_code["D210000"]["axes"] == 0    # 연결 BS = 축0
        assert by_code["D610000"]["axes"] == 1    # CE = 자본구성 1축

    def test_gate3_two_axis_nested(self, rendered):
        """게이트 3 (축 2개 중첩): 유형자산 D822100 — 이미지1 형식."""
        pp = next(r for r in rendered["roles"]
                  if "D822100" in r["definition"])
        assert pp["axes"] == 2                    # 클래스 × 장부금액 중첩
        assert pp["sections"] >= 2                # 서브롤(a/b/…) 섹션 병합
        assert os.path.exists(rendered["out_path"])

    def test_subrole_merge(self):
        """def.xml 서브롤 a/b/c가 기본 코드로 병합된다."""
        cube = HypercubeDef(_SAMSUNG)
        assert len(cube.by_base["D822100"]) >= 2
        axes_sets = [{a["axis"] for a in cb["axes"]}
                     for cb in cube.by_base["D822100"]]
        assert any(len(s - {FILTER_AXIS}) == 2 for s in axes_sets)
