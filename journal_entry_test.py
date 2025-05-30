#!/usr/bin/env python
"""
Journal Entry Test Automation Script
===================================

본 스크립트는 **총계정원장(General Ledger)** 엑셀 파일을 입력받아 감사인이 자주 수행하는
8가지 Journal-Entry Test(분개 테스트)를 자동으로 실행하고, 시나리오별 결과를
**하나의 엑셀 파일**(시트 분리)로 저장한다.
"""

from __future__ import annotations
import argparse
import datetime as dt
from pathlib import Path
import sys
import re
import io # 추가: io.BytesIO, io.StringIO 타입 힌트 사용을 위해

import numpy as np
import pandas as pd

######################################################################
# 1. CLI 파서 (Streamlit에서는 사용되지 않음)
######################################################################
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="General‑Ledger Journal Entry Test Automation")
    parser.add_argument("--input_gl", required=True, help="총계정원장 Excel 또는 CSV 파일 경로")
    parser.add_argument("--output", default="journal_entry_test_results.xlsx", help="분석 결과를 저장할 Excel 파일 경로")
    parser.add_argument("--keywords", type=str, default="", help="계정과목 키워드(쉼표로 구분) — 시나리오1")
    parser.add_argument("--account_codes", type=str, default="", help="관심 계정코드(쉼표로 구분) — 시나리오2")
    parser.add_argument("--freq_account", type=int, default=None, help="희귀 계정 기준 사용 횟수(미만) — 시나리오4")
    parser.add_argument("--freq_user", type=int, default=None, help="희귀 입력자 기준 전표 수(미만) — 시나리오5")
    parser.add_argument("--start_date", type=str, default=None, help="시나리오4/5 기간 시작(YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default=None, help="시나리오4/5 기간 종료(YYYY-MM-DD)")
    parser.add_argument("--zero_digits", type=int, default=None, help="끝자리 0 개수 기준 — 시나리오8")
    parser.add_argument("--repeat_len", type=int, default=None, help="끝자리 반복 숫자 길이 — 시나리오7")
    parser.add_argument("--holidays", type=str, default=None, help="공휴일 CSV/TXT/XLSX 파일 경로")
    return parser.parse_args()

######################################################################
# 2. 데이터 적재 및 공통 전처리 (Streamlit 앱에서 호출될 함수)
######################################################################
def load_gl(path_or_buffer: str | Path | io.BytesIO | io.StringIO) -> pd.DataFrame: # 함수 이름 변경 및 타입 힌트 수정
    """총계정원장 파일을 DataFrame으로 읽고, 기본 전처리를 수행한다 (Excel 및 CSV 지원)."""
    is_path = isinstance(path_or_buffer, (str, Path))
    filename = Path(path_or_buffer).name if is_path else getattr(path_or_buffer, 'name', 'GL_JET_file.xlsx') # 기본 이름 지정
    suffix = Path(filename).suffix.lower()

    dtype_spec = {
        "전표번호": str, "계정코드": str, "계정과목": str,
        "거래처코드": str, "입력사원": str
    }

    print(f"[INFO] JET용 총계정원장 로딩 시도: {filename} (형식: {suffix})")

    try:
        if suffix == ".xlsx":
            df = pd.read_excel(path_or_buffer, dtype=dtype_spec)
        elif suffix == ".csv":
            if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
            try:
                df = pd.read_csv(path_or_buffer, dtype=dtype_spec, encoding='utf-8')
            except UnicodeDecodeError:
                if hasattr(path_or_buffer, 'seek'): path_or_buffer.seek(0)
                print(f"[경고] JET GL CSV UTF-8 인코딩 실패 ({filename}). 'cp949'로 재시도합니다.")
                df = pd.read_csv(path_or_buffer, dtype=dtype_spec, encoding='cp949')
        else:
            raise ValueError(f"지원하지 않는 총계정원장 파일 형식 (JET용): {suffix}. Excel 또는 CSV 파일을 사용해주세요.")

        # 필수 열 확인
        essential_cols = ["전표일자", "계정과목", "차변금액", "대변금액", "전표번호", "계정코드", "입력사원"]
        missing_cols = [col for col in essential_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"총계정원장 파일에 다음 필수 열이 없습니다: {', '.join(missing_cols)}")

        # 날짜 열 파싱
        df["전표일자"] = pd.to_datetime(df["전표일자"], errors="coerce")
        if df["전표일자"].isnull().all(): # 모든 날짜가 파싱 실패한 경우
             raise ValueError("'전표일자' 열의 모든 값을 날짜 형식으로 변환할 수 없습니다. 데이터 형식을 확인해주세요.")
        elif df["전표일자"].isnull().any():
             print(f"[경고] '전표일자' 열에 일부 유효하지 않은 날짜 형식이 포함되어 NaT로 처리되었습니다 ({df['전표일자'].isnull().sum()} 건).")


        # 금액 열을 숫자(float/int)로 변환 (천단위 구분 쉼표 제거)
        for col in ("차변금액", "대변금액"):
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        print(f"[INFO] JET용 총계정원장 로딩 완료: {len(df)} 행")
        return df
    except Exception as e:
        print(f"[오류] JET 총계정원장 파일 로드 중 에러 발생 ({filename}): {e}")
        raise

######################################################################
# 3. 시나리오별 필터 함수들
######################################################################
def scenario1_keyword(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    if not keywords: return pd.DataFrame()
    pattern = "|".join(map(re.escape, keywords))
    mask = df["계정과목"].str.contains(pattern, case=False, na=False)
    return df.loc[mask].copy()

def scenario2_account_code(df: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    if not codes: return pd.DataFrame()
    mask = df["계정코드"].isin(codes)
    return df.loc[mask].copy()

def scenario3_abnormal_sales(df: pd.DataFrame) -> pd.DataFrame:
    sales_mask = df["계정과목"].str.contains(r"제품매출|상품매출", na=False)
    allowed = {"현금", "당좌예금", "보통예금", "외상매출금", "받을어음", "미수금", "선수금"}
    abnormal_entries = []
    for _, sub in df.groupby("전표번호"):
        if not sales_mask.loc[sub.index].any(): continue
        cond_a = (((sub["계정과목"].str.contains(r"제품매출|상품매출", na=False)) & (sub["차변금액"] > 0)) |
                  ((sub["계정과목"].str.contains(r"제품매출|상품매출", na=False)) & (sub["대변금액"] < 0)))
        other_accounts = set(sub.loc[~sub["계정과목"].str.contains(r"제품매출|상품매출", na=False), "계정과목"].tolist())
        cond_b = not other_accounts.issubset(allowed) if other_accounts else False # 상대계정 없으면 정상으로 간주
        if cond_a.any() or cond_b:
            abnormal_entries.append(sub)
    if abnormal_entries: return pd.concat(abnormal_entries, ignore_index=True)
    return pd.DataFrame()

def _apply_period(df: pd.DataFrame, start: dt.datetime | None, end: dt.datetime | None) -> pd.DataFrame:
    """주어진 시작일과 종료일(datetime 객체)로 DataFrame을 필터링한다."""
    if start: df = df[df["전표일자"] >= start]
    if end: df = df[df["전표일자"] <= end] # 종료일은 해당 날짜의 마지막 시간까지 포함
    return df

def scenario4_rare_accounts(df: pd.DataFrame, start: dt.datetime | None, end: dt.datetime | None, threshold: int | None) -> pd.DataFrame:
    if threshold is None: return pd.DataFrame()
    sub = _apply_period(df.copy(), start, end) # 원본 보존 위해 copy
    if sub.empty: return pd.DataFrame()
    counts = sub["계정코드"].value_counts()
    rare_codes = counts[counts < threshold].index
    return sub[sub["계정코드"].isin(rare_codes)].copy()

def scenario5_rare_users(df: pd.DataFrame, start: dt.datetime | None, end: dt.datetime | None, threshold: int | None) -> pd.DataFrame:
    if threshold is None: return pd.DataFrame()
    sub = _apply_period(df.copy(), start, end) # 원본 보존 위해 copy
    if sub.empty: return pd.DataFrame()
    counts = sub["입력사원"].value_counts()
    rare_users = counts[counts < threshold].index
    return sub[sub["입력사원"].isin(rare_users)].copy()

def scenario6_weekend_holiday(df: pd.DataFrame, holiday_file_path: str | Path | None) -> pd.DataFrame:
    # 전표일자 NaT 값 있는 행은 미리 제거 (dt.weekday 등에서 오류 방지)
    df_filtered = df.dropna(subset=['전표일자']).copy()
    if df_filtered.empty: return pd.DataFrame()

    weekend_mask = df_filtered["전표일자"].dt.weekday >= 5  # 5=Sat,6=Sun
    holiday_dates: set[pd.Timestamp] = set()

    if holiday_file_path:
        path_obj = Path(holiday_file_path)
        try:
            h_df = pd.DataFrame()
            file_suffix = path_obj.suffix.lower()
            print(f"[INFO] 공휴일 파일 로딩 시도: {holiday_file_path} (형식: {file_suffix})")
            if file_suffix in ['.csv', '.txt']:
                h_df = pd.read_csv(path_obj, header=None)
            elif file_suffix in ['.xlsx', '.xls']:
                h_df = pd.read_excel(path_obj, header=None)
            else:
                print(f"[경고] 지원하지 않는 공휴일 파일 형식: {file_suffix}. 공휴일 처리 없이 주말만 검토합니다.")

            if not h_df.empty:
                # 첫 번째 열의 날짜들을 파싱
                parsed_dates = pd.to_datetime(h_df.iloc[:, 0], errors='coerce').dropna().dt.normalize()
                holiday_dates = set(parsed_dates)
                print(f"[INFO] 공휴일 {len(holiday_dates)}일 로드 완료.")
            elif file_suffix in ['.csv', '.txt', '.xlsx', '.xls']: # 지원 형식인데 비어있거나 파싱 실패
                 print(f"[경고] 공휴일 파일('{holiday_file_path}')이 비어있거나 유효한 날짜를 포함하지 않습니다.")

        except Exception as e:
            print(f"[경고] 공휴일 파일('{holiday_file_path}') 처리 중 오류: {e}. 공휴일 처리 없이 주말만 검토합니다.")

    if holiday_dates:
        holiday_mask = df_filtered["전표일자"].dt.normalize().isin(holiday_dates)
        mask = weekend_mask | holiday_mask
    else:
        mask = weekend_mask
    return df_filtered.loc[mask].copy()

def scenario7_repeating_digits(df: pd.DataFrame, repeat_len: int | None) -> pd.DataFrame:
    if repeat_len is None or repeat_len < 2 : return pd.DataFrame()
    repeat_pattern = re.compile(rf"(\d)\1{{{repeat_len - 1}}}$")
    def _has_repeat(val: float) -> bool:
        if pd.isna(val) or val == 0: return False # 0은 제외
        val_str = str(int(abs(val)))
        return bool(repeat_pattern.search(val_str))
    mask = df.apply(lambda row: _has_repeat(row["차변금액"]) or _has_repeat(row["대변금액"]), axis=1)
    return df.loc[mask].copy()

def scenario8_round_numbers(df: pd.DataFrame, zero_digits: int | None) -> pd.DataFrame:
    if zero_digits is None or zero_digits < 1: return pd.DataFrame()
    factor = 10 ** zero_digits
    mask = (((df["차변금액"].astype(int) % factor == 0) & (df["차변금액"] != 0)) |
            ((df["대변금액"].astype(int) % factor == 0) & (df["대변금액"] != 0)))
    return df.loc[mask].copy()

######################################################################
# 4. 메인 (CLI 실행용 - Streamlit에서는 사용되지 않음)
######################################################################
def main():
    args = _parse_args()
    print(f"[INFO] 입력된 총계정원장 파일: {args.input_gl}")
    print(f"[INFO] 결과 저장 파일: {args.output}")

    try:
        # CLI에서는 이 파일의 load_gl 함수를 직접 사용
        gl_df_cli = load_gl(args.input_gl) # 함수 이름 변경됨
    except Exception as e:
        print(f"[오류] 총계정원장 파일 처리 실패: {e}")
        sys.exit(1)

    results: dict[str, pd.DataFrame] = {}

    if args.keywords:
        kw_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
        if kw_list:
            print(f"[INFO] 시나리오1 (키워드: {kw_list}) 실행...")
            res = scenario1_keyword(gl_df_cli, kw_list)
            if not res.empty: results["시나리오1_키워드"] = res

    if args.account_codes:
        code_list = [c.strip() for c in args.account_codes.split(",") if c.strip()]
        if code_list:
            print(f"[INFO] 시나리오2 (계정코드: {code_list}) 실행...")
            res = scenario2_account_code(gl_df_cli, code_list)
            if not res.empty: results["시나리오2_계정코드"] = res
    
    print("[INFO] 시나리오3 (비정상매출) 실행...")
    res = scenario3_abnormal_sales(gl_df_cli)
    if not res.empty: results["시나리오3_비정상매출"] = res

    start_dt_obj = pd.to_datetime(args.start_date, errors='coerce').to_pydatetime(warn=False) if args.start_date else None
    end_dt_obj = pd.to_datetime(args.end_date, errors='coerce').to_pydatetime(warn=False) if args.end_date else None
    if start_dt_obj and end_dt_obj and start_dt_obj > end_dt_obj:
        print("[경고] 시작일이 종료일보다 늦습니다. 날짜 필터링 없이 진행될 수 있습니다.")

    if args.freq_account is not None:
        print(f"[INFO] 시나리오4 (희귀계정, 임계값: {args.freq_account}, 기간: {args.start_date}~{args.end_date}) 실행...")
        res = scenario4_rare_accounts(gl_df_cli, start_dt_obj, end_dt_obj, args.freq_account)
        if not res.empty: results["시나리오4_희귀계정"] = res

    if args.freq_user is not None:
        print(f"[INFO] 시나리오5 (희귀입력자, 임계값: {args.freq_user}, 기간: {args.start_date}~{args.end_date}) 실행...")
        res = scenario5_rare_users(gl_df_cli, start_dt_obj, end_dt_obj, args.freq_user)
        if not res.empty: results["시나리오5_희귀입력자"] = res

    print(f"[INFO] 시나리오6 (주말/휴일, 공휴일 파일: {args.holidays}) 실행...")
    res = scenario6_weekend_holiday(gl_df_cli, args.holidays)
    if not res.empty: results["시나리오6_주말휴일"] = res

    if args.repeat_len is not None:
        print(f"[INFO] 시나리오7 (반복숫자, 길이: {args.repeat_len}) 실행...")
        res = scenario7_repeating_digits(gl_df_cli, args.repeat_len)
        if not res.empty: results["시나리오7_반복숫자"] = res

    if args.zero_digits is not None:
        print(f"[INFO] 시나리오8 (라운드넘버, 0개수: {args.zero_digits}) 실행...")
        res = scenario8_round_numbers(gl_df_cli, args.zero_digits)
        if not res.empty: results["시나리오8_라운드넘버"] = res

    if not results:
        print("[INFO] 어떤 시나리오에서도 이상 거래가 발견되지 않았습니다.")
        sys.exit(0)

    output_path = Path(args.output)
    try:
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            for sheet_name, df_out in results.items():
                df_out.to_excel(writer, sheet_name=sheet_name[:31], index=False) # 시트 이름 31자 제한
        print(f"[SUCCESS] 결과가 '{output_path.resolve()}'에 저장되었습니다.")
    except Exception as e:
        print(f"[오류] 결과 파일 저장 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()