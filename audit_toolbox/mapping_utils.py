# -*- coding: utf-8 -*-
"""
컬럼 매핑 보조 유틸 (헤더행 자동 탐지 · 컬럼 추정).
- streamlit 비의존 → 단위 테스트 가능. 외부 통신 없음.
- PATCH 2(H1) 헤더행 자동탐지 / 이후 PATCH 4(H2) 별칭·시그니처 추정의 공통 토대.
"""

# 컬럼 헤더 동의어 사전 (ERP별 표기 차이 흡수)
GUESS = {
    "vendor": ["거래처", "거래처명", "상대처", "거래상대", "업체", "업체명", "계정상대"],
    "account": ["계정과목", "계정", "계정명", "과목"],
    "memo": ["적요", "비고", "메모", "내역", "거래내역", "summary"],
    "amount": ["금액", "차변", "대변", "차변금액", "대변금액", "발생액", "잔액"],
}


def guess_col(cols, keys):
    """컬럼명 목록에서 keys 동의어가 포함된 첫 컬럼 반환, 없으면 '(없음)'."""
    for k in keys:
        for c in cols:
            if k in str(c):
                return c
    return "(없음)"


def _row_field_categories(cells):
    """한 행(cells)이 매칭하는 필드 카테고리(vendor/account/memo/amount) 집합."""
    texts = [str(c) for c in cells if c is not None and str(c).strip() != ""]
    hit = set()
    for field, keys in GUESS.items():
        if any(any(k in t for t in texts) for k in keys):
            hit.add(field)
    return hit


def detect_header_row(rows, max_scan=20):
    """
    H1: 업로드 파일 상단을 스캔해 헤더 행 인덱스를 추정.
    - rows: 원본 셀 값의 2차원 리스트 (header=None 으로 읽은 결과 .values.tolist()).
    - 거래처·계정·적요·금액류 키워드가 '2개 카테고리 이상' 포함된 첫 행을 헤더로 본다.
    - 추정 실패 시 0 반환 (회계사가 number_input 으로 덮어쓰기 가능).
    완전성 우선: 자동 추정을 맹신하지 않되 회사당 반복 부담을 줄이는 기본값 제공.
    """
    best_idx, best_score = 0, 0
    limit = min(len(rows), max_scan + 1)
    for i in range(limit):
        cats = _row_field_categories(rows[i])
        score = len(cats)
        if score >= 2:
            return i  # 2개 이상이면 즉시 헤더로 확정 (상단 우선)
        if score > best_score:
            best_idx, best_score = i, score
    return best_idx
