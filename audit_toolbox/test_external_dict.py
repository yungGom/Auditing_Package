# -*- coding: utf-8 -*-
"""
PATCH 5 — 사전·온라인목록 외부 엑셀 분리 회귀 테스트.
- pytest:      pytest test_external_dict.py
- standalone:  python test_external_dict.py
- 항상 임시 폴더를 쓰고, 종료 시 내장 기본값으로 복귀시킨다.
"""
import os
import tempfile
from openpyxl import Workbook

import fi_detector as D


def _tmpdir():
    return tempfile.mkdtemp(prefix="aud_dict_")


def _write_dict(dirpath, rows):
    wb = Workbook(); ws = wb.active
    ws.append(["카테고리", "키워드"])
    for r in rows:
        ws.append(list(r))
    wb.save(os.path.join(dirpath, D.DICT_XLSX_NAME))


def _write_online(dirpath, rows):
    wb = Workbook(); ws = wb.active
    ws.append(["기관명", "유형", "서비스일자", "전화번호"])
    for r in rows:
        ws.append(list(r))
    wb.save(os.path.join(dirpath, D.ONLINE_XLSX_NAME))


# ── 내보내기 → 재로드 왕복: 기본값과 동일하게 복원되고 동작 유지 ──
def test_export_then_reload_roundtrip():
    d = _tmpdir()
    D.export_templates(d)
    flags = D.reload_external(d)
    try:
        assert flags == (True, True)
        # 내장 기본값을 그대로 내보냈으므로 핵심 동작 유지
        assert D._match_dict("신한은행")[0] == "은행"
        assert D.lookup_online("국민은행", "은행")["online"]
    finally:
        D.reload_external()  # 기본값 복귀


# ── 외부 엑셀로 신규 기관 추가가 코드 수정 없이 반영됨 ──
def test_custom_external_files_apply():
    d = _tmpdir()
    _write_dict(d, [("저축은행", "테스트저축"), ("은행", "신한은행")])
    _write_online(d, [("테스트은행", "은행", "2025-01-01", "02-000-0000")])
    D.reload_external(d)
    try:
        assert D.EXTERNAL_DICT_LOADED and D.EXTERNAL_ONLINE_LOADED
        hit = D._match_dict("테스트저축")
        assert hit == ("저축은행", "테스트저축"), hit
        o = D.lookup_online("테스트은행", "은행")
        assert o["online"] and o["정식명"] == "테스트은행", o
        # 외부 목록으로 교체되었으므로 기존 내장 전용 기관은 빠짐
        assert not D.lookup_online("국민은행", "은행")["online"]
    finally:
        D.reload_external()


# ── 파일이 없으면 내장 기본값으로 안전 복귀 (동작 불변) ──
def test_missing_files_fallback_to_default():
    d = _tmpdir()  # 빈 폴더
    flags = D.reload_external(d)
    try:
        assert flags == (False, False)
        assert not D.EXTERNAL_DICT_LOADED
        # 내장 기본값 회귀 테스트가 그대로 통과
        assert D._match_dict("신한은행")[0] == "은행"
        assert D.lookup_online("국민은행", "은행")["online"]
        assert len(D.ONLINE_FI) == len(D._DEFAULT_ONLINE_FI)
    finally:
        D.reload_external()


# ── 손상/형식오류 파일이면 None 처리 → 기본값 유지 ──
def test_corrupt_file_is_ignored():
    d = _tmpdir()
    with open(os.path.join(d, D.DICT_XLSX_NAME), "w", encoding="utf-8") as fp:
        fp.write("이건 엑셀이 아님")
    flags = D.reload_external(d)
    try:
        assert flags[0] is False  # 사전 로드 실패 → 기본값
        assert D._match_dict("신한은행")[0] == "은행"
    finally:
        D.reload_external()


if __name__ == "__main__":
    import traceback
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn(); print(f"  PASS  {name}"); passed += 1
        except Exception:
            print(f"  FAIL  {name}"); traceback.print_exc(); failed += 1
    print(f"\n{passed} passed, {failed} failed (총 {len(tests)}개)")
    raise SystemExit(1 if failed else 0)
