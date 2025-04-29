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

# --- 검증 로직 함수 ---
# --- difference.py 파일 중간 ---
def verify(gl_path: str | Path, tb_path: str | Path, header_row: int) -> tuple[bool, tuple]:
    """GL과 TB를 로드하고, GL 차/대 합계 및 TB 차/대 합계/잔액을 검증한다."""
    gl = load_gl(gl_path)
    tb = load_tb(tb_path, header_row)

    # --- 시산표의 차변/대변 잔액(Bal) 및 합계(Tot) 열 이름 찾기 ---
    d_bal_col, c_bal_col, d_tot_col, c_tot_col = detect_cols(tb) # 수정된 함수 호출

    # 디버깅: 실제 감지된 컬럼과 전체 컬럼 목록 출력
    print(f"[DEBUG] 감지된 시산표 열: 차_잔액='{d_bal_col}', 대_잔액='{c_bal_col}', 차_합계='{d_tot_col}', 대_합계='{c_tot_col}'")
    print(f"[DEBUG] 시산표 전체 컬럼 목록: {tb.columns.tolist()}")

    # 필수 열(잔액, 합계)이 모두 찾아졌는지 확인
    if None in [d_bal_col, c_bal_col, d_tot_col, c_tot_col]:
        missing = []
        if d_bal_col is None: missing.append("차변 잔액")
        if c_bal_col is None: missing.append("대변 잔액")
        if d_tot_col is None: missing.append("차변 합계")
        if c_tot_col is None: missing.append("대변 합계")
        raise ValueError(
            f"시산표에서 다음 열들을 찾지 못했습니다: {', '.join(missing)}\n"
            f"  ➜ 헤더 행 번호(--tb-header={header_row} 확인), 정규식 패턴, 실제 컬럼명을 확인하세요 (위 DEBUG 목록 참고)."
        )

    # --- 총계정원장(GL) 합계 계산 ---
    gl_d = sum_col(gl, "차변금액")
    gl_c = sum_col(gl, "대변금액")

    # --- 시산표(TB)에서 최종 '합계' 행 찾고 해당 **잔액** 및 **합계** 값 추출 ---
    # !! 중요: 아래 두 변수는 실제 시산표 파일 맨 아래 내용을 보고 확인/수정해야 합니다 !!
    account_col_name = '계정과목_계정과목' # 합계 레이블이 있는 열 (실제 이름 확인 필요!)
    total_label = '합계'             # 합계 행의 실제 텍스트 (실제 텍스트 확인 필요!)

    # 계정과목 열 이름 확인 및 조정 (Fallback)
    if account_col_name not in tb.columns:
        if '계정과목' in tb.columns:
             account_col_name = '계정과목'
             print(f"[INFO] 계정과목 열 이름으로 '{account_col_name}'을 사용합니다.")
        else:
             print(f"[DEBUG] 사용 가능한 시산표 컬럼: {tb.columns.tolist()}")
             raise ValueError(f"시산표에서 합계 레이블을 찾을 열 '{account_col_name}' 또는 '계정과목'을(를) 찾을 수 없습니다.")

    # 합계 행 찾기
    total_rows = tb[tb[account_col_name].astype(str).str.strip() == total_label]
    if total_rows.empty:
        raise ValueError(f"시산표 '{account_col_name}' 열에서 '{total_label}' 텍스트를 가진 합계 행을 찾지 못했습니다.")
    total_row_index = total_rows.index[0]
    print(f"[INFO] 시산표에서 '{total_label}' 행 (인덱스 {total_row_index})을 찾았습니다.")

    # 합계 행에서 잔액(Bal)과 합계(Tot) 열의 값을 숫자로 가져오기
    tb_d_bal_val = tb.loc[total_row_index, d_bal_col]
    tb_c_bal_val = tb.loc[total_row_index, c_bal_col]
    tb_d_tot_val = tb.loc[total_row_index, d_tot_col]
    tb_c_tot_val = tb.loc[total_row_index, c_tot_col]

    # 숫자 변환 함수
    def to_numeric_safe(val):
        return pd.to_numeric(str(val).replace(",", ""), errors='coerce')

    tb_d_bal = to_numeric_safe(tb_d_bal_val) # TB 차변 잔액 합계
    tb_c_bal = to_numeric_safe(tb_c_bal_val) # TB 대변 잔액 합계
    tb_d_tot = to_numeric_safe(tb_d_tot_val) # TB 차변 합계
    tb_c_tot = to_numeric_safe(tb_c_tot_val) # TB 대변 합계

    # 숫자 변환 실패 시 오류
    if pd.isna(tb_d_bal) or pd.isna(tb_c_bal) or pd.isna(tb_d_tot) or pd.isna(tb_c_tot):
         raise ValueError(f"시산표 합계 행(인덱스:{total_row_index})의 값을 숫자로 변환할 수 없습니다.")

    # --- 검증 수행 ---
    # 1. GL 차/대 합계 일치 여부
    is_ok_gl_diff = abs(gl_d - gl_c) <= TOL
    # 2. TB 차/대 잔액 합계 일치 여부
    is_ok_tb_bal_diff = abs(tb_d_bal - tb_c_bal) <= TOL
    # 3. (요청사항) GL 차/대 합계와 TB 차/대 합계 4-Way 일치 여부
    is_ok_4way_match = (
        is_ok_gl_diff and # GL 차대 맞고
        (abs(tb_d_tot - tb_c_tot) <= TOL) and # TB 합계 차대 맞고
        (abs(gl_d - tb_d_tot) <= TOL) and # GL차 = TB 합계차 맞고
        (abs(gl_c - tb_c_tot) <= TOL)   # GL대 = TB 합계대 맞고
    )

    # 최종 성공 여부 (4-Way 기준)
    is_ok = is_ok_4way_match

    print(f"[INFO] GL 차/대 합계 차이: {abs(gl_d - gl_c):,.0f} (일치: {is_ok_gl_diff})")
    print(f"[INFO] TB 차/대 잔액 합계 차이: {abs(tb_d_bal - tb_c_bal):,.0f} (일치: {is_ok_tb_bal_diff})")
    print(f"[INFO] 4-Way (GL합계=TB합계) 일치 여부: {is_ok_4way_match}")

    # 결과 튜플 반환 (모든 계산값 포함)
    diff_summary = {
        "Δ_GL": abs(gl_d - gl_c), "Δ_TB_Bal": abs(tb_d_bal - tb_c_bal),
        "Δ_TB_Tot": abs(tb_d_tot - tb_c_tot), "Δ_GLd_TBtotd": abs(gl_d - tb_d_tot),
        "Δ_GLc_TBtotc": abs(gl_c - tb_c_tot)
    }
    tb_values = {"bal_d": tb_d_bal, "bal_c": tb_c_bal, "tot_d": tb_d_tot, "tot_c": tb_c_tot}
    detected_cols = {"bal_d": d_bal_col, "bal_c": c_bal_col, "tot_d": d_tot_col, "tot_c": c_tot_col}

    return is_ok, (gl_d, gl_c, tb_values, diff_summary, detected_cols)


# --- CLI 파서 ---
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GL vs TB 합계 비교 자동화"
    )
    parser.add_argument("gl", help="총계정원장 파일 경로 (xlsx/csv)")
    parser.add_argument("tb", help="시산표 파일 경로 (xlsx/csv)")
    # 기본 헤더 행 인덱스를 3으로 설정 (엑셀 4행에 해당)
    parser.add_argument("--tb-header", type=int, default=3,
                       help="시산표의 첫째 헤더(차/대) 행 번호(0-based). 기본 3 → 엑셀 4행")
    # 필요시 다른 인자 추가 (예: --tolerance 등)
    return parser.parse_args()


# --- 메인 실행 함수 ---
def main():
    args = _parse_args()

    try:
        # verify 함수 호출 (반환값 구조 변경됨)
        ok, (gl_d, gl_c, tb_vals, diff, cols) = verify(
            args.gl, args.tb, args.tb_header
        )

        # 결과 출력 (수정)
        print("\n──────── 최종 결과 ────────")
        print(f"감지된 시산표 열 -> 잔액(차:'{cols['bal_d']}', 대:'{cols['bal_c']}') | 합계(차:'{cols['tot_d']}', 대:'{cols['tot_c']}')")
        print("-" * 60)
        print(f"GL 총차변          : {gl_d:15,.0f}  |  GL 총대변          : {gl_c:15,.0f}  |  GL 차액(Δ) : {diff['Δ_GL']:,.0f}")
        print(f"TB 차변 합계       : {tb_vals['tot_d']:15,.0f}  |  TB 대변 합계       : {tb_vals['tot_c']:15,.0f}  |  TB 합계 차액(Δ) : {diff['Δ_TB_Tot']:,.0f}")
        print(f"TB 차변 잔액 합계  : {tb_vals['bal_d']:15,.0f}  |  TB 대변 잔액 합계  : {tb_vals['bal_c']:15,.0f}  |  TB 잔액 차액(Δ) : {diff['Δ_TB_Bal']:,.0f}")
        print("-" * 60)
        print(f"GL 차변 vs TB 합계 차변 차이 : {diff['Δ_GLd_TBtotd']:,.0f}")
        print(f"GL 대변 vs TB 합계 대변 차이 : {diff['Δ_GLc_TBtotc']:,.0f}")

        # 최종 결과 메시지 (4-Way 기준)
        if ok:
            print("\n✅ 검증 성공: GL 차/대 합계와 TB 차/대 합계가 허용 오차 내에서 모두 일치합니다.")
            sys.exit(0) # 성공 시 종료 코드 0
        else:
            # 실패 원인 추가 설명
            if not (diff['Δ_GL'] <= TOL): msg = "GL의 차/대변 합계가 불일치합니다."
            elif not (diff['Δ_TB_Tot'] <= TOL): msg = "TB의 차/대변 합계가 불일치합니다."
            elif not (diff['Δ_GLd_TBtotd'] <= TOL): msg = "GL 차변 합계와 TB 차변 합계가 불일치합니다."
            elif not (diff['Δ_GLc_TBtotc'] <= TOL): msg = "GL 대변 합계와 TB 대변 합계가 불일치합니다."
            else: msg = "알 수 없는 불일치 발생." # 이 경우는 거의 없음
            print(f"\n❌ 검증 실패: {msg}")
            sys.exit(1) # 실패 시 종료 코드 1

    except FileNotFoundError as e:
        print(f"[오류] 파일을 찾을 수 없습니다: {e.filename}")
        sys.exit(1)
    except ValueError as e:
        print(f"[오류] 데이터 처리 중 문제가 발생했습니다: {e}")
        sys.exit(1)
    except Exception as e:
        # 예상치 못한 다른 모든 오류 처리
        print(f"[오류] 예상치 못한 에러가 발생했습니다: {e}")
        import traceback
        traceback.print_exc() # 상세 에러 스택 출력
        sys.exit(1)

# --- 스크립트 실행 진입점 ---
if __name__ == "__main__":
    main()