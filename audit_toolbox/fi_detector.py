"""
금융기관 탐지 엔진 (모집단 완전성 검토용)
- 외부 통신 없음. 전부 로컬 처리.
- 판정이 아니라 '후보 추출 + 근거 제시'가 목적.
"""
import os
import re
import unicodedata

# ─────────────────────────────────────────────────────────────
# 레이어 1: 금융기관 명칭 사전 (카테고리별)
# 회사별로 자유롭게 추가/삭제 가능한 고정 사전
# ─────────────────────────────────────────────────────────────
FI_DICT = {
    "은행": [
        "국민은행", "KB국민", "신한은행", "우리은행", "하나은행", "농협은행", "NH농협",
        "기업은행", "IBK", "산업은행", "KDB", "수협은행", "수협", "SC제일", "한국씨티", "씨티은행",
        "대구은행", "iM뱅크", "부산은행", "경남은행", "광주은행", "전북은행", "제주은행",
        "케이뱅크", "카카오뱅크", "토스뱅크", "외환은행", "씨티",
    ],
    "증권": [
        "미래에셋증권", "삼성증권", "한국투자증권", "NH투자증권", "KB증권", "키움증권",
        "대신증권", "메리츠증권", "하나증권", "신한투자증권", "유안타", "교보증권",
        "한화투자증권", "현대차증권", "DB금융투자", "이베스트", "SK증권",
    ],
    "보험": [
        "삼성생명", "한화생명", "교보생명", "신한라이프", "NH농협생명", "동양생명",
        "삼성화재", "DB손해보험", "현대해상", "KB손해보험", "메리츠화재", "한화손해보험",
        "흥국화재", "롯데손해보험", "MG손해보험",
    ],
    "보증기관": ["신용보증기금", "기술보증기금", "서울보증보험", "신용보증재단", "무역보험공사", "주택금융공사"],
    "카드": ["삼성카드", "신한카드", "현대카드", "KB국민카드", "롯데카드", "하나카드", "우리카드", "BC카드"],
    "저축은행": ["저축은행", "OK저축", "SBI저축", "웰컴저축", "페퍼저축"],
    "캐피탈/기타": ["캐피탈", "자산운용", "신탁", "할부금융", "리스금융", "팩토링"],
}

# 기관유형(사전 카테고리) → 조회서 양식 매핑
CONFIRM_FORM = {
    "은행": "은행", "증권": "증권사", "보험": "보험회사", "보증기관": "보증기관",
    "카드": "여신전문", "저축은행": "저축은행", "캐피탈/기타": "여신전문",
    "기타(접미어)": "기타(검토필요)",
}

# 사전에 없어도 아래 일반 접미어가 거래처명에 있으면 후보로 승격
GENERIC_SUFFIX = ["은행", "Bank", "증권", "Securities", "생명", "화재", "해상", "손해보험",
                  "보험", "캐피탈", "저축은행", "자산운용", "카드"]

# ─────────────────────────────────────────────────────────────
# 레이어 2: 금융기관 거래가 반드시 흔적을 남기는 계정과목
#   거래처명이 비거나 약칭이어도 계정으로 후보를 건진다 (완전성 보강)
# ─────────────────────────────────────────────────────────────
FI_ACCOUNTS = {
    "예금/현금성": ["보통예금", "당좌예금", "정기예금", "정기적금", "현금성자산", "단기금융상품", "기타예금"],
    "차입": ["단기차입금", "장기차입금", "유동성장기부채", "사채", "당좌차월", "외화차입금"],
    "손익": ["이자수익", "이자비용", "지급수수료"],
    "유가증권/파생": ["당기손익공정가치측정금융자산", "기타포괄손익공정가치측정금융자산",
                  "상각후원가측정금융자산", "파생상품자산", "파생상품부채", "매도가능증권", "단기매매증권"],
}
FI_ACCOUNT_FLAT = {a: cat for cat, lst in FI_ACCOUNTS.items() for a in lst}

# 적요(摘要)에서 잡는 보조 키워드 (계정이 두루뭉술할 때)
MEMO_HINTS = ["이자", "예금이자", "차입", "대출이자", "지급이자", "수수료", "외화환산", "배당"]


def _norm(s):
    """거래처명 정규화: 법인격 표기·공백·지점명 제거 → 기관 단위로 롤업"""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).strip()
    s = re.sub(r"\(주\)|㈜|주식회사|\(유\)|유한회사|\(주\)", "", s)
    # 지점/영업점 표기 제거 (롤업용 키 생성)
    s = re.sub(r"\s*(제?\d+|[가-힣A-Za-z]+)\s*(지점|영업점|출장소|센터|지店)\s*$", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def _match_dict(name):
    """레이어1: 사전 매칭. (카테고리, 매칭키워드) 반환, 없으면 None"""
    if not name:
        return None
    nm = unicodedata.normalize("NFKC", str(name))
    for cat, kws in FI_DICT.items():
        for kw in kws:
            if kw in nm:
                return (cat, kw)
    # 일반 접미어 승격
    for suf in GENERIC_SUFFIX:
        if suf in nm:
            return ("기타(접미어)", suf)
    return None


def scan(records):
    """
    records: list of dict, 각 행은
      {row_no, source, date, slip_no, account, vendor, memo, amount}
    반환: 후보별 집계 + 원천 추적 리스트
    """
    hits = []  # 원천 추적용: 행 단위 매칭 결과
    for r in records:
        vendor = r.get("vendor") or ""
        account = (r.get("account") or "").strip()
        memo = r.get("memo") or ""

        dict_hit = _match_dict(vendor)
        acct_hit = FI_ACCOUNT_FLAT.get(account)
        memo_hit = next((h for h in MEMO_HINTS if h in memo), None)

        if not (dict_hit or acct_hit or memo_hit):
            continue

        if dict_hit:
            basis, category, kw = "사전매칭", dict_hit[0], dict_hit[1]
            form = CONFIRM_FORM.get(category, "기타(검토필요)")
        elif acct_hit:
            basis, category, kw = "계정추적", acct_hit, account
            form = None  # 기관유형 미상 → 회계사 판단
        else:
            basis, category, kw = "적요키워드", "추정", memo_hit
            form = None

        hits.append({
            **r,
            "norm_vendor": _norm(vendor) or "(거래처미상)",
            "basis": basis,
            "category": category,
            "form": form,
            "matched": kw,
        })
    return hits


def aggregate(hits):
    """레이어3: 정규화 기관 단위로 집계. 조회 대상 마스터 생성."""
    agg = {}
    for h in hits:
        key = h["norm_vendor"]
        if key not in agg:
            agg[key] = {
                "기관(정규화)": key,
                "조회서양식": None,
                "근거": set(),
                "매칭값": set(),
                "발견건수": 0,
                "원천행": [],
                "_hits": [],
            }
        a = agg[key]
        a["근거"].add(h["basis"])
        a["매칭값"].add(str(h["matched"]))
        a["발견건수"] += 1
        a["원천행"].append(h["row_no"])
        a["_hits"].append(h)
        # 사전매칭으로 기관유형이 확정되면 채택
        if h["form"] and a["조회서양식"] is None:
            a["조회서양식"] = h["form"]
    for a in agg.values():
        a["사전매칭여부"] = "Y" if "사전매칭" in a["근거"] else "N(검토필요)"
        if a["조회서양식"] is None:
            a["조회서양식"] = "미분류(검토필요)"
        a["근거"] = ", ".join(sorted(a["근거"]))
        a["매칭값"] = ", ".join(sorted(a["매칭값"]))
        a["원천행"] = ", ".join(str(x) for x in a["원천행"])
        a["포함근거"] = "당기 탐지"
        # 온라인 조회 가능 여부 + 고객센터 자동기입
        o = lookup_online(a["기관(정규화)"], a["조회서양식"])
        a["조회방법"] = "온라인 조회" if o["online"] else "서면 조회(확인필요)"
        a["전화번호"] = o["전화번호"]
        a["온라인정식명"] = o["정식명"]
    return list(agg.values())


def inst_key(name, form=None):
    """기관 동일성 판단 키. 온라인 참가 기관은 정식명으로 통일(명칭 변형 흡수)."""
    o = lookup_online(name, form)
    if o["online"]:
        return ("ON", o["정식명"])
    return ("OFF", _canon(name))


def merge_prior(candidates, prior_names):
    """
    전기 발송 조회처(담당자 직접 입력)를 당기 탐지 결과에 병합.
    - 명칭 변형(KEB하나은행=하나은행 등)은 inst_key의 온라인 정식명 통일로 흡수.
    - 당기에 이미 있으면 '포함근거'에 전기 표시, 없으면 '전기보유분'으로 추가.
    반환: (병합된 candidates, 신규 추가된 전기보유분 수)
    """
    idx = {}
    for c in candidates:
        c.setdefault("포함근거", "당기 탐지")
        k = inst_key(c.get("온라인정식명") or c["기관(정규화)"], c["조회서양식"])
        idx[k] = c
    added = 0
    for raw in prior_names:
        nm = str(raw).strip()
        if not nm:
            continue
        dh = _match_dict(nm)
        form = CONFIRM_FORM.get(dh[0], None) if dh else None
        o = lookup_online(nm, form)
        if not form and o["유형"] in ("은행", "증권사", "보험회사", "보증기관"):
            form = o["유형"]
        k = inst_key(nm, form)
        if k in idx:
            c = idx[k]
            if "전기" not in c["포함근거"]:
                c["포함근거"] = c["포함근거"] + " + 전기 조회처"
        else:
            newc = {
                "기관(정규화)": o["정식명"] or _norm(nm) or nm,
                "온라인정식명": o["정식명"],
                "조회서양식": form or "미분류(검토필요)",
                "사전매칭여부": "N(전기)",
                "근거": "전기 조회처",
                "매칭값": nm,
                "발견건수": 0,
                "원천행": "-",
                "_hits": [],
                "조회방법": "온라인 조회" if o["online"] else "서면 조회(확인필요)",
                "전화번호": o["전화번호"],
                "포함근거": "전기 조회처(당기 미탐지)",
            }
            candidates.append(newc)
            idx[k] = newc
            added += 1
    return candidates, added


# ─────────────────────────────────────────────────────────────
# 온라인 조회 가능 기관 목록 (전자조회 참가기관)
#   탐지된 기관이 여기 있으면 → "온라인 조회" + 고객센터 자동기입
#   type 표기는 CONFIRM_FORM 기준(은행/증권사/보험회사/보증기관/기타)
# ─────────────────────────────────────────────────────────────
ONLINE_FI = [
    # 은행
    ("HSBC", "은행", "2019-09-23", "02)2004-0298"),
    ("KEB하나은행", "은행", "2014-12-01", "1599-1111"),
    ("SC제일은행", "은행", "2015-06-15", "1588-1599"),
    ("경남은행", "은행", "2013-12-02", "1600-8585"),
    ("광주은행", "은행", "2013-10-31", "1588-3388"),
    ("국민은행", "은행", "2013-12-18", "1599-9999"),
    ("기업은행", "은행", "2013-12-16", "1566-2566"),
    ("농협은행", "은행", "2013-11-11", "1588-2100"),
    ("미즈호은행", "은행", "2025-03-10", "02-3782-6094"),
    ("부산은행", "은행", "2013-11-20", "1588-6200"),
    ("산업은행", "은행", "2015-12-01", "1588-1500"),
    ("수협은행", "은행", "2013-12-02", "1588-1515"),
    ("신한은행", "은행", "2013-12-02", "1599-8000"),
    ("씨티은행", "은행", "2013-12-27", "1588-7000"),
    ("아이엠뱅크(구 대구)", "은행", "2013-12-02", "1588-5050"),
    ("우리은행", "은행", "2014-01-03", "1588-5000, 1599-5000"),
    ("전북은행", "은행", "2014-06-01", "1588-4477"),
    ("제이피모간체이스은행", "은행", "2024-11-06", "02-758-5026"),
    ("제주은행", "은행", "2013-11-11", "1588-0079"),
    ("중소벤처기업진흥공단", "기타", "2026-06-01", "055-751-9607"),
    ("카카오뱅크", "은행", "2017-12-19", "1599-3333"),
    ("케이뱅크", "은행", "2018-12-10", "1522-1000"),
    ("토스뱅크", "은행", "2023-11-20", "1661-7654"),
    ("한국수출입은행", "은행", "2024-01-02", "02)3779-6114"),
    # 증권
    ("KB증권", "증권사", "2020-01-03", "1588-6611"),
    ("NH투자증권", "증권사", "2019-12-20", "1544-0000"),
    ("SK증권", "증권사", "2023-12-27", "1544-8245"),
    ("교보증권", "증권사", "2017-12-21", "1544-0900"),
    ("대신증권", "증권사", "2024-11-08", "1544-4488"),
    ("메리츠증권", "증권사", "2023-11-03", "1588-3400"),
    ("미래에셋증권", "증권사", "2020-12-28", "1588-6800"),
    ("삼성증권", "증권사", "2017-12-21", "1588-2323"),
    ("신한투자증권", "증권사", "2020-12-31", "1588-0365"),
    ("아이엠증권", "증권사", "2018-05-11", "1588-7171"),
    ("키움증권", "증권사", "2020-01-28", "02)1544-9000"),
    ("하나증권", "증권사", "2020-10-16", "1588-3111"),
    ("한국증권금융", "증권사", "2020-01-13", "02)3770-8800"),
    ("한국투자증권", "증권사", "2019-08-05", "1544-5000, 1588-0023"),
    ("한화투자증권", "증권사", "2020-12-28", "02)3772-7727"),
    ("현대차증권", "증권사", "2020-12-18", "1588-6655"),
    # 보험
    ("DB손해보험", "보험회사", "2021-12-31", "1588-0100"),
    ("KB손해보험", "보험회사", "2021-11-01", "02)6900-2556"),
    ("NH농협생명보험", "보험회사", "2022-12-13", "02)3786-8156"),
    ("NH농협손해보험", "보험회사", "2024-05-10", "1644-9000"),
    ("교보생명보험", "보험회사", "2021-11-22", "02)721-2707"),
    ("롯데손해보험", "보험회사", "2022-01-14", "02)3455-3621"),
    ("메리츠화재해상보험", "보험회사", "2018-01-15", "1566-7711"),
    ("미래에셋생명", "보험회사", "2023-06-16", "02-3271-4948"),
    ("삼성생명보험", "보험회사", "2022-08-16", "1588-3114"),
    ("삼성화재해상보험", "보험회사", "2020-01-10", "02)758-4634"),
    ("신한라이프생명보험", "보험회사", "2023-01-06", "02)3455-4741"),
    ("에이아이지손해보험", "보험회사", "2024-11-18", "02-316-5982"),
    ("한화생명보험", "보험회사", "2025-01-13", "1588-6363"),
    ("한화손해보험", "보험회사", "2020-12-31", "02)316-0476"),
    ("현대해상화재보험", "보험회사", "2019-08-19", "1588-5656"),
    ("흥국생명보험", "보험회사", "2025-01-13", "1588-2288"),
    # 보증기관
    ("기술보증기금", "보증기관", "2020-12-31", "1544-1120"),
    ("서울보증보험", "보증기관", "2017-12-21", "1670-7000"),
    ("신용보증기금", "보증기관", "2024-12-30", "1588-6565"),
]

# 토큰 정규화로 안 잡히는 표기 차이 보정 (분개장 표기 → 온라인목록 표준 표기)
ONLINE_ALIAS = {
    "대구은행": "아이엠뱅크", "iM뱅크": "아이엠뱅크", "디지비대구은행": "아이엠뱅크",
    "하이투자증권": "아이엠증권", "iM증권": "아이엠증권",
    "한국씨티은행": "씨티은행", "씨티": "씨티은행",
    "중소기업은행": "기업은행", "IBK기업은행": "기업은행",
    "제이피모간": "제이피모간체이스", "JP모간": "제이피모간체이스",
}


def _canon(name):
    """온라인 매칭 비교용: 법인격·지점·괄호·공백 제거 (영문약어는 식별자라 보존)"""
    s = unicodedata.normalize("NFKC", str(name or "")).upper().strip()
    s = re.sub(r"\(.*?\)", "", s)  # 괄호 내용 제거
    s = re.sub(r"주식회사|㈜|\(주\)|\(유\)", "", s)
    s = re.sub(r"\s*(제?\d+|[가-힣A-Z]+)\s*(지점|영업점|출장소|센터)\s*$", "", s)
    s = re.sub(r"\s+", "", s)
    return s


# 사전 인덱싱
_ONLINE_INDEX = [(_canon(ONLINE_ALIAS.get(n, n)), n, t, d, tel) for (n, t, d, tel) in ONLINE_FI]


def lookup_online(vendor_norm, form):
    """
    탐지 기관(vendor_norm) + 기관유형(form)을 온라인 목록과 대조.
    반환: {"online":bool, "정식명":str, "전화번호":str, "서비스일자":str} or 미매칭시 online=False
    """
    target = _canon(ONLINE_ALIAS.get(vendor_norm, vendor_norm))
    if not target:
        return {"online": False, "정식명": "", "전화번호": "", "서비스일자": "", "유형": ""}
    type_known = form in ("은행", "증권사", "보험회사", "보증기관")
    matches = []
    for canon, name, typ, date, tel in _ONLINE_INDEX:
        # 유형이 확정된 경우 같은 유형만, 미확정이면 전체 대상
        if type_known and typ != form and typ != "기타":
            continue
        if target == canon or target in canon or canon in target:
            matches.append((name, typ, date, tel, len(canon)))
    if not matches:
        return {"online": False, "정식명": "", "전화번호": "", "서비스일자": "", "유형": ""}
    # 유형 정확히 일치하는 것 우선, 그 다음 이름 길이 가까운 순(가장 구체적 매칭)
    matches.sort(key=lambda m: (m[1] != form, abs(m[4] - len(target))))
    name, typ, date, tel, _ = matches[0]
    return {"online": True, "정식명": name, "전화번호": tel, "서비스일자": date, "유형": typ}


# ─────────────────────────────────────────────────────────────
# PATCH 5: 사전·온라인목록 외부 엑셀 분리 (회계사가 코드 없이 갱신)
#   같은 폴더에 아래 파일이 있으면 내장 기본값 대신 사용한다:
#     금융기관사전.xlsx     (열: 카테고리, 키워드)
#     온라인조회목록.xlsx   (열: 기관명, 유형, 서비스일자, 전화번호)
#   파일이 없거나 읽기 실패 시 내장 기본값으로 자동 복귀(동작 불변).
#   외부 통신 없음. 로컬 엑셀만 읽는다.
# ─────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICT_XLSX_NAME = "금융기관사전.xlsx"
ONLINE_XLSX_NAME = "온라인조회목록.xlsx"

# 내장 기본값 스냅샷 (외부 파일 없을 때 복귀용)
_DEFAULT_FI_DICT = {k: list(v) for k, v in FI_DICT.items()}
_DEFAULT_ONLINE_FI = list(ONLINE_FI)

EXTERNAL_DICT_LOADED = False
EXTERNAL_ONLINE_LOADED = False


def _load_external_dict(path):
    """금융기관사전.xlsx → {카테고리:[키워드,...]} 또는 None(없음/실패)."""
    if not path or not os.path.exists(path):
        return None
    try:
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        d = {}
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0 or not row:
                continue  # 헤더 / 빈 행
            cat = str(row[0]).strip() if row[0] is not None else ""
            kw = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            if cat and kw:
                d.setdefault(cat, []).append(kw)
        wb.close()
        return d or None
    except Exception:
        return None


def _load_external_online(path):
    """온라인조회목록.xlsx → [(기관명, 유형, 서비스일자, 전화번호),...] 또는 None."""
    if not path or not os.path.exists(path):
        return None
    try:
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        out = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0 or not row:
                continue
            name = str(row[0]).strip() if row[0] is not None else ""
            typ = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            svc = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
            tel = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""
            if name and typ:
                out.append((name, typ, svc, tel))
        wb.close()
        return out or None
    except Exception:
        return None


def reload_external(base_dir=None):
    """외부 엑셀이 있으면 사전/온라인목록을 교체, 없으면 내장 기본값으로 복귀."""
    global FI_DICT, ONLINE_FI, _ONLINE_INDEX
    global EXTERNAL_DICT_LOADED, EXTERNAL_ONLINE_LOADED
    base = base_dir or _BASE_DIR
    d = _load_external_dict(os.path.join(base, DICT_XLSX_NAME))
    o = _load_external_online(os.path.join(base, ONLINE_XLSX_NAME))
    FI_DICT = d if d else {k: list(v) for k, v in _DEFAULT_FI_DICT.items()}
    ONLINE_FI = o if o else list(_DEFAULT_ONLINE_FI)
    EXTERNAL_DICT_LOADED = bool(d)
    EXTERNAL_ONLINE_LOADED = bool(o)
    _ONLINE_INDEX = [(_canon(ONLINE_ALIAS.get(n, n)), n, t, dt, tel)
                     for (n, t, dt, tel) in ONLINE_FI]
    return EXTERNAL_DICT_LOADED, EXTERNAL_ONLINE_LOADED


def export_templates(dirpath):
    """현재 사전/온라인목록을 엑셀 템플릿 2개로 내보낸다(회계사 편집용)."""
    from openpyxl import Workbook
    os.makedirs(dirpath, exist_ok=True)
    dict_path = os.path.join(dirpath, DICT_XLSX_NAME)
    online_path = os.path.join(dirpath, ONLINE_XLSX_NAME)

    wb = Workbook(); ws = wb.active; ws.title = "금융기관사전"
    ws.append(["카테고리", "키워드"])
    for cat, kws in FI_DICT.items():
        for kw in kws:
            ws.append([cat, kw])
    wb.save(dict_path)

    wb2 = Workbook(); ws2 = wb2.active; ws2.title = "온라인조회목록"
    ws2.append(["기관명", "유형", "서비스일자", "전화번호"])
    for (n, t, dt, tel) in ONLINE_FI:
        ws2.append([n, t, dt, tel])
    wb2.save(online_path)
    return dict_path, online_path


# 임포트 시 외부 파일 자동 반영 (없으면 내장 기본값 유지 → 동작 불변)
reload_external()
