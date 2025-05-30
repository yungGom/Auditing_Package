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

# difference.py의 detect_cols 함수도 import 필요 (초기 제안용)
try:
    from difference import verify as verify_gl_tb, detect_cols
    COMP_AVAILABLE = True
except ImportError:
    COMP_AVAILABLE = False
    #에러 메시지는 탭 안에서 표시

# -------------------------------------------------------------------
# Import analysis utilities
# -------------------------------------------------------------------

# --- Tab 1: GL vs TB Comparison (수정) ---
with tab_comp:
    if not COMP_AVAILABLE:
        st.error("difference.py 파일을 찾을 수 없거나 오류가 있어 GL/TB 비교를 실행할 수 없습니다.")
        st.info("스크립트가 올바르게 준비되었는지 확인하세요.")
    else:
        st.header("GL vs TB 합계/잔액 검증")
        st.markdown("업로드한 **총계정원장(GL)**과 **시산표(TB)**의 컬럼을 매핑하고 합계/잔액 및 상세 차이를 비교합니다.") # 문구 수정

        # --- 컬럼 매핑 및 설정 UI ---
        st.subheader("⚙️ 시산표(TB) 설정 및 컬럼 매핑")

        # 세션 상태 초기화 (파일이 변경되면 매핑 초기화)
        if 'tb_cols' not in st.session_state: st.session_state.tb_cols = []
        if 'tb_last_file_id' not in st.session_state: st.session_state.tb_last_file_id = None
        if tb_file and getattr(tb_file, 'file_id', id(tb_file)) != st.session_state.tb_last_file_id:
            st.session_state.tb_last_file_id = getattr(tb_file, 'file_id', id(tb_file))
            # 파일을 임시로 읽어 컬럼 목록 가져오기 (헤더 행 번호 임시 사용)
            try:
                 # 임시 로딩 시 헤더는 0으로 가정하거나, 사용자가 먼저 지정하게 유도
                 temp_tb_df = pd.read_excel(tb_file, header=0) # 엑셀 첫 행을 임시 헤더로 읽음
                 st.session_state.tb_cols = temp_tb_df.columns.astype(str).tolist()
                 st.info(f"시산표 파일 '{tb_file.name}' 컬럼 로드 완료. 아래에서 헤더 행 번호와 컬럼 매핑을 확인/수정하세요.")
            except Exception as e:
                 st.error(f"시산표 파일 미리보기 실패: {e}. 파일 형식이나 헤더 행 번호를 확인하세요.")
                 st.session_state.tb_cols = []


        # 1. 헤더 행 번호 입력
        tb_header_row = st.number_input(
            "시산표(TB) 실제 헤더 행 번호 (0-based)",
            min_value=0, value=0, step=1, key="tb_header_input_map", # 키 변경 가능
            help="시산표 파일에서 실제 열 이름이 있는 행의 번호 (0부터 시작)."
        )

        # 2. 합계 행 정보 입력
        col_label1, col_label2 = st.columns(2)
        with col_label1:
             # 계정과목 열 선택 (로드된 컬럼 목록 사용)
             tb_account_col_options = st.session_state.get('tb_cols', [])
             tb_account_col_index = tb_account_col_options.index('계정 과목') if '계정 과목' in tb_account_col_options else (tb_account_col_options.index('계정과목') if '계정과목' in tb_account_col_options else 0) if tb_account_col_options else 0
             tb_account_col_selected = st.selectbox(
                 "합계 레이블 포함 열 (계정과목 열)",
                 options=tb_account_col_options,
                 index=tb_account_col_index,
                 key="tb_account_col_select",
                 help="시산표에서 '합계' 또는 '총계' 텍스트가 있는 열을 선택하세요."
             )
        with col_label2:
             tb_total_label_input = st.text_input(
                 "합계 행 식별 텍스트", value="합계", key="tb_total_label_input",
                 help="시산표 맨 아래 합계 행을 나타내는 정확한 텍스트 (예: 합계, 총계)"
             )

        # 3. 주요 금액 열 매핑
        st.markdown("**주요 금액 컬럼 매핑:** (자동 감지 결과를 확인하고 필요시 수정)")

        # 자동 감지 시도 (파일이 있고 컬럼 로드 성공 시) - detect_cols는 DataFrame 필요
        detected_map = {}
        if tb_file and st.session_state.tb_cols:
             try:
                  # 실제 데이터로 detect_cols 실행 위해 임시 로드 (주의: 성능 영향 가능)
                  # load_tb는 수정했으므로 파일 객체와 헤더 로우 전달
                  from difference import load_tb as load_tb_for_detect # 필요시 import
                  temp_tb_df_detect = load_tb(tb_file, tb_header_row, filename=tb_file.name)
                  d_bal, c_bal, d_tot, c_tot = detect_cols(temp_tb_df_detect)
                  detected_map = {'bal_d': d_bal, 'bal_c': c_bal, 'tot_d': d_tot, 'tot_c': c_tot}
                  print("[INFO] 컬럼 자동 감지 시도 결과:", detected_map) # 디버깅용
             except Exception as e_detect:
                  st.warning(f"컬럼 자동 감지 중 오류: {e_detect}. 수동으로 지정해주세요.")


        col_map1, col_map2 = st.columns(2)
        # 드롭다운 옵션 (파일 로드 후 컬럼 목록 사용)
        tb_col_options = st.session_state.get('tb_cols', []) + [None] # None 옵션 추가

        # 각 항목별 드롭다운 생성 및 자동 감지 결과 표시
        def get_col_index(col_name):
            try: return tb_col_options.index(col_name) if col_name else len(tb_col_options) - 1 # None은 마지막 인덱스
            except ValueError: return len(tb_col_options) - 1 # 못 찾으면 None 선택

        with col_map1:
             d_bal_selected = st.selectbox("차변 잔액 열", options=tb_col_options, index=get_col_index(detected_map.get('bal_d')), key="d_bal_select")
             d_tot_selected = st.selectbox("차변 합계 열", options=tb_col_options, index=get_col_index(detected_map.get('tot_d')), key="d_tot_select")
        with col_map2:
             c_bal_selected = st.selectbox("대변 잔액 열", options=tb_col_options, index=get_col_index(detected_map.get('bal_c')), key="c_bal_select")
             c_tot_selected = st.selectbox("대변 합계 열", options=tb_col_options, index=get_col_index(detected_map.get('tot_c')), key="c_tot_select")


        # --- Comparison Execution Button and Logic ---
        st.divider()
        run_comp_btn = st.button("📊 GL/TB 합계 비교 실행", key="run_comp_map", disabled=(gl_file is None or tb_file is None))

        if run_comp_btn and gl_file and tb_file:
            # 사용자가 선택한 매핑 정보 구성
            user_tb_col_map = {
                'bal_d': d_bal_selected, 'bal_c': c_bal_selected,
                'tot_d': d_tot_selected, 'tot_c': c_tot_selected
            }
            user_tb_account_col = tb_account_col_selected
            user_tb_total_label = tb_total_label_input

            # 필수 매핑 정보 확인
            if None in user_tb_col_map.values() or not user_tb_account_col or not user_tb_total_label:
                 st.error("시산표(TB) 설정 및 컬럼 매핑을 올바르게 완료해주세요.")
            else:
                 with st.spinner("GL/TB 비교 분석 중..."):
                    try:
                        # verify 함수 호출 시 사용자 매핑 정보 전달
                        ok, (totals, diffs, cols), diff_details_df = verify_gl_tb(
                            gl_file,
                            tb_file,
                            tb_header_row,
                            tb_col_map=user_tb_col_map,
                            tb_account_col=user_tb_account_col,
                            tb_total_label=user_tb_total_label
                        )

                        # --- 결과 표시 (이전과 동일 + 계정별 상세 내역) ---
                        st.subheader("📊 비교 결과 요약")
                        if ok: st.success("✅ 검증 성공: 전체 합계 일치")
                        else: st.error("❌ 검증 실패: 전체 합계 불일치")

                        col_gl, col_tb_tot, col_tb_bal = st.columns(3)
                        # (st.metric 등 결과 표시 로직은 이전 답변과 동일하게 유지)
                        with col_gl: ...
                        with col_tb_tot: ...
                        with col_tb_bal: ...

                        st.divider()
                        # ... (참고 비교 차이 markdown) ...

                        st.divider()
                        st.subheader("📝 계정별 상세 차이 내역")
                        if diff_details_df is not None and not diff_details_df.empty:
                            st.warning(f"{len(diff_details_df)}개 계정에서 GL과 TB 간 금액 차이가 발견되었습니다.")
                            st.dataframe(diff_details_df.style.format({
                                 col: '{:,.0f}' for col in diff_details_df.select_dtypes(include='number').columns
                             }), use_container_width=True)
                        else:
                            st.success("✅ 모든 계정에서 GL과 TB 간 금액이 일치합니다 (허용 오차 내).")

                    except FileNotFoundError as e: st.error(f"파일 처리 오류: {e}")
                    except ValueError as e: st.error(f"데이터 처리 오류: {e}")
                    except Exception as e: st.error(f"예상치 못한 오류: {e}"); st.exception(e)


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