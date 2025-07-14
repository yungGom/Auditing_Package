# logic_jet.py

from __future__ import annotations
import io
import re
import pandas as pd
from pathlib import Path

def _find_column(df_columns: list[str], possible_names: list[str]) -> str | None:
    """사용 가능한 컬럼 목록에서 후보 이름 중 하나를 찾아 반환 (대소문자/공백/특수문자 무시)"""
    def normalize(text: str) -> str:
        return re.sub(r'[\s._-]', '', text).upper()

    df_cols_map = {normalize(col): col for col in df_columns}
    for name in possible_names:
        normalized_name = normalize(name)
        if normalized_name in df_cols_map:
            return df_cols_map[normalized_name]
    return None

def load_gl_for_jet(path_or_buffer: str | Path | io.BytesIO | io.StringIO, header_row: int = 0) -> pd.DataFrame:
    """총계정원장 파일을 로드하고 JET 분석을 위해 표준화 및 정제한다."""
    filename = getattr(path_or_buffer, 'name', 'GL_file.xlsx')
    suffix = Path(filename).suffix.lower()

    dtype_spec = { "전표번호": str, "계정코드": str, "계정과목코드": str, "입력사원": str, "작성자ID": str}

    if suffix == ".xlsx":
        df = pd.read_excel(path_or_buffer, header=header_row, dtype=dtype_spec)
    elif suffix == ".csv":
        if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
        try:
            df = pd.read_csv(path_or_buffer, header=header_row, dtype=dtype_spec, encoding='utf-8')
        except UnicodeDecodeError:
            if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
            df = pd.read_csv(path_or_buffer, header=header_row, dtype=dtype_spec, encoding='cp949')
    else:
        raise ValueError(f"지원하지 않는 총계정원장 파일 형식: {suffix}")

    # --- 열 이름 표준화 ---
    rename_map = {
        _find_column(df.columns, ['전표일자', '회계일자', '기표일자', 'Posting Date']): "전표일자",
        _find_column(df.columns, ['입력일자', '작성일자', 'Entry Date', 'Created on']): "입력일자",
        _find_column(df.columns, ['전표번호', '전표 번호', 'Document No.', 'Doc. No.']): "전표번호",
        _find_column(df.columns, ['계정코드', '계정과목코드', '계정 코드', 'G/L Account', 'ACCT_CODE', 'ACCT_CD']): "계정코드",
        _find_column(df.columns, ['계정과목', '계정과목명', '계정명', 'G/L Account Name', 'ACCT_NAME']): "계정과목",
        _find_column(df.columns, ['차변금액', '차변', '차변 금액', 'Debit', 'DR_AMOUNT']): "차변금액",
        _find_column(df.columns, ['대변금액', '대변', '대변 금액', 'Credit', 'CR_AMOUNT']): "대변금액",
        _find_column(df.columns, ['적요', '摘要', 'Text', 'Description', '내용']): "적요",
        _find_column(df.columns, ['입력사원', '작성자', '입력자', 'User Name', 'Created By', 'USER_ID']): "입력사원"
    }
    # None 키 제거 및 실제 rename 수행
    df.rename(columns={k: v for k, v in rename_map.items() if k is not None and k != v}, inplace=True)
    
    # SAP 형식 등 차/대변이 한 컬럼에 있는 경우 처리
    if '차변금액' in df.columns and '대변금액' not in df.columns:
         # 금액이 음수/양수로 구분된 경우
         if pd.api.types.is_numeric_dtype(df['차변금액']):
             df['대변금액'] = df['차변금액'].apply(lambda x: abs(x) if x < 0 else 0)
             df['차변금액'] = df['차변금액'].apply(lambda x: x if x > 0 else 0)
    
    # --- 데이터 정제 (Cleansing) ---
    # 필수 컬럼 존재 여부 확인
    required_cols = ['전표일자', '전표번호', '계정코드', '차변금액', '대변금액']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"필수 컬럼을 찾을 수 없습니다: {', '.join(missing_cols)}. 컬럼 이름 자동 탐지 기능을 강화했지만, 여전히 파일을 식별할 수 없습니다. 파일의 컬럼명을 확인해주세요.")

    for col in ['계정과목', '계정코드', '입력사원', '적요', '전표번호']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace('nan', '')
    
    for col in ['전표일자', '입력일자']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    for col in ["차변금액", "대변금액"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            ).fillna(0)
        else:
            df[col] = 0

    return df

# --- JET 시나리오 함수들 (기존과 동일, 변경 없음) ---

def s1_keyword_search(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    if not keywords or '적요' not in df.columns:
        return pd.DataFrame()
    pattern = "|".join(map(re.escape, keywords))
    mask = df["적요"].str.contains(pattern, case=False, na=False)
    return df[mask].copy()

def s2_backdated_entries(df: pd.DataFrame, threshold_days: int) -> pd.DataFrame:
    if '입력일자' not in df.columns or '전표일자' not in df.columns:
        return pd.DataFrame()
    
    df_copy = df.dropna(subset=['입력일자', '전표일자']).copy()
    df_copy['지연일수'] = (df_copy['입력일자'] - df_copy['전표일자']).dt.days
    return df_copy[df_copy['지연일수'] > threshold_days]

def s3_rare_accounts(df: pd.DataFrame, threshold: int) -> pd.DataFrame:
    if '계정코드' not in df.columns: return pd.DataFrame()
    counts = df["계정코드"].value_counts()
    rare_codes = counts[counts < threshold].index
    return df[df["계정코드"].isin(rare_codes)].copy()

def s4_rare_users(df: pd.DataFrame, threshold: int) -> pd.DataFrame:
    if '입력사원' not in df.columns: return pd.DataFrame()
    counts = df["입력사원"].value_counts()
    rare_users = counts[counts < threshold].index
    return df[df["입력사원"].isin(rare_users)].copy()

def s5_weekend_holiday(df: pd.DataFrame) -> pd.DataFrame:
    if '전표일자' not in df.columns: return pd.DataFrame()
    df_copy = df.dropna(subset=['전표일자']).copy()
    mask = df_copy["전표일자"].dt.weekday >= 5
    return df_copy[mask]

def s6_round_numbers(df: pd.DataFrame, zero_digits: int) -> pd.DataFrame:
    if zero_digits < 1: return pd.DataFrame()
    factor = 10 ** zero_digits
    mask = (((df["차변금액"] % factor == 0) & (df["차변금액"] != 0)) |
            ((df["대변금액"] % factor == 0) & (df["대변금액"] != 0)))
    return df[mask].copy()

def s7_abnormal_combo_sales(df: pd.DataFrame) -> pd.DataFrame:
    if '계정과목' not in df.columns or '전표번호' not in df.columns: return pd.DataFrame()
    allowed_accounts = {'현금', '당좌예금', '보통예금', '외상매출금', '받을어음', '미수금', '선수금', '부가세예수금'}
    
    sales_journals = df[df['계정과목'].str.contains('매출', na=False)]
    if sales_journals.empty: return pd.DataFrame()
    
    abnormal_jns = []
    for jn, group in df.groupby('전표번호'):
        if jn not in sales_journals['전표번호'].values:
            continue
            
        accounts_in_jn = set(group['계정과목'])
        contra_accounts = {acc for acc in accounts_in_jn if '매출' not in acc}
        
        if not contra_accounts.issubset(allowed_accounts):
            abnormal_jns.append(jn)
            
    return df[df['전표번호'].isin(abnormal_jns)].copy()


# --- 전체 시나리오 실행기 ---
def run_all_jet_scenarios(df: pd.DataFrame, params: dict) -> dict[str, pd.DataFrame]:
    """설정된 파라미터에 따라 모든 JET 시나리오를 실행하고 결과를 딕셔너리로 반환"""
    results = {}
    
    kw_list = [k.strip() for k in params['keywords'].split(",") if k.strip()]
    if kw_list:
        res = s1_keyword_search(df, kw_list)
        if not res.empty: results["S1_적요키워드"] = res
    
    res = s2_backdated_entries(df, params['backdate_threshold'])
    if not res.empty: results["S2_기표지연"] = res

    res = s3_rare_accounts(df, params['rare_account_threshold'])
    if not res.empty: results["S3_희귀계정"] = res

    res = s4_rare_users(df, params['rare_user_threshold'])
    if not res.empty: results["S4_희귀입력자"] = res

    if params['enable_weekend_holiday']:
        res = s5_weekend_holiday(df)
        if not res.empty: results["S5_주말휴일거래"] = res

    res = s6_round_numbers(df, params['round_number_zeros'])
    if not res.empty: results["S6_라운드넘버"] = res

    if params['enable_abnormal_combo']:
        res = s7_abnormal_combo_sales(df)
        if not res.empty: results["S7_비경상계정조합(매출)"] = res

    return results
