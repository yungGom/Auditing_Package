# logic_comparison.py

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

def _to_numeric_safe(series: pd.Series) -> pd.Series:
    """문자열, 쉼표 포함된 Series를 숫자로 안전하게 변환"""
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False),
        errors='coerce'
    ).fillna(0)

def load_tb(path_or_buffer: str | Path | io.BytesIO | io.StringIO, header_row: int) -> pd.DataFrame:
    """시산표 파일을 로드하고 기본 전처리를 수행하는 함수"""
    filename = getattr(path_or_buffer, 'name', 'TB_file.xlsx')
    suffix = Path(filename).suffix.lower()

    if suffix == ".xlsx":
        df = pd.read_excel(path_or_buffer, header=header_row)
    elif suffix == ".csv":
        if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
        try:
            df = pd.read_csv(path_or_buffer, header=header_row, encoding='utf-8')
        except UnicodeDecodeError:
            if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
            df = pd.read_csv(path_or_buffer, header=header_row, encoding='cp949')
    else:
        raise ValueError(f"지원하지 않는 시산표 파일 형식: {suffix}")

    # 모든 object 타입 컬럼의 좌우 공백 제거
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.strip()
        
    return df

def perform_roll_forward_test(gl_df: pd.DataFrame, pre_tb_df: pd.DataFrame, cur_tb_df: pd.DataFrame) -> pd.DataFrame:
    """
    기초(전기TB) + 당기증감(GL) = 기말(당기TB) 검증을 수행한다.
    """
    # --- 1. GL 데이터 집계 ---
    # GL의 필수 컬럼 이름 찾기 (logic_jet.py에서 표준화된 이름을 사용)
    gl_code_col = '계정코드'
    gl_dr_col = '차변금액'
    gl_cr_col = '대변금액'

    if any(col not in gl_df.columns for col in [gl_code_col, gl_dr_col, gl_cr_col]):
        raise ValueError("총계정원장(GL)에 '계정코드', '차변금액', '대변금액' 표준 컬럼이 없습니다. 데이터 로드를 먼저 확인하세요.")

    gl_summary = gl_df.groupby(gl_code_col).agg(
        당기차변=(gl_dr_col, 'sum'),
        당기대변=(gl_cr_col, 'sum')
    ).reset_index()
    gl_summary['당기증감'] = gl_summary['당기차변'] - gl_summary['당기대변']
    
    # --- 2. 시산표(TB) 데이터 처리 ---
    def process_tb(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        code_col = _find_column(df.columns, ['계정코드', '계정과목코드', 'ACCT_CODE', 'ACCT_CD', '계정'])
        name_col = _find_column(df.columns, ['계정과목', '계정과목명', '계정명', 'ACCT_NAME'])
        dr_col = _find_column(df.columns, ['차변잔액', '차변 잔액', '차변', 'DR_BAL', '차변합계'])
        cr_col = _find_column(df.columns, ['대변잔액', '대변 잔액', '대변', 'CR_BAL', '대변합계'])

        if not code_col or not dr_col or not cr_col:
            raise ValueError(f"{prefix} 시산표에서 필수 열(계정코드, 차변잔액, 대변잔액)을 찾을 수 없습니다. 컬럼명을 확인해주세요.")
        if not name_col:
            name_col = f'{prefix}계정과목' # 계정과목명 컬럼이 없으면 임시 생성
            df[name_col] = ''

        tb_processed = df[[code_col, name_col, dr_col, cr_col]].copy()
        tb_processed.columns = ['계정코드', f'{prefix}계정과목', f'{prefix}차변', f'{prefix}대변']
        
        tb_processed[f'{prefix}차변'] = _to_numeric_safe(tb_processed[f'{prefix}차변'])
        tb_processed[f'{prefix}대변'] = _to_numeric_safe(tb_processed[f'{prefix}대변'])
        tb_processed[f'{prefix}잔액'] = tb_processed[f'{prefix}차변'] - tb_processed[f'{prefix}대변']
        
        return tb_processed[['계정코드', f'{prefix}계정과목', f'{prefix}잔액']]

    prior_tb_summary = process_tb(pre_tb_df, "기초")
    current_tb_summary = process_tb(cur_tb_df, "기말")

    # --- 3. 데이터 병합 (Merge) ---
    all_codes = pd.concat([
        gl_summary[[gl_code_col]],
        prior_tb_summary[['계정코드']],
        current_tb_summary[['계정코드']]
    ]).drop_duplicates(subset=[gl_code_col])
    all_codes.columns = ['계정코드'] # 컬럼명 통일

    name_map = pd.concat([
        current_tb_summary[['계정코드', '기말계정과목']].rename(columns={'기말계정과목':'계정과목'}),
        prior_tb_summary[['계정코드', '기초계정과목']].rename(columns={'기초계정과목':'계정과목'})
    ]).drop_duplicates(subset=['계정코드'])
    
    merged_df = pd.merge(all_codes, name_map, on='계정코드', how='left')
    merged_df = pd.merge(merged_df, prior_tb_summary, on='계정코드', how='left')
    merged_df = pd.merge(merged_df, gl_summary[[gl_code_col, '당기증감']], left_on='계정코드', right_on=gl_code_col, how='left')
    merged_df = pd.merge(merged_df, current_tb_summary, on='계정코드', how='left')
    
    merged_df = merged_df.drop(columns=['기초계정과목', '기말계정과목', gl_code_col], errors='ignore')
    
    numeric_cols = ['기초잔액', '당기증감', '기말잔액']
    for col in numeric_cols:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(0)
        else:
            merged_df[col] = 0

    # --- 4. 차이 계산 및 결과 필터링 ---
    merged_df['검증차액'] = (merged_df['기초잔액'] + merged_df['당기증감'] - merged_df['기말잔액']).round(0)

    # 허용오차(TOL) 1원 초과 차이 계정만 필터링
    diff_accounts = merged_df[merged_df['검증차액'].abs() > 1].copy()

    if not diff_accounts.empty:
        # 최종 결과 컬럼 순서 정리
        final_cols = ['계정코드', '계정과목', '기초잔액', '당기증감', '기말잔액', '검증차액']
        diff_accounts = diff_accounts[final_cols]
        return diff_accounts
    
    return pd.DataFrame() # 차이 없으면 빈 DataFrame 반환
