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
           tb_account_col: str,
           tb_total_label: str
           ) -> tuple[bool, tuple, pd.DataFrame | None]:
    gl = load_gl(gl_path)
    tb = load_tb(tb_path, header_row)

    d_bal_col = tb_col_map.get('bal_d')
    c_bal_col = tb_col_map.get('bal_c')
    d_tot_col = tb_col_map.get('tot_d')
    c_tot_col = tb_col_map.get('tot_c')
    account_col_name = tb_account_col
    total_label = tb_total_label

    print(f"[INFO] 사용자가 지정한 시산표 열: 차_잔액='{d_bal_col}', 대_잔액='{c_bal_col}', 차_합계='{d_tot_col}', 대_합계='{c_tot_col}'")
    print(f"[INFO] 사용할 계정과목 열: '{account_col_name}', 합계 행 레이블: '{total_label}'")

    required_cols_map_keys = {'bal_d': d_bal_col, 'bal_c': c_bal_col, 'tot_d': d_tot_col, 'tot_c': c_tot_col}
    if None in required_cols_map_keys.values() or account_col_name is None or total_label is None:
        missing = [k for k, v in required_cols_map_keys.items() if v is None]
        if account_col_name is None: missing.append('계정과목 열')
        if total_label is None: missing.append('합계 행 레이블')
        raise ValueError(f"다음 필수 정보가 누락되었습니다: {', '.join(missing)}. Streamlit 앱에서 해당 설정을 확인하세요.")

    check_cols_exist = [d_bal_col, c_bal_col, d_tot_col, c_tot_col, account_col_name]
    for col in check_cols_exist:
        if col not in tb.columns:
            print(f"[DEBUG] 사용 가능한 시산표 컬럼: {tb.columns.tolist()}")
            raise ValueError(f"지정된 열 '{col}'이(가) 로드된 시산표 DataFrame에 없습니다. 헤더 행 번호나 열 매핑을 확인하세요.")

    gl_d_total = sum_col(gl, "차변금액")
    gl_c_total = sum_col(gl, "대변금액")

    total_rows = tb[tb[account_col_name].astype(str).str.strip() == total_label]
    if total_rows.empty:
        raise ValueError(f"시산표 '{account_col_name}' 열에서 '{total_label}' 텍스트를 가진 합계 행을 찾지 못했습니다.")
    total_row_index = total_rows.index[0]
    print(f"[INFO] 시산표에서 '{total_label}' 행 (인덱스 {total_row_index})을 찾았습니다.")

    def to_numeric_safe(val): return pd.to_numeric(str(val).replace(",", ""), errors='coerce')
    tb_d_bal_total = to_numeric_safe(tb.loc[total_row_index, d_bal_col])
    tb_c_bal_total = to_numeric_safe(tb.loc[total_row_index, c_bal_col])
    tb_d_tot_total = to_numeric_safe(tb.loc[total_row_index, d_tot_col])
    tb_c_tot_total = to_numeric_safe(tb.loc[total_row_index, c_tot_col])

    if pd.isna(tb_d_bal_total) or pd.isna(tb_c_bal_total) or pd.isna(tb_d_tot_total) or pd.isna(tb_c_tot_total):
           raise ValueError(f"시산표 합계 행(인덱스:{total_row_index})의 값을 숫자로 변환할 수 없습니다.")

    is_ok_gl_diff = abs(gl_d_total - gl_c_total) <= TOL
    is_ok_tb_tot_diff = abs(tb_d_tot_total - tb_c_tot_total) <= TOL
    is_ok_d_match = abs(gl_d_total - tb_d_tot_total) <= TOL
    is_ok_c_match = abs(gl_c_total - tb_c_tot_total) <= TOL
    is_overall_ok = is_ok_gl_diff and is_ok_tb_tot_diff and is_ok_d_match and is_ok_c_match
    print(f"[INFO] 4-Way (GL합계=TB합계) 일치 여부: {is_overall_ok}")

    print("[INFO] 계정별 상세 비교 시작...")
    grouping_key = '계정코드' if '계정코드' in gl.columns else '계정과목'
    gl_summary = gl.groupby(grouping_key).agg(GL_차변합계=('차변금액', 'sum'), GL_대변합계=('대변금액', 'sum')).reset_index()
    gl_summary['GL_잔액'] = gl_summary['GL_차변합계'] - gl_summary['GL_대변합계']
    if grouping_key == '계정코드' and '계정과목' in gl.columns:
        account_map = gl.drop_duplicates(subset=['계정코드'])[['계정코드', '계정과목']]
        gl_summary = pd.merge(gl_summary, account_map, on='계정코드', how='left')

    tb_data = tb[tb[account_col_name].astype(str).str.strip() != total_label].copy()
    tb_data['TB_차변잔액'] = tb_data[d_bal_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_대변잔액'] = tb_data[c_bal_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_차변합계'] = tb_data[d_tot_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_대변합계'] = tb_data[c_tot_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_잔액'] = tb_data['TB_차변잔액'] - tb_data['TB_대변잔액'] # 잔액 계산 시 TB의 잔액 열을 사용 또는 합계 열로 계산

    tb_comparison_data = tb_data[[account_col_name, 'TB_차변잔액', 'TB_대변잔액', 'TB_차변합계', 'TB_대변합계', 'TB_잔액']].copy()
    merge_key_tb = account_col_name

    merge_key_gl = '계정과목' if grouping_key == '계정코드' and '계정과목' in gl_summary.columns else grouping_key
    gl_summary[merge_key_gl] = gl_summary[merge_key_gl].astype(str).str.strip()
    tb_comparison_data[merge_key_tb] = tb_comparison_data[merge_key_tb].astype(str).str.strip()

    merged_df = pd.merge(gl_summary, tb_comparison_data, left_on=merge_key_gl, right_on=merge_key_tb, how='outer')
    numeric_cols_fill = ['GL_차변합계', 'GL_대변합계', 'GL_잔액', 'TB_차변잔액', 'TB_대변잔액', 'TB_차변합계', 'TB_대변합계', 'TB_잔액']
    for col in numeric_cols_fill:
        if col in merged_df.columns: merged_df[col] = merged_df[col].fillna(0)
        else: merged_df[col] = 0

    final_account_col_name = '계정과목명' # 최종 출력에 사용할 계정과목 이름 (혹은 계정코드)
    # GL에서 가져온 계정과목명을 우선 사용하고, 없으면 TB에서 가져온 것을 사용, 그래도 없으면 키 자체를 사용
    if '계정과목' in merged_df.columns: # GL에서 온 '계정과목' (grouping_key가 '계정코드'였을 경우 join됨)
        merged_df[final_account_col_name] = merged_df['계정과목']
    elif merge_key_gl in merged_df.columns and merge_key_gl != final_account_col_name : # GL의 키가 계정과목이 아니었을 경우
         merged_df[final_account_col_name] = merged_df[merge_key_gl]
    elif merge_key_tb in merged_df.columns and merge_key_tb != final_account_col_name: # TB의 키
         merged_df[final_account_col_name] = merged_df[merge_key_tb]
    else: # 둘 다 없거나 이미 final_account_col_name인 경우 (예외적)
        merged_df[final_account_col_name] = merged_df.index.astype(str) # 임시로 인덱스 사용

    # 사용된 키 컬럼들 정리 (final_account_col_name 제외)
    cols_to_drop = []
    if merge_key_gl in merged_df.columns and merge_key_gl != final_account_col_name: cols_to_drop.append(merge_key_gl)
    if merge_key_tb in merged_df.columns and merge_key_tb != final_account_col_name: cols_to_drop.append(merge_key_tb)
    if '계정과목' in merged_df.columns and '계정과목' != final_account_col_name: cols_to_drop.append('계정과목') # GL의 계정과목이 최종 이름이 아닐경우
    merged_df.drop(columns=list(set(cols_to_drop)), inplace=True, errors='ignore')


    merged_df['차이_차변합계'] = merged_df['GL_차변합계'] - merged_df['TB_차변합계']
    merged_df['차이_대변합계'] = merged_df['GL_대변합계'] - merged_df['TB_대변합계']
    merged_df['차이_잔액'] = merged_df['GL_잔액'] - merged_df['TB_잔액'] # GL 잔액과 TB 잔액 비교

    discrepancy_df = merged_df[
        (merged_df['차이_차변합계'].abs() > TOL) |
        (merged_df['차이_대변합계'].abs() > TOL) |
        (merged_df['차이_잔액'].abs() > TOL) # 잔액 차이도 확인
    ].copy()

    if not discrepancy_df.empty:
        print(f"[INFO] {len(discrepancy_df)}개 계정에서 차이 발견.")
        output_columns_list = [final_account_col_name]
        if grouping_key == '계정코드' and '계정코드' in discrepancy_df.columns: output_columns_list.append('계정코드')
        output_columns_list.extend(['GL_차변합계', 'TB_차변합계', '차이_차변합계',
                                   'GL_대변합계', 'TB_대변합계', '차이_대변합계',
                                   'GL_잔액', 'TB_잔액', '차이_잔액'])
        final_output_columns_ordered = [col for col in output_columns_list if col in discrepancy_df.columns]
        discrepancy_df = discrepancy_df[final_output_columns_ordered]
    else:
        print("[INFO] 모든 계정에서 GL과 TB 간 금액이 일치합니다.")
        discrepancy_df = pd.DataFrame() # None 대신 빈 DataFrame 반환

    # --- 7. 최종 반환값 구성 --- 
    grand_totals = {
        'gl_d': float(gl_d_total),
        'gl_c': float(gl_c_total),
        'tb_bal_d': float(tb_d_bal_total),
        'tb_bal_c': float(tb_c_bal_total),
        'tb_tot_d': float(tb_d_tot_total),
        'tb_tot_c': float(tb_c_tot_total),
    }
    grand_diffs = {
        'Δ_GL': float(gl_d_total - gl_c_total),
        'Δ_TB_Bal': float(tb_d_bal_total - tb_c_bal_total),
        'Δ_TB_Tot': float(tb_d_tot_total - tb_c_tot_total),
        'Δ_GLd_TBtotd': float(gl_d_total - tb_d_tot_total),
        'Δ_GLc_TBtotc': float(gl_c_total - tb_c_tot_total),
    }
    # detected_cols_info는 사용자 지정 컬럼맵(tb_col_map)을 그대로 사용
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
