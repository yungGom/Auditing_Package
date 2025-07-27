import streamlit as st
import pandas as pd
from logic_jet import calculate_trial_balance, scenario_A02_check_dr_cr_balance, scenario_JS001_sales_and_purchase_analysis, scenario_JS006_unusual_monthly_sales
from logic_comparison import compare_trial_balances

st.set_page_config(layout="wide")

st.title("🔍 회계감사 Journal Entry Test 자동화 툴")
st.write("전기/당기 시산표와 분개장 CSV 파일을 업로드하여 시산표 검증 및 이상 징후 분석을 수행합니다.")

# --- 파일 업로드 섹션 ---
with st.sidebar:
    st.header("1. 파일 업로드")
    pre_tb_file = st.file_uploader("전기 시산표 (CSV)", type="csv")
    journal_file = st.file_uploader("분개장 (CSV)", type="csv")
    post_tb_file = st.file_uploader("당기 시산표 (CSV)", type="csv")
    
    # --- 시나리오 선택 UI ---
    st.header("2. 분석 시나리오 선택")
    
    # 사용 가능한 시나리오 목록
    scenario_options = {
        "A02: 전표 차/대변 일치 검증": "A02",
        "A03: 시산표 검증 (기초+분개장=기말)": "A03",
        "JS001: 매출/매입 동시 발생 거래처 분석": "JS001",
        "JS006: 비경상적 월 매출 트렌드 분석": "JS006"
    }
    
    selected_scenarios = st.multiselect(
        "실행할 분석 시나리오를 선택하세요.",
        options=list(scenario_options.keys()),
        default=["A03: 시산표 검증 (기초+분개장=기말)"] # 기본 선택값
    )
    
    run_button = st.button("분석 실행", type="primary")


# --- 메인 로직 실행 ---
if not (pre_tb_file and journal_file and post_tb_file):
    st.info("검증을 시작하려면 사이드바에서 세 종류의 파일을 모두 업로드하고 '분석 실행' 버튼을 클릭해주세요.")
else:
    if run_button:
        try:
            # 업로드된 파일들을 pandas 데이터프레임으로 읽어옵니다.
            pre_tb_df = pd.read_csv(pre_tb_file, encoding='cp949')
            journal_df = pd.read_csv(journal_file, encoding='cp949')
            post_tb_df = pd.read_csv(post_tb_file, encoding='cp949')

            st.success("모든 파일이 성공적으로 로드되었습니다. 선택한 시나리오 분석을 시작합니다.")
            
            # 선택된 시나리오 ID 목록
            selected_ids = [scenario_options[s] for s in selected_scenarios]

            # --- 시나리오별 분석 및 결과 출력 ---
            
            # A03: 시산표 검증 (필수 시나리오)
            if "A03" in selected_ids:
                with st.expander("A03: 시산표 검증 (기초+분개장=기말)", expanded=True):
                    with st.spinner('당기 시산표를 계산하고 비교하는 중입니다...'):
                        calculated_tb = calculate_trial_balance(pre_tb_df, journal_df, post_tb_df)
                        st.write("🧮 **계산된 당기 시산표**")
                        st.dataframe(calculated_tb)
                        
                        diff_df = compare_trial_balances(calculated_tb, post_tb_df)
                        st.write("📊 **비교 결과**")
                        if diff_df.empty:
                            st.success("🎉 검증 완료! 계산된 시산표와 제공된 당기 시산표가 완전히 일치합니다.")
                        else:
                            st.error("⚠️ 검증 실패! 아래 계정에서 차이가 발견되었습니다.")
                            st.dataframe(diff_df)

            # A02: 전표 차/대변 일치 검증
            if "A02" in selected_ids:
                with st.expander("A02: 전표 차/대변 일치 검증", expanded=True):
                    with st.spinner('전표의 차/대변 금액 일치 여부를 검증하는 중입니다...'):
                        unbalanced = scenario_A02_check_dr_cr_balance(journal_df)
                        if not unbalanced.empty:
                            st.warning(f"총 {len(unbalanced)}개의 전표에서 차/대변 불일치가 발견되었습니다.")
                            st.dataframe(unbalanced)
                        else:
                            st.success("✅ 모든 전표의 차/대변 금액이 일치합니다.")
            
            # JS001: 매출/매입 동시 발생 거래처 분석
            if "JS001" in selected_ids:
                with st.expander("JS001: 매출/매입 동시 발생 거래처 분석", expanded=True):
                    # 계정과목표(당기 시산표)에서 매출/매입 계정 자동 식별
                    all_accounts = post_tb_df.astype({'계정코드': str})
                    sales_acc = all_accounts[all_accounts['계정코드'].str.startswith('4')]['계정코드'].astype(int).tolist()
                    purchase_acc = all_accounts[all_accounts['계정코드'].str.startswith('14') | all_accounts['계정코드'].str.startswith('5')]['계정코드'].astype(int).tolist()
                    
                    st.write(f"매출 계정(4xxxx) {len(sales_acc)}개, 매입/원가 관련 계정(14xxx, 5xxxx) {len(purchase_acc)}개를 대상으로 분석합니다.")
                    
                    with st.spinner('매출과 매입이 동시에 발생한 거래처를 분석하는 중입니다...'):
                        common_journals = scenario_JS001_sales_and_purchase_analysis(journal_df, sales_acc, purchase_acc)
                        common_clients_count = len(common_journals['거래처코드'].unique())
                        if common_clients_count > 0:
                            st.warning(f"총 {common_clients_count}개의 거래처에서 매출과 매입이 동시에 발생했습니다.")
                            st.dataframe(common_journals)
                        else:
                            st.success("✅ 매출과 매입이 동시에 발생한 거래처가 없습니다.")

            # JS006: 비경상적 월 매출 트렌드 분석
            if "JS006" in selected_ids:
                 with st.expander("JS006: 비경상적 월 매출 트렌드 분석", expanded=True):
                    all_accounts = post_tb_df.astype({'계정코드': str})
                    sales_acc = all_accounts[all_accounts['계정코드'].str.startswith('4')]['계정코드'].astype(int).tolist()
                    
                    multiplier = st.slider("월평균 매출액 대비 배수 설정", 1.0, 10.0, 3.0, 0.5)
                    st.write(f"월평균 매출액의 **{multiplier}배**를 초과하는 월 매출이 발생한 거래처를 탐지합니다.")

                    with st.spinner('비정상적인 월 매출 패턴을 분석하는 중입니다...'):
                        unusual_sales_df = scenario_JS006_unusual_monthly_sales(journal_df, sales_acc, multiplier)
                        unusual_clients_count = len(unusual_sales_df['거래처코드'].unique())
                        if unusual_clients_count > 0:
                            st.warning(f"총 {unusual_clients_count}개의 거래처에서 비경상적인 월 매출이 발견되었습니다.")
                            st.dataframe(unusual_sales_df)
                        else:
                            st.success("✅ 비경상적인 월 매출 트렌드가 발견되지 않았습니다.")

        except Exception as e:
            st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
            st.warning("CSV 파일의 인코딩(e.g., 'cp949', 'utf-8') 또는 컬럼명이 올바른지 확인해주세요.")
