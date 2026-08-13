"""N-2 게이트: DSD 입력 경로 해석 — 폴더 스캔·직접 경로 이중 수용.

원인 지점(진단 보고): 종전에는 폴더 경로가 스캔 단계 없이 파일 존재
검사에서 즉시 거부 — 나열이 비거나 필터에서 떨어진 게 아니라 나열
자체 부재. discover.resolve_dsd_path가 그 단계를 신설.
G1 한글·공백·하이픈·이중 중첩 폴더 — 폴더 스캔·직접 경로 둘 다 성공
G2 파일별 제외 사유 보고 — 0건 폴더도 항목별 사유 (침묵 실패 금지)
G3 다건 — .dsd 1건이면 우선 채택, 그 외 후보 목록 안내
G4 유니코드 NFD(OneDrive 자모 분해 대비)·대소문자 무시·IXD 사유
"""
import os
import unicodedata

import pytest

from dsd_tool.discover import resolve_dsd_path


@pytest.fixture()
def nested(tmp_path):
    """한글·공백·하이픈 + 이중 중첩 폴더 합성 픽스처."""
    d = tmp_path / "한글 폴더-검토" / "이중 중첩 폴더"
    d.mkdir(parents=True)
    (d / "테스트 회사-반기.DSD").write_bytes(b"PK\x03\x04dummy")
    (d / "메모.txt").write_text("x", encoding="utf-8")
    (d / "편집중.ixd").write_bytes(b"x")
    (d / "하위폴더").mkdir()
    return d


def test_g1_folder_and_direct_both_ok(nested):
    r = resolve_dsd_path(str(nested))               # 폴더 스캔
    assert r["error"] is None
    assert r["file"].endswith("테스트 회사-반기.DSD")   # 대소문자 무시
    direct = resolve_dsd_path(r["file"])            # 직접 경로 현행 유지
    assert direct["error"] is None and direct["file"] == r["file"]
    # 끝 구분자 붙은 폴더 경로도 수용
    assert resolve_dsd_path(str(nested) + "\\")["error"] is None


def test_g2_reasons_reported(nested):
    r = resolve_dsd_path(str(nested))
    reasons = dict(r["report"])
    assert reasons["메모.txt"].startswith("확장자 불일치")
    assert "IXD" in reasons["편집중.ixd"]
    assert reasons["하위폴더"] == "폴더"
    # 0건 폴더 — 항목별 사유 + 클라우드 안내 (사유 없는 실패 금지)
    empty = resolve_dsd_path(str(nested / "하위폴더"))
    assert empty["file"] is None
    assert "찾지 못했습니다" in empty["error"]
    assert "OneDrive" in empty["error"]


def test_g3_multi_candidates(nested, tmp_path):
    (nested / "인스턴스.xml").write_text("<x/>", encoding="utf-8")
    r = resolve_dsd_path(str(nested))               # .dsd 1 + .xml 1
    assert r["error"] is None and r["file"].lower().endswith(".dsd")
    (nested / "다른회사.dsd").write_bytes(b"PK")
    r2 = resolve_dsd_path(str(nested))              # .dsd 2건 → 안내
    assert r2["file"] is None
    assert "후보" in r2["error"] and "지정하세요" in r2["error"]


def test_g4_nfd_normalized_name(tmp_path):
    d = tmp_path / "동기화 폴더"
    d.mkdir()
    name = unicodedata.normalize("NFD", "검토보고서") + ".dsd"
    (d / name).write_bytes(b"PK")
    r = resolve_dsd_path(str(d))
    assert r["error"] is None and os.path.isfile(r["file"])
