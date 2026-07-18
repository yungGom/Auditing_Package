"""변동리스료 처리 (K-IFRS 1116호 문단 27, 38)"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO
import calendar

st.set_page_config(page_title="변동리스료", page_icon="📈", layout="wide")
st.title("📈 변동리스료 처리")
st.caption("K-IFRS 1116호 문단 27, 38 | 지수/요율 연동 리스료 재측정")

with st.expander("📖 변동리스료 유형 구분", expanded=False):
    st.markdown("""
    | 유형 | 리스부채 포함 | 재측정 | 예시 |
    |------|:---:|:---:|------|
    | 지수 연동 (CPI 등) | O | O | "소비자물가지수 상승률만큼 매년 조정" |
    | 요율 연동 (금리 등) | O | O | "CD금리 + 2%" |
    | 매출액 연동 | **X** | X | "매출의 3%" → 발생 시 비용 |
    | 사용량 연동 | **X** | X | "생산량 × 단가" → 발생 시 비용 |

    **문단 27(a):** 지수/요율에 따라 달라지는 변동리스료 → 리스부채 측정에 포함 (개시일 지수 기준)
    **문단 38:** 지수/요율 변동 시 → 잔여리스료를 변경된 리스료로 재측정
    """)

st.divider()

var_type = st.radio("변동리스료 유형", ["지수 연동 (CPI 등)", "요율 연동 (금리 등)", "매출/사용량 연동 (비용처리)"], horizontal=True)

if "매출" in var_type:
    st.subheader("매출/사용량 연동 변동리스료")
    st.info("리스부채에 포함하지 않습니다. 발생 시 비용으로 인식합니다.")
    st.markdown("#### 분개")
    st.code("Dr. 변동리스료 (비용)    xxx\n    Cr. 현금              xxx")

    c1, c2 = st.columns(2)
    amount = c1.number_input("당기 발생 변동리스료", value=0, step=100000, key="var_amt")
    base_dt = c2.date_input("기준일", value=date(2025, 12, 31), key="var_base")
    if amount > 0:
        st.metric("당기 비용 인식액", f"{amount:,}원")

else:
    st.subheader("지수/요율 연동 리스부채 재측정")

    st.markdown("#### 기존 리스 정보")
    c1, c2, c3, c4 = st.columns(4)
    original_rent = c1.number_input("최초 월 리스료", value=1000000, step=100000, key="vr_rent")
    annual_rate = c2.number_input("할인율 (%)", value=10.0, step=0.1, key="vr_rate")
    remaining_months = c3.number_input("잔여 리스기간 (개월)", value=24, step=1, key="vr_remain")
    current_liability = c4.number_input("현재 리스부채 잔액", value=20000000, step=100000, key="vr_liab")

    st.markdown("#### 변동 정보")
    if "지수" in var_type:
        c1, c2 = st.columns(2)
        base_index = c1.number_input("기준 지수값 (개시일)", value=100.0, step=0.1, key="vr_bi")
        current_index = c2.number_input("현재 지수값", value=105.0, step=0.1, key="vr_ci")
        ratio = current_index / base_index if base_index > 0 else 1
        new_rent = round(original_rent * ratio)
        st.info(f"변동 후 월 리스료: {original_rent:,} × ({current_index}/{base_index}) = **{new_rent:,}원**")
    else:
        c1, c2, c3 = st.columns(3)
        base_rate_val = c1.number_input("기준금리 (%)", value=3.0, step=0.1, key="vr_br")
        spread = c2.number_input("가산금리 (%)", value=2.0, step=0.1, key="vr_sp")
        new_rate_val = c3.number_input("변동 후 기준금리 (%)", value=3.5, step=0.1, key="vr_nr")
        new_rent = round(original_rent * (new_rate_val + spread) / (base_rate_val + spread)) if (base_rate_val + spread) > 0 else original_rent
        st.info(f"변동 후 월 리스료: **{new_rent:,}원**")

    reassess_date = st.date_input("재측정일", value=date(2025, 1, 1), key="vr_date")
    current_rou = st.number_input("현재 사용권자산 잔액", value=18000000, step=100000, key="vr_rou")

    if st.button("🔢 재측정 실행", type="primary", use_container_width=True, key="var_run_btn"):
        mr = annual_rate / 100 / 12
        # 잔여 리스료 PV (변동 후)
        new_pv = sum(new_rent / ((1 + mr) ** (i + 1)) for i in range(remaining_months))
        new_liability = round(new_pv)
        adjustment = new_liability - current_liability
        new_rou = current_rou + adjustment

        st.session_state["var_result"] = {
            "new_rent": new_rent, "new_liability": new_liability,
            "adjustment": adjustment, "new_rou": new_rou,
            "current_liability": current_liability, "current_rou": current_rou,
        }

    if "var_result" in st.session_state:
        r = st.session_state["var_result"]
        st.divider()
        st.subheader("📋 재측정 결과")

        c1, c2, c3 = st.columns(3)
        c1.metric("변동 후 리스부채", f"{r['new_liability']:,}", delta=f"{r['adjustment']:+,}")
        c2.metric("변동 후 사용권자산", f"{r['new_rou']:,}", delta=f"{r['adjustment']:+,}")
        c3.metric("조정액", f"{r['adjustment']:,}", delta="증가" if r['adjustment'] > 0 else "감소")

        st.markdown("#### 재측정 분개")
        if r['adjustment'] > 0:
            st.code(f"Dr. 사용권자산    {r['adjustment']:>12,}\n    Cr. 리스부채    {r['adjustment']:>12,}")
        elif r['adjustment'] < 0:
            st.code(f"Dr. 리스부채      {-r['adjustment']:>12,}\n    Cr. 사용권자산  {-r['adjustment']:>12,}")
        else:
            st.info("조정액 없음")

        st.markdown("#### 요약")
        summary = pd.DataFrame([
            {"구분": "재측정 전", "리스부채": r['current_liability'], "사용권자산": r['current_rou']},
            {"구분": "조정액", "리스부채": r['adjustment'], "사용권자산": r['adjustment']},
            {"구분": "재측정 후", "리스부채": r['new_liability'], "사용권자산": r['new_rou']},
        ])
        st.dataframe(summary.style.format({"리스부채": "{:,.0f}", "사용권자산": "{:,.0f}"}), use_container_width=True, hide_index=True)
