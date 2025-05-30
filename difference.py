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

# import numpy as np # numpy는 현재 코드에서 사용되지 않음
import pandas as pd

# --- 전역 설정 ---
TOL = 1  # 허용 오차(원) - 필요에 따라 조정

# --- 열 이름 감지용 정규식 패턴 ---
# '차변', '차', 'dr' + '합계', '합', '액', 'total', 'amount' 등을 포함하는 열 찾기
# '잔액' 열을 찾는 패턴 (단어 사이 여러 공백 허용)
_DEBIT_PAT_BAL  = re.compile(r"(차\s*변.*잔\s*액|\bdr\b.*bal)", re.I)
_CREDIT_PAT_BAL = re.compile(r"(대\s*변.*잔\s*액|\bcr\b.*bal)", re.I)
# '합계' 열을 찾는 패턴 (단어 사이 여러 공백 허용)
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
    # 쉼표 등을 제거하고 숫자로 변환 시도
    s = df[col].astype(str).str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0).sum()

# --- 데이터 로딩 함수 ---
def load_gl(path_or_buffer: str | Path | io.BytesIO | io.StringIO) -> pd.DataFrame:
    """총계정원장 파일을 로드한다 (경로 또는 파일 객체)."""
    is_path = isinstance(path_or_buffer, (str, Path))
    filename = Path(path_or_buffer).name if is_path else getattr(path_or_buffer, 'name', 'GL file')

    try:
        # 파일 확장자 결정 (파일 객체는 이름에서 추론)
        suffix = Path(filename).suffix.lower() if filename else '.xlsx' # 이름 없으면 xlsx 가정

        dtype_spec = { "전표번호": str, "계정코드": str, "계정과목": str,
                       "거래처코드": str, "입력사원": str }

        if suffix == ".xlsx":
            print(f"[INFO] 총계정원장(GL) 로딩 (XLSX): {filename}")
            df = pd.read_excel(path_or_buffer, dtype=dtype_spec)
        elif suffix == ".csv":
            print(f"[INFO] 총계정원장(GL) 로딩 (CSV): {filename}")
            try:
                # BytesIO/StringIO의 경우 seek(0) 필요할 수 있음
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
        # Streamlit 환경에서는 sys.exit 대신 에러를 다시 발생시키는 것이 나을 수 있음
        raise

    # 날짜 및 금액 열 처리 (이전과 동일)
    if "전표일자" in df.columns:
         df["전표일자"] = pd.to_datetime(df["전표일자"], errors="coerce")
    else: print("[경고] GL 파일에 '전표일자' 열이 없습니다.")
    for col in ("차변금액", "대변금액"):
        if col in df.columns:
             s = df[col].astype(str).str.replace(",", "", regex=False)
             df[col] = pd.to_numeric(s, errors="coerce").fillna(0)
        else:
             print(f"[경고] GL 파일에 '{col}' 열이 없습니다. 해당 합계는 0으로 처리됩니다.")
             df[col] = 0
    return df

def load_tb(path_or_buffer: str | Path | io.BytesIO | io.StringIO, header_row: int, filename: str | None = None) -> pd.DataFrame:
    """시산표 파일을 로드한다 (경로 또는 파일 객체). XLSX는 2-level 헤더 처리."""
    is_path = isinstance(path_or_buffer, (str, Path))
    if filename is None: # 파일 이름이 주어지지 않으면 추론
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

            # 헤더 평탄화 (기존 로직 동일)
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

# --- 검증 로직 함수 (사용자 지정 열 이름/레이블 사용하도록 수정) ---
def verify(gl_path: str | Path | io.BytesIO | io.StringIO,
           tb_path: str | Path | io.BytesIO | io.StringIO,
           header_row: int,
           # Streamlit에서 전달받을 사용자 지정 정보 추가
           tb_col_map: dict[str, str], # {'bal_d': '실제차변잔액열', 'bal_c': '실제대변잔액열', ...}
           tb_account_col: str,        # 합계 레이블 찾을 실제 계정과목 열 이름
           tb_total_label: str         # 합계 행의 실제 텍스트 레이블
           ) -> tuple[bool, tuple, pd.DataFrame | None]:
    """GL과 TB를 로드하고, 사용자가 지정한 열과 레이블을 사용하여 검증한다."""
    # 1. 데이터 로드
    gl = load_gl(gl_path)
    tb = load_tb(tb_path, header_row) # load_tb는 헤더행만 읽어옴

    # 2. 시산표 열 이름 할당 (detect_cols 대신 사용자 매핑 사용)
    d_bal_col = tb_col_map.get('bal_d')
    c_bal_col = tb_col_map.get('bal_c')
    d_tot_col = tb_col_map.get('tot_d')
    c_tot_col = tb_col_map.get('tot_c')
    account_col_name = tb_account_col # 사용자가 지정한 계정과목 열 이름
    total_label = tb_total_label     # 사용자가 지정한 합계 행 레이블

    print(f"[INFO] 사용자가 지정한 시산표 열: 차_잔액='{d_bal_col}', 대_잔액='{c_bal_col}', 차_합계='{d_tot_col}', 대_합계='{c_tot_col}'")
    print(f"[INFO] 사용할 계정과목 열: '{account_col_name}', 합계 행 레이블: '{total_label}'")

    # 필수 열 이름이 제대로 전달되었는지 확인
    required_cols = {'bal_d': d_bal_col, 'bal_c': c_bal_col, 'tot_d': d_tot_col, 'tot_c': c_tot_col}
    if None in required_cols.values() or account_col_name is None or total_label is None:
        missing = [k for k, v in required_cols.items() if v is None]
        if account_col_name is None: missing.append('계정과목 열')
        if total_label is None: missing.append('합계 행 레이블')
        raise ValueError(f"다음 필수 정보가 누락되었습니다: {', '.join(missing)}. Streamlit 앱에서 해당 설정을 확인하세요.")

    # 전달받은 열 이름들이 실제 DataFrame에 존재하는지 확인
    check_cols = [d_bal_col, c_bal_col, d_tot_col, c_tot_col, account_col_name]
    for col in check_cols:
        if col not in tb.columns:
             print(f"[DEBUG] 사용 가능한 시산표 컬럼: {tb.columns.tolist()}")
             raise ValueError(f"지정된 열 '{col}'이(가) 로드된 시산표 DataFrame에 없습니다. 헤더 행 번호나 열 매핑을 확인하세요.")

    # --- 3. 총계정원장(GL) 합계 계산 --- (이하 로직은 이전과 거의 동일, 변수명만 사용)
    gl_d_total = sum_col(gl, "차변금액")
    gl_c_total = sum_col(gl, "대변금액")

    # --- 4. 시산표(TB) 최종 합계 행 찾고 값 추출 ---
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

    # --- 5. 전체 합계 검증 ---
    # ... (is_overall_ok 계산 및 print 로직은 이전과 동일) ...
    is_ok_gl_diff = abs(gl_d_total - gl_c_total) <= TOL
    is_ok_tb_tot_diff = abs(tb_d_tot_total - tb_c_tot_total) <= TOL
    is_ok_d_match = abs(gl_d_total - tb_d_tot_total) <= TOL
    is_ok_c_match = abs(gl_c_total - tb_c_tot_total) <= TOL
    is_overall_ok = is_ok_gl_diff and is_ok_tb_tot_diff and is_ok_d_match and is_ok_c_match
    print(f"[INFO] 4-Way (GL합계=TB합계) 일치 여부: {is_overall_ok}")

    # --- 6. 계정별 상세 비교 로직 ---
    # ... (이전과 동일, 단 account_col_name, d_bal_col 등을 사용) ...
    print("[INFO] 계정별 상세 비교 시작...")
    grouping_key = '계정코드' if '계정코드' in gl.columns else '계정과목'
    # ... (GL 집계 로직 동일) ...
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
    tb_data['TB_잔액'] = tb_data['TB_차변잔액'] - tb_data['TB_대변잔액']

    tb_comparison_data = tb_data[[account_col_name, 'TB_차변잔액', 'TB_대변잔액', 'TB_차변합계', 'TB_대변합계', 'TB_잔액']].copy()
    merge_key_tb = account_col_name # 사용자가 지정한 계정과목 열 이름 사용

    merge_key_gl = '계정과목' if grouping_key == '계정코드' and '계정과목' in gl_summary.columns else grouping_key
    gl_summary[merge_key_gl] = gl_summary[merge_key_gl].astype(str).str.strip()
    tb_comparison_data[merge_key_tb] = tb_comparison_data[merge_key_tb].astype(str).str.strip()

    merged_df = pd.merge(gl_summary, tb_comparison_data, left_on=merge_key_gl, right_on=merge_key_tb, how='outer')
    # ... (NaN 채우기, 컬럼 정리, 차이 계산, discrepancy_df 필터링 로직은 이전과 동일) ...
    numeric_cols = ['GL_차변합계', 'GL_대변합계', 'GL_잔액', 'TB_차변잔액', 'TB_대변잔액', 'TB_차변합계', 'TB_대변합계', 'TB_잔액']
    for col in numeric_cols:
        if col in merged_df.columns: merged_df[col] = merged_df[col].fillna(0)
        else: merged_df[col] = 0
    final_account_col = '계정과목'
    if merge_key_gl in merged_df.columns and merge_key_gl != final_account_col: merged_df.rename(columns={merge_key_gl: final_account_col}, inplace=True)
    if merge_key_tb in merged_df.columns and merge_key_tb != final_account_col: merged_df.rename(columns={merge_key_tb: final_account_col}, inplace=True)
    if merge_key_gl != final_account_col and merge_key_tb != final_account_col and merge_key_tb != merge_key_gl and merge_key_tb in merged_df.columns : merged_df.drop(columns=[merge_key_tb], inplace=True, errors='ignore')

    merged_df['차이_차변합계'] = merged_df['GL_차변합계'] - merged_df['TB_차변합계']
    merged_df['차이_대변합계'] = merged_df['GL_대변합계'] - merged_df['TB_대변합계']
    merged_df['차이_잔액'] = merged_df['GL_잔액'] - merged_df['TB_잔액']
    discrepancy_df = merged_df[(merged_df['차이_차변합계'].abs() > TOL) | (merged_df['차이_대변합계'].abs() > TOL) | (merged_df['차이_잔액'].abs() > TOL)].copy()
    if not discrepancy_df.empty:
        print(f"[INFO] {len(discrepancy_df)}개 계정에서 차이 발견.")
        output_columns = [final_account_col]
        if grouping_key == '계정코드' and '계정코드' in discrepancy_df.columns: output_columns.append('계정코드')
        output_columns.extend(['GL_차변합계', 'TB_차변합계', '차이_차변합계', 'GL_대변합계', 'TB_대변합계', '차이_대변합계', 'GL_잔액', 'TB_잔액', '차이_잔액'])
        final_output_columns = [col for col in output_columns if col in discrepancy_df.columns]
        discrepancy_df = discrepancy_df[final_output_columns]
    else: print("[INFO] 모든 계정에서 GL과 TB 간 금액이 일치합니다."); discrepancy_df = None

    # --- 7. 최종 반환값 구성 --- (이전과 동일)
    grand_totals = { ... } # 내용 동일
    grand_diffs = { ... } # 내용 동일
    detected_cols_info = {"bal_d": d_bal_col, "bal_c": c_bal_col, "tot_d": d_tot_col, "tot_c": c_tot_col} # 이건 이제 사용자 지정 값이지만, 구조 유지를 위해 전달
    return is_overall_ok, (grand_totals, grand_diffs, detected_cols_info), discrepancy_df

# --- 메인 실행 함수 (수정) ---
def main():
    args = _parse_args()

    try:
        # verify 함수 호출 (반환값 구조 변경됨)
        ok, (totals, diffs, cols), diff_details_df = verify(
            args.gl, args.tb, args.tb_header
        )

        # 결과 출력 (수정)
        print("\n──────── 전체 합계 비교 결과 ────────")
        print(f"감지된 시산표 열 -> 잔액(차:'{cols['bal_d']}', 대:'{cols['bal_c']}') | 합계(차:'{cols['tot_d']}', 대:'{cols['tot_c']}')")
        print("-" * 70)
        print(f"GL 총차변          : {totals['gl_d']:15,.0f} | GL 총대변          : {totals['gl_c']:15,.0f} | GL 차액(Δ) : {diffs['Δ_GL']:,.0f}")
        print(f"TB 차변 합계       : {totals['tb_tot_d']:15,.0f} | TB 대변 합계       : {totals['tb_tot_c']:15,.0f} | TB 합계 차액(Δ) : {diffs['Δ_TB_Tot']:,.0f}")
        print(f"TB 차변 잔액 합계  : {totals['tb_bal_d']:15,.0f} | TB 대변 잔액 합계  : {totals['tb_bal_c']:15,.0f} | TB 잔액 차액(Δ) : {diffs['Δ_TB_Bal']:,.0f}")
        print("-" * 70)
        print(f"GL 차변 vs TB 합계 차변 차이 : {diffs['Δ_GLd_TBtotd']:,.0f}")
        print(f"GL 대변 vs TB 합계 대변 차이 : {diffs['Δ_GLc_TBtotc']:,.0f}")

        # 최종 결과 메시지 (4-Way 기준)
        if ok:
            print("\n✅ 전체 합계 검증 성공: GL 차/대 합계와 TB 차/대 합계가 허용 오차 내에서 모두 일치합니다.")
        else:
            # 실패 원인 추가 설명
            if not (diffs['Δ_GL'] <= TOL): msg = "GL의 차/대변 합계가 불일치합니다."
            elif not (diffs['Δ_TB_Tot'] <= TOL): msg = "TB의 차/대변 합계가 불일치합니다."
            elif not (diffs['Δ_GLd_TBtotd'] <= TOL): msg = "GL 차변 합계와 TB 차변 합계가 불일치합니다."
            elif not (diffs['Δ_GLc_TBtotc'] <= TOL): msg = "GL 대변 합계와 TB 대변 합계가 불일치합니다."
            else: msg = "알 수 없는 불일치 발생."
            print(f"\n❌ 전체 합계 검증 실패: {msg}")

        # 계정별 차이 내역 출력
        if diff_details_df is not None and not diff_details_df.empty:
            print("\n──────── 계정별 상세 차이 내역 ────────")
            # 숫자를 보기 좋게 포맷팅 (옵션)
            pd.options.display.float_format = '{:,.0f}'.format
            print(diff_details_df.to_string(index=False)) # 인덱스 없이 전체 출력
        else:
            print("\n✅ 모든 계정에서 GL과 TB 간 금액이 일치합니다.")

        # 최종 종료 코드
        sys.exit(0 if ok else 1)

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

# --- 스크립트 실행 진입점 ---
if __name__ == "__main__":
    main() 