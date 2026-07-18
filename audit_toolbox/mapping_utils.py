# -*- coding: utf-8 -*-
"""
컬럼 매핑 보조 유틸 (헤더행 자동 탐지 · 컬럼 추정).
- streamlit 비의존 → 단위 테스트 가능. 외부 통신 없음.
- PATCH 2(H1) 헤더행 자동탐지 / 이후 PATCH 4(H2) 별칭·시그니처 추정의 공통 토대.
"""

# 컬럼 헤더 동의어 사전 (ERP별 표기 차이 흡수) — H2에서 ERP 실제 헤더명 수집·확장
GUESS = {
    "vendor": ["거래처명", "거래처", "상대처", "거래상대", "업체명", "업체", "계정상대",
               "공급처", "공급자", "매입처", "매출처", "고객명", "고객", "거래처코드명",
               "상대계정명", "vendor", "customer", "supplier"],
    "account": ["계정과목명", "계정과목", "계정명칭", "계정코드명", "계정명", "과목명",
                "계정", "과목", "account", "acct"],
    "memo": ["적요명", "적요내용", "적요", "비고사항", "비고", "메모", "거래내역", "내역",
             "요약", "설명", "summary", "note", "description", "contents", "remark"],
    "amount": ["차변금액", "대변금액", "거래금액", "공급가액", "합계금액", "발생액",
               "차변", "대변", "금액", "잔액", "amount", "debit", "credit"],
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


# ─────────────────────────────────────────────────────────────
# H2: 데이터 시그니처 보조 추정
#   헤더명 추정이 실패해도 '컬럼 값의 성질'로 위치를 추정한다.
#   - 금액 = 숫자 변환 성공률이 높은 컬럼
#   - 계정과목 = 계정명 사전(금융계정+일반계정) 매칭률이 높은 컬럼
#   - 적요 = 서술형(공백 포함/긴 문장) 비율이 높은 컬럼
#   - 거래처 = 날짜·숫자가 아니고 고유명사형(짧은 토큰)인 컬럼
# ─────────────────────────────────────────────────────────────
import re as _re

try:  # 금융 계정명은 fi_detector 사전을 재사용 (순환참조 없음)
    from fi_detector import FI_ACCOUNT_FLAT as _FI_ACCT
except Exception:
    _FI_ACCT = {}

# 일반(비금융) 계정명 — 계정과목 컬럼 식별 보조
GENERIC_ACCOUNTS = {
    "현금", "매출", "매입", "매출원가", "외상매출금", "외상매입금", "미수금", "미지급금",
    "선급금", "선수금", "받을어음", "지급어음", "제품", "상품", "원재료", "재공품",
    "급여", "상여금", "복리후생비", "여비교통비", "지급임차료", "감가상각비", "세금과공과",
    "지급수수료", "광고선전비", "접대비", "소모품비", "보험료", "수선비", "운반비",
    "부가세대급금", "부가세예수금", "예수금", "가지급금", "가수금", "자본금", "이익잉여금",
}
_ACCOUNT_VOCAB = set(_FI_ACCT.keys()) | GENERIC_ACCOUNTS

_DATE_RE = _re.compile(r"^\s*\d{4}\s*[-/.년]\s*\d{1,2}\s*[-/.월]\s*\d{1,2}\s*일?\s*$")


def _cells(values):
    return [str(v).strip() for v in values if v is not None and str(v).strip() != ""]


def _numeric_ratio(values):
    cs = _cells(values)
    if not cs:
        return 0.0
    ok = 0
    for s in cs:
        t = s.replace(",", "").replace(" ", "").replace("₩", "").replace("(", "-").replace(")", "")
        try:
            float(t)
            ok += 1
        except ValueError:
            pass
    return ok / len(cs)


def _date_ratio(values):
    cs = _cells(values)
    if not cs:
        return 0.0
    return sum(1 for s in cs if _DATE_RE.match(s)) / len(cs)


def _account_ratio(values):
    cs = _cells(values)
    if not cs:
        return 0.0
    ok = 0
    for s in cs:
        if s in _ACCOUNT_VOCAB or any(a in s for a in _ACCOUNT_VOCAB):
            ok += 1
    return ok / len(cs)


def _memo_score(values):
    cs = _cells(values)
    if not cs:
        return 0.0
    desc = sum(1 for s in cs if (" " in s or len(s) >= 5)
               and _numeric_ratio([s]) < 1 and not _DATE_RE.match(s))
    return desc / len(cs)


def _vendor_score(values):
    cs = _cells(values)
    if not cs:
        return 0.0
    # 숫자·날짜가 아니고, 너무 길지 않은(고유명사형) 토큰 비율
    good = sum(1 for s in cs if _numeric_ratio([s]) < 1 and not _DATE_RE.match(s) and len(s) <= 30)
    return good / len(cs)


def suggest_by_data(columns_data):
    """
    컬럼 값 성질로 4개 필드 위치를 추정.
    columns_data: {컬럼명: [값,...]}  (보통 df.to_dict('list'))
    반환: {"vendor"/"account"/"memo"/"amount": 컬럼명 or None}
    """
    stats = {c: {
        "num": _numeric_ratio(v), "date": _date_ratio(v),
        "acct": _account_ratio(v), "memo": _memo_score(v), "vend": _vendor_score(v),
    } for c, v in columns_data.items()}

    used = set()

    def pick(key, thr):
        best, bs = None, thr
        for c, s in stats.items():
            if c in used or s["date"] > 0.6:  # 날짜 컬럼은 후보 제외
                continue
            if s[key] > bs:
                bs, best = s[key], c
        if best:
            used.add(best)
        return best

    # 식별이 가장 확실한 순서로 선점 (금액 → 계정 → 적요 → 거래처)
    res = {}
    res["amount"] = pick("num", 0.6)
    res["account"] = pick("acct", 0.3)
    res["memo"] = pick("memo", 0.3)
    res["vendor"] = pick("vend", 0.3)
    return res


def resolve_mapping(columns, columns_data):
    """
    최종 컬럼 매핑 결정: ① 헤더명 동의어 추정 → ② 실패 필드는 데이터 시그니처 보조.
    반환: {"vendor"/"account"/"memo"/"amount": 컬럼명 or None}
    """
    res = {}
    for field, keys in GUESS.items():
        g = guess_col(columns, keys)
        res[field] = g if g != "(없음)" else None

    # 헤더명으로 못 찾은 필드만 데이터로 보강 (이미 잡힌 컬럼은 후보에서 제외)
    missing = [f for f in ("vendor", "account", "memo", "amount") if not res.get(f)]
    if missing:
        taken = {res[f] for f in res if res.get(f)}
        remaining = {c: v for c, v in columns_data.items() if c not in taken}
        sugg = suggest_by_data(remaining)
        for f in missing:
            res[f] = sugg.get(f)
    return res
