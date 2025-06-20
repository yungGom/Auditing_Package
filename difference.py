# logic_comparison.py

from __future__ import annotations
import io
import pandas as pd
from pathlib import Path

def _find_column(df_columns: list[str], possible_names: list[str]) -> str | None:
    """사용 가능한 컬럼 목록에서 후보 이름 중 하나를 찾아 반환 (대소문자/공백 무시)"""
    df_cols_map = {col.strip().upper(): col for col in df_columns}
    for name in possible_names:
        if name.strip().upper() in df_cols_map:
            return df_cols_map[name.strip().upper()]
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
    삼일회계법인 자료의 전표 완전성 검토 개념을 충실히 반영.
    """
    # --- 1. GL 데이터 집계 ---
    # GL의 계정코드/계정과목 열 이름 찾기
    gl_code_col = _find_column(gl_df.columns, ['계정코드', '계정과목코드', 'ACCT_CODE', 'ACCT_CD'])
    gl_name_col = _find_column(gl_df.columns, ['계정과목', '계정과목명', '계정명', 'ACCT_NAME'])
    
    if not gl_code_col:
        raise ValueError("총계정원장(GL)에서 '계정코드' 관련 열을 찾을 수 없습니다.")
    
    gl_summary = gl_df.groupby(gl_code_col).agg(
        당기차변=('차변금액', 'sum'),
        당기대변=('대변금액', 'sum')
    ).reset_index()
    gl_summary['당기증감'] = gl_summary['당기차변'] - gl_summary['당기대변']
    
    # --- 2. 시산표(TB) 데이터 처리 ---
    def process_tb(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        code_col = _find_column(df.columns, ['계정코드', '계정과목코드', 'ACCT_CODE', 'ACCT_CD'])
        name_col = _find_column(df.columns, ['계정과목', '계정과목명', '계정명', 'ACCT_NAME'])
        dr_col = _find_column(df.columns, ['차변잔액', '차변 잔액', 'DR_BAL'])
        cr_col = _find_column(df.columns, ['대변잔액', '대변 잔액', 'CR_BAL'])

        if not code_col or not dr_col or not cr_col:
            raise ValueError(f"{prefix} 시산표에서 필수 열(계정코드, 차변잔액, 대변잔액)을 찾을 수 없습니다.")

        tb_processed = df[[code_col, name_col, dr_col, cr_col]].copy()
        tb_processed.columns = ['계정코드', f'{prefix}계정과목', f'{prefix}차변', f'{prefix}대변']
        
        tb_processed[f'{prefix}차변'] = _to_numeric_safe(tb_processed[f'{prefix}차변'])
        tb_processed[f'{prefix}대변'] = _to_numeric_safe(tb_processed[f'{prefix}대변'])
        tb_processed[f'{prefix}잔액'] = tb_processed[f'{prefix}차변'] - tb_processed[f'{prefix}대변']
        
        return tb_processed[['계정코드', f'{prefix}계정과목', f'{prefix}잔액']]

    prior_tb_summary = process_tb(pre_tb_df, "기초")
    current_tb_summary = process_tb(cur_tb_df, "기말")

    # --- 3. 데이터 병합 (Merge) ---
    # 계정코드 마스터 생성 (모든 계정 포함)
    all_codes = pd.concat([
        gl_summary[[gl_code_col]],
        prior_tb_summary[['계정코드']],
        current_tb_summary[['계정코드']]
    ]).drop_duplicates(subset=[gl_code_col])
    all_codes.columns = ['계정코드'] # 컬럼명 통일

    # 계정과목명 정보 추가 (가장 최신 정보인 당기 TB 우선)
    name_map = pd.concat([
        current_tb_summary[['계정코드', '기말계정과목']].rename(columns={'기말계정과목':'계정과목'}),
        prior_tb_summary[['계정코드', '기초계정과목']].rename(columns={'기초계정과목':'계정과목'})
    ]).drop_duplicates(subset=['계정코드'])
    
    merged_df = pd.merge(all_codes, name_map, on='계정코드', how='left')
    merged_df = pd.merge(merged_df, prior_tb_summary, on='계정코드', how='left')
    merged_df = pd.merge(merged_df, gl_summary[[gl_code_col, '당기증감']], left_on='계정코드', right_on=gl_code_col, how='left')
    merged_df = pd.merge(merged_df, current_tb_summary, on='계정코드', how='left')
    
    # 불필요한 열 제거
    merged_df = merged_df.drop(columns=['기초계정과목', '기말계정과목', gl_code_col], errors='ignore')
    
    # NaN 값 0으로 채우기
    numeric_cols = ['기초잔액', '당기증감', '기말잔액']
    for col in numeric_cols:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(0)
        else: # 혹시 열이 생성 안된 경우
            merged_df[col] = 0

    # --- 4. 차이 계산 및 결과 필터링 ---
    merged_df['검증차액'] = merged_df['기초잔액'] + merged_df['당기증감'] - merged_df['기말잔액']

    # 허용오차(TOL) 1원 초과 차이 계정만 필터링
    diff_accounts = merged_df[merged_df['검증차액'].abs() > 1].copy()

    if not diff_accounts.empty:
        return diff_accounts[['계정코드', '계정과목', '기초잔액', '당기증감', '기말잔액', '검증차액']]
    
    return pd.DataFrame() # 차이 없으면 빈 DataFrame 반환
