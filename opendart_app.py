"""
OpenDART 재무정보 분석 앱
- DART API를 통해 기업 재무제표 조회 및 분석
- 엑셀 파일 다운로드 지원
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from opendart_api import (
    analyze_financial_statements,
    get_excel_bytes,
    REPRT_CODES,
    FS_DIVS
)

st.set_page_config(
    page_title="OpenDART 재무분석",
    page_icon="📊",
    layout="wide"
)

st.title("📊 OpenDART 재무정보 분석")
st.write("DART(전자공시시스템) API를 통해 기업의 재무제표를 조회하고 분석합니다.")

# =============================================================================
# 사이드바: 설정 입력
# =============================================================================
with st.sidebar:
    st.header("🔑 API 설정")

    # API 키 입력 (password 타입으로 마스킹)
    api_key = st.text_input(
        "OpenDART 인증키",
        type="password",
        help="DART 오픈API에서 발급받은 인증키를 입력하세요. (https://opendart.fss.or.kr)"
    )

    st.divider()

    st.header("🏢 기업 정보")

    corp_code = st.text_input(
        "기업 고유번호 (8자리)",
        value="",
        max_chars=8,
        help="DART에서 부여한 기업 고유번호 8자리를 입력하세요."
    )

    # 자주 사용하는 기업 코드 예시
    with st.expander("기업 코드 예시 보기"):
        st.markdown("""
        | 기업명 | 고유번호 |
        |--------|----------|
        | 삼성전자 | 00126380 |
        | SK하이닉스 | 00164779 |
        | LG전자 | 00401731 |
        | 현대자동차 | 00164742 |
        | NAVER | 00266961 |
        | 카카오 | 00918444 |
        | 프로텍 | 00325112 |
        """)

    st.divider()

    st.header("📅 조회 기간")

    current_year = datetime.now().year

    col1, col2 = st.columns(2)
    with col1:
        start_year = st.number_input(
            "시작 연도",
            min_value=2015,
            max_value=current_year - 1,
            value=current_year - 10,
            step=1
        )
    with col2:
        end_year = st.number_input(
            "종료 연도",
            min_value=2015,
            max_value=current_year - 1,
            value=current_year - 1,
            step=1
        )

    st.divider()

    st.header("📋 보고서 설정")

    reprt_type = st.selectbox(
        "보고서 유형",
        options=list(REPRT_CODES.keys()),
        index=0,
        help="사업보고서는 연간 기준, 반기/분기보고서는 해당 기간 기준입니다."
    )

    fs_type = st.selectbox(
        "재무제표 유형",
        options=list(FS_DIVS.keys()),
        index=0,
        help="별도재무제표는 개별 법인 기준, 연결재무제표는 종속회사 포함 기준입니다."
    )

    st.divider()

    # 분석 실행 버튼
    run_analysis = st.button("🔍 재무분석 실행", type="primary", use_container_width=True)

# =============================================================================
# 메인 영역: 분석 결과
# =============================================================================

# 입력 검증
if run_analysis:
    if not api_key:
        st.error("❌ OpenDART 인증키를 입력해주세요.")
        st.stop()

    if not corp_code or len(corp_code) != 8:
        st.error("❌ 기업 고유번호 8자리를 정확히 입력해주세요.")
        st.stop()

    if start_year > end_year:
        st.error("❌ 시작 연도는 종료 연도보다 클 수 없습니다.")
        st.stop()

    # 분석 실행
    with st.spinner(f"📊 {start_year}~{end_year}년 재무정보를 조회하는 중입니다..."):
        try:
            result_df = analyze_financial_statements(
                crtfc_key=api_key,
                corp_code=corp_code,
                start_year=int(start_year),
                end_year=int(end_year),
                fs_div=FS_DIVS[fs_type],
                reprt_code=REPRT_CODES[reprt_type]
            )

            # 결과 저장 (session state)
            st.session_state['result_df'] = result_df
            st.session_state['corp_code'] = corp_code
            st.session_state['start_year'] = start_year
            st.session_state['end_year'] = end_year

            st.success(f"✅ {len(result_df)}개 연도의 재무정보 조회 완료!")

        except Exception as e:
            st.error(f"❌ 오류가 발생했습니다: {e}")
            st.stop()

# 결과 표시
if 'result_df' in st.session_state:
    result_df = st.session_state['result_df']
    corp_code = st.session_state['corp_code']
    start_year = st.session_state['start_year']
    end_year = st.session_state['end_year']

    st.subheader(f"📈 재무분석 결과 (기업코드: {corp_code})")

    # 데이터 테이블 표시
    st.dataframe(
        result_df,
        use_container_width=True,
        hide_index=True
    )

    # 금액 포맷팅된 테이블 (억원 단위)
    st.subheader("💰 금액 요약 (억원 단위)")

    numeric_cols = ['매출액', '영업이익', '법인세비용차감전순이익', '당기순이익', '자산총계', '자본총계']
    summary_df = result_df.copy()

    for col in numeric_cols:
        if col in summary_df.columns:
            summary_df[col] = summary_df[col].apply(
                lambda x: f"{x/100000000:,.1f}" if pd.notna(x) and x != 0 else "-"
            )

    st.dataframe(
        summary_df[['사업연도'] + numeric_cols + ['비고']],
        use_container_width=True,
        hide_index=True
    )

    # 시각화
    st.subheader("📊 추이 차트")

    chart_col = st.selectbox(
        "차트로 볼 항목 선택",
        options=['매출액', '영업이익', '당기순이익', '자산총계', '자본총계'],
        index=0
    )

    chart_data = result_df[['사업연도', chart_col]].copy()
    chart_data = chart_data.dropna(subset=[chart_col])
    chart_data = chart_data.set_index('사업연도')

    if not chart_data.empty:
        st.line_chart(chart_data)
    else:
        st.info("📭 표시할 데이터가 없습니다.")

    # 엑셀 다운로드
    st.divider()
    st.subheader("📥 엑셀 다운로드")

    excel_bytes = get_excel_bytes(result_df)
    file_name = f"dart_financial_{corp_code}_{start_year}_{end_year}.xlsx"

    st.download_button(
        label="📥 엑셀 파일 다운로드",
        data=excel_bytes,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

else:
    # 초기 안내 화면
    st.info("👈 사이드바에서 API 키와 기업 정보를 입력한 후 '재무분석 실행' 버튼을 클릭하세요.")

    with st.expander("📖 사용 방법"):
        st.markdown("""
        ### 1. OpenDART 인증키 발급
        1. [DART 오픈API](https://opendart.fss.or.kr) 접속
        2. 회원가입 후 로그인
        3. 인증키 신청 및 발급

        ### 2. 기업 고유번호 확인
        - DART 사이트에서 기업 검색 후 고유번호 확인
        - 또는 사이드바의 '기업 코드 예시'에서 주요 기업 코드 참조

        ### 3. 조회 설정
        - **시작/종료 연도**: 분석할 기간 설정
        - **보고서 유형**: 사업보고서(연간), 반기/분기보고서 선택
        - **재무제표 유형**: 별도(개별) 또는 연결 재무제표 선택

        ### 4. 분석 실행
        - '재무분석 실행' 버튼 클릭
        - 결과 확인 및 엑셀 다운로드
        """)

    with st.expander("📊 조회 가능 항목"):
        st.markdown("""
        | 항목 | 설명 |
        |------|------|
        | 매출액 | 영업활동을 통한 총 수익 |
        | 영업이익 | 매출액 - 매출원가 - 판관비 |
        | 법인세비용차감전순이익 | 영업이익 + 영업외손익 |
        | 당기순이익 | 법인세 차감 후 최종 이익 |
        | 자산총계 | 기업이 보유한 총 자산 |
        | 자본총계 | 자산 - 부채 |
        """)
