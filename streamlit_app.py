"""Streamlit Web App – Journal Entry Test Automation
===================================================
Run:
    streamlit run streamlit_app.py

Dependencies:
    pip install streamlit pandas numpy xlsxwriter openpyxl

Place this file in the same folder as *journal_entry_test.py* (core logic).
"""

from __future__ import annotations

import io
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

# Import analysis utilities from the core script
from journal_entry_test import (
    _load_gl,
    scenario1_keyword,
    scenario2_account_code,
    scenario3_abnormal_sales,
    scenario4_rare_accounts,
    scenario5_rare_users,
    scenario6_weekend_holiday,
    scenario7_repeating_digits,
    scenario8_round_numbers,
)

st.set_page_config(page_title="Journal Entry Test", layout="wide")

st.title("📑 Journal Entry Test – Streamlit Edition")
st.markdown("업로드한 **총계정원장 Excel** 데이터에 대해 8가지 분개 테스트를 실행하고 결과를 시나리오별로 확인·다운로드할 수 있습니다.")

# -------------------------------------------------------------------
# Sidebar – 옵션 입력
# -------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 테스트 설정")
    st.markdown("필드를 비워두면 해당 시나리오는 건너뜁니다.")

    keywords = st.text_input("🔍 키워드(쉼표 구분)")
    account_codes = st.text_input("📁 계정코드(쉼표 구분)")

    st.markdown("---")
    st.subheader("기간 & 빈도")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작일", value=None)
    with col2:
        end_date = st.date_input("종료일", value=None)

    freq_account = st.number_input("희귀 계정 기준(미만)", min_value=1, value=5, step=1)
    freq_user = st.number_input("희귀 입력자 기준(미만)", min_value=1, value=3, step=1)

    st.markdown("---")
    st.subheader("특이 금액 패턴")
    repeat_len = st.number_input("끝자리 반복 숫자 길이", min_value=2, value=3, step=1)
    zero_digits = st.number_input("끝자리 0 개수", min_value=1, value=3, step=1)

    st.markdown("---")
    st.subheader("기타 시나리오")
    enable_s3 = st.checkbox("비정상 매출 계정 조합 (시나리오3)", value=True)
    enable_s6 = st.checkbox("주말/공휴일 분개 (시나리오6)", value=True)

    holiday_file = st.file_uploader("공휴일 CSV 업로드 (선택)", type=["csv", "txt"], key="holidays")

# -------------------------------------------------------------------
# Main – 파일 업로드 & 실행
# -------------------------------------------------------------------
file = st.file_uploader("총계정원장 Excel 업로드", type=["xlsx", "xls"], key="gl")

run_btn = st.button("🚀 테스트 실행", disabled=file is None)

if run_btn and file:
    with st.spinner("분석 중..."):
        # 1) 파일 저장 & 로드 --------------------------------------------------
        try:
            df = _load_gl(file)
        except Exception as exc:
            st.error(f"[파일 로드 실패] {exc}")
            st.stop()

        # 2) 시나리오별 실행 ---------------------------------------------------
        results: dict[str, pd.DataFrame] = {}

        if keywords.strip():
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
            res = scenario1_keyword(df, kw_list)
            if not res.empty:
                results["시나리오1_키워드"] = res

        if account_codes.strip():
            codes = [c.strip() for c in account_codes.split(",") if c.strip()]
            res = scenario2_account_code(df, codes)
            if not res.empty:
                results["시나리오2_계정코드"] = res

        if enable_s3:
            res = scenario3_abnormal_sales(df)
            if not res.empty:
                results["시나리오3_비정상매출"] = res

        start_datetime = None  # 시작 날짜 기본값은 '없음'
        if start_date:  # 사용자가 시작 날짜를 선택했다면
            # 선택한 날짜의 가장 이른 시간(00:00:00)으로 설정
            start_datetime = dt.datetime.combine(start_date, dt.datetime.min.time())

        end_datetime = None  # 종료 날짜 기본값은 '없음'
        if end_date:  # 사용자가 종료 날짜를 선택했다면
        # 선택한 날짜의 가장 늦은 시간(23:59:59...)으로 설정
            end_datetime = dt.datetime.combine(end_date, dt.datetime.max.time())

        # 이제 제대로 바꾼 날짜+시간(start_datetime, end_datetime)을 사용해서 시나리오 4번 함수를 실행합니다.
        res = scenario4_rare_accounts(df, start_datetime, end_datetime, freq_account)
        if not res.empty:  # 결과가 있다면
            results["시나리오4_희귀계정"] = res  # 결과 저장

        # 제대로 바꾼 날짜+시간(start_datetime, end_datetime)을 사용해서 시나리오 5번 함수를 실행합니다.
        res = scenario5_rare_users(df, start_datetime, end_datetime, freq_user)
        if not res.empty:  # 결과가 있다면
            results["시나리오5_희귀입력자"] = res  # 결과 저장

        holiday_path = None
        if holiday_file is not None:
            holiday_path = Path("/tmp") / ("holidays_" + holiday_file.name)
            holiday_path.write_bytes(holiday_file.getvalue())

        if enable_s6:
            res = scenario6_weekend_holiday(df, str(holiday_path) if holiday_path else None)
            if not res.empty:
                results["시나리오6_주말휴일"] = res

        res = scenario7_repeating_digits(df, repeat_len)
        if not res.empty:
            results["시나리오7_반복숫자"] = res

        res = scenario8_round_numbers(df, zero_digits)
        if not res.empty:
            results["시나리오8_라운드넘버"] = res

        if not results:
            st.success("✅ 어떤 시나리오에서도 이상 거래가 발견되지 않았습니다.")
            st.stop()

        # 3) 결과 미리보기 -----------------------------------------------------
        st.success("🎉 테스트 완료! 시나리오별 결과를 아래에서 확인하거나 Excel로 다운로드하세요.")
        for sheet, df_out in results.items():
            with st.expander(f"{sheet} – {len(df_out):,} 건"):
                st.dataframe(df_out, use_container_width=True)

        # 4) Excel 바이너리 생성 & 다운로드 -------------------------------------
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            for sheet, df_out in results.items():
                df_out.to_excel(writer, sheet_name=sheet[:31], index=False)
        buffer.seek(0)

        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="📥 결과 Excel 다운로드",
            data=buffer,
            file_name=f"journal_entry_test_results_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

