"""A-3b 게이트: version-check CLI + 즉석 G2 스모크.

게이트:
1. 기존 세대에서 version-check 정상 판정
   (지시서는 5.106/5.107/6.0변환 3종을 언급하나, 이 저장소는 batch_validate로
   실제 확보·검증한 세대가 5.049 하나뿐 — 5.106/5.107은 KNOWN_VERSIONS.md에
   "픽스처 미확보"로 명시돼 있음. 대신 실제 보유한 3개 직렬화 세대
   [구형 4.1 / 6.0변환 3.5(실파일) / 6.0변환 4.1(합성)]으로 "정상 판정"을 검증)
2. 가짜 editver 픽스처로 미확인 경고 + 절차 안내 출력 확인
"""
import glob
import os

import pytest

from dsd_tool.cli import main
from dsd_tool.version import (NEW_VERSION_PROCEDURE, g2_smoke, is_known,
                              known_versions_table, read_version_info)

from .fixture import build_dsd

_REAL_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "real")
_SAMSUNG = os.path.join(_REAL_DIR, "[삼성전자(주)]_2025_[감사보고서].dsd")
_SAMSUNG_60 = os.path.join(
    _REAL_DIR, "[삼성전자(주)]_2025_[연결감사보고서]-6_0변환.dsd")
_HANBIT_60 = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "synthetic",
    "한빛정밀_클린-6_0변환.dsd")

_KNOWN_GENERATIONS = [p for p in (_SAMSUNG, _SAMSUNG_60, _HANBIT_60)
                     if os.path.exists(p)]


def test_g2_smoke_direct():
    assert _KNOWN_GENERATIONS
    res = g2_smoke(_KNOWN_GENERATIONS[0])
    assert res == {"changes": 0, "byte_identical": True}


def test_known_versions_table_parses():
    rows = known_versions_table()
    assert any(r["editver"] == "5.049" and r["g2"] == "PASS" for r in rows)


# ---------------------------------------------------------------------------
# 게이트 1: 기존 세대 3종에서 정상 판정 (known + G2 PASS)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(len(_KNOWN_GENERATIONS) < 3,
                    reason="기존 세대 픽스처 3종 미확보")
@pytest.mark.parametrize("path", _KNOWN_GENERATIONS)
def test_gate_known_generations_pass(path):
    with open(path, "rb") as f:
        v = read_version_info(f.read())
    assert is_known(v["editver"]), f"{path}: editver {v['editver']} 미확인"
    smoke = g2_smoke(path)
    assert smoke["changes"] == 0 and smoke["byte_identical"], \
        f"{path}: G2 스모크 실패 {smoke}"


@pytest.mark.skipif(len(_KNOWN_GENERATIONS) < 3,
                    reason="기존 세대 픽스처 3종 미확보")
def test_gate_known_generations_cli(capsys):
    for path in _KNOWN_GENERATIONS:
        assert main(["version-check", path]) == 0
        out = capsys.readouterr().out
        assert "확인된 버전" in out
        assert "즉석 G2 스모크(무변경 왕복): PASS" in out
        assert "미확인" not in out


# ---------------------------------------------------------------------------
# 게이트 2: 가짜 editver → 미확인 경고 + 절차 안내
# ---------------------------------------------------------------------------

def test_gate_unknown_editver_warns_and_guides(tmp_path, capsys):
    fake = build_dsd(str(tmp_path / "가짜버전.dsd"), editver="9.999")
    assert main(["version-check", fake]) == 0
    out = capsys.readouterr().out
    assert "미확인 DART 편집기 버전" in out
    assert "새 편집기 버전 대응 절차" in out
    for step_keyword in ("한빛정밀 클린본", "fixtures/real", "batch_validate",
                        "KNOWN_VERSIONS.md"):
        assert step_keyword in out
    # 미확인이어도 G2 스모크는 여전히 표시된다 (합성 픽스처는 무변경 PASS)
    assert "즉석 G2 스모크(무변경 왕복): PASS" in out


def test_new_version_procedure_matches_known_versions_doc():
    """CLI 안내 문구와 KNOWN_VERSIONS.md의 절차 서술이 동일 소스임을 보증."""
    from dsd_tool.version import known_versions_path
    with open(known_versions_path(), encoding="utf-8") as f:
        doc = f.read()
    assert "새 편집기 버전 출시 시 절차" in doc
    for line in NEW_VERSION_PROCEDURE.splitlines()[:1]:
        assert line in doc
