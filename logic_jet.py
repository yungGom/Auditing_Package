import pandas as pd

# --------------------------------------------------------------------------------
# 기존 기능: 시산표 계산 함수 (Original Function: Trial Balance Calculation)
# --------------------------------------------------------------------------------
def calculate_trial_balance(pre_tb_df, journal_df, post_tb_df):
    """
    전기 시산표와 분개장 데이터를 바탕으로 당기 시산표를 계산합니다.

    ---
    ### 시나리오 분석 (Scenario Analysis)

    이 함수는 회계감사의 기본 절차 중 하나인 시산표 검증을 자동화합니다.
    '전기시산표 + 분개장 = 당기시산표'라는 회계 등식을 기반으로 작동하며,
    다음과 같은 세 가지 데이터를 입력받습니다.

    1.  **전기 시산표 (pre_tb_df)**: 회계 기간 시작 시점의 잔액 정보
        - `계정코드`: 계정의 고유 식별자
        - `계정과목`: 계정의 이름 (예: 현금, 외상매출금)
        - `차변잔액`: 자산, 비용 계정의 기초 잔액
        - `대변잔액`: 부채, 자본, 수익 계정의 기초 잔액

    2.  **분개장 (journal_df)**: 회계 기간 동안 발생한 모든 거래 기록
        - `계정코드`: 거래에 사용된 계정
        - `차변금액`: 계정의 차변에 기록된 금액 (자산/비용 증가 등)
        - `대변금액`: 계정의 대변에 기록된 금액 (부채/자본 증가 등)

    3.  **당기 시산표 (post_tb_df)**: 검증의 목표가 되는 실제 기말 잔액 정보
        - 전기 시산표와 구조는 동일하며, 계정과목 정보를 참조하는 데 사용됩니다.

    ### 핵심 로직 (Core Logic)

    회계 원리에 따라 기말 잔액은 다음과 같이 계산됩니다.
    `기말 잔액 = 기초 잔액 + 당기 증가액 - 당기 감소액`

    이를 시산표 계산에 적용하면 다음과 같습니다.
    - **잔액 계산**: `(기초 차변잔액 + 당기 차변금액 합계) - (기초 대변잔액 + 당기 대변금액 합계)`
    - **최종 잔액 결정**: 위 계산 결과가 양수(+)이면 차변 잔액으로, 음수(-)이면 절댓값을 취해 대변 잔액으로 기록합니다.
    ---

    Args:
        pre_tb_df (pd.DataFrame): 전기 시산표 데이터프레임
        journal_df (pd.DataFrame): 분개장 데이터프레임
        post_tb_df (pd.DataFrame): 당기 시산표 데이터프레임 (계정과목 정보 참조용)

    Returns:
        pd.DataFrame: 계산된 당기 시산표 데이터프레임
    """
    # --- 1. 데이터 전처리 ---
    if '차변진액' in pre_tb_df.columns:
        pre_tb_df.rename(columns={'차변진액': '차변잔액'}, inplace=True)

    journal_df['차변금액'] = pd.to_numeric(journal_df['차변금액'], errors='coerce').fillna(0)
    journal_df['대변금액'] = pd.to_numeric(journal_df['대변금액'], errors='coerce').fillna(0)
    journal_sum = journal_df.groupby('계정코드')[['차변금액', '대변금액']].sum().reset_index()

    # --- 2. 데이터 병합 ---
    merged_tb = pd.merge(pre_tb_df, journal_sum, on='계정코드', how='outer').fillna(0)

    # --- 3. 기말 잔액 계산 ---
    balance = (merged_tb['차변잔액'] + merged_tb['차변금액']) - \
              (merged_tb['대변잔액'] + merged_tb['대변금액'])
    merged_tb['계산된_차변잔액'] = balance.where(balance >= 0, 0).astype(int)
    merged_tb['계산된_대변잔액'] = abs(balance.where(balance < 0, 0)).astype(int)

    # --- 4. 최종 데이터 정리 ---
    if '계정과목' in merged_tb.columns:
        merged_tb.drop('계정과목', axis=1, inplace=True)
    final_tb = pd.merge(merged_tb[['계정코드', '계산된_차변잔액', '계산된_대변잔액']],
                        post_tb_df[['계정코드', '계정과목']],
                        on='계정코드',
                        how='left')
    final_tb.rename(columns={'계산된_차변잔액': '차변잔액', '계산된_대변잔액': '대변잔액'}, inplace=True)
    return final_tb[['계정코드', '계정과목', '차변잔액', '대변잔액']]


# --------------------------------------------------------------------------------
# 추가 기능: 시나리오 기반 분석 함수 (New Functions: Scenario-based Analysis)
# --------------------------------------------------------------------------------

def scenario_A02_check_dr_cr_balance(journal_df):
    """
    시나리오 A02: 전표번호별 차대변 일치 검증 (Transaction DR/CR Test)
    각 전표번호 내의 차변금액 합계와 대변금액 합계가 일치하는지 검증합니다.

    Args:
        journal_df (pd.DataFrame): 분개장 데이터프레임

    Returns:
        pd.DataFrame: 차대변 금액이 일치하지 않는 전표번호 목록
    """
    # 금액 필드를 숫자형으로 변환
    journal_df['차변금액'] = pd.to_numeric(journal_df['차변금액'], errors='coerce').fillna(0)
    journal_df['대변금액'] = pd.to_numeric(journal_df['대변금액'], errors='coerce').fillna(0)

    # 전표번호별로 차/대변 합계 계산
    grouped = journal_df.groupby('전표번호').agg(
        차변합계=('차변금액', 'sum'),
        대변합계=('대변금액', 'sum')
    ).reset_index()

    # 차이가 0이 아닌 (불일치하는) 전표만 필터링
    unbalanced_journals = grouped[grouped['차변합계'] != grouped['대변합계']]
    return unbalanced_journals


def scenario_JS001_sales_and_purchase_analysis(journal_df, sales_accounts, purchase_accounts):
    """
    시나리오 JS001: 동일거래처의 매출과 매입 동시 발생 검토
    매출과 매입이 함께 발생하는 거래처를 식별합니다.

    Args:
        journal_df (pd.DataFrame): 분개장 데이터프레임
        sales_accounts (list): 매출로 간주할 계정코드 리스트
        purchase_accounts (list): 매입으로 간주할 계정코드 리스트

    Returns:
        pd.DataFrame: 매출과 매입이 동시에 발생한 거래처 목록과 관련 전표
    """
    # 매출 전표와 매입 전표를 필터링
    sales_journals = journal_df[journal_df['계정코드'].isin(sales_accounts)]
    purchase_journals = journal_df[journal_df['계정코드'].isin(purchase_accounts)]

    # 매출이 발생한 거래처와 매입이 발생한 거래처 목록 생성
    sales_clients = set(sales_journals['거래처코드'].dropna().unique())
    purchase_clients = set(purchase_journals['거래처코드'].dropna().unique())

    # 두 목록에 모두 포함된 거래처(교집합)를 찾음
    common_clients = list(sales_clients.intersection(purchase_clients))

    # 해당 거래처들의 모든 전표를 반환
    result_df = journal_df[journal_df['거래처코드'].isin(common_clients)].sort_values(by=['거래처코드', '전표일자'])
    return result_df

def scenario_JS006_unusual_monthly_sales(journal_df, sales_accounts, threshold_multiplier=3.0):
    """
    시나리오 JS006: 비경상적 매출 트렌드 검토
    거래처별 월평균 매출액 대비 특정 월의 매출이 비정상적으로 높은 거래처를 탐지합니다.

    Args:
        journal_df (pd.DataFrame): 분개장 데이터프레임
        sales_accounts (list): 매출로 간주할 계정코드 리스트
        threshold_multiplier (float): 월평균 대비 몇 배 이상일 때 이상징후로 판단할지 설정 (기본값: 3배)

    Returns:
        pd.DataFrame: 비경상적인 월 매출이 발생한 거래처의 해당 월 전표
    """
    # 매출 전표만 필터링
    sales_df = journal_df[journal_df['계정코드'].isin(sales_accounts)].copy()
    
    # 날짜 형식 변환 및 '연월' 컬럼 생성
    sales_df['전표일자'] = pd.to_datetime(sales_df['전표일자'], format='%Y%m%d', errors='coerce')
    sales_df.dropna(subset=['전표일자'], inplace=True)
    sales_df['연월'] = sales_df['전표일자'].dt.to_period('M')

    # 거래처별 월별 매출액 계산
    monthly_sales = sales_df.groupby(['거래처코드', '연월'])['대변금액'].sum().reset_index()

    # 거래처별 평균 월 매출액 계산
    avg_sales = monthly_sales.groupby('거래처코드')['대변금액'].mean().reset_index()
    avg_sales.rename(columns={'대변금액': '월평균매출액'}, inplace=True)

    # 월별 매출 데이터와 평균 매출 데이터 병합
    merged_sales = pd.merge(monthly_sales, avg_sales, on='거래처코드')

    # 평균 대비 특정 월 매출이 임계치를 초과하는 경우 필터링
    unusual_sales = merged_sales[merged_sales['대변금액'] > merged_sales['월평균매출액'] * threshold_multiplier]

    # 원본 분개장에서 해당 거래처와 연월의 전표를 추출하여 반환
    result_df = pd.merge(sales_df, unusual_sales[['거래처코드', '연월']], on=['거래처코드', '연월'])
    return result_df.sort_values(by=['거래처코드', '전표일자'])
