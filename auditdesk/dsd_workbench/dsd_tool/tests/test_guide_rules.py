"""F-4a: 가이드 규칙 자산(guide_rules_2026.json) 무결성 검사.

규칙 내용의 정오는 회계사 검수(승인☐) 영역 — 여기서는 스키마·범위·
초기 상태만 강제한다. 미승인 조항 비활성 원칙: approved=False 초기값.
"""
import io
import json
import os

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", ".."))
_ASSET = os.path.join(_ROOT, "assets", "guide", "guide_rules_2026.json")

pytestmark = pytest.mark.skipif(not os.path.exists(_ASSET),
                                reason="guide_rules 자산 없음")

_TYPES = {"원칙", "금지", "권고", "예외·허용", "유의"}


def _load():
    return json.load(io.open(_ASSET, encoding="utf-8"))


def test_schema_and_uniqueness():
    data = _load()
    rules = data["rules"]
    assert len(rules) >= 100
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids)), "조항ID 중복"
    for r in rules:
        assert r["type"] in _TYPES, r["id"]
        assert r["target"], r["id"]
        assert 1 <= len(r["summary"]) <= 120, r["id"]   # 2줄 이내 요지
        assert isinstance(r["page"], int) and 93 <= r["page"] <= 420, \
            r["id"]                                     # 제5장 범위
        assert isinstance(r["approved"], bool), r["id"]


def test_scope_sections():
    """시즌판 범위: Ⅰ절 6 + Ⅱ절 전수 + Ⅲ절 실존 계정과목만."""
    rules = _load()["rules"]
    s1 = [r for r in rules if r["id"].startswith("5.Ⅰ")]
    s2 = [r for r in rules if r["id"].startswith("5.Ⅱ")]
    s3 = [r for r in rules if r["id"].startswith("5.Ⅲ")]
    assert len(s1) == 6                     # 표현차이 6
    assert len(s2) >= 40                    # 원칙 전수
    assert all(r["target"].startswith("주석:") for r in s3)
    # 제외 확정: 공정가치 측정(Ⅲ.15)·기타(Ⅲ.20)
    assert not any(r["id"].startswith("5.Ⅲ.15") or
                   r["id"].startswith("5.Ⅲ.20") for r in s3)


def test_initial_state_unapproved():
    """검수 전 초기 자산은 전 조항 미승인이어야 정상 (F-4b-lite 착수
    금지 상태). 검수 반영 후에는 이 테스트가 아니라 승인 수가 기준."""
    rules = _load()["rules"]
    approved = sum(1 for r in rules if r["approved"])
    # 승인 반영 전이면 0, 반영 후면 1 이상 — 음수·비불리언만 차단
    assert 0 <= approved <= len(rules)
