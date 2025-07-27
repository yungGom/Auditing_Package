import pandas as pd

def compare_trial_balances(calculated_tb, post_tb):
    """
    계산된 당기 시산표와 실제 당기 시산표를 비교하고, 차이가 있는 항목을 찾아 데이터프레임으로 반환합니다.
    시나리오 A03 (시산표 Reconcilliation 검증)에 해당합니다.

    Args:
        calculated_tb (pd.DataFrame): 계산된 당기 시산표
        post_tb (pd.DataFrame): 실제 당기 시산표

    Returns:
        pd.DataFrame: 차이가 발생한 항목들에 대한 상세 정보가 담긴 데이터프레임. 차이가 없으면 빈 데이터프레임.
    """
    # --- 1. 데이터 정제 ---
    # 비교를 위해 양쪽 데이터프레임의 데이터 타입을 정수형으로 통일합니다.
    for col in ['차변잔액', '대변잔액']:
        calculated_tb[col] = pd.to_numeric(calculated_tb[col], errors='coerce').fillna(0).astype(int)
        post_tb[col] = pd.to_numeric(post_tb[col], errors='coerce').fillna(0).astype(int)

    # --- 2. 데이터 비교 ---
    # 계정코드를 기준으로 두 데이터프레임을 병합합니다.
    # _계산, _원본 접미사를 붙여 출처를 구분합니다.
    comparison_df = pd.merge(
        calculated_tb,
        post_tb,
        on='계정코드',
        suffixes=('_계산', '_원본'),
        how='outer'
    )
    # 병합 후 NaN 값은 0으로 채웁니다. (한쪽에만 존재하는 계정 처리)
    comparison_df.fillna(0, inplace=True)
    
    # 계정과목 열을 정리합니다. (원본 데이터의 계정과목을 우선 사용)
    comparison_df['계정과목'] = comparison_df['계정과목_원본'].combine_first(comparison_df['계정과목_계산'])


    # --- 3. 차이 계산 및 필터링 ---
    # 차변과 대변의 차이를 계산하여 새로운 열에 저장합니다.
    comparison_df['차변차이'] = comparison_df['차변잔액_계산'] - comparison_df['차변잔액_원본']
    comparison_df['대변차이'] = comparison_df['대변잔액_계산'] - comparison_df['대변잔액_원본']

    # 차이가 0이 아닌 행들만 필터링합니다.
    diff_df = comparison_df[
        (comparison_df['차변차이'] != 0) |
        (comparison_df['대변차이'] != 0)
    ].copy()

    # 보기 좋게 컬럼 순서를 정리합니다.
    if not diff_df.empty:
        diff_df = diff_df[[
            '계정코드', '계정과목',
            '차변잔액_계산', '차변잔액_원본', '차변차이',
            '대변잔액_계산', '대변잔액_원본', '대변차이'
        ]]
    
    return diff_df
