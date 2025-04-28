#!/usr/bin/env python
"""
Journal Entry Test Automation Script
===================================

본 스크립트는 **총계정원장(General Ledger)** 엑셀 파일을 입력받아 감사인이 자주 수행하는
8 가지 Journal‑Entry Test(분개 테스트)를 자동으로 실행하고, 시나리오별 결과를
**하나의 엑셀 파일**(시트 분리)로 저장한다.

사용법
------
python journal_entry_test.py --input_gl GL.xlsx --output results.xlsx \
        --keywords "보험,조정" --account_codes "410000,420000" \
        --freq_account 5 --freq_user 3 --start_date 2025-01-01 \
        --end_date 2025-12-31 --zero_digits 3 --repeat_len 3 \
        --holidays holidays.csv

모든 옵션은 생략 가능하며, 생략 시 합리적인 기본값이 적용된다.

필수 열 구조
------------
전표일자 | 전표번호 | 계정코드 | 계정과목 | 차변금액 | 대변금액 | 거래처코드 | 입력사원

(열 이름이 다를 경우 --colmap 옵션으로 매핑 가능하도록 추가 구현을 고려할 수 있음.)
"""

from __future__ import annotations
import argparse
import datetime as dt
from pathlib import Path
import sys
import re

import numpy as np
import pandas as pd

######################################################################
# 1. CLI 파서
######################################################################

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="General‑Ledger Journal Entry Test Automation"
    )

    parser.add_argument("--input_gl", required=True, help="총계정원장 Excel 파일 경로")
    parser.add_argument(
        "--output",
        default="journal_entry_test_results.xlsx",
        help="분석 결과를 저장할 Excel 파일 경로",
    )

    # 시나리오 1
    parser.add_argument(
        "--keywords",
        type=str,
        default="",  # 쉼표 구분 문자열
        help="계정과목 키워드(쉼표로 구분) — 시나리오1. 비워두면 실행하지 않음.",
    )

    # 시나리오 2
    parser.add_argument(
        "--account_codes",
        type=str,
        default="",
        help="관심 계정코드(쉼표로 구분) — 시나리오2. 비워두면 실행하지 않음.",
    )

    # 시나리오 4 / 5 공통 입력
    parser.add_argument(
        "--freq_account",
        type=int,
        default=None,
        help="희귀 계정의 기준 사용 횟수(미만) — 시나리오4. None이면 실행 안 함.",
    )
    parser.add_argument(
        "--freq_user",
        type=int,
        default=None,
        help="희귀 입력자의 기준 전표 수(미만) — 시나리오5. None이면 실행 안 함.",
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default=None,
        help="시나리오4/5 기간 시작(YYYY-MM-DD). 지정 없으면 전체.",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="시나리오4/5 기간 종료(YYYY-MM-DD). 지정 없으면 전체.",
    )

    # 시나리오8 / 7
    parser.add_argument(
        "--zero_digits",
        type=int,
        default=None,
        help="끝자리 0이 몇 개 이상인지 기준 — 시나리오8. None이면 실행 안 함.",
    )
    parser.add_argument(
        "--repeat_len",
        type=int,
        default=None,
        help="끝자리 반복 숫자 길이 — 시나리오7. None이면 실행 안 함.",
    )

    # 시나리오6
    parser.add_argument(
        "--holidays",
        type=str,
        default=None,
        help="공휴일 CSV/텍스트 파일 경로(YYYY-MM-DD 컬럼 또는 한 줄 한 날짜).",
    )

    return parser.parse_args()

######################################################################
# 2. 데이터 적재 및 공통 전처리
######################################################################

def _load_gl(path: str | Path) -> pd.DataFrame:
    """총계정원장 엑셀 파일을 DataFrame으로 읽고, 기본 전처리를 수행한다."""

    df = pd.read_excel(path, dtype={
        "전표번호": str,
        "계정코드": str,
        "계정과목": str,
        "거래처코드": str,
        "입력사원": str,
    })

    # 날짜 열 파싱
    df["전표일자"] = pd.to_datetime(df["전표일자"], errors="coerce")

    # 금액 열을 숫자(float/int)로 변환 (천단위 구분 쉼표 제거)
    for col in ("차변금액", "대변금액"):
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

######################################################################
# 3. 시나리오별 필터 함수들
######################################################################

def scenario1_keyword(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    if not keywords:
        return pd.DataFrame()
    pattern = "|".join(map(re.escape, keywords))
    mask = df["계정과목"].str.contains(pattern, case=False, na=False)
    return df.loc[mask].copy()


def scenario2_account_code(df: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    if not codes:
        return pd.DataFrame()
    mask = df["계정코드"].isin(codes)
    return df.loc[mask].copy()


def scenario3_abnormal_sales(df: pd.DataFrame) -> pd.DataFrame:
    sales_mask = df["계정과목"].str.contains(r"제품매출|상품매출", na=False)

    # 허용 상대계정(정상 범주)
    allowed = {
        "현금",
        "당좌예금",
        "보통예금",
        "외상매출금",
        "받을어음",
        "미수금",
        "선수금",
    }

    abnormal_entries = []

    for vchr_no, sub in df.groupby("전표번호"):
        if not sales_mask.loc[sub.index].any():
            continue  # 매출 계정이 포함되지 않은 전표

        # (a) 매출 계정의 차변 +금액 또는 대변 -금액 조건 (비정상 방향)
        cond_a = (
            ((sub["계정과목"].str.contains(r"제품매출|상품매출", na=False)) & (sub["차변금액"] > 0))
            | ((sub["계정과목"].str.contains(r"제품매출|상품매출", na=False)) & (sub["대변금액"] < 0))
        )
        # (b) 상대 계정이 allowed 리스트에 없는 경우
        other_accounts = set(sub.loc[~sub["계정과목"].str.contains(r"제품매출|상품매출", na=False), "계정과목"].tolist())
        cond_b = not other_accounts.issubset(allowed)

        if cond_a.any() or cond_b:
            abnormal_entries.append(sub)

    if abnormal_entries:
        return pd.concat(abnormal_entries, ignore_index=True)
    return pd.DataFrame()


def _apply_period(df: pd.DataFrame, start: dt.datetime | None, end: dt.datetime | None) -> pd.DataFrame:
    """주어진 시작일과 종료일(datetime 객체)로 DataFrame을 필터링한다."""
    # start와 end가 이미 datetime 객체라고 가정하고 비교
    if start:
        df = df[df["전표일자"] >= start]
    if end:
        # 종료일은 해당 날짜의 마지막 시간까지 포함하도록 '<=' 사용
        df = df[df["전표일자"] <= end]
    return df


def scenario4_rare_accounts(
    df: pd.DataFrame, start: dt.datetime | None, end: dt.datetime | None, threshold: int | None
) -> pd.DataFrame:
    if threshold is None:
        return pd.DataFrame()

    sub = _apply_period(df, start, end)
    counts = sub["계정코드"].value_counts()
    rare_codes = counts[counts < threshold].index
    return sub[sub["계정코드"].isin(rare_codes)].copy()


def scenario5_rare_users(df: pd.DataFrame, start: dt.datetime | None, end: dt.datetime | None, threshold: int | None) -> pd.DataFrame:
    if threshold is None:
        return pd.DataFrame()

    sub = _apply_period(df, start, end)
    counts = sub["입력사원"].value_counts()
    rare_users = counts[counts < threshold].index
    return sub[sub["입력사원"].isin(rare_users)].copy()


def scenario6_weekend_holiday(
    df: pd.DataFrame, holiday_file: str | None
) -> pd.DataFrame:
    weekend_mask = df["전표일자"].dt.weekday >= 5  # 5=Sat,6=Sun

    holiday_dates: set[pd.Timestamp] = set()
    if holiday_file:
        h = pd.read_csv(holiday_file, header=None)
        holiday_dates = set(pd.to_datetime(h[0]).dt.normalize())

    if holiday_dates:
        holiday_mask = df["전표일자"].dt.normalize().isin(holiday_dates)
        mask = weekend_mask | holiday_mask
    else:
        mask = weekend_mask

    return df.loc[mask].copy()


def scenario7_repeating_digits(df: pd.DataFrame, repeat_len: int | None) -> pd.DataFrame:
    if repeat_len is None:
        return pd.DataFrame()

    repeat_pattern = re.compile(rf"(\d)\1{{{repeat_len - 1}}}$")

    def _has_repeat(val: float) -> bool:
        val_str = str(int(abs(val)))  # 정수부만 확인
        return bool(repeat_pattern.search(val_str))

    mask = df.apply(
        lambda row: _has_repeat(row["차변금액"]) or _has_repeat(row["대변금액"]), axis=1
    )
    return df.loc[mask].copy()


def scenario8_round_numbers(df: pd.DataFrame, zero_digits: int | None) -> pd.DataFrame:
    if zero_digits is None:
        return pd.DataFrame()

    factor = 10 ** zero_digits

    mask = (
        (df["차변금액"].astype(int) % factor == 0) & (df["차변금액"] != 0)
    ) | (
        (df["대변금액"].astype(int) % factor == 0) & (df["대변금액"] != 0)
    )
    return df.loc[mask].copy()

######################################################################
# 4. 메인
######################################################################

def main():
    args = _parse_args()

    gl_df = _load_gl(args.input_gl)

    results: dict[str, pd.DataFrame] = {}

    if args.keywords:
        kw_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
        res = scenario1_keyword(gl_df, kw_list)
        if not res.empty:
            results["시나리오1_키워드"] = res

    if args.account_codes:
        code_list = [c.strip() for c in args.account_codes.split(",") if c.strip()]
        res = scenario2_account_code(gl_df, code_list)
        if not res.empty:
            results["시나리오2_계정코드"] = res

    res = scenario3_abnormal_sales(gl_df)
    if not res.empty:
        results["시나리오3_비정상매출"] = res

    # CLI 인수로 받은 문자열 날짜를 datetime 객체로 변환
    start_dt_obj = None
    if args.start_date:
        try:
            # 문자열을 datetime 객체로 파싱 (시간은 00:00:00)
            start_dt_obj = pd.to_datetime(args.start_date).to_pydatetime(warn=False)
            # 시작일은 자정부터 포함하도록 시간을 명시적으로 설정할 수도 있습니다.
            start_dt_obj = start_dt_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            print(f"[경고] 잘못된 시작 날짜 형식입니다: {args.start_date}. 날짜 필터링 없이 진행합니다.")

    end_dt_obj = None
    if args.end_date:
        try:
            # 문자열을 datetime 객체로 파싱 (시간은 00:00:00)
            end_dt_obj = pd.to_datetime(args.end_date).to_pydatetime(warn=False)
            # 종료일은 해당 날짜 전체를 포함하도록 시간을 마지막으로 설정합니다.
            end_dt_obj = end_dt_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            print(f"[경고] 잘못된 종료 날짜 형식입니다: {args.end_date}. 날짜 필터링 없이 진행합니다.")
    
     #변환된 datetime 객체(start_dt_obj, end_dt_obj)를 사용해서 함수 호출
    res = scenario4_rare_accounts(gl_df, start_dt_obj, end_dt_obj, args.freq_account)
    if not res.empty:
        results["시나리오4_희귀계정"] = res

    res = scenario5_rare_users(gl_df, start_dt_obj, end_dt_obj, args.freq_user)
    if not res.empty:
        results["시나리오5_희귀입력자"] = res

    res = scenario6_weekend_holiday(gl_df, args.holidays)
    if not res.empty:
        results["시나리오6_주말휴일"] = res

    res = scenario7_repeating_digits(gl_df, args.repeat_len)
    if not res.empty:
        results["시나리오7_반복숫자"] = res

    res = scenario8_round_numbers(gl_df, args.zero_digits)
    if not res.empty:
        results["시나리오8_라운드넘버"] = res

    if not results:
        print("[INFO] 어떤 시나리오에서도 이상 거래가 발견되지 않았습니다.")
        sys.exit(0)

    # 결과 엑셀 저장
    output_path = Path(args.output)
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        for sheet_name, df_out in results.items():
            df_out.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    print(f"[SUCCESS] 결과가 '{output_path.resolve()}'에 저장되었습니다.")


if __name__ == "__main__":
    main()
