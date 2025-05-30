"""Streamlit Web App – Journal Entry Test (+ GL/TB Comparison)
================================================================
Run:
    streamlit run streamlit_app.py

Dependencies:
    pip install streamlit pandas numpy xlsxwriter openpyxl

Place this file in the same folder as:
    * journal_entry_test.py (Original JET logic)
    * difference.py (GL/TB comparison logic)
"""

from __future__ import annotations

import io
import datetime as dt
from pathlib import Path
import pandas as pd
import streamlit as st
import traceback # 에러 상세 출력을 위해 추가

# --- Streamlit 앱 기본 설정 ---
st.set_page_config(layout="wide", page_title="회계 감사 분석 도구")
st.title("📊 회계 감사 분석 도구")
st.markdown("총계정원장(GL) 및 시산표(TB)를 활용한 자동화된 분석 기능을 제공합니다.")

# --- 사이드바: 파일 업로드 및 설정 ---
with st.sidebar:
    st.header("📁 파일 업로드")
    gl_file = st.file_uploader(
        "총계정원장 (GL) 파일 업로드 (.xlsx, .csv)",
        type=["xlsx", "csv"],
        key="gl_uploader"
    )
    tb_file = st.file_uploader(
        "시산표 (TB) 파일 업로드 (.xlsx, .csv)",
        type=["xlsx", "csv"],
        key="tb_uploader"
    )

    st.divider()
    st.header("⚙️ 분개 테스트 (JET) 설정")
    # JET 시나리오용 설정값들
    keywords = st.text_area(
        "시나리오 1: 적요欄 검색 키워드 (쉼표로 구분)",
        "수정, 오류, 전기이월, 조정",
        help="예: 수정, 오류, 전기, 조정"
    )
    account_codes = st.text_input(
        "시나리오 2: 특정 계정코드 필터링 (쉼표로 구분)",
        "",
        help="예: 11120 (당좌예금), 40100 (상품매출)"
    )
    enable_s3 = st.checkbox("시나리오 3: 비정상적 수익 인식 검토 활성화", True)

    st.subheader("시나리오 4 & 5: 기간 및 빈도 설정")
    col_s45_1, col_s45_2 = st.columns(2)
    with col_s45_1:
        start_date = st.date_input("검색 시작일", None, key="jet_start_date")
    with col_s45_2:
        end_date = st.date_input("검색 종료일", None, key="jet_end_date")

    freq_account = st.number_input("시나리오 4: 희귀 계정과목 사용 빈도 임계값", min_value=1, value=3, step=1)
    freq_user = st.number_input("시나리오 5: 희귀 전기자 사용 빈도 임계값", min_value=1, value=3, step=1)

    st.subheader("시나리오 6: 주말/공휴일 거래 검토")
    enable_s6 = st.checkbox("시나리오 6: 주말/공휴일 거래 검토 활성화", True)
    holiday_file = st.file_uploader(
        "공휴일 목록 파일 (.xlsx, .csv) - (YYYY-MM-DD 형식, 첫 번째 열)",
        type=["xlsx", "csv"],
        key="holiday_uploader"
    )

    st.subheader("시나리오 7 & 8: 특정 숫자 패턴 검토")
    repeat_len = st.number_input("시나리오 7: 동일 숫자 반복 최소 길이", min_value=2, value=4, step=1)
    zero_digits = st.number_input("시나리오 8: Round Number (연속된 0의 개수)", min_value=2, value=3, step=1)


# --- 분석 유틸리티 Import ---
try:
    from journal_entry_test import (
        load_gl as load_gl_jet,  # JET용 GL 로드 함수
        scenario1_keyword,
        scenario2_account_code,
        scenario3_abnormal_sales,
        scenario4_rare_accounts,
        scenario5_rare_users,
        scenario6_weekend_holiday,
        scenario7_repeating_digits,
        scenario8_round_numbers
    )
    JET_AVAILABLE = True
except ImportError:
    JET_AVAILABLE = False
    st.sidebar.error("`journal_entry_test.py`를 찾을 수 없습니다. JET 기능을 사용할 수 없습니다.")

try:
    from difference import (
        verify as verify_gl_tb,
        detect_cols,
        load_tb  # GL/TB 비교용 TB 로드 함수
    )
    COMP_AVAILABLE = True
except ImportError:
    COMP_AVAILABLE = False
    st.sidebar.error("`difference.py`를 찾을 수 없습니다. GL/TB 비교 기능을 사용할 수 없습니다.")


# --- 탭 생성 ---
tab_comp_title = "1️⃣ GL vs TB 비교"
tab_jet_title = "2️⃣ 분개 테스트 (JET)"
tab_comp, tab_jet = st.tabs([tab_comp_title, tab_jet_title])


# --- Tab 1: GL vs TB Comparison ---
with tab_comp:
    if not COMP_AVAILABLE: # difference.py 로드 실패 시
        st.error("`difference.py` 파일을 찾을 수 없거나, 파일 내에 필요한 함수(verify, detect_cols, load_tb)가 없어 GL/TB 비교를 실행할 수 없습니다.")
        st.info("스크립트가 올바르게 준비되었는지 확인하세요.")
    elif gl_file is None or tb_file is None: # 파일 업로드가 안된 경우 (사이드바에서 업로드)
        st.info("👈 사이드바에서 총계정원장(GL)과 시산표(TB) 파일을 모두 업로드해주세요.")
    else:
        st.header("GL vs TB 합계/잔액 검증")
        st.markdown("업로드한 **총계정원장(GL)**과 **시산표(TB)**의 컬럼을 매핑하고 합계/잔액 및 상세 차이를 비교합니다.")

        st.subheader("⚙️ 시산표(TB) 설정 및 컬럼 매핑")

        # --- 세션 상태 초기화 ---
        if 'tb_cols' not in st.session_state:
            st.session_state.tb_cols = []
        if 'tb_header_input_val' not in st.session_state: # 헤더 행 번호 저장용
            st.session_state.tb_header_input_val = 0
        if 'tb_cols_load_success' not in st.session_state:
            st.session_state.tb_cols_load_success = False
        if 'tb_last_file_id' not in st.session_state:
             st.session_state.tb_last_file_id = None


        # 1. 헤더 행 번호 입력
        # 이전에 입력된 값을 유지하도록 value 설정
        current_header_val = st.session_state.get('tb_header_input_val', 0)
        tb_header_row_input = st.number_input(
            "시산표(TB) 실제 헤더 행 번호 (0-based)",
            min_value=0,
            value=current_header_val, # 세션 상태 값 사용
            step=1,
            key="tb_header_num_input", # 고유 키 부여
            help="시산표 파일에서 실제 열 이름이 있는 행의 번호 (0부터 시작)."
        )
        # 입력 값 변경 시 세션 상태에도 저장
        if tb_header_row_input != current_header_val:
            st.session_state.tb_header_input_val = tb_header_row_input
            st.session_state.tb_cols_load_success = False # 헤더 변경 시 컬럼 다시 로드 필요
            st.session_state.tb_cols = [] # 이전 컬럼 목록 초기화


        # 컬럼 목록을 업데이트하는 함수
        def refresh_tb_columns_from_file(uploaded_file, header_row_to_use):
            try:
                uploaded_file.seek(0) # 파일 포인터 초기화
                # difference.py의 load_tb 함수를 사용하여 실제 헤더 기준으로 컬럼 로드
                df_for_cols = load_tb(uploaded_file, header_row_to_use, filename=uploaded_file.name)
                st.session_state.tb_cols = df_for_cols.columns.astype(str).tolist()
                st.session_state.tb_cols_load_success = True
                st.success(f"'{uploaded_file.name}' 파일의 컬럼 목록을 헤더 행 {header_row_to_use}(으)로 성공적으로 읽어왔습니다.")
                uploaded_file.seek(0) # 다음 사용을 위해 파일 포인터 다시 초기화
            except Exception as e:
                st.session_state.tb_cols = []
                st.session_state.tb_cols_load_success = False
                st.error(f"선택한 헤더 행({header_row_to_use})(으)로 컬럼을 읽는 중 오류가 발생했습니다: {e}. 헤더 행 번호나 파일 형식을 확인해주세요.")
                if hasattr(uploaded_file, 'seek'): uploaded_file.seek(0)


        # 2. "선택한 헤더로 컬럼 목록 업데이트" 버튼
        if st.button("🔄 선택한 헤더로 컬럼 목록 업데이트", key="refresh_columns_button"):
            if tb_file:
                refresh_tb_columns_from_file(tb_file, st.session_state.tb_header_input_val)
            else:
                st.warning("먼저 시산표(TB) 파일을 업로드해주세요.")

        # 파일이 변경되었는지 확인하고, 변경되었다면 안내 메시지 표시
        if tb_file:
            current_file_id = getattr(tb_file, 'file_id', id(tb_file))
            if st.session_state.tb_last_file_id != current_file_id:
                st.session_state.tb_last_file_id = current_file_id
                st.session_state.tb_cols_load_success = False # 새 파일이므로 컬럼 다시 로드 필요
                st.session_state.tb_cols = [] # 이전 컬럼 목록 초기화
                st.info(f"새로운 시산표 파일 '{tb_file.name}'이(가) 선택되었습니다. 헤더 행 번호를 확인하고 '컬럼 목록 업데이트' 버튼을 눌러주세요.")

        # 컬럼 로드 상태에 따른 메시지
        if not st.session_state.tb_cols and tb_file and not st.session_state.tb_cols_load_success:
             st.warning("정확한 컬럼 선택을 위해, 위에서 '실제 헤더 행 번호'를 설정한 후 '컬럼 목록 업데이트' 버튼을 꼭 눌러주세요.")


        # --- 이제 st.session_state.tb_cols에는 올바른 컬럼 이름이 들어있다고 가정 ---

        # 3. 합계 행 정보 입력
        col_label1, col_label2 = st.columns(2)
        with col_label1:
            tb_account_col_options = st.session_state.get('tb_cols', []) # 여기서 올바른 목록 사용
            # 기본 선택 로직 (이전과 유사하게, 혹은 첫 번째 옵션으로)
            default_acct_col_val = '계정과목' if '계정과목' in tb_account_col_options else \
                                  ('계정 과목' if '계정 과목' in tb_account_col_options else \
                                  (tb_account_col_options[0] if tb_account_col_options else None))
            tb_account_col_selected = st.selectbox(
                "합계 레이블 포함 열 (계정과목 열)",
                options=tb_account_col_options,
                index=tb_account_col_options.index(default_acct_col_val) if default_acct_col_val and default_acct_col_val in tb_account_col_options else 0,
                key="tb_account_col_select",
                help="시산표에서 '합계' 또는 '총계' 텍스트가 있는 열을 선택하세요. (컬럼 목록 업데이트 후 선택)"
            )
        with col_label2:
            tb_total_label_input = st.text_input(
                "합계 행 식별 텍스트", value="합계", key="tb_total_label_input",
                help="시산표 맨 아래 합계 행을 나타내는 정확한 텍스트 (예: 합계, 총계)"
            )

        # 4. 주요 금액 컬럼 매핑
        st.markdown("**주요 금액 컬럼 매핑:** (컬럼 목록 업데이트 후, 자동 감지 결과를 확인하고 필요시 수정)")

        detected_map = {}
        # 자동 감지는 컬럼이 성공적으로 로드된 후에만 시도
        if tb_file and st.session_state.get('tb_cols_load_success', False) and st.session_state.get('tb_cols'):
            try:
                tb_file.seek(0)
                # 자동 감지 시에도 현재 설정된 헤더 행 번호 사용
                current_header_for_detect = st.session_state.get("tb_header_input_val", 0)
                temp_tb_df_detect = load_tb(tb_file, current_header_for_detect, filename=tb_file.name)
                tb_file.seek(0) # 다음 사용을 위해 포인터 초기화

                d_bal, c_bal, d_tot, c_tot = detect_cols(temp_tb_df_detect) # difference.py의 함수
                detected_map = {'bal_d': d_bal, 'bal_c': c_bal, 'tot_d': d_tot, 'tot_c': c_tot}
                st.caption(f"자동 감지 결과 (헤더 {current_header_for_detect} 기준): 차변잔액({d_bal}), 대변잔액({c_bal}), 차변합계({d_tot}), 대변합계({c_tot})")
            except Exception as e_detect:
                st.warning(f"컬럼 자동 감지 중 오류 (헤더 {st.session_state.get('tb_header_input_val', 0)} 기준): {e_detect}. 수동으로 지정해주세요.")
                if st.checkbox("자동 감지 오류 상세 보기", key="show_detect_error_checkbox"):
                    st.exception(e_detect)
        elif tb_file: # 파일은 있지만 컬럼 로드가 안된 경우
            st.caption("컬럼 목록을 먼저 업데이트해야 자동 감지가 실행됩니다.")


        col_map1, col_map2 = st.columns(2)
        tb_col_options_for_mapping = st.session_state.get('tb_cols', []) + [None] # None 옵션 추가

        def get_col_index_for_mapping(col_name_to_find):
            try:
                return tb_col_options_for_mapping.index(col_name_to_find) if col_name_to_find and col_name_to_find in tb_col_options_for_mapping else len(tb_col_options_for_mapping) -1 # 못찾으면 None
            except ValueError:
                return len(tb_col_options_for_mapping) - 1

        with col_map1:
            d_bal_selected = st.selectbox("차변 잔액 열", options=tb_col_options_for_mapping, index=get_col_index_for_mapping(detected_map.get('bal_d')), key="d_bal_select_map")
            d_tot_selected = st.selectbox("차변 합계 열", options=tb_col_options_for_mapping, index=get_col_index_for_mapping(detected_map.get('tot_d')), key="d_tot_select_map")
        with col_map2:
            c_bal_selected = st.selectbox("대변 잔액 열", options=tb_col_options_for_mapping, index=get_col_index_for_mapping(detected_map.get('bal_c')), key="c_bal_select_map")
            c_tot_selected = st.selectbox("대변 합계 열", options=tb_col_options_for_mapping, index=get_col_index_for_mapping(detected_map.get('tot_c')), key="c_tot_select_map")

        # --- Comparison Execution Button and Logic ---
        st.divider()
        # 실행 버튼은 모든 필수 파일이 있고, 컬럼 로드가 성공했을 때 활성화되도록 고려 가능
        is_ready_for_comparison = gl_file and tb_file and st.session_state.get('tb_cols_load_success', False)
        run_comp_btn = st.button("📊 GL/TB 합계 비교 실행", key="run_comparison_button", disabled=(not is_ready_for_comparison))

        if run_comp_btn: # 버튼 클릭 시
            if not is_ready_for_comparison:
                st.error("GL 파일, TB 파일이 모두 업로드되고, TB 컬럼 목록이 성공적으로 업데이트되어야 비교를 실행할 수 있습니다.")
            else:
                user_tb_col_map = {
                    'bal_d': d_bal_selected, 'bal_c': c_bal_selected,
                    'tot_d': d_tot_selected, 'tot_c': c_tot_selected
                }
                # header_row는 위에서 입력받은 tb_header_row_input 또는 세션 상태의 st.session_state.tb_header_input_val 사용
                actual_header_row_for_verify = st.session_state.get("tb_header_input_val", 0)

                if not all(user_tb_col_map.values()) or not tb_account_col_selected or not tb_total_label_input:
                    st.error("시산표(TB) 설정 및 모든 주요 금액 컬럼(차/대변 잔액, 차/대변 합계), 계정과목 열, 합계 행 식별 텍스트를 올바르게 설정 및 선택해주세요.")
                else:
                    with st.spinner("GL/TB 비교 분석 중... 잠시만 기다려주세요."):
                        try:
                            gl_file.seek(0)
                            tb_file.seek(0)
                            ok, (totals, diffs, cols_from_verify), diff_details_df = verify_gl_tb(
                                gl_file, tb_file,
                                header_row=actual_header_row_for_verify, # 수정된 파라미터 이름 사용
                                tb_col_map=user_tb_col_map,
                                tb_account_col=tb_account_col_selected,
                                tb_total_label=tb_total_label_input
                            )

                            # --- 디버깅을 위한 정보 출력 (임시) ---
                            st.divider()
                            st.subheader("🕵️ 디버깅 정보")
                            st.write(f"함수 반환 'ok': {ok}")
                            st.write(f"함수 반환 'totals':")
                            st.json(totals if totals is not None else "None") # totals가 None일 경우를 대비
                            st.write(f"함수 반환 'diffs':")
                            st.json(diffs if diffs is not None else "None") # diffs가 None일 경우를 대비
                            st.write(f"함수 반환 'cols_from_verify': {cols_from_verify}")
                            st.write(f"함수 반환 'diff_details_df' is None: {diff_details_df is None}")
                            if diff_details_df is not None:
                                st.write(f"함수 반환 'diff_details_df' is empty: {diff_details_df.empty}")
                                st.write("diff_details_df 내용 (상위 5개):")
                                st.dataframe(diff_details_df.head())
                            st.divider()
                            # --- 디버깅 정보 출력 끝 ---

                            st.subheader("📊 비교 결과 요약") # 이 부분은 이미지에서 보입니다.
                            if ok: # ok가 True 또는 False 여야 합니다.
                                st.success("✅ 검증 성공: 전체 합계 일치")
                            else: # ok가 False 이거나 bool이 아닌 다른 값(예: None)일 경우
                                st.error("❌ 검증 실패: 전체 합계 불일치 (또는 'ok' 상태값 문제)")
                                if ok is None: # 만약 ok가 None이라면 추가 정보 제공
                                     st.warning("'ok' 변수가 None입니다. verify_gl_tb 함수 반환값을 확인해주세요.")


                                # streamlit_app.py의 결과 표시 부분 수정 예시
                                if totals and isinstance(totals, dict):
                                    st.write("#### 📊 전체 합계 요약")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("GL 차변", f"{totals.get('gl_d', 0):,.0f}")
                                        st.metric("GL 대변", f"{totals.get('gl_c', 0):,.0f}")
                                    with col2:
                                        st.metric("TB 차변 합계", f"{totals.get('tb_tot_d', 0):,.0f}")
                                        st.metric("TB 대변 합계", f"{totals.get('tb_tot_c', 0):,.0f}")
                                    with col3:
                                        st.metric("TB 차변 잔액", f"{totals.get('tb_bal_d', 0):,.0f}")
                                        st.metric("TB 대변 잔액", f"{totals.get('tb_bal_c', 0):,.0f}")
                                else:
                                    st.warning("요약 합계(totals) 정보가 없거나 잘못된 형식입니다.")

                            st.divider()
                            st.subheader("📝 계정별 상세 차이 내역")
                            if diff_details_df is not None and not diff_details_df.empty:
                                st.warning(f"{len(diff_details_df)}개 계정에서 GL과 TB 간 금액 차이가 발견되었습니다.")
                                st.dataframe(diff_details_df.style.format({
                                    col: '{:,.0f}' for col in diff_details_df.select_dtypes(include='number').columns
                                }), use_container_width=True)
                            elif ok and (diff_details_df is None or diff_details_df.empty): # ok는 True인데 차이가 없는 경우
                                st.success("✅ 모든 계정에서 GL과 TB 간 금액이 일치합니다 (허용 오차 내).")
                            elif not ok and (diff_details_df is None or diff_details_df.empty): # ok는 False인데 차이 내역이 없는 경우
                                 st.info("전체 합계는 불일치하지만, 상세 차이 내역은 없습니다. (예: 시산표 합계 행 자체의 문제일 수 있음)")

                            # ... (이하 결과 표시 로직은 이전과 유사하게 구성) ...
                            st.subheader("📈 비교 결과 요약")
                            if ok: st.success("✅ 검증 성공: GL과 TB의 전체 합계가 일치합니다.")
                            # ... (이하 생략) ...

                        except FileNotFoundError as e_fnf: st.error(f"파일 처리 오류: {e_fnf}")
                        except ValueError as e_val: st.error(f"데이터 처리 오류: {e_val}")
                        except Exception as e_generic:
                            st.error(f"GL/TB 비교 중 예상치 못한 오류 발생: {e_generic}")
                            st.exception(e_generic)
                            
# --- Tab 2: Journal Entry Test ---
with tab_jet:
    if not JET_AVAILABLE:
        st.error("`journal_entry_test.py` 파일을 찾을 수 없거나, 파일 내에 필요한 함수들이 없어 분개 테스트를 실행할 수 없습니다.")
        st.info("스크립트가 올바르게 준비되었는지 확인하세요.")
    elif gl_file is None:
        st.info("👈 사이드바에서 총계정원장(GL) 파일을 먼저 업로드해주세요.")
    else:
        st.header("분개 테스트 실행 (Journal Entry Test)")
        st.markdown("업로드한 **총계정원장(GL)** 데이터에 대해 다양한 조건의 분개 테스트를 실행합니다. 설정은 사이드바에서 변경하세요.")

        run_jet_btn = st.button("🚀 분개 테스트 실행", key="run_jet")

        if run_jet_btn:
            with st.spinner("분개 테스트 분석 중... 시간이 다소 소요될 수 있습니다."):
                try:
                    gl_file.seek(0) # 파일 포인터 초기화
                    df_gl = load_gl_jet(gl_file) # journal_entry_test.py 안의 load_gl 함수
                    if df_gl is None or df_gl.empty:
                        raise ValueError("총계정원장(GL) 파일 로딩에 실패했거나 데이터가 비어있습니다 (JET용).")

                    results: dict[str, pd.DataFrame] = {}
                    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
                    ac_list = [c.strip() for c in account_codes.split(",") if c.strip()]

                    # 시나리오 1
                    if kw_list:
                        res = scenario1_keyword(df_gl, kw_list)
                        if not res.empty: results["시나리오1_키워드검색"] = res
                    # 시나리오 2
                    if ac_list:
                        res = scenario2_account_code(df_gl, ac_list)
                        if not res.empty: results["시나리오2_특정계정검색"] = res
                    # 시나리오 3
                    if enable_s3:
                        res = scenario3_abnormal_sales(df_gl)
                        if not res.empty: results["시나리오3_비정상매출"] = res

                    # 기간 설정 (datetime 객체로 변환)
                    start_datetime = dt.datetime.combine(start_date, dt.time.min) if start_date else None
                    end_datetime = dt.datetime.combine(end_date, dt.time.max) if end_date else None

                    # 시나리오 4
                    res = scenario4_rare_accounts(df_gl, start_datetime, end_datetime, freq_account)
                    if not res.empty: results["시나리오4_희귀계정"] = res
                    # 시나리오 5
                    res = scenario5_rare_users(df_gl, start_datetime, end_datetime, freq_user)
                    if not res.empty: results["시나리오5_희귀입력자"] = res

                    # 시나리오 6 (공휴일 파일 처리)
                    holiday_path_for_jet = None
                    if enable_s6 and holiday_file:
                        try:
                            temp_dir = Path("./temp_jet_files")
                            temp_dir.mkdir(exist_ok=True)
                            # 파일 이름을 고유하게 만들기 (옵션)
                            temp_holiday_filepath = temp_dir / f"holidays_{holiday_file.file_id}.csv"
                            with open(temp_holiday_filepath, "wb") as f:
                                f.write(holiday_file.getvalue())
                            holiday_path_for_jet = str(temp_holiday_filepath)
                            res = scenario6_weekend_holiday(df_gl, holiday_path_for_jet)
                            if not res.empty: results["시나리오6_주말휴일거래"] = res
                        except Exception as e_holiday:
                            st.warning(f"공휴일 파일 처리 중 오류 (시나리오 6): {e_holiday}")
                    elif enable_s6 and not holiday_file:
                         st.warning("시나리오 6 (주말/공휴일 거래)이 활성화되었지만 공휴일 파일이 업로드되지 않았습니다. 주말 거래만 검토합니다.")
                         res = scenario6_weekend_holiday(df_gl, None) # 공휴일 파일 없이 주말만 검토
                         if not res.empty: results["시나리오6_주말거래"] = res


                    # 시나리오 7
                    res = scenario7_repeating_digits(df_gl, repeat_len)
                    if not res.empty: results["시나리오7_반복숫자금액"] = res
                    # 시나리오 8
                    res = scenario8_round_numbers(df_gl, zero_digits)
                    if not res.empty: results["시나리오8_라운드넘버금액"] = res

                    if not results:
                        st.success("✅ 모든 분개 테스트 시나리오에서 특이사항이 발견되지 않았습니다.")
                    else:
                        st.success(f"🎉 분개 테스트 완료! {len(results)}개 시나리오에서 결과가 나왔습니다. 아래에서 확인하거나 Excel로 다운로드하세요.")
                        for sheet_name, df_out in results.items():
                            with st.expander(f"{sheet_name} – {len(df_out):,} 건"):
                                st.dataframe(df_out, use_container_width=True)

                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                            for sheet_name, df_out in results.items():
                                df_out.to_excel(writer, sheet_name=sheet_name[:31], index=False) # 시트 이름 길이 제한
                        buffer.seek(0)
                        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.download_button(
                            label="📥 분개 테스트 결과 Excel 다운로드",
                            data=buffer,
                            file_name=f"JET_results_{timestamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_jet_results"
                        )
                except ValueError as e_val:
                    st.error(f"분개 테스트 데이터 처리 오류: {e_val}")
                except Exception as e_jet:
                    st.error(f"분개 테스트 실행 중 예상치 못한 오류 발생: {e_jet}")
                    st.exception(e_jet) # 전체 traceback 출력

st.sidebar.divider()
