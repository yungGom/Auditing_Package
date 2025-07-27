import pandas as pd

def calculate_trial_balance(pre_tb_df, journal_df, post_tb_df):
    """
    전기 시산표와 분개장 데이터를 바탕으로 당기 시산표를 계산합니다.

    Args:
        pre_tb_df (pd.DataFrame): 전기 시산표 데이터프레임
        journal_df (pd.DataFrame): 분개장 데이터프레임
        post_tb_df (pd.DataFrame): 당기 시산표 데이터프레임 (계정과목 정보 참조용)

    Returns:
        pd.DataFrame: 계산된 당기 시산표 데이터프레임
    """
    # --- 1. 데이터 전처리 ---
    # 전기 시산표의 '차변진액' 오타를 '차변잔액'으로 수정합니다.
    if '차변진액' in pre_tb_df.columns:
        pre_tb_df.rename(columns={'차변진액': '차변잔액'}, inplace=True)

    # 분개장 금액 열의 결측값을 0으로 채웁니다.
    journal_df['차변금액'] = journal_df['차변금액'].fillna(0)
    journal_df['대변금액'] = journal_df['대변금액'].fillna(0)

    # 숫자가 아닌 데이터가 있어도 오류가 나지 않도록 숫자형으로 변환합니다.
    journal_df['차변금액'] = pd.to_numeric(journal_df['차변금액'], errors='coerce').fillna(0)
    journal_df['대변금액'] = pd.to_numeric(journal_df['대변금액'], errors='coerce').fillna(0)

    # 계정코드별로 분개 내역을 합산합니다.
    journal_sum = journal_df.groupby('계정코드')[['차변금액', '대변금액']].sum().reset_index()

    # --- 2. 데이터 병합 ---
    # 전기 시산표와 분개장 합계를 계정코드를 기준으로 외부 조인(outer join)합니다.
    # 이렇게 하면 한쪽에만 존재하는 계정도 결과에 포함됩니다.
    merged_tb = pd.merge(pre_tb_df, journal_sum, on='계정코드', how='outer')

    # 병합 과정에서 생긴 NaN 값을 0으로 채웁니다.
    merged_tb = merged_tb.fillna(0)

    # --- 3. 기말 잔액 계산 ---
    # 회계 원리에 따라 기말 잔액을 계산합니다.
    # 잔액 = (기초 차변잔액 + 당기 차변금액) - (기초 대변잔액 + 당기 대변금액)
    balance = (merged_tb['차변잔액'] + merged_tb['차변금액']) - \
              (merged_tb['대변잔액'] + merged_tb['대변금액'])

    # 계산된 잔액이 양수이면 차변잔액, 음수이면 대변잔액으로 설정합니다.
    merged_tb['계산된_차변잔액'] = balance.where(balance >= 0, 0).astype(int)
    merged_tb['계산된_대변잔액'] = abs(balance.where(balance < 0, 0)).astype(int)

    # --- 4. 최종 데이터 정리 ---
    # 계정과목이 비어있는 경우(분개장에만 있는 신규 계정)를 위해 원본 당기시산표에서 정보를 가져옵니다.
    if '계정과목' in merged_tb.columns:
        merged_tb.drop('계정과목', axis=1, inplace=True)
    
    # 당기시산표의 계정과목 정보를 사용하여 최종 계정과목을 설정합니다.
    final_tb = pd.merge(merged_tb[['계정코드', '계산된_차변잔액', '계산된_대변잔액']],
                        post_tb_df[['계정코드', '계정과목']],
                        on='계정코드',
                        how='left')

    # 컬럼 이름을 표준화합니다.
    final_tb.rename(columns={'계산된_차변잔액': '차변잔액', '계산된_대변잔액': '대변잔액'}, inplace=True)
    
    # 최종 컬럼 순서를 정리하여 반환합니다.
    return final_tb[['계정코드', '계정과목', '차변잔액', '대변잔액']]
