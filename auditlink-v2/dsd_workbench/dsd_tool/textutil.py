"""텍스트 정규화·숫자 판정·이스케이프 유틸.

스펙 3.4 비교 규칙 / 3.5 역변환 규칙 구현.
"""
import re

# DSD 줄바꿈 엔티티 (XML 원문에는 &amp;cr; 로 저장됨 → 엔티티 해제 후 &cr;)
CR_ENTITY = "&cr;"

_TAG_RE = re.compile(r"<[^>]*>")
_NUM_DEC_RE = re.compile(r"&#(\d+);")
_NUM_HEX_RE = re.compile(r"&#x([0-9a-fA-F]+);")
_PLAIN_NUM_RE = re.compile(r"\d+(\.\d+)?")


def unescape_entities(s: str) -> str:
    """XML 엔티티 해제. &amp; 는 반드시 마지막에 처리."""
    s = _NUM_DEC_RE.sub(lambda m: chr(int(m.group(1))), s)
    s = _NUM_HEX_RE.sub(lambda m: chr(int(m.group(1), 16)), s)
    s = s.replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&quot;", '"').replace("&apos;", "'")
    s = s.replace("&amp;", "&")
    return s


def clean_text(raw: str) -> str:
    """셀 원본 XML → 표시용 텍스트.

    순서: 태그 제거 → 엔티티 해제 → &cr; → \\n → 양끝 공백 제거
    """
    if raw is None:
        return ""
    s = _TAG_RE.sub("", raw)
    s = unescape_entities(s)
    s = s.replace(CR_ENTITY, "\n")
    return s.strip()


def escape_for_dsd(text) -> str:
    """새 값 → DSD XML 텍스트.

    스펙 3.4-3: \\n → &cr; 먼저, 그다음 & → &amp;
    (그래야 원문 형식인 &amp;cr; 이 만들어진다)
    """
    s = str(text)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", CR_ENTITY)
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    return s


def try_number(value):
    """숫자로 확실히 해석되면 float 반환, 아니면 None.

    천단위 검증(스펙 3.4-1): 콤마가 있으면 첫 그룹 1~3자리, 이후 그룹 정확히 3자리.
    "3,4,5,6"(주석참조) → None(텍스트 유지). 괄호 음수 "(1,234)" → -1234.
    선행 0("012")은 텍스트로 본다(전화번호·코드 보호).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    t = str(value).strip()
    if not t:
        return None

    neg = False
    if t.startswith("(") and t.endswith(")") and len(t) > 2:
        neg = True
        t = t[1:-1].strip()
    if t.startswith("-"):
        neg = not neg
        t = t[1:].strip()
    if t.startswith("+"):
        t = t[1:].strip()
    if not t:
        return None

    int_part, dot, frac = t.partition(".")
    if dot and (not frac or not frac.isdigit()):
        return None

    if "," in int_part:
        groups = int_part.split(",")
        if not all(g.isdigit() for g in groups):
            return None
        if not (1 <= len(groups[0]) <= 3):
            return None
        if any(len(g) != 3 for g in groups[1:]):
            return None
        digits = "".join(groups)
    else:
        if not int_part.isdigit():
            return None
        digits = int_part

    # 선행 0 (한 자리 "0" 자체는 숫자로 인정)
    if len(digits) > 1 and digits.startswith("0"):
        return None

    num = float(digits + (("." + frac) if dot else ""))
    return -num if neg else num


def numbers_equal(a: float, b: float) -> bool:
    return abs(a - b) < 1e-6


def format_number_like(orig_text: str, value) -> str:
    """원본 표기 스타일(콤마·괄호음수·소수자릿수)을 따라 새 숫자를 문자열화.

    orig_text 가 비어 있으면(빈 셀 삽입) 콤마 그룹 + '-' 음수 기본값.
    """
    orig = (orig_text or "").strip()
    v = float(value)
    neg = v < 0
    v = abs(v)

    # 소수 자릿수: 새 값이 정수면 정수로, 아니면 새 값 그대로
    if v == int(v):
        int_str = str(int(v))
        frac_str = ""
    else:
        s = repr(v)
        int_str, _, frac = s.partition(".")
        frac_str = "." + frac

    use_comma = ("," in orig) or not orig
    if use_comma:
        int_str = f"{int(int_str):,}"

    body = int_str + frac_str
    if neg:
        paren = orig.startswith("(") and orig.endswith(")")
        return f"({body})" if paren else f"-{body}"
    return body


# ---------------------------------------------------------------------------
# 주석 번호 중복 정리 — dartdb 제공 DSD의 "1. 1. 일반적 사항" 오염
# ---------------------------------------------------------------------------

# 같은 번호가 연속 중복될 때만 매칭 ("1. 2. ..."는 비중복이므로 제외)
NOTE_DUP_RE = re.compile(r"^(\d+)\.\s*\1\.\s*")


def dedup_note_number(text: str) -> str:
    """주석 헤더의 중복 번호 정리: "1. 1. 일반적 사항" → "1. 일반적 사항"."""
    return NOTE_DUP_RE.sub(r"\1. ", (text or "").strip())


# ---------------------------------------------------------------------------
# &cr;-only 셀 (개행 엔티티만 있는 셀) 판정 — repack --clean-cr 대상
# ---------------------------------------------------------------------------

# 원본 XML 기준: &amp;cr; 만 1회 이상 반복 (값과 섞인 셀은 매칭 안 됨)
CR_ONLY_RE = re.compile(r"^(?:&amp;cr;)+$")

# 클린업 허용 태그 — P(서술문)의 의도적 빈 줄은 절대 제외
CLEANABLE_TAGS = {"TD", "TH", "TE", "TU"}

_OPEN_TAG_RE = re.compile(r"<([A-Za-z0-9-]+)")


def enclosing_tag(text: str, content_start: int):
    """내용 오프셋 직전의 여는 태그 이름 (대문자). 못 찾으면 None."""
    lt = text.rfind("<", 0, content_start)
    if lt < 0:
        return None
    m = _OPEN_TAG_RE.match(text, lt)
    return m.group(1).upper() if m else None


def is_cr_only_cell(text: str, content_start: int, raw: str) -> bool:
    """TD/TH/TE/TU 셀이면서 내용이 &amp;cr; 반복뿐인지."""
    return bool(raw) and bool(CR_ONLY_RE.match(raw)) and \
        enclosing_tag(text, content_start) in CLEANABLE_TAGS


# ---------------------------------------------------------------------------
# 재무제표 제목 정규화 (스펙 2.3)
# ---------------------------------------------------------------------------

_WS_RE = re.compile(r"[\s　 ]+")

FS_TITLE_RE = re.compile(
    r"^(반기|분기)?(연결)?"
    r"(재무상태표|손익계산서|포괄손익계산서|자본변동표|현금흐름표|"
    r"이익잉여금처분계산서|결손금처리계산서)$"
)

FS_ABBREV = {
    "재무상태표": "BS",
    "손익계산서": "PL",
    "포괄손익계산서": "CI",  # 손익계산서 존재 여부에 따라 PL1 또는 PL 로 확정
    "자본변동표": "CE",
    "현금흐름표": "CF",
    "이익잉여금처분계산서": "RE",
    "결손금처리계산서": "DE",
}


def normalize_title(s: str) -> str:
    """공백(전각 포함) 전부 제거."""
    return _WS_RE.sub("", s or "")


def match_fs_title(s: str):
    """FS 제목이면 (period_prefix, consol_prefix, base_name) 반환, 아니면 None."""
    m = FS_TITLE_RE.match(normalize_title(s))
    if not m:
        return None
    return (m.group(1) or "", m.group(2) or "", m.group(3))
