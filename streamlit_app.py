"""Streamlit Web App – Journal Entry Test (+ GL/TB Comparison)
================================================================
Run:
    streamlit run streamlit_app.py

Dependencies:
    pip install streamlit pandas numpy xlsxwriter openpyxl

Place this file in the same folder as:
    * journal_entry_test.py (Original JET logic)
    * difference.py (GL/TB comparison logic - MUST BE UPDATED)
"""

from __future__ import annotations

import io
import datetime as dt
from pathlib import Path
import pandas as pd
import streamlit as st
import traceback # 에러 상세 출력을 위해 추가

# -------------------------------------------------------------------
# Import analysis utilities
# -------------------------------------------------------------------

# --- 1. Original Journal Entry Test Functions ---
try:
    from journal_entry_test import (
        _load_gl as load_gl_jet,
        scenario1_keyword,
        scenario2_account_code,
        scenario3_abnormal_sales,
        scenario4_rare_accounts,
        scenario5_rare_users,
        scenario6_weekend_holiday,
        scenario7_repeating_digits,
        scenario8_round_numbers,
    )
    JET_AVAILABLE = True
except ImportError:
    JET_AVAILABLE = False
    st.error("journal_entry_test.py 파일을 찾을 수 없습니다. 분개 테스트 기능을 사용할 수 없습니다.")

# --- 2. GL vs TB Comparison Functions ---
try:
    from difference import verify as verify_gl_tb
    COMP_AVAILABLE = True
except ImportError:
    COMP_AVAILABLE = False

# -------------------------------------------------------------------
# Streamlit App Configuration and Title
# -------------------------------------------------------------------
st.set_page_config(page_title="Journal Entry Test", layout="wide")

st.title("Journal Entry Test")
st.caption("총계정원장-시산표 비교 및 분개 테스트 자동화 기능을 제공합니다.")


# -------------------------------------------------------------------
# File Uploaders
# -------------------------------------------------------------------
st.divider()
st.subheader("📂 파일 업로드")
col1_upload, col2_upload = st.columns(2)
with col1_upload:
    gl_file = st.file_uploader("1. 총계정원장 (GL) 파일", type=["xlsx", "xls", "csv"], key="gl_file_uploader")
with col2_upload:
    tb_file = st.file_uploader("2. 시산표 (TB) 파일 (GL/TB 비교용)", type=["xlsx", "csv"], key="tb_file_uploader")
st.divider()


# -------------------------------------------------------------------
# Sidebar Definition (★★★★★ 위치 이동됨 ★★★★★)
# -------------------------------------------------------------------
# 사이드바 정의를 탭 로직보다 먼저 실행되도록 이곳으로 이동
with st.sidebar:
    st.header("⚙️ 분개 테스트 설정")
    st.markdown("*(이 설정은 '2️⃣ 분개 테스트' 탭에만 적용됩니다)*")
    st.markdown("---")
    # 이제 여기서 정의된 변수들이 탭 안에서 사용될 때 에러가 발생하지 않습니다.
    keywords = st.text_input("🔍 키워드(쉼표 구분)", key="jet_keywords")
    account_codes = st.text_input("📁 계정코드(쉼표 구분)", key="jet_accounts")

    st.markdown("---")
    st.subheader("기간 & 빈도")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작일", value=None, key="jet_start_date")
    with col2:
        end_date = st.date_input("종료일", value=None, key="jet_end_date")

    freq_account = st.number_input("희귀 계정 기준(미만)", min_value=1, value=5, step=1, key="jet_freq_acc")
    freq_user = st.number_input("희귀 입력자 기준(미만)", min_value=1, value=3, step=1, key="jet_freq_user")

    st.markdown("---")
    st.subheader("특이 금액 패턴")
    repeat_len = st.number_input("끝자리 반복 숫자 길이", min_value=2, value=3, step=1, key="jet_repeat")
    zero_digits = st.number_input("끝자리 0 개수", min_value=1, value=3, step=1, key="jet_zeros")

    st.markdown("---")
    st.subheader("기타 시나리오")
    enable_s3 = st.checkbox("비정상 매출 계정 조합 (S3)", value=True, key="jet_s3")
    enable_s6 = st.checkbox("주말/공휴일 분개 (S6)", value=True, key="jet_s6")
    holiday_file = st.file_uploader("공휴일 CSV 업로드 (S6용)", type=["csv", "txt"], key="jet_holidays")
    st.markdown("---")


# -------------------------------------------------------------------
# Main Area with Tabs
# -------------------------------------------------------------------
tab_comp, tab_jet = st.tabs(["1️⃣ GL vs TB 검증", "2️⃣ 분개 테스트 (Journal Entry Test)"])

# --- Tab 1: GL vs TB Comparison ---
with tab_comp:
    if not COMP_AVAILABLE:
        st.error("difference.py 파일을 찾을 수 없거나 오류가 있어 GL/TB 비교를 실행할 수 없습니다.")
        st.info("스크립트가 올바르게 준비되었는지 확인하세요 (특히 difference.py의 load_gl, load_tb 함수).")
    else:
        st.header("GL vs TB 합계/잔액 검증")
        st.markdown("업로드한 **총계정원장(GL)**과 **시산표(TB)**의 주요 합계/잔액을 비교합니다.")

        tb_header_row = st.number_input(
            "시산표(TB) 헤더 시작 행 번호 (0-based)",
            min_value=0, value=3, step=1, key="tb_header_input",
            help="엑셀에서 '차 변', '대 변' 헤더가 있는 행의 번호(0부터 시작). 예: 엑셀 4행이면 3 입력."
        )

        run_comp_btn = st.button("📊 GL/TB 합계 비교 실행", key="run_comp", disabled=(gl_file is None or tb_file is None))

        if run_comp_btn and gl_file and tb_file:
            with st.spinner("GL/TB 비교 분석 중..."):
                try:
                    ok, (gl_d, gl_c, tb_vals, diff, cols) = verify_gl_tb(
                        gl_file, tb_file, tb_header_row
                    )
                    st.subheader("📊 비교 결과 요약")
                    if ok:
                        st.success("✅ 검증 성공: GL 차/대 합계와 TB 차/대 합계가 허용 오차 내에서 모두 일치합니다.")
                    else:
                        st.error("❌ 검증 실패: GL 또는 TB의 합계가 일치하지 않습니다. 아래 상세 내용을 확인하세요.")

                    col_gl, col_tb_tot, col_tb_bal = st.columns(3)
                    # (결과 표시 로직은 이전과 동일)
                    with col_gl:
                        st.metric("GL 총차변", f"{gl_d:,.0f}")
                        st.metric("GL 총대변", f"{gl_c:,.0f}")
                        st.metric("GL 차액(Δ)", f"{diff['Δ_GL']:,.0f}", delta_color="off")
                    with col_tb_tot:
                        st.metric(f"TB 차변 합계 ({cols['tot_d']})", f"{tb_vals['tot_d']:,.0f}")
                        st.metric(f"TB 대변 합계 ({cols['tot_c']})", f"{tb_vals['tot_c']:,.0f}")
                        st.metric("TB 합계 차액(Δ)", f"{diff['Δ_TB_Tot']:,.0f}", delta_color="off")
                    with col_tb_bal:
                        st.metric(f"TB 차변 잔액 합계 ({cols['bal_d']})", f"{tb_vals['bal_d']:,.0f}")
                        st.metric(f"TB 대변 잔액 합계 ({cols['bal_c']})", f"{tb_vals['bal_c']:,.0f}")
                        st.metric("TB 잔액 차액(Δ)", f"{diff['Δ_TB_Bal']:,.0f}", delta_color="off")

                    st.divider()
                    st.markdown("**참고: 직접 비교 차이**")
                    st.markdown(f"* GL 차변 vs TB 합계 차변 차이 : {diff['Δ_GLd_TBtotd']:,.0f}")
                    st.markdown(f"* GL 대변 vs TB 합계 대변 차이 : {diff['Δ_GLc_TBtotc']:,.0f}")

                except FileNotFoundError as e:
                    st.error(f"파일 처리 중 오류 발생: 파일을 찾을 수 없습니다. {e}")
                except ValueError as e:
                    st.error(f"데이터 처리 중 오류 발생: {e}")
                    st.info("시산표 헤더 행 번호나 파일 내용을 확인하거나, difference.py 코드의 'total_label' 또는 'account_col_name' 변수를 수정해야 할 수 있습니다.")
                except Exception as e:
                    st.error(f"예상치 못한 오류 발생: {e}")
                    st.exception(e)


# --- Tab 2: Journal Entry Test ---
with tab_jet:
    if not JET_AVAILABLE:
        st.error("journal_entry_test.py 가 없어 분개 테스트를 실행할 수 없습니다.")
    else:
        st.header("분개 테스트 실행")
        st.markdown("업로드한 **총계정원장(GL)** 데이터에 대해 8가지 분개 테스트를 실행합니다. 설정은 사이드바에서 변경하세요.")

        run_jet_btn = st.button("🚀 분개 테스트 실행", key="run_jet", disabled=(gl_file is None))

        if run_jet_btn and gl_file:
             with st.spinner("분개 테스트 분석 중..."):
                try:
                    df = load_gl_jet(gl_file)
                    if df is None: raise ValueError("총계정원장(GL) 파일 로딩 실패 (JET용).")

                    results: dict[str, pd.DataFrame] = {}

                    # --- 시나리오별 실행 ---
                    # 이제 사이드바 변수(keywords, account_codes 등)가 정의된 후에 사용되므로 에러 없음
                    if keywords.strip():
                         kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
                         res = scenario1_keyword(df, kw_list)
                         if not res.empty: results["시나리오1_키워드"] = res
                    if account_codes.strip():
                        codes = [c.strip() for c in account_codes.split(",") if c.strip()]
                        res = scenario2_account_code(df, codes)
                        if not res.empty: results["시나리오2_계정코드"] = res
                    if enable_s3:
                        res = scenario3_abnormal_sales(df)
                        if not res.empty: results["시나리오3_비정상매출"] = res
                    start_datetime = dt.datetime.combine(start_date, dt.datetime.min.time()) if start_date else None
                    end_datetime = dt.datetime.combine(end_date, dt.datetime.max.time()) if end_date else None
                    res = scenario4_rare_accounts(df, start_datetime, end_datetime, freq_account)
                    if not res.empty: results["시나리오4_희귀계정"] = res
                    res = scenario5_rare_users(df, start_datetime, end_datetime, freq_user)
                    if not res.empty: results["시나리오5_희귀입력자"] = res
                    holiday_path_for_jet = None
                    if holiday_file is not None:
                        try:
                            temp_holiday_path = Path("./temp_holidays") # Use relative path or tempfile module
                            temp_holiday_path.mkdir(exist_ok=True)
                            holiday_file_path = temp_holiday_path / f"jet_holidays_{holiday_file.name}"
                            holiday_file_path.write_bytes(holiday_file.getvalue())
                            holiday_path_for_jet = str(holiday_file_path)
                        except Exception as e_tmp:
                             st.warning(f"임시 공휴일 파일 저장 실패 (분개 테스트용): {e_tmp}")
                    if enable_s6:
                         res = scenario6_weekend_holiday(df, holiday_path_for_jet)
                         if not res.empty: results["시나리오6_주말휴일"] = res
                    res = scenario7_repeating_digits(df, repeat_len)
                    if not res.empty: results["시나리오7_반복숫자"] = res
                    res = scenario8_round_numbers(df, zero_digits)
                    if not res.empty: results["시나리오8_라운드넘버"] = res
                    # --- End Scenario Execution ---


                    # --- 결과 표시 및 다운로드 ---
                    if not results:
                         st.success("✅ 어떤 분개 테스트 시나리오에서도 이상 거래가 발견되지 않았습니다.")
                    else:
                        st.success("🎉 분개 테스트 완료! 시나리오별 결과를 아래에서 확인하거나 Excel로 다운로드하세요.")
                        for sheet, df_out in results.items():
                            with st.expander(f"{sheet} – {len(df_out):,} 건"):
                                st.dataframe(df_out, use_container_width=True)
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                            for sheet, df_out in results.items():
                                df_out.to_excel(writer, sheet_name=sheet[:31], index=False)
                        buffer.seek(0)
                        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.download_button(
                            label="📥 분개 테스트 결과 Excel 다운로드",
                            data=buffer,
                            file_name=f"journal_entry_test_results_{timestamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_jet"
                        )
                except Exception as e:
                    st.error(f"분개 테스트 실행 중 오류 발생: {e}")
                    st.exception(e)