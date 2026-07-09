"""B-2 구조 대조 회귀 테스트 (REPORT_B2_구조대조.md 근거 고정).

지시서 B-2-2 ※: OpenDART 원본에는 dartdb 주석번호 오염("N. N.")이 없다 →
note-dedup 로직이 no-op으로 통과해야 정상.
"""
import os

import pytest

from dart_explorer.converters.document_wrap import (extract_to_excel,
                                                    unwrap_document,
                                                    wrap_as_contents)

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "홈플러스_20260608000212_document.zip")
_DARTDB = os.path.join(
    os.path.dirname(__file__), "..", "..", "dsd_workbench", "dsd_tool",
    "fixtures", "real", "[홈플러스 주식회사]_2025_[감사보고서 (2026.02)].dsd")

pytestmark = pytest.mark.skipif(
    not os.path.exists(_FIXTURE), reason="OpenDART 원본 픽스처 없음")


def test_unwrap_document():
    with open(_FIXTURE, "rb") as f:
        inner = unwrap_document(f.read())
    assert inner.lstrip()[:5] == b"<?xml"
    assert b"dart4.xsd" in inner[:400]          # 루트 스키마 동일 (리포트 §1)


def test_extract_and_note_dedup_noop(tmp_path):
    """FS·표지·외부감사 추출 정상 + note-dedup no-op (오염 없음)."""
    info = extract_to_excel(_FIXTURE, str(tmp_path / "홈플러스.xlsx"),
                            work_dir=str(tmp_path))
    assert info["fs_sheets"] == ["BS", "PL", "CE", "CF"]
    assert info["deduped_notes"] == 0           # ★ no-op 회귀 (지시서 B-2-2)
    assert info["cr_only_cells"] == 0           # &cr; 오염도 없음
    assert info["te_tables"] == 4
    assert info["mapped_cells"] > 3000


def test_wrapped_roundtrip_byte_identity(tmp_path):
    """읽기 전용 수신물이지만 무변경 왕복(G2)은 성립해야 한다."""
    from dsd_tool.excel_out import extract
    from dsd_tool.repack import repack
    with open(_FIXTURE, "rb") as f:
        inner = unwrap_document(f.read())
    wrapped = str(tmp_path / "wrapped.zip")
    wrap_as_contents(inner, wrapped)
    xlsx = str(tmp_path / "w.xlsx")
    extract(wrapped, xlsx, keep_note_numbers=True)
    out = str(tmp_path / "out.zip")
    res = repack(xlsx, wrapped, out, clean_cr=False, record_history=False)
    assert res["changes"] == []
    assert open(out, "rb").read() == open(wrapped, "rb").read()


@pytest.mark.skipif(not os.path.exists(_DARTDB), reason="dartdb 픽스처 없음")
def test_contamination_is_dartdb_artifact(tmp_path):
    """동일 문서의 dartdb판만 오염 보유 → 오염은 dartdb 가공 아티팩트."""
    from dsd_tool.excel_out import extract
    info_db = extract(_DARTDB, str(tmp_path / "db.xlsx"))
    assert info_db["deduped_notes"] == 41       # dartdb판: 전 주석 오염
    info_od = extract_to_excel(_FIXTURE, str(tmp_path / "od.xlsx"),
                               work_dir=str(tmp_path))
    assert info_od["deduped_notes"] == 0        # OpenDART판: 오염 없음
