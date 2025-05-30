#!/usr/bin/env python
"""
GL-TB 합계 비교 스크립트 (2-Level Header 및 합계 행 처리)
======================================================

총계정원장(GL)과 시산표(TB) 파일을 비교하여 차/대변 합계(또는 잔액)가
일치하는지 확인합니다. 시산표는 2-Level 헤더 구조를 가정하며,
최종 합계는 특정 '합계' 행에서 추출합니다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path # pathlib 사용
import io # 추가: io.BytesIO, io.StringIO 타입 힌트 사용을 위해

# import numpy as np # numpy는 현재 코드에서 사용되지 않음
import pandas as pd

# --- 전역 설정 ---
TOL = 1  # 허용 오차(원) - 필요에 따라 조정

# --- 열 이름 감지용 정규식 패턴 ---
_DEBIT_PAT_BAL  = re.compile(r"(차\s*변.*잔\s*액|\bdr\b.*bal)", re.I)
_CREDIT_PAT_BAL = re.compile(r"(대\s*변.*잔\s*액|\bcr\b.*bal)", re.I)
_DEBIT_PAT_TOT  = re.compile(r"(차\s*변.*합\s*계|\bdr\b.*(tot|total))", re.I)
_CREDIT_PAT_TOT = re.compile(r"(대\s*변.*합\s*계|\bcr\b.*(tot|total))", re.I)

# --- 유틸리티 함수 ---
def detect_cols(df: pd.DataFrame) -> tuple[str | None, str | None, str | None, str | None]:
    """DataFrame 컬럼에서 차변/대변의 잔액(Bal) 및 합계(Tot) 열 이름을 찾는다."""
    d_bal = next((c for c in df.columns if _DEBIT_PAT_BAL.search(str(c))), None)
    c_bal = next((c for c in df.columns if _CREDIT_PAT_BAL.search(str(c))), None)
    d_tot = next((c for c in df.columns if _DEBIT_PAT_TOT.search(str(c))), None)
    c_tot = next((c for c in df.columns if _CREDIT_PAT_TOT.search(str(c))), None)
    return d_bal, c_bal, d_tot, c_tot

def sum_col(df: pd.DataFrame, col: str) -> float:
    """지정된 컬럼의 합계를 숫자로 계산한다 (오류 발생 시 0으로 처리)."""
    s = df[col].astype(str).str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0).sum()

# --- 데이터 로딩 함수 ---
def load_gl(path_or_buffer: str | Path | io.BytesIO | io.StringIO) -> pd.DataFrame:
    """총계정원장 파일을 로드한다 (경로 또는 파일 객체)."""
    is_path = isinstance(path_or_buffer, (str, Path))
    filename = Path(path_or_buffer).name if is_path else getattr(path_or_buffer, 'name', 'GL file')

    try:
        suffix = Path(filename).suffix.lower() if filename else '.xlsx'

        dtype_spec = { "전표번호": str, "계정코드": str, "계정과목": str,
                       "거래처코드": str, "입력사원": str }

        if suffix == ".xlsx":
            print(f"[INFO] 총계정원장(GL) 로딩 (XLSX): {filename}")
            df = pd.read_excel(path_or_buffer, dtype=dtype_spec)
        elif suffix == ".csv":
            print(f"[INFO] 총계정원장(GL) 로딩 (CSV): {filename}")
            try:
                if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
                df = pd.read_csv(path_or_buffer, dtype=dtype_spec, encoding='utf-8')
            except UnicodeDecodeError:
                print("[경고] GL CSV UTF-8 인코딩 실패. 'cp949'로 재시도합니다.")
                if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
                df = pd.read_csv(path_or_buffer, dtype=dtype_spec, encoding='cp949')
        else:
            raise ValueError(f"지원하지 않는 총계정원장 파일 형식: {suffix}")

    except Exception as e:
        print(f"[오류] 총계정원장 파일 로드 중 에러 발생 ({filename}): {e}")
        raise

    if "전표일자" in df.columns:
        df["전표일자"] = pd.to_datetime(df["전표일자"], errors="coerce")
    else: print("[경고] GL 파일에 '전표일자' 열이 없습니다.")

    for col_name in ("차변금액", "대변금액"):
        if col_name in df.columns:
            s = df[col_name].astype(str).str.replace(",", "", regex=False)
            df[col_name] = pd.to_numeric(s, errors="coerce").fillna(0)
        else:
            print(f"[경고] GL 파일에 '{col_name}' 열이 없습니다. 해당 합계는 0으로 처리됩니다.")
            df[col_name] = 0 # 해당 열이 없으면 0으로 채워진 열 생성
    return df

def load_tb(path_or_buffer: str | Path | io.BytesIO | io.StringIO, header_row: int, filename: str | None = None) -> pd.DataFrame:
    """시산표 파일을 로드한다 (경로 또는 파일 객체). XLSX는 2-level 헤더 처리."""
    is_path = isinstance(path_or_buffer, (str, Path))
    if filename is None:
        filename = Path(path_or_buffer).name if is_path else getattr(path_or_buffer, 'name', 'TB file')

    try:
        suffix = Path(filename).suffix.lower() if filename else '.xlsx'

        if suffix == ".csv":
            print(f"[INFO] 시산표(TB) 로딩 (CSV, 헤더 행: {header_row}): {filename}")
            try:
                if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
                df = pd.read_csv(path_or_buffer, header=header_row, encoding='utf-8')
            except UnicodeDecodeError:
                print("[경고] TB CSV UTF-8 인코딩 실패. 'cp949'로 재시도합니다.")
                if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
                df = pd.read_csv(path_or_buffer, header=header_row, encoding='cp949')
        elif suffix == ".xlsx":
            print(f"[INFO] 시산표(TB) 로딩 (XLSX, 헤더 행: {header_row}, {header_row+1}): {filename}")
            if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
            df = pd.read_excel(path_or_buffer, header=[header_row, header_row+1])
            def clean_level(level_val):
                s = str(level_val)
                return s if s != 'nan' and not s.startswith('Unnamed:') else None
            df.columns = ["_".join(filter(None, map(clean_level, col)))
                          for col in df.columns]
        else:
            raise ValueError(f"지원하지 않는 시산표 파일 형식입니다: {suffix}")
    except Exception as e:
        print(f"[오류] 시산표 파일 로드 중 에러 발생 ({filename}): {e}")
        raise
    return df

def verify(gl_path: str | Path | io.BytesIO | io.StringIO,
           tb_path: str | Path | io.BytesIO | io.StringIO,
           header_row: int,
           tb_col_map: dict[str, str],
           tb_account_col: str,    # TB에서 계정 식별자로 사용자가 선택한 열 이름
           tb_total_label: str
           ) -> tuple[bool, tuple, pd.DataFrame | None]:
    gl = load_gl(gl_path)
    tb = load_tb(tb_path, header_row)

    d_bal_col = tb_col_map.get('bal_d')
    c_bal_col = tb_col_map.get('bal_c')
    d_tot_col = tb_col_map.get('tot_d')
    c_tot_col = tb_col_map.get('tot_c')
    # tb_account_col 은 사용자가 TB에서 계정을 식별하기 위해 선택한 열 (예: TB의 '계정과목' 열)
    # total_label 은 TB의 합계 행을 식별하는 텍스트

    print(f"[INFO] 사용자가 지정한 시산표 열: 차_잔액='{d_bal_col}', 대_잔액='{c_bal_col}', 차_합계='{d_tot_col}', 대_합계='{c_tot_col}'")
    print(f"[INFO] 사용할 TB 계정과목 열: '{tb_account_col}', 합계 행 레이블: '{tb_total_label}'")

    required_cols_map_keys = {'bal_d': d_bal_col, 'bal_c': c_bal_col, 'tot_d': d_tot_col, 'tot_c': c_tot_col}
    if None in required_cols_map_keys.values() or tb_account_col is None or tb_total_label is None:
        missing = [k for k, v in required_cols_map_keys.items() if v is None]
        if tb_account_col is None: missing.append('TB 계정과목 열')
        if tb_total_label is None: missing.append('TB 합계 행 레이블')
        raise ValueError(f"다음 필수 정보가 누락되었습니다: {', '.join(missing)}. Streamlit 앱에서 해당 설정을 확인하세요.")

    check_cols_exist_in_tb = [d_bal_col, c_bal_col, d_tot_col, c_tot_col, tb_account_col]
    for col in check_cols_exist_in_tb:
        if col not in tb.columns:
            print(f"[DEBUG] 사용 가능한 시산표 컬럼: {tb.columns.tolist()}")
            raise ValueError(f"지정된 시산표 열 '{col}'이(가) 로드된 시산표 DataFrame에 없습니다. 헤더 행 번호나 열 매핑을 확인하세요.")

    # GL의 '차변금액', '대변금액' 열 존재 확인 (sum_col 함수 내부에서도 확인하지만, 미리 명시적 확인 가능)
    if '차변금액' not in gl.columns or '대변금액' not in gl.columns:
        raise ValueError(f"총계정원장(GL) 파일에 '차변금액' 또는 '대변금액' 열이 없습니다. GL 파일 형식을 확인해주세요. 현재 GL 컬럼: {gl.columns.tolist()}")

    gl_d_total = sum_col(gl, "차변금액")
    gl_c_total = sum_col(gl, "대변금액")

    total_rows = tb[tb[tb_account_col].astype(str).str.strip() == tb_total_label.strip()]
    if total_rows.empty:
        raise ValueError(f"시산표의 '{tb_account_col}' 열에서 '{tb_total_label}' 텍스트를 가진 합계 행을 찾지 못했습니다.")
    total_row_index = total_rows.index[0]
    print(f"[INFO] 시산표에서 '{tb_total_label}' 행 (인덱스 {total_row_index})을 찾았습니다.")

    def to_numeric_safe(val): return pd.to_numeric(str(val).replace(",", ""), errors='coerce')
    tb_d_bal_total = to_numeric_safe(tb.loc[total_row_index, d_bal_col])
    tb_c_bal_total = to_numeric_safe(tb.loc[total_row_index, c_bal_col])
    tb_d_tot_total = to_numeric_safe(tb.loc[total_row_index, d_tot_col])
    tb_c_tot_total = to_numeric_safe(tb.loc[total_row_index, c_tot_col])

    if pd.isna(tb_d_bal_total) or pd.isna(tb_c_bal_total) or pd.isna(tb_d_tot_total) or pd.isna(tb_c_tot_total):
           raise ValueError(f"시산표 합계 행(인덱스:{total_row_index})의 값을 숫자로 변환할 수 없습니다. 해당 행의 금액 열 값을 확인해주세요.")

    is_ok_gl_diff = abs(gl_d_total - gl_c_total) <= TOL
    is_ok_tb_tot_diff = abs(tb_d_tot_total - tb_c_tot_total) <= TOL
    is_ok_d_match = abs(gl_d_total - tb_d_tot_total) <= TOL
    is_ok_c_match = abs(gl_c_total - tb_c_tot_total) <= TOL
    is_overall_ok = is_ok_gl_diff and is_ok_tb_tot_diff and is_ok_d_match and is_ok_c_match
    print(f"[INFO] 전체 합계 검증 (GL 차대일치, TB 차대일치, GL-TB 차변일치, GL-TB 대변일치) 결과: {is_overall_ok}")

    # --- 계정별 상세 비교 로직 시작 ---
    print("-" * 50)
    print("DEBUG difference.py: 계정별 상세 비교 시작 - grouping_key 결정 로직 (버전 20250530_Final)")
    
    if not hasattr(gl, 'columns'): # GL이 DataFrame이 아니거나 columns 속성이 없는 경우
        raise ValueError("GL 데이터가 올바르게 DataFrame으로 로드되지 않았습니다 (컬럼 정보 없음). load_gl 함수를 확인하세요.")
    if not gl.columns.tolist(): # 컬럼 리스트가 비어있는 경우
        raise ValueError(f"GL 파일에서 열 이름을 읽어오지 못했습니다. GL 파일의 헤더 행을 확인하거나 load_gl 함수를 점검하세요. (현재 인식된 컬럼: {gl.columns.tolist()})")

    print(f"DEBUG: GL 원본 컬럼명: {gl.columns.tolist()}")
    gl_columns_stripped_map = {col.strip().upper() : col for col in gl.columns} # 대소문자 구분 없이, 공백 제거된 이름과 원본 이름 매핑
    print(f"DEBUG: GL 컬럼명 (공백제거, 대문자화된 키): {list(gl_columns_stripped_map.keys())}")

    gl_actual_code_col_name = None # GL에 실제 존재하는 계정코드 열 이름 (공백 등 포함 가능)
    possible_code_names = ['계정코드', '계정과목코드', 'ACCT_CODE', 'ACCT_CD']
    for name_candidate in possible_code_names:
        if name_candidate.upper() in gl_columns_stripped_map: # 대소문자 구분 없이, 공백 제거된 이름으로 비교
            gl_actual_code_col_name = gl_columns_stripped_map[name_candidate.upper()] # 매핑된 원본 이름 사용
            print(f"DEBUG: GL 계정코드 열로 '{gl_actual_code_col_name}' (원본이름) 찾음 (후보: '{name_candidate}')")
            break

    gl_actual_name_col_name = None # GL에 실제 존재하는 계정과목명 열 이름
    possible_name_names = ['계정과목', '계정과목명', '계정명', 'ACCT_NAME', 'ACCT_NM']
    for name_candidate in possible_name_names:
        if name_candidate.upper() in gl_columns_stripped_map:
            gl_actual_name_col_name = gl_columns_stripped_map[name_candidate.upper()]
            print(f"DEBUG: GL 계정과목명 열로 '{gl_actual_name_col_name}' (원본이름) 찾음 (후보: '{name_candidate}')")
            break

    grouping_key_for_gl = None # GL 그룹화에 사용할 실제 열 이름
    standard_key_type_for_gl = None # 'code' 또는 'name' (논리적 타입)

    if gl_actual_code_col_name:
        grouping_key_for_gl = gl_actual_code_col_name
        standard_key_type_for_gl = 'code'
    elif gl_actual_name_col_name:
        grouping_key_for_gl = gl_actual_name_col_name
        standard_key_type_for_gl = 'name'
    else:
        print("DEBUG: GL에서 적합한 계정코드 또는 계정과목 열을 찾지 못했습니다! ValueError 발생 직전.")
        raise ValueError("총계정원장(GL) 파일에서 계정 식별을 위한 '계정코드' 또는 '계정과목' 관련 열을 찾을 수 없습니다. "
                         "GL 파일의 열 이름을 확인하거나, 프로그램 코드(difference.py)의 열 이름 후보 리스트를 확인해주세요.")
    
    print(f"DEBUG: GL 그룹화에 사용될 최종 키: '{grouping_key_for_gl}' (타입: {standard_key_type_for_gl})")
    print("-" * 50)

    # GL 데이터 집계 (실제 존재하는 열 이름으로 그룹화)
    gl_summary = gl.groupby(grouping_key_for_gl).agg(
        GL_차변합계=('차변금액', 'sum'),
        GL_대변합계=('대변금액', 'sum')
    ).reset_index()
    gl_summary['GL_잔액'] = gl_summary['GL_차변합계'] - gl_summary['GL_대변합계']

    # gl_summary에 표준 '계정과목' 열 추가 (TB와 병합 용도)
    # grouping_key_for_gl이 실제 계정코드 열 이름, gl_actual_name_col_name이 실제 계정과목명 열 이름
    if standard_key_type_for_gl == 'code':
        if gl_actual_name_col_name and gl_actual_name_col_name in gl.columns: # GL에 계정과목명 열이 실제로 존재하면
            # 계정코드에 해당하는 계정과목명 매핑 (grouping_key_for_gl은 실제 코드열 이름)
            account_map_df = gl[[grouping_key_for_gl, gl_actual_name_col_name]].drop_duplicates(subset=[grouping_key_for_gl])
            gl_summary = pd.merge(gl_summary, account_map_df, on=grouping_key_for_gl, how='left')
            # 새로 추가된 계정과목명 열의 이름을 '계정과목'으로 표준화 (만약 이미 '계정과목'이 없다면)
            if gl_actual_name_col_name != '계정과목' and '계정과목' not in gl_summary.columns:
                gl_summary.rename(columns={gl_actual_name_col_name: '계정과목'}, inplace=True)
            elif '계정과목' not in gl_summary.columns and gl_actual_name_col_name == '계정과목': # 이미 이름이 '계정과목'인 경우
                pass # 이미 '계정과목' 열이 존재 (gl_actual_name_col_name 자체가 '계정과목'인 경우)
        else: # 계정코드만 있고, GL 파일에서 계정과목명 정보를 가져올 수 없을 때
            print(f"[WARNING] GL 파일에서 계정과목명 정보를 찾을 수 없어, '{grouping_key_for_gl}' (코드) 열을 '계정과목'으로 간주하여 병합을 시도합니다.")
            if grouping_key_for_gl != '계정과목' and '계정과목' not in gl_summary.columns:
                 gl_summary.rename(columns={grouping_key_for_gl: '계정과목'}, inplace=True)

    elif standard_key_type_for_gl == 'name': # 계정과목명으로 그룹화한 경우
        if grouping_key_for_gl != '계정과목' and '계정과목' not in gl_summary.columns:
            gl_summary.rename(columns={grouping_key_for_gl: '계정과목'}, inplace=True)
    
    # TB와 병합 시 사용할 GL의 키 (우선 '계정과목', 없으면 grouping_key_for_gl 사용)
    if '계정과목' in gl_summary.columns:
        merge_key_gl_for_tb = '계정과목'
    elif grouping_key_for_gl in gl_summary.columns: # '계정과목'으로 rename되지 않은 경우 (예: 코드만 있는 GL)
        merge_key_gl_for_tb = grouping_key_for_gl
    else:
        raise ValueError(f"GL 요약 데이터에서 TB와 병합할 기준열을 결정할 수 없습니다. (gl_summary 컬럼: {gl_summary.columns.tolist()})")
    
    print(f"DEBUG: GL 요약본과 TB 비교 데이터 병합 시 사용할 GL 키: '{merge_key_gl_for_tb}'")


    # --- TB 데이터 처리 ---
    tb_data = tb[tb[tb_account_col].astype(str).str.strip() != tb_total_label.strip()].copy()
    tb_data['TB_차변잔액'] = tb_data[d_bal_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_대변잔액'] = tb_data[c_bal_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_차변합계'] = tb_data[d_tot_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_대변합계'] = tb_data[c_tot_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_잔액'] = tb_data['TB_차변잔액'] - tb_data['TB_대변잔액']

    # TB 비교용 데이터 준비 (사용자가 지정한 tb_account_col을 기준으로 함)
    tb_comparison_data = tb_data[[tb_account_col, 'TB_차변잔액', 'TB_대변잔액', 'TB_차변합계', 'TB_대변합계', 'TB_잔액']].copy()
    merge_key_tb = tb_account_col # 사용자가 선택한 TB의 계정과목(또는 코드) 열 이름

    # 병합 전 키 값들의 타입 통일 및 공백 제거
    if merge_key_gl_for_tb in gl_summary.columns:
        gl_summary[merge_key_gl_for_tb] = gl_summary[merge_key_gl_for_tb].astype(str).str.strip()
    else:
        raise ValueError(f"병합 키 '{merge_key_gl_for_tb}'가 gl_summary에 없습니다. 컬럼: {gl_summary.columns.tolist()}")

    if merge_key_tb in tb_comparison_data.columns:
        tb_comparison_data[merge_key_tb] = tb_comparison_data[merge_key_tb].astype(str).str.strip()
    else:
        raise ValueError(f"병합 키 '{merge_key_tb}'가 tb_comparison_data에 없습니다. 컬럼: {tb_comparison_data.columns.tolist()}")
    
    print(f"DEBUG: 병합 시도: GL키='{merge_key_gl_for_tb}', TB키='{merge_key_tb}'")
    merged_df = pd.merge(gl_summary, tb_comparison_data, left_on=merge_key_gl_for_tb, right_on=merge_key_tb, how='outer')

    # 숫자 열 NaN 값 0으로 채우기
    numeric_cols_to_fill = ['GL_차변합계', 'GL_대변합계', 'GL_잔액', 'TB_차변잔액', 'TB_대변잔액', 'TB_차변합계', 'TB_대변합계', 'TB_잔액']
    for col in numeric_cols_to_fill:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(0)
        else: # 병합 과정에서 열이 생성 안된 경우 (이론상 발생 안해야 함)
            merged_df[col] = 0
            print(f"[WARNING] 병합 후 '{col}' 열이 없어 0으로 생성합니다.")

    # 최종 출력용 계정과목 열 이름 설정 ('계정명' 또는 '계정과목' 등으로 통일)
    # 최종적으로 사용할 계정과목 열 이름 (예: '계정과목명_표시용')
    final_display_account_col = '계정과목_결과'

    # merged_df에 어떤 계정 이름/코드 열이 있는지 확인하고 최종 표시용 열 생성
    if '계정과목' in merged_df.columns: # 표준 '계정과목' 열이 있다면 그것을 사용
        merged_df[final_display_account_col] = merged_df['계정과목']
    elif merge_key_gl_for_tb in merged_df.columns and merge_key_gl_for_tb != merge_key_tb : # GL키가 최종 계정과목으로 사용될 수 있는 경우
        merged_df[final_display_account_col] = merged_df[merge_key_gl_for_tb]
    elif merge_key_tb in merged_df.columns: # TB키가 최종 계정과목으로 사용될 수 있는 경우
        merged_df[final_display_account_col] = merged_df[merge_key_tb]
    else: # 위 모든 경우가 해당 안되면, 임시로 인덱스 사용 (문제 상황)
        print(f"[ERROR] 최종 표시용 계정과목 열을 merged_df에서 찾을 수 없습니다. 컬럼: {merged_df.columns.tolist()}")
        merged_df[final_display_account_col] = "알수없는_계정"


    # 중복되거나 불필요한 원본 키 열들 정리 (final_display_account_col과 다른 경우)
    cols_to_potentially_drop = []
    if merge_key_gl_for_tb in merged_df.columns and merge_key_gl_for_tb != final_display_account_col:
        cols_to_potentially_drop.append(merge_key_gl_for_tb)
    if merge_key_tb in merged_df.columns and merge_key_tb != final_display_account_col:
        cols_to_potentially_drop.append(merge_key_tb)
    if '계정과목' in merged_df.columns and '계정과목' != final_display_account_col: # 표준 '계정과목' 열이 최종 표시용이 아닐 경우
         cols_to_potentially_drop.append('계정과목')
    if grouping_key_for_gl in merged_df.columns and grouping_key_for_gl != final_display_account_col: # 원본 GL 그룹핑 키
         cols_to_potentially_drop.append(grouping_key_for_gl)

    merged_df.drop(columns=list(set(cols_to_potentially_drop)), inplace=True, errors='ignore')


    merged_df['차이_차변합계'] = merged_df['GL_차변합계'] - merged_df['TB_차변합계']
    merged_df['차이_대변합계'] = merged_df['GL_대변합계'] - merged_df['TB_대변합계']
    merged_df['차이_잔액'] = merged_df['GL_잔액'] - merged_df['TB_잔액']

    discrepancy_df = merged_df[
        (merged_df['차이_차변합계'].abs() > TOL) |
        (merged_df['차이_대변합계'].abs() > TOL) |
        (merged_df['차이_잔액'].abs() > TOL)
    ].copy()

    if not discrepancy_df.empty:
        print(f"[INFO] {len(discrepancy_df)}개 계정에서 차이 발견.")
        # 출력 컬럼 순서 및 이름 정리
        output_columns_order = [final_display_account_col] # 최종 표시용 계정과목 열을 가장 앞에
        
        # gl_summary에 원본 계정코드 열(grouping_key_for_gl)이 있고, 그것이 코드 타입이었다면 추가
        if standard_key_type_for_gl == 'code' and grouping_key_for_gl in discrepancy_df.columns and grouping_key_for_gl != final_display_account_col:
            output_columns_order.append(grouping_key_for_gl) # 원본 코드 열 추가
            # 만약 원본 코드 열 이름이 '계정코드'가 아니라면, '계정코드'로 별칭 부여도 고려 가능
            if grouping_key_for_gl != '계정코드' and '계정코드' not in discrepancy_df.columns:
                discrepancy_df.rename(columns={grouping_key_for_gl: '계정코드_원본'}, inplace=True) # 임시로 원본 명시
                if '계정코드_원본' not in output_columns_order: output_columns_order.insert(1, '계정코드_원본')


        common_cols = ['GL_차변합계', 'TB_차변합계', '차이_차변합계',
                       'GL_대변합계', 'TB_대변합계', '차이_대변합계',
                       'GL_잔액', 'TB_잔액', '차이_잔액']
        output_columns_order.extend(common_cols)
        
        # 실제 discrepancy_df에 있는 열들만으로 최종 순서 구성
        final_ordered_cols = [col for col in output_columns_order if col in discrepancy_df.columns]
        # 추가로 존재할 수 있는 다른 열들도 포함 (순서상 뒤로)
        # for col in discrepancy_df.columns:
        #     if col not in final_ordered_cols:
        #         final_ordered_cols.append(col)
        discrepancy_df = discrepancy_df[final_ordered_cols]
    else:
        print("[INFO] 모든 계정에서 GL과 TB 간 금액이 일치합니다 (허용 오차 내).")
        discrepancy_df = pd.DataFrame() # 빈 DataFrame 반환 일관성 유지

    # --- 최종 반환값 구성 ---
    grand_totals = {
        'gl_d': float(gl_d_total), 'gl_c': float(gl_c_total),
        'tb_bal_d': float(tb_d_bal_total), 'tb_bal_c': float(tb_c_bal_total),
        'tb_tot_d': float(tb_d_tot_total), 'tb_tot_c': float(tb_c_tot_total),
    }
    grand_diffs = {
        'Δ_GL': float(gl_d_total - gl_c_total),
        'Δ_TB_Bal': float(tb_d_bal_total - tb_c_bal_total),
        'Δ_TB_Tot': float(tb_d_tot_total - tb_c_tot_total),
        'Δ_GLd_TBtotd': float(gl_d_total - tb_d_tot_total),
        'Δ_GLc_TBtotc': float(gl_c_total - tb_c_tot_total),
    }
    return is_overall_ok, (grand_totals, grand_diffs, tb_col_map), discrepancy_df
               
def _parse_args():
    """CLI 인자를 파싱한다 (Streamlit에서는 사용되지 않음)."""
    parser = argparse.ArgumentParser(description="GL-TB 합계 비교 유틸리티")
    parser.add_argument("gl", help="총계정원장 파일 경로 (Excel 또는 CSV)")
    parser.add_argument("tb", help="시산표 파일 경로 (Excel 또는 CSV)")
    parser.add_argument(
        "--tb_header", type=int, default=0, help="시산표 헤더 행 번호 (0-based, CSV용, XLSX는 0,1로 가정)"
    )
    # CLI용 사용자 정의 컬럼/레이블 인자 (Streamlit에서는 UI로 입력받음)
    # 예시: parser.add_argument("--tb_account_col", type=str, default="계정과목", help="TB의 계정과목 열 이름")
    # 예시: parser.add_argument("--tb_total_label", type=str, default="합계", help="TB의 합계 행 레이블")
    # 예시: parser.add_argument("--d_bal_col", type=str, help="TB 차변 잔액 열")
    # ... (c_bal_col, d_tot_col, c_tot_col 등)
    return parser.parse_args()

def main():
    args = _parse_args()
    try:
        # CLI에서는 detect_cols를 사용하거나, 사용자 인자를 받아 tb_col_map 등을 구성해야 함
        # 여기서는 Streamlit에서 사용하는 verify 함수 구조를 유지하기 위해 임시값을 사용하거나
        # _parse_args에서 관련 인자를 받아와야 함.
        # 아래는 임시 예시로, 실제 CLI 사용 시에는 이 부분을 확장해야 함.
        print("[경고] CLI 모드는 예시이며, TB 컬럼 자동 감지 또는 상세 인자 지정이 필요합니다.")
        # 임시 tb_col_map (실제 CLI에서는 인자 또는 detect_cols 사용)
        # temp_tb_for_detect = load_tb(args.tb, args.tb_header)
        # d_bal, c_bal, d_tot, c_tot = detect_cols(temp_tb_for_detect)
        # cli_tb_col_map = {'bal_d': d_bal, 'bal_c': c_bal, 'tot_d': d_tot, 'tot_c': c_tot}
        # cli_tb_account_col = "계정과목" # 또는 args.tb_account_col
        # cli_tb_total_label = "합계"   # 또는 args.tb_total_label

        # 이 main 함수는 Streamlit 앱에서는 사용되지 않으므로,
        # Streamlit 앱의 `verify` 함수 시그니처와 다른 임시값을 넣는 것은 지양.
        # CLI 전용 로직으로 완전히 분리하거나, Streamlit 앱과 동일한 정보를 받도록 수정 필요.
        # 현재는 verify 함수를 직접 호출하지 않고, Streamlit 앱에서 호출되도록 함.
        # 따라서 이 main 함수는 독립 실행 시의 예시로만 남겨둠.
        print("이 스크립트는 Streamlit 앱의 일부로 사용되도록 설계되었습니다.")
        print("독립 실행을 위해서는 main() 함수의 verify 호출 부분을 CLI 인자에 맞게 수정해야 합니다.")

        # 예시: 만약 CLI에서 직접 verify를 테스트하고 싶다면,
        # ok, (totals, diffs, cols_map), diff_details_df = verify(
        #     args.gl, args.tb, args.tb_header,
        #     tb_col_map=cli_tb_col_map, # 위에서 정의한 cli_tb_col_map
        #     tb_account_col=cli_tb_account_col,
        #     tb_total_label=cli_tb_total_label
        # )
        # ... (결과 출력 로직) ...

    except FileNotFoundError as e:
        print(f"[오류] 파일을 찾을 수 없습니다: {e.filename}")
        sys.exit(1)
    except ValueError as e:
        print(f"[오류] 데이터 처리 중 문제가 발생했습니다: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[오류] 예상치 못한 에러가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
