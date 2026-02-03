"""
OpenDART API 모듈
- DART(전자공시시스템) API를 통해 기업 재무정보 조회
- 법인세비용차감전순이익 등 주요 재무항목 추출
- 엑셀 파일로 결과 저장
"""

import requests
import pandas as pd
from datetime import datetime
from io import BytesIO


# =========================
# OpenDART API 호출 함수
# =========================

def fetch_fnltt_singl_all(crtfc_key: str, corp_code: str, year: int, reprt_code: str, fs_div: str) -> dict:
    """
    OpenDART '단일회사 전체 재무제표' API 호출

    Args:
        crtfc_key: OpenDART 인증키
        corp_code: 기업 고유번호 (8자리)
        year: 사업연도
        reprt_code: 보고서 코드 (11011=사업보고서, 11012=반기보고서, 11013=1분기, 11014=3분기)
        fs_div: 재무제표 구분 (OFS=별도, CFS=연결)

    Returns:
        dict: API 응답 JSON
    """
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": crtfc_key,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": reprt_code,
        "fs_div": fs_div,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_corp_code_list(crtfc_key: str) -> bytes:
    """
    OpenDART 기업 고유번호 목록 조회 (ZIP 파일)

    Args:
        crtfc_key: OpenDART 인증키

    Returns:
        bytes: ZIP 파일 바이너리
    """
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    params = {"crtfc_key": crtfc_key}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.content


# =========================
# 유틸리티 함수
# =========================

def to_number(x):
    """콤마/공백 포함 문자열을 int로 변환 (실패 시 None 반환)"""
    if x is None:
        return None
    s = str(x).replace(",", "").strip()
    if s in ("", "-", "nan", "None"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def pick_account_value(records: list, keywords: list, amount_field: str = "thstrm_amount"):
    """
    레코드 목록에서 특정 계정의 금액 추출

    Args:
        records: API 응답의 list 필드
        keywords: 검색할 계정명 키워드 목록 (우선순위 순)
        amount_field: 추출할 금액 필드명

    Returns:
        tuple: (금액, 계정명, 재무제표구분)
    """
    if not records:
        return None, None, None

    df = pd.DataFrame(records)

    if "account_nm" not in df.columns:
        return None, None, None

    cand = pd.DataFrame()
    for kw in keywords:
        tmp = df[df["account_nm"].fillna("").str.contains(kw, regex=False)]
        if not tmp.empty:
            cand = tmp.copy()
            break

    if cand.empty:
        return None, None, None

    # 재무제표 구분 우선순위: IS > CIS > BS > 기타
    pri = {"IS": 1, "CIS": 2, "BS": 3}
    cand["sj_pri"] = cand["sj_div"].map(pri).fillna(9)
    cand = cand.sort_values(["sj_pri"])

    row = cand.iloc[0]
    amount = to_number(row.get(amount_field))
    return amount, row.get("account_nm"), row.get("sj_div")


def pick_pretax_profit(records: list):
    """
    법인세비용차감전순이익 추출

    Args:
        records: API 응답의 list 필드

    Returns:
        tuple: (금액, 계정명, 재무제표구분)
    """
    keywords = [
        "법인세비용차감전순이익",
        "법인세비용차감전계속사업이익",
        "법인세비용차감전",
    ]
    return pick_account_value(records, keywords, "thstrm_amount")


def pick_revenue(records: list):
    """
    매출액 추출

    Args:
        records: API 응답의 list 필드

    Returns:
        tuple: (금액, 계정명, 재무제표구분)
    """
    keywords = [
        "매출액",
        "수익(매출액)",
        "영업수익",
    ]
    return pick_account_value(records, keywords, "thstrm_amount")


def pick_operating_profit(records: list):
    """
    영업이익 추출

    Args:
        records: API 응답의 list 필드

    Returns:
        tuple: (금액, 계정명, 재무제표구분)
    """
    keywords = [
        "영업이익",
        "영업이익(손실)",
    ]
    return pick_account_value(records, keywords, "thstrm_amount")


def pick_net_income(records: list):
    """
    당기순이익 추출

    Args:
        records: API 응답의 list 필드

    Returns:
        tuple: (금액, 계정명, 재무제표구분)
    """
    keywords = [
        "당기순이익",
        "당기순이익(손실)",
        "분기순이익",
    ]
    return pick_account_value(records, keywords, "thstrm_amount")


def pick_total_assets(records: list):
    """
    총자산 추출

    Args:
        records: API 응답의 list 필드

    Returns:
        tuple: (금액, 계정명, 재무제표구분)
    """
    keywords = [
        "자산총계",
    ]
    return pick_account_value(records, keywords, "thstrm_amount")


def pick_total_equity(records: list):
    """
    총자본 추출

    Args:
        records: API 응답의 list 필드

    Returns:
        tuple: (금액, 계정명, 재무제표구분)
    """
    keywords = [
        "자본총계",
    ]
    return pick_account_value(records, keywords, "thstrm_amount")


# =========================
# 메인 분석 함수
# =========================

def analyze_financial_statements(
    crtfc_key: str,
    corp_code: str,
    start_year: int = None,
    end_year: int = None,
    fs_div: str = "OFS",
    reprt_code: str = "11011"
) -> pd.DataFrame:
    """
    지정 기업의 연도별 재무제표 주요 항목 분석

    Args:
        crtfc_key: OpenDART 인증키
        corp_code: 기업 고유번호
        start_year: 시작 연도 (기본: 최근 10년)
        end_year: 종료 연도 (기본: 전년도)
        fs_div: 재무제표 구분 (OFS=별도, CFS=연결)
        reprt_code: 보고서 코드 (11011=사업보고서)

    Returns:
        pd.DataFrame: 연도별 재무 분석 결과
    """
    if end_year is None:
        end_year = datetime.now().year - 1
    if start_year is None:
        start_year = end_year - 9

    rows = []
    for year in range(start_year, end_year + 1):
        try:
            data = fetch_fnltt_singl_all(crtfc_key, corp_code, year, reprt_code, fs_div)

            if data.get("status") != "000":
                rows.append({
                    "사업연도": year,
                    "매출액": None,
                    "영업이익": None,
                    "법인세비용차감전순이익": None,
                    "당기순이익": None,
                    "자산총계": None,
                    "자본총계": None,
                    "비고": f"API 오류: {data.get('message')}"
                })
                continue

            records = data.get("list", [])

            revenue, _, _ = pick_revenue(records)
            op_profit, _, _ = pick_operating_profit(records)
            pretax, acc_nm, sj_div = pick_pretax_profit(records)
            net_income, _, _ = pick_net_income(records)
            total_assets, _, _ = pick_total_assets(records)
            total_equity, _, _ = pick_total_equity(records)

            rows.append({
                "사업연도": year,
                "매출액": revenue,
                "영업이익": op_profit,
                "법인세비용차감전순이익": pretax,
                "당기순이익": net_income,
                "자산총계": total_assets,
                "자본총계": total_equity,
                "비고": ""
            })

        except requests.exceptions.RequestException as e:
            rows.append({
                "사업연도": year,
                "매출액": None,
                "영업이익": None,
                "법인세비용차감전순이익": None,
                "당기순이익": None,
                "자산총계": None,
                "자본총계": None,
                "비고": f"네트워크 오류: {type(e).__name__}"
            })
        except Exception as e:
            rows.append({
                "사업연도": year,
                "매출액": None,
                "영업이익": None,
                "법인세비용차감전순이익": None,
                "당기순이익": None,
                "자산총계": None,
                "자본총계": None,
                "비고": f"예외: {type(e).__name__}: {e}"
            })

    return pd.DataFrame(rows).sort_values("사업연도")


def save_to_excel(df: pd.DataFrame, filename: str) -> str:
    """
    DataFrame을 엑셀 파일로 저장

    Args:
        df: 저장할 DataFrame
        filename: 파일명

    Returns:
        str: 저장된 파일 경로
    """
    df.to_excel(filename, index=False, engine='openpyxl')
    return filename


def get_excel_bytes(df: pd.DataFrame) -> bytes:
    """
    DataFrame을 엑셀 바이트로 변환 (다운로드용)

    Args:
        df: 변환할 DataFrame

    Returns:
        bytes: 엑셀 파일 바이트
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='재무분석')
    return output.getvalue()


# =========================
# 보고서/재무제표 구분 상수
# =========================

REPRT_CODES = {
    "사업보고서": "11011",
    "반기보고서": "11012",
    "1분기보고서": "11013",
    "3분기보고서": "11014",
}

FS_DIVS = {
    "별도재무제표": "OFS",
    "연결재무제표": "CFS",
}


# =========================
# CLI 실행 (테스트용)
# =========================

if __name__ == "__main__":
    # 테스트 실행 예시
    print("OpenDART API 모듈")
    print("사용법: from opendart_api import analyze_financial_statements")
    print("")
    print("예시:")
    print('  result = analyze_financial_statements(')
    print('      crtfc_key="YOUR_API_KEY",')
    print('      corp_code="00325112",  # 프로텍')
    print('      start_year=2015,')
    print('      end_year=2024')
    print('  )')
    print('  print(result)')
