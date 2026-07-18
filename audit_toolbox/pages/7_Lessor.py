"""리스제공자 회계처리 (K-IFRS 1116호 문단 61~84)"""
import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

st.set_page_config(page_title="리스제공자", page_icon="🏦", layout="wide")
st.title("🏦 리스제공자 회계처리")
st.caption("K-IFRS 1116호 문단 61~84 | 금융리스/운용리스 분류 + 재계산")

with st.expander("📖 분류 기준 (문단 63)", expanded=False):
    st.markdown("""
    **아래 중 하나라도 해당 → 금융리스:**
    1. 리스기간 종료 시 소유권 이전
    2. 염가매수선택권 포함
    3. 리스기간 ≈ 경제적 내용연수의 상당부분
    4. 리스료 PV ≈ 자산 공정가치의 대부분
    5. 자산이 특수하여 리스이용자만 사용 가능

    **그 외 → 운용리스**
    """)

st.divider()

# ── 분류 판단 ──
st.subheader("Step 1: 금융/운용 분류")
c1, c2 = st.columns(2)
with c1:
    ownership_transfer = st.checkbox("① 소유권 이전", key="ls_ot")
    bargain_option = st.checkbox("② 염가매수선택권", key="ls_bo")
    specialized = st.checkbox("⑤ 특수자산 (이용자만 사용)", key="ls_sp")
with c2:
    lease_term = st.number_input("리스기간 (년)", value=3, key="ls_term")
    useful_life = st.number_input("경제적 내용연수 (년)", value=5, key="ls_ul")
    st.caption(f"리스기간/내용연수 = {lease_term/useful_life*100:.0f}%" if useful_life > 0 else "")

    monthly_rent = st.number_input("정기리스료 (연 말)", value=1000000, step=10000, key="ls_rent")
    fair_value = st.number_input("자산 공정가치", value=3163171, step=1000, key="ls_fv")
    rate = st.number_input("내재이자율 (%)", value=10.0, step=0.1, key="ls_rate")

term_ratio = lease_term / useful_life if useful_life > 0 else 0
mr = rate / 100
pv_factor = sum(1 / ((1 + mr) ** i) for i in range(1, lease_term + 1))
pv_rent = round(monthly_rent * pv_factor)
pv_ratio = pv_rent / fair_value if fair_value > 0 else 0

major_part = term_ratio >= 0.75
substantially_all = pv_ratio >= 0.90

is_finance = ownership_transfer or bargain_option or specialized or major_part or substantially_all

reasons = []
if ownership_transfer: reasons.append("① 소유권 이전")
if bargain_option: reasons.append("② 염가매수선택권")
if major_part: reasons.append(f"③ 리스기간/내용연수 = {term_ratio*100:.0f}% (상당부분)")
if substantially_all: reasons.append(f"④ 리스료PV/공정가치 = {pv_ratio*100:.0f}% (대부분)")
if specialized: reasons.append("⑤ 특수자산")

if is_finance:
    st.success(f"### 📊 금융리스\n\n근거: {', '.join(reasons)}")
else:
    st.info("### 📊 운용리스\n\n금융리스 지표에 해당하지 않음")

st.divider()

# ── 추가 입력 ──
st.subheader("Step 2: 회계처리 계산")
c1, c2 = st.columns(2)
book_value = c1.number_input("자산 장부금액 (제공자)", value=3163171, step=1000, key="ls_bv")
residual_guaranteed = c2.number_input("보증잔존가치", value=0, step=10000, key="ls_rg")

c3, c4 = st.columns(2)
residual_unguaranteed = c3.number_input("무보증잔존가치", value=100000, step=10000, key="ls_ru")
initial_direct_cost = c4.number_input("초기직접원가", value=75000, step=1000, key="ls_idc")

base_dt = st.date_input("기준일", value=date(2025, 12, 31), key="ls_base")

if st.button("🔢 계산 실행", type="primary", use_container_width=True, key="lessor_run_btn"):
    if is_finance:
        # 금융리스
        rv_pv = round((residual_guaranteed + residual_unguaranteed) / ((1 + mr) ** lease_term))
        net_investment = round(pv_rent + rv_pv)  # 리스순투자
        # 매출 = 리스료PV + 보증잔존가치PV
        rv_g_pv = round(residual_guaranteed / ((1 + mr) ** lease_term))
        sales = pv_rent + rv_g_pv
        cogs = book_value - round(residual_unguaranteed / ((1 + mr) ** lease_term))

        # 상각표
        schedule = []
        bal = net_investment
        for yr in range(1, lease_term + 1):
            interest = round(bal * mr)
            receipt = monthly_rent
            principal = receipt - interest
            if yr == lease_term:
                principal = receipt - interest  # 마지막에 잔존가치 회수
            bal_end = bal - principal
            schedule.append({"연도": yr, "기초잔액": bal, "이자수익": interest, "리스료수취": receipt, "원금회수": principal, "기말잔액": round(bal_end)})
            bal = round(bal_end)

        st.session_state["lessor_result"] = {
            "type": "금융리스", "net_investment": net_investment,
            "sales": sales, "cogs": cogs, "schedule": schedule,
            "pv_rent": pv_rent, "rv_pv": rv_pv,
            "book_value": book_value, "idc": initial_direct_cost,
        }
    else:
        # 운용리스
        annual_income = monthly_rent  # 정액
        annual_dep = round((book_value - residual_guaranteed - residual_unguaranteed) / useful_life) if useful_life > 0 else 0
        annual_idc = round(initial_direct_cost / lease_term) if lease_term > 0 else 0

        st.session_state["lessor_result"] = {
            "type": "운용리스", "annual_income": annual_income,
            "annual_dep": annual_dep, "annual_idc": annual_idc,
            "book_value": book_value, "idc": initial_direct_cost,
        }

if "lessor_result" in st.session_state:
    r = st.session_state["lessor_result"]
    st.divider()
    st.subheader(f"📋 {r['type']} 결과")

    if r["type"] == "금융리스":
        c1, c2, c3 = st.columns(3)
        c1.metric("리스순투자", f"{r['net_investment']:,}")
        c2.metric("매출 인식", f"{r['sales']:,}")
        c3.metric("매출원가", f"{r['cogs']:,}")

        st.markdown("#### 개시일 분개")
        profit = r['sales'] - r['cogs']
        st.code(f"Dr. 리스채권(순투자)    {r['net_investment']:>12,}\nDr. 매출원가            {r['cogs']:>12,}\n    Cr. 유형자산        {r['book_value']:>12,}\n    Cr. 매출            {r['sales']:>12,}")
        if r['idc'] > 0:
            st.caption(f"※ 초기직접원가 {r['idc']:,}원은 내재이자율 산정 시 반영 (리스순투자에 포함)")

        st.markdown("#### 이자수익 스케줄")
        df = pd.DataFrame(r['schedule'])
        st.dataframe(df.style.format({k: "{:,.0f}" for k in ["기초잔액", "이자수익", "리스료수취", "원금회수", "기말잔액"]}),
                     use_container_width=True, hide_index=True)

        st.markdown("#### 매기 분개 (연말)")
        yr1 = r['schedule'][0]
        st.code(f"Dr. 현금        {yr1['리스료수취']:>12,}\n    Cr. 이자수익  {yr1['이자수익']:>12,}\n    Cr. 리스채권  {yr1['원금회수']:>12,}")

    else:  # 운용리스
        c1, c2, c3 = st.columns(3)
        c1.metric("연간 리스료수익 (정액)", f"{r['annual_income']:,}")
        c2.metric("연간 감가상각비", f"{r['annual_dep']:,}")
        c3.metric("연간 초기직접원가 상각", f"{r['annual_idc']:,}")

        net_income = r['annual_income'] - r['annual_dep'] - r['annual_idc']
        st.metric("연간 순손익 효과", f"{net_income:,}")

        st.markdown("#### 매기 분개 (연말)")
        st.code(f"Dr. 현금              {r['annual_income']:>12,}\n    Cr. 운용리스료수익  {r['annual_income']:>12,}\n\nDr. 감가상각비        {r['annual_dep']:>12,}\n    Cr. 감가상각누계액  {r['annual_dep']:>12,}")
