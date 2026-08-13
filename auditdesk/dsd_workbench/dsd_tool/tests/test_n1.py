"""N-1 게이트: 수신물 친화명 — rcept_no 정체성 불변·표시 계층 분리.

G1 수신 사이드카 → {회사명}_{보고서명}_{기간} (첨부 표식 유지)
G2 캐시 파일·폴더명 불변 — 사이드카만 추가 (정체성 보존)
G3 기존 캐시 소급 — 사이드카 없이 corp_code 폴더 → 회사명만
   (보고서명 미상 시 접수번호 유지), 소급 불가 시 None(파일명 유지)
G4 파일명 안전 문자 치환
"""
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dart_explorer.converters.document_wrap import (  # noqa: E402
    friendly_name, sanitize_name, save_name_meta)

_RCEPT = "20250814002901"


@pytest.fixture()
def cached(tmp_path):
    d = tmp_path / "01234567"                   # corp_code 폴더 규약
    d.mkdir()
    dsd = d / f"{_RCEPT}.dsd"
    dsd.write_bytes(b"PK")
    return d, str(dsd)


def test_g1_sidecar_friendly(cached):
    d, dsd = cached
    save_name_meta(dsd, _RCEPT, corp_name="케이엔솔",
                   report_nm="반기보고서 (2025.06)", rcept_dt="20250814")
    assert friendly_name(dsd) == "케이엔솔_반기보고서_2025.06"
    att = d / f"{_RCEPT}_별도감사보고서.dsd"
    att.write_bytes(b"PK")
    assert friendly_name(str(att)) == \
        "케이엔솔_반기보고서_2025.06_별도감사보고서"


def test_g2_rcept_identity_preserved(cached):
    d, dsd = cached
    before = sorted(os.listdir(d))
    save_name_meta(dsd, _RCEPT, corp_name="케이엔솔")
    after = sorted(os.listdir(d))
    assert f"{_RCEPT}.dsd" in after             # 캐시 파일명 그대로
    assert set(after) - set(before) == {f"{_RCEPT}.name.json"}


def test_g3_retro_from_corp_code(cached):
    _d, dsd = cached
    # 사이드카 없음 — corp_code 폴더 소급 (보고서명 미상 → 접수번호)
    assert friendly_name(dsd, corp_resolver=lambda c: "케이엔솔"
                         if c == "01234567" else None) == \
        f"케이엔솔_{_RCEPT}"
    # 소급 실패(resolver 없음·비코드 폴더) → None = 기존 파일명 유지
    assert friendly_name(dsd) is None
    assert friendly_name(dsd, corp_resolver=lambda c: None) is None
    # rcept 형식이 아닌 파일명 → 대상 아님
    assert friendly_name(os.path.join(os.path.dirname(dsd),
                                      "회사보유.dsd")) is None


def test_g4_sanitize(cached):
    _d, dsd = cached
    save_name_meta(dsd, _RCEPT, corp_name="케이/엔:솔",
                   report_nm='사업보고서*"? (2025.12)')
    name = friendly_name(dsd)
    assert not any(ch in name for ch in '\\/:*?"<>|')
    assert name.startswith("케이_엔_솔")
    assert sanitize_name("a<b>|c") == "a_b_c"
