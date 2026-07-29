"""H-1 게이트: 재무제표 제목 정규화 — 반기/분기 접두 미인식 수정.

- 공통 정규화 단위(순서 무관 접두·괄호·제N기, 연결 보존, 오탐 방지)
- 접두 변형 픽스처 extract → 시트 인식 + 미분류 노출 (침묵 탈락 금지)
- foot fs_sheets · worksheet 카테고리 · recon 접두 불문 페어링
"""
import os

import pytest

from dsd_tool.textutil import (FS_SHEET_RE, fs_title_unclassified,
                               match_fs_title)


@pytest.mark.parametrize("title,expected", [
    ("재 무 상 태 표", ("", "", "재무상태표")),
    ("반기재무상태표", ("반기", "", "재무상태표")),
    ("분기연결손익계산서", ("분기", "연결", "손익계산서")),
    ("연결반기재무상태표", ("반기", "연결", "재무상태표")),   # 순서 역전
    ("중간재무상태표", ("", "", "재무상태표")),               # 중간 제거
    ("요약분기포괄손익계산서", ("분기", "", "포괄손익계산서")),
    ("재무상태표(제43기)", ("", "", "재무상태표")),           # 괄호
    ("제57기중간현금흐름표", ("", "", "현금흐름표")),         # 제N기
    ("연결 중간 요약 자본변동표", ("", "연결", "자본변동표")),
])
def test_match_fs_title_variants(title, expected):
    assert match_fs_title(title) == expected


@pytest.mark.parametrize("title", [
    "재무상태표상자산",          # 주석 셀 — 오탐 금지
    "현금흐름표 주석",
    "재무상태표 부속명세서",
])
def test_no_false_positive_but_flagged(title):
    assert match_fs_title(title) is None
    assert fs_title_unclassified(title)


def test_fs_sheet_re_matches_scanner_prefixes():
    for name in ("BS", "PL", "PL1", "CE", "CF", "반기BS", "분기PL",
                 "연결CF", "반기연결BS"):
        assert FS_SHEET_RE.match(name), name
    for name in ("원문", "1", "_MAP", "BS_2"):
        assert not FS_SHEET_RE.match(name), name


@pytest.fixture(scope="module")
def half_extract(tmp_path_factory):
    """접두 변형 픽스처 → extract (재현 사례 재실행)."""
    from dsd_tool.excel_out import extract
    from dsd_tool.tests.fixture import CONTENTS_XML_HALF, build_dsd
    tmp = tmp_path_factory.mktemp("h1")
    dsd = build_dsd(str(tmp / "half.dsd"), contents=CONTENTS_XML_HALF)
    xlsx = str(tmp / "half.xlsx")
    meta = extract(dsd, xlsx)
    return {"tmp": tmp, "dsd": dsd, "xlsx": xlsx, "meta": meta}


def test_prefix_titles_recognized(half_extract):
    """연결반기/중간요약/괄호/제N기분기 제목 전부 시트로 인식."""
    fs = half_extract["meta"]["fs_sheets"]
    assert "반기연결BS" in fs                   # 연결 반기 (순서 역전)
    assert "PL" in fs                           # 중간요약 → 접두 제거
    assert "CE" in fs                           # 괄호(제57기 반기)
    assert "분기CF" in fs                       # 제 57 기 분기
    print(f"\n[H-1] 접두 변형 4종 전부 인식: {fs}")


def test_unclassified_exposed(half_extract):
    """FS유사 미판별 제목은 침묵 탈락 금지 — meta로 노출."""
    unc = half_extract["meta"]["fs_unclassified"]
    assert any("부속명세" in t for t in unc), unc
    print(f"[H-1] 미분류 노출: {unc}")


def test_downstream_recognition(half_extract):
    """foot 시트 인식 · worksheet 카테고리 · A-4 푸팅 스코프."""
    from dsd_tool.foot import FootingContext
    from dsd_tool.worksheet import _sheet_category
    ctx = FootingContext(half_extract["xlsx"])
    assert set(ctx.fs_sheets) >= {"반기연결BS", "PL", "CE", "분기CF"}
    assert _sheet_category("반기연결BS") == "BS"
    assert _sheet_category("분기CF") == "CF"


def test_recon_pairing_prefix_insensitive(half_extract):
    """전기대사: 반기연결BS(당기) ↔ 연결BS(전기) — 접두 차이 페어링."""
    from dsd_tool.excel_out import extract
    from dsd_tool.foot import FootingContext
    from dsd_tool.recon import pair_fs_sheets
    from dsd_tool.tests.fixture import CONTENTS_XML, build_dsd
    # 전기본: 접두 없는 기본 픽스처에 연결 접두만 부여
    plain = (CONTENTS_XML
             .replace("재 무 상 태 표", "연결재무상태표")
             .replace("현 금 흐 름 표", "현금흐름표"))
    tmp = half_extract["tmp"]
    pri = build_dsd(str(tmp / "prior.dsd"), contents=plain)
    pri_x = str(tmp / "prior.xlsx")
    extract(pri, pri_x)
    pairs = pair_fs_sheets(FootingContext(half_extract["xlsx"]),
                           FootingContext(pri_x))
    assert pairs["반기연결BS"] == "연결BS"      # 반기 접두 무시, 연결 보존
    assert pairs["분기CF"] == "CF"
    assert pairs["PL"] == "PL"
    print(f"[H-1] 전기대사 페어링(접두 불문): {pairs}")
