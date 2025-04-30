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

# --- 검증 로직 함수 (계정별 비교 추가) ---
def verify(gl_path: str | Path | io.BytesIO | io.StringIO,
           tb_path: str | Path | io.BytesIO | io.StringIO,
           header_row: int) -> tuple[bool, tuple, pd.DataFrame | None]: # 반환 타입 변경
    """
    GL과 TB를 로드하고, 전체 합계 및 계정별 상세 차이를 검증한다.
    반환값: (전체 합계 일치 여부, 전체 합계 정보 튜플, 계정별 차이 DataFrame)
    """
    # 1. 데이터 로드
    gl = load_gl(gl_path)
    tb = load_tb(tb_path, header_row)

    # 2. 시산표 열 감지
    d_bal_col, c_bal_col, d_tot_col, c_tot_col = detect_cols(tb)
    print(f"[DEBUG] 감지된 시산표 열: 차_잔액='{d_bal_col}', 대_잔액='{c_bal_col}', 차_합계='{d_tot_col}', 대_합계='{c_tot_col}'")
    print(f"[DEBUG] 시산표 전체 컬럼 목록: {tb.columns.tolist()}")
    if None in [d_bal_col, c_bal_col, d_tot_col, c_tot_col]:
        # ... (기존 오류 처리 로직) ...
        missing = [col for col, name in zip([d_bal_col, c_bal_col, d_tot_col, c_tot_col], ["차변 잔액", "대변 잔액", "차변 합계", "대변 합계"]) if col is None]
        raise ValueError(f"시산표에서 다음 열들을 찾지 못했습니다: {', '.join(missing)}\n ...")

    # 3. 전체 합계 계산 (기존 로직 활용)
    gl_d_total = sum_col(gl, "차변금액")
    gl_c_total = sum_col(gl, "대변금액")

    # 시산표(TB)의 전체 합계 행 찾기 및 값 추출 (기존 로직 활용)
    account_col_name = '계정과목_계정과목' # 기본값
    total_label = '합계'
    if account_col_name not in tb.columns and '계정과목' in tb.columns:
        account_col_name = '계정과목'
        print(f"[INFO] 계정과목 열 이름으로 '{account_col_name}'을 사용합니다.")
    elif account_col_name not in tb.columns:
         raise ValueError(f"시산표에서 합계 레이블을 찾을 열 '{account_col_name}' 또는 '계정과목'을(를) 찾을 수 없습니다.")

    total_rows = tb[tb[account_col_name].astype(str).str.strip() == total_label]
    if total_rows.empty: raise ValueError(f"시산표 '{account_col_name}' 열에서 '{total_label}' 행을 찾지 못했습니다.")
    total_row_index = total_rows.index[0]

    def to_numeric_safe(val): return pd.to_numeric(str(val).replace(",", ""), errors='coerce')

    tb_d_bal_total = to_numeric_safe(tb.loc[total_row_index, d_bal_col])
    tb_c_bal_total = to_numeric_safe(tb.loc[total_row_index, c_bal_col])
    tb_d_tot_total = to_numeric_safe(tb.loc[total_row_index, d_tot_col])
    tb_c_tot_total = to_numeric_safe(tb.loc[total_row_index, c_tot_col])

    if pd.isna(tb_d_bal_total) or pd.isna(tb_c_bal_total) or pd.isna(tb_d_tot_total) or pd.isna(tb_c_tot_total):
         raise ValueError(f"시산표 합계 행(인덱스:{total_row_index})의 값을 숫자로 변환할 수 없습니다.")

    # 4. 전체 합계 검증 (4-Way Match)
    is_ok_gl_diff = abs(gl_d_total - gl_c_total) <= TOL
    is_ok_tb_tot_diff = abs(tb_d_tot_total - tb_c_tot_total) <= TOL
    is_ok_d_match = abs(gl_d_total - tb_d_tot_total) <= TOL
    is_ok_c_match = abs(gl_c_total - tb_c_tot_total) <= TOL
    is_overall_ok = is_ok_gl_diff and is_ok_tb_tot_diff and is_ok_d_match and is_ok_c_match
    print(f"[INFO] 4-Way (GL합계=TB합계) 일치 여부: {is_overall_ok}")


    # --- 계정별 상세 비교 로직 추가 ---
    print("[INFO] 계정별 상세 비교 시작...")

    # 5. GL 데이터 계정별 집계
    #    '계정코드'가 있다면 사용하는 것이 더 정확함. 없다면 '계정과목' 사용.
    grouping_key = '계정코드' if '계정코드' in gl.columns else '계정과목'
    print(f"[INFO] GL 집계 기준 컬럼: '{grouping_key}'")
    gl_summary = gl.groupby(grouping_key).agg(
        GL_차변합계=('차변금액', 'sum'),
        GL_대변합계=('대변금액', 'sum')
    ).reset_index()
    gl_summary['GL_잔액'] = gl_summary['GL_차변합계'] - gl_summary['GL_대변합계']

    # 만약 grouping_key가 '계정코드'였고, 계정과목 정보도 필요하다면 추가
    if grouping_key == '계정코드' and '계정과목' in gl.columns:
         account_map = gl.drop_duplicates(subset=['계정코드'])[['계정코드', '계정과목']]
         gl_summary = pd.merge(gl_summary, account_map, on='계정코드', how='left')


    # 6. TB 데이터 준비 (합계 행 제외, 숫자 변환, 잔액 계산)
    tb_data = tb[tb[account_col_name].astype(str).str.strip() != total_label].copy()
    tb_data['TB_차변잔액'] = tb_data[d_bal_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_대변잔액'] = tb_data[c_bal_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_차변합계'] = tb_data[d_tot_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_대변합계'] = tb_data[c_tot_col].apply(to_numeric_safe).fillna(0)
    tb_data['TB_잔액'] = tb_data['TB_차변잔액'] - tb_data['TB_대변잔액'] # 잔액 기준으로 계산

    # TB 데이터에서 비교에 사용할 컬럼 선택 및 이름 변경
    tb_comparison_data = tb_data[[account_col_name, 'TB_차변잔액', 'TB_대변잔액', 'TB_차변합계', 'TB_대변합계', 'TB_잔액']].copy()
    # account_col_name이 '계정과목_계정과목' 이었다면 '계정과목'으로 단순화 시도
    merge_key_tb = '계정과목' if account_col_name.startswith('계정과목') else account_col_name
    tb_comparison_data.rename(columns={account_col_name: merge_key_tb}, inplace=True)


    # 7. GL과 TB 데이터 병합 (계정과목 기준)
    #    병합 기준 키 결정 (GL에서 사용한 키와 TB에서 정리한 키)
    merge_key_gl = '계정과목' if grouping_key == '계정코드' and '계정과목' in gl_summary.columns else grouping_key

    # 계정과목 앞뒤 공백 제거 후 병합
    gl_summary[merge_key_gl] = gl_summary[merge_key_gl].astype(str).str.strip()
    tb_comparison_data[merge_key_tb] = tb_comparison_data[merge_key_tb].astype(str).str.strip()

    print(f"[INFO] '{merge_key_gl}' 키를 사용하여 GL 요약과 TB 데이터 병합 시도...")
    merged_df = pd.merge(gl_summary, tb_comparison_data, left_on=merge_key_gl, right_on=merge_key_tb, how='outer')

    # 병합 후 NaN값(한쪽에만 있는 계정)은 0으로 채움
    numeric_cols = ['GL_차변합계', 'GL_대변합계', 'GL_잔액', 'TB_차변잔액', 'TB_대변잔액', 'TB_차변합계', 'TB_대변합계', 'TB_잔액']
    for col in numeric_cols:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(0)
        else:
             # 만약 GL이나 TB에 해당 컬럼이 아예 없었다면 생성하고 0으로 채움
             merged_df[col] = 0
             print(f"[경고] 병합 과정 중 '{col}' 컬럼이 없어 0으로 생성되었습니다.")

    # 병합 키 컬럼 정리 (GL 기준 사용)
    if merge_key_gl != merge_key_tb and merge_key_tb in merged_df.columns:
        merged_df.drop(columns=[merge_key_tb], inplace=True)
    merged_df.rename(columns={merge_key_gl: '계정과목'}, inplace=True) # 최종 컬럼명 '계정과목'으로 통일

    # 8. 계정별 차이 계산
    merged_df['차이_차변합계'] = merged_df['GL_차변합계'] - merged_df['TB_차변합계']
    merged_df['차이_대변합계'] = merged_df['GL_대변합계'] - merged_df['TB_대변합계']
    merged_df['차이_잔액'] = merged_df['GL_잔액'] - merged_df['TB_잔액']

    # 9. 차이가 있는 계정만 필터링
    discrepancy_df = merged_df[
        (merged_df['차이_차변합계'].abs() > TOL) |
        (merged_df['차이_대변합계'].abs() > TOL) |
        (merged_df['차이_잔액'].abs() > TOL)
    ].copy()

    # 보기 좋게 컬럼 순서 정리 및 불필요 컬럼 제거 (선택)
    if not discrepancy_df.empty:
        print(f"[INFO] {len(discrepancy_df)}개 계정에서 차이 발견.")
        output_columns = [
            '계정과목', 'GL_차변합계', 'TB_차변합계', '차이_차변합계',
            'GL_대변합계', 'TB_대변합계', '차이_대변합계',
            'GL_잔액', 'TB_잔액', '차이_잔액'
        ]
        # GL 집계 기준이 계정코드였으면 코드 컬럼 추가
        if grouping_key == '계정코드':
            output_columns.insert(1, '계정코드')

        # 실제 존재하는 컬럼만 선택
        final_output_columns = [col for col in output_columns if col in discrepancy_df.columns]
        discrepancy_df = discrepancy_df[final_output_columns]
    else:
        print("[INFO] 모든 계정에서 GL과 TB 간 금액이 일치합니다.")
        discrepancy_df = None # 차이가 없으면 None 반환


    # --- 최종 반환값 구성 ---
    # 전체 합계 정보
    grand_totals = {
        "gl_d": gl_d_total, "gl_c": gl_c_total,
        "tb_bal_d": tb_d_bal_total, "tb_bal_c": tb_c_bal_total,
        "tb_tot_d": tb_d_tot_total, "tb_tot_c": tb_c_tot_total
    }
    # 전체 합계 차이 정보
    grand_diffs = {
        "Δ_GL": abs(gl_d_total - gl_c_total),
        "Δ_TB_Bal": abs(tb_d_bal_total - tb_c_bal_total),
        "Δ_TB_Tot": abs(tb_d_tot_total - tb_c_tot_total),
        "Δ_GLd_TBtotd": abs(gl_d_total - tb_d_tot_total),
        "Δ_GLc_TBtotc": abs(gl_c_total - tb_c_tot_total)
    }
    # 감지된 컬럼 정보
    detected_cols_info = {"bal_d": d_bal_col, "bal_c": c_bal_col, "tot_d": d_tot_col, "tot_c": c_tot_col}

    # 반환: (전체 합계 4way 일치 여부, 전체 합계 값 딕셔너리, 전체 합계 차이 딕셔너리, 감지된 컬럼 딕셔너리, 계정별 차이 DataFrame | None)
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