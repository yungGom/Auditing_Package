# -*- coding: utf-8 -*-
"""
매핑 프로파일 저장·재사용 (PATCH 3 / Phase H3).

- 컬럼 헤더 집합의 시그니처(정렬된 헤더명 해시)를 키로, 확정된 컬럼 매핑을
  로컬 JSON(`~/.audit_toolbox/mapping_profiles.json`)에 저장한다.
- 동일 시그니처 파일 재업로드 시 매핑을 자동 로드 → 회계사는 확인만.
- 외부 통신 없음. streamlit 비의존 → 단위 테스트 가능.

보안: JSON에는 **컬럼명 매핑 메타데이터만** 저장한다.
  재무수치·기관명·거래처값·파일명·클라이언트명은 절대 저장하지 않는다.
  허용 키(_ALLOWED_KEYS) 외에는 저장 단계에서 모두 폐기한다.
"""
import os
import json
import hashlib

# 저장 허용 키 — 이 외의 키(데이터 등)는 _sanitize 에서 전부 버린다.
_ALLOWED_KEYS = {"vendor", "account", "memo", "amount", "header_row", "label", "headers"}
_FIELD_KEYS = ("vendor", "account", "memo", "amount")


def default_path():
    """기본 저장 경로: 사용자 홈 ~/.audit_toolbox/mapping_profiles.json"""
    return os.path.join(os.path.expanduser("~"), ".audit_toolbox", "mapping_profiles.json")


def _norm_header(h):
    return str(h).strip()


def compute_signature(headers):
    """헤더명 집합 → 안정적 시그니처(정렬·해시). 컬럼 순서·중복 무관."""
    norm = sorted({_norm_header(h) for h in headers if _norm_header(h) != ""})
    raw = "".join(norm)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def load_profiles(path=None):
    """저장된 프로파일 전체 로드. 파일 없거나 손상 시 빈 dict."""
    path = path or default_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _sanitize(mapping):
    """허용 키만 남기고, 데이터로 오해될 값은 형변환/차단."""
    out = {}
    for k, v in mapping.items():
        if k not in _ALLOWED_KEYS:
            continue  # 데이터(수치·기관명 등) 키는 폐기
        if k == "header_row":
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                out[k] = 0
        elif k == "headers":
            if isinstance(v, (list, tuple)):
                out[k] = [str(x) for x in v]
        else:
            out[k] = "" if v is None else str(v)
    return out


def save_profile(signature, mapping, path=None):
    """시그니처 → 매핑 저장(원자적 교체). 허용 키만 기록."""
    path = path or default_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    profiles = load_profiles(path)
    profiles[signature] = _sanitize(mapping)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(profiles, fp, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return profiles[signature]


def get_profile(signature, path=None):
    """시그니처로 사용자 저장 프로파일 조회. 없으면 None."""
    return load_profiles(path).get(signature)


# ─────────────────────────────────────────────────────────────
# ERP 표준 프리셋 (헤더명이 알려진 경우) — 사용자 저장본이 없을 때 보조 제안.
#   매핑값(컬럼명)이 업로드 헤더에 '모두 존재'하면 매칭(부분집합).
#   오탐 위험을 줄이기 위해 보수적으로 최소만 둔다.
# ─────────────────────────────────────────────────────────────
PRESETS = [
    {
        "label": "더존 분개장(표준)",
        "mapping": {"vendor": "거래처명", "account": "계정과목", "memo": "적요", "amount": "차변금액"},
    },
    {
        "label": "더존 분개장(차/대변 분리)",
        "mapping": {"vendor": "거래처", "account": "계정과목", "memo": "적요", "amount": "차변"},
    },
]


def match_preset(headers):
    """프리셋 중 매핑 컬럼명이 헤더에 모두 존재하는 첫 항목 반환."""
    hset = {_norm_header(h) for h in headers}
    for p in PRESETS:
        vals = [v for v in p["mapping"].values() if v]
        if vals and all(v in hset for v in vals):
            return p
    return None


def match_mapping(headers, path=None):
    """
    업로드 헤더에 대한 매핑 자동 결정.
    반환: (mapping_or_None, source, signature)
      source: "user"(저장본) | "preset"(ERP 프리셋) | None
    """
    sig = compute_signature(headers)
    prof = get_profile(sig, path)
    if prof:
        return prof, "user", sig
    p = match_preset(headers)
    if p:
        m = dict(p["mapping"])
        m["label"] = p["label"]
        return m, "preset", sig
    return None, None, sig
