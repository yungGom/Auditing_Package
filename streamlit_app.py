# streamlit_app.py

from __future__ import annotations
import io
import datetime as dt
import pandas as pd
import streamlit as st

# --- 페이지 기본 설정 ---
st.set_page_config(
    layout="wide",
    page_title="Advanced JET Program",
    page_icon="📊"
)

# --- 다른 로직 파일들을 안전하게 import ---
try:
    from logic_jet import (
        load_gl_for_jet,
        run_all_jet_scenarios
    )
    JET_LOGIC_AVAILABLE = True
except ImportError:
    JET_LOGIC_AVAILABLE = False

try:
    from logic_comparison import (
        load_tb,
        perform_roll_forward_test
    )
    COMP_LOGIC_AVAILABLE = True
except ImportError:
    COMP_LOGIC_AVAILABLE = False


# --- 세션 상태 초기화 ---
if "gl_df" not in st.session_state:
    st.session_state.gl_df = None
if "pre_tb_df" not in st.session_state:
    st.session_state.pre_tb_df = None
if "cur_tb_df" not in st.session_state:
    st.session_state.cur_tb_df = None
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False


# --- UI 구성 ---
st.title("📊 Advanced Journal Entry Test Program")
st.markdown("삼일회계법인 실무 자료에 기반한 감사 절차 자동화 프로그램 (Developed for 문용님)")

if not JET_LOGIC_AVAILABLE or not COMP_LOGIC_AVAILABLE:
    st.error("필수 로직 파일(`logic_jet.py`, `logic_comparison.py`)을 찾을 수 없습니다. 파일들이 `streamlit_app.py`와 같은 폴더에 있는지 확인하세요.")
    st.stop()

# --- 사이드바: 파일 업로드 및 설정 ---
with st.sidebar:
    st.header("📂 1. 데이터 업로드")
    gl_file = st.file_uploader("총계정원장 (GL)", type=["xlsx", "csv"])
    pre_tb_file = st.file_uploader("전기말 시산표 (Prior TB for Roll-forward)", type=["xlsx", "csv"])
    cur_tb_file = st.file_uploader("당기말 시산표 (Current TB)", type=["xlsx", "csv"])
    
    st.divider()
    
    if st.button("🔄 데이터 불러오기 및 검증", use_container_width=True):
        st.session_state.data_loaded = False # 재로딩 시 상태 초기화
        gl_ok, tb1_ok, tb2_ok = True, True, True
        
        with st.spinner("데이터를 불러오는 중입니다..."):
            if gl_file:
                try:
                    st.session_state.gl_df = load_gl_for_jet(gl_file)
                    st.info("✅ 총계정원장(GL) 로드 성공")
                except Exception as e:
                    st.error(f"GL 로드 실패: {e}")
                    gl_ok = False
            
            # Roll-forward용 TB 로딩
            if pre_tb_file:
                try:
                    # TB 로딩은 헤더를 0으로 가정. 복잡한 TB는 logic_comparison.py에서 처리 로직 추가 필요
                    st.session_state.pre_tb_df = load_tb(pre_tb_file, 0)
                    st.info("✅ 전기말 시산표(Prior TB) 로드 성공")
                except Exception as e:
                    st.error(f"전기말 TB 로드 실패: {e}")
                    tb1_ok = False

            if cur_tb_file:
                try:
                    st.session_state.cur_tb_df = load_tb(cur_tb_file, 0)
                    st.info("✅ 당기말 시산표(Current TB) 로드 성공")
                except Exception as e:
                    st.error(f"당기말 TB 로드 실패: {e}")
                    tb2_ok = False

            if gl_ok and tb1_ok and tb2_ok and gl_file and pre_tb_file and cur_tb_file:
                 st.session_state.data_loaded = True
                 st.success("모든 데이터가 성공적으로 로드되었습니다!")
            else:
                 st.warning("필요한 파일 중 일부가 로드되지 않았거나 오류가 발생했습니다.")


    st.divider()
    st.header("⚙️ 2. JET 시나리오 설정")
    
    # 설정값들을 st.session_state에 저장하여 유지
    st.session_state.jet_params = {
        'keywords': st.text_area("S1: 적요欄 검색 키워드", "수정,오류,조정,전기", help="쉼표로 구분"),
        'backdate_threshold': st.number_input("S2: 기표 지연일수 임계값", min_value=1, value=30),
        'rare_account_threshold': st.number_input("S3: 희귀 계정 사용빈도 임계값", min_value=1, value=5),
        'rare_user_threshold': st.number_input("S4: 희귀 입력자 사용빈도 임계값", min_value=1, value=5),
        'enable_weekend_holiday': st.checkbox("S5: 주말/공휴일 거래 검토", True),
        'round_number_zeros': st.number_input("S6: 라운드 넘버 (0의 개수)", min_value=2, value=3),
        'enable_abnormal_combo': st.checkbox("S7: 비경상적 계정조합(매출) 검토", True)
    }


# --- 메인 탭 구성 ---
tab1, tab2 = st.tabs(["1️⃣ 전표 완전성 검증 (Roll-forward)", "2️⃣ 분개 테스트 (JET)"])

with tab1:
    st.header(" 전표 완전성 검증 (Roll-forward Test)")
    st.markdown("""
    업로드된 **전기말 시산표, 당기 총계정원장, 당기말 시산표**를 사용하여 전표 데이터의 완전성을 검증합니다.  
    **검증 공식: `계정별 기초잔액(전기말TB) + 당기증감(GL) - 기말잔액(당기말TB) = 0`**
    """)

    if not st.session_state.data_loaded:
        st.info("👈 사이드바에서 GL, 전기말TB, 당기말TB 파일을 모두 업로드하고 '데이터 불러오기' 버튼을 눌러주세요.")
    else:
        if st.button("완전성 검증 실행", use_container_width=True):
            with st.spinner("계정별 대사 및 검증을 수행중입니다..."):
                try:
                    diff_df = perform_roll_forward_test(
                        st.session_state.gl_df,
                        st.session_state.pre_tb_df,
                        st.session_state.cur_tb_df
                    )
                    
                    st.subheader("📊 검증 결과")
                    if diff_df.empty:
                        st.success("✅ 완전성 검증 완료! 모든 계정에서 차이가 발견되지 않았습니다.")
                    else:
                        st.error(f"🚨 완전성 검증 실패! {len(diff_df)}개 계정에서 차이가 발견되었습니다.")
                        st.dataframe(diff_df.style.format(
                            {col: '{:,.0f}' for col in diff_df.select_dtypes(include='number').columns},
                            na_rep=""
                        ), use_container_width=True)
                        
                        # 결과 다운로드 버튼
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                            diff_df.to_excel(writer, sheet_name="Roll_forward_diff", index=False)
                        st.download_button(
                            label="📥 차이 내역 Excel 다운로드",
                            data=buffer.getvalue(),
                            file_name="roll_forward_differences.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                except Exception as e:
                    st.error(f"완전성 검증 중 오류가 발생했습니다: {e}")

with tab2:
    st.header("분개 테스트 (Journal Entry Test)")
    st.markdown("사이드바에서 설정된 조건에 따라 총계정원장(GL) 데이터에 대한 이상 징후를 탐지합니다.")
    
    if not st.session_state.gl_df is not None:
        st.info("👈 사이드바에서 총계정원장(GL) 파일을 업로드하고 '데이터 불러오기' 버튼을 눌러주세요.")
    else:
        if st.button("🚀 JET 전체 시나리오 실행", use_container_width=True):
            with st.spinner("전체 JET 시나리오를 실행 중입니다. 데이터 양에 따라 시간이 소요될 수 있습니다..."):
                try:
                    jet_results = run_all_jet_scenarios(
                        st.session_state.gl_df,
                        st.session_state.jet_params
                    )

                    st.subheader("📊 JET 실행 결과")
                    if not jet_results:
                        st.success("✅ 모든 JET 시나리오에서 특이사항이 발견되지 않았습니다.")
                    else:
                        st.success(f"🎉 JET 완료! {len(jet_results)}개 시나리오에서 결과가 발견되었습니다.")
                        
                        for scenario_name, result_df in jet_results.items():
                            with st.expander(f"📄 {scenario_name} - {len(result_df)}건 발견"):
                                st.dataframe(result_df, use_container_width=True, height=300)

                        # 전체 결과 다운로드
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                            for sheet_name, df_out in jet_results.items():
                                # 시트 이름 길이 31자 제한 처리
                                safe_sheet_name = sheet_name.replace(":", "").replace("?", "").replace("*", "")[:31]
                                df_out.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                        
                        st.download_button(
                            label="📥 JET 전체 결과 Excel 다운로드",
                            data=buffer.getvalue(),
                            file_name=f"JET_results_{dt.datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                except Exception as e:
                    st.error(f"JET 실행 중 오류가 발생했습니다: {e}")
