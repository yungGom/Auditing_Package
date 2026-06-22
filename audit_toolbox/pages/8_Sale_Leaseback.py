"""판매후리스 (K-IFRS 1116호 문단 98~103)"""
import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

st.set_page_config(page_title="판매후리스", page_icon="🔁", layout="wide")
st.title("🔁 판매후리스")
st.caption("K-IFRS 1116호 문단 98~103 | 매각손익 안분 + 리스백 회계처리")

with st.expander("📖 판매후리스 처리 기준", expanded=False):
    st.markdown("""
    **판단:** 자산 이전이 K-IFRS 1115호의 '매각' 요건 충족?

    **매각 인정 시 (판매후리스):**
    - 보유비율 = 리스부채 ÷ 공정가치
    - 사용권자산 = **장부금액 × 보유비율**
    - 처분이익 인식 = (매각가 - 장부가) × **처분비율** (= 1 - 보유비율)

    **매각가 ≠ 공정가치인 경우:**
    - 매각가 > 공정가치 → 초과분 = 추가 금융부채 (선수리스료)
    - 매각가 < 공정가치 → 미달분 = 선급리스료 → 보유비율 재산정

    **매각 불인정 시 (금융거래):**
    - 자산 제거하지 않음
    - 수취 대가 → 금융부채 (장기차입금)
    """)

st.divider()

is_sale = st.radio("K-IFRS 1115호 매각 요건 충족 여부", ["매각 인정 (판매후리스)", "매각 불인정 (금융거래)"], horizontal=True)

if "매각 인정" in is_sale:
    st.subheader("매각 정보")
    c1, c2, c3 = st.columns(3)
    book_value = c1.number_input("자산 장부금액", value=5000000, step=100000, key="sl_bv")
    sale_price = c2.number_input("매각 가격", value=6000000, step=100000, key="sl_sp")
    fair_value = c3.number_input("자산 공정가치", value=6000000, step=100000, key="sl_fv")

    st.subheader("리스백 조건")
    c1, c2, c3, c4 = st.columns(4)
    lb_rent = c1.number_input("리스백 연 리스료", value=1000000, step=10000, key="sl_rent")
    lb_term = c2.number_input("리스백 기간 (년)", value=3, step=1, key="sl_term")
    lb_rate = c3.number_input("할인율 (%)", value=10.0, step=0.1, key="sl_rate")
    lb_rv = c4.number_input("추정 잔존가치", value=0, step=10000, key="sl_rv")

    pricing = st.radio("매각가 vs 공정가치", [
        "공정가치와 동일",
        "공정가치 초과 (초과분 = 추가 금융부채)",
        "공정가치 미달 (미달분 = 선급리스료)",
    ], key="sl_pricing")

    if st.button("🔢 판매후리스 계산", type="primary", use_container_width=True, key="sl_run_btn"):
        mr = lb_rate / 100
        pv_factor = sum(1 / ((1 + mr) ** i) for i in range(1, lb_term + 1))
        rv_pv = round(lb_rv / ((1 + mr) ** lb_term))
        lease_liability = round(lb_rent * pv_factor + rv_pv)

        if "초과" in pricing:
            excess = sale_price - fair_value
            effective_price = fair_value
            additional_liability = excess  # 추가 금융부채
        elif "미달" in pricing:
            shortfall = fair_value - sale_price
            effective_price = fair_value
            # 선급리스료 → 실질리스부채에 가산하여 보유비율 재산정
            effective_liability = lease_liability + shortfall
            additional_liability = 0
        else:
            effective_price = sale_price
            effective_liability = lease_liability
            additional_liability = 0

        if "미달" in pricing:
            retention_ratio = effective_liability / fair_value
        else:
            retention_ratio = lease_liability / fair_value if fair_value > 0 else 0

        disposal_ratio = 1 - retention_ratio
        rou = round(book_value * retention_ratio)
        gain_total = effective_price - book_value
        gain_recognized = round(gain_total * disposal_ratio)

        # 리스백 이자비용 (1년차)
        interest_yr1 = round(lease_liability * mr)
        # 감가상각비 (1년차)
        dep_yr1 = round(rou / lb_term) if lb_term > 0 else 0

        st.session_state["sl_result"] = {
            "book_value": book_value, "sale_price": sale_price, "fair_value": fair_value,
            "lease_liability": lease_liability, "rou": rou,
            "retention_ratio": retention_ratio, "disposal_ratio": disposal_ratio,
            "gain_total": gain_total, "gain_recognized": gain_recognized,
            "additional_liability": additional_liability,
            "interest_yr1": interest_yr1, "dep_yr1": dep_yr1,
            "pricing": pricing, "lb_term": lb_term, "lb_rate": lb_rate,
        }

    if "sl_result" in st.session_state:
        r = st.session_state["sl_result"]
        st.divider()
        st.subheader("📋 판매후리스 결과")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("보유비율", f"{r['retention_ratio']*100:.1f}%")
        c2.metric("처분비율", f"{r['disposal_ratio']*100:.1f}%")
        c3.metric("사용권자산", f"{r['rou']:,}")
        c4.metric("인식 처분이익", f"{r['gain_recognized']:,}")

        st.markdown("#### 계산 과정")
        st.markdown(f"""
        1. 리스부채 = 리스료 PV = **{r['lease_liability']:,}**
        2. 보유비율 = 리스부채 / 공정가치 = {r['lease_liability']:,} / {r['fair_value']:,} = **{r['retention_ratio']*100:.1f}%**
        3. 사용권자산 = 장부금액 × 보유비율 = {r['book_value']:,} × {r['retention_ratio']*100:.1f}% = **{r['rou']:,}**
        4. 처분이익 인식 = ({r['sale_price']:,} - {r['book_value']:,}) × {r['disposal_ratio']*100:.1f}% = **{r['gain_recognized']:,}**
        """)

        st.markdown("#### 개시일 분개 (매도인=리스이용자)")
        je_lines = [f"Dr. 현금              {r['sale_price']:>12,}"]
        je_lines.append(f"Dr. 사용권자산        {r['rou']:>12,}")
        je_lines.append(f"    Cr. 유형자산      {r['book_value']:>12,}")
        je_lines.append(f"    Cr. 리스부채      {r['lease_liability']:>12,}")
        if r['gain_recognized'] > 0:
            je_lines.append(f"    Cr. 유형자산처분이익  {r['gain_recognized']:>12,}")
        elif r['gain_recognized'] < 0:
            je_lines.insert(1, f"Dr. 유형자산처분손실  {-r['gain_recognized']:>12,}")
        if r['additional_liability'] > 0:
            je_lines.append(f"    Cr. 선수리스료    {r['additional_liability']:>12,}")
        st.code("\n".join(je_lines))

        st.markdown("#### 1년차 손익 효과")
        st.dataframe(pd.DataFrame([
            {"항목": "이자비용 (리스부채)", "금액": -r['interest_yr1']},
            {"항목": "감가상각비 (사용권자산)", "금액": -r['dep_yr1']},
            {"항목": "합계", "금액": -(r['interest_yr1'] + r['dep_yr1'])},
        ]).style.format({"금액": "{:,.0f}"}), use_container_width=True, hide_index=True)

        st.markdown("#### 리스제공자 분개 (참고)")
        st.code(f"Dr. 운용리스자산    {r['sale_price']:>12,}\n    Cr. 현금        {r['sale_price']:>12,}\n\n또는 (선수리스료 처리)\nDr. 현금            {r['sale_price']:>12,}\n    Cr. 선수리스료  {r['additional_liability']:>12,}" if r['additional_liability'] > 0 else f"(운용리스 또는 금융리스로 분류하여 처리)")

else:  # 매각 불인정
    st.subheader("금융거래 처리")
    st.info("매각 요건 미충족 → 자산 제거하지 않음, 수취 대가 = 금융부채")

    c1, c2 = st.columns(2)
    proceeds = c1.number_input("수취 대가", value=6000000, step=100000, key="sl_proceeds")
    fin_rate = c2.number_input("금융부채 이자율 (%)", value=10.0, step=0.1, key="sl_fin_rate")

    if st.button("🔢 금융거래 분개", type="primary", use_container_width=True, key="sl_fin_btn"):
        st.markdown("#### 리스이용자 분개")
        st.code(f"Dr. 현금          {proceeds:>12,}\n    Cr. 장기차입금  {proceeds:>12,}")

        st.markdown("#### 리스제공자 분개")
        st.code(f"Dr. 장기대여금    {proceeds:>12,}\n    Cr. 현금        {proceeds:>12,}")

        st.warning("자산은 매도인(리스이용자)의 재무상태표에 계속 인식됩니다. 감가상각도 계속합니다.")
