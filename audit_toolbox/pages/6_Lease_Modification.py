"""리스변경 재측정 (K-IFRS 1116호 문단 44~46)"""
import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

st.set_page_config(page_title="리스변경", page_icon="🔄", layout="wide")
st.title("🔄 리스이용자 리스계약 변경")
st.caption("K-IFRS 1116호 문단 44~46 | 별도리스 · 기간연장 · 범위축소 · 혼합변경")

with st.expander("📖 변경 유형별 처리 요약", expanded=False):
    st.markdown("""
    | 유형 | 할인율 | 처리 |
    |------|--------|------|
    | 별도 리스 | 수정 할인율 | 기존 리스 영향 없음, 새 리스 별도 인식 |
    | 기간 연장 | **수정** 할인율 | 리스부채 재측정 → ROU 조정, 변경손익 없음 |
    | 범위 축소 1단계 | **최초** 할인율 | 비례 감소 → 차이 = 변경손익 |
    | 범위 축소 2단계 | **수정** 할인율 | 나머지 재측정 → ROU 조정 |
    | 리스료 변경 (범위 외) | **수정** 할인율 | 리스부채 재측정 → ROU 조정 |
    """)

st.divider()

mod_type = st.selectbox("변경 유형", [
    "별도 리스 (범위 증가 + 상응 대가)",
    "기간 연장",
    "범위 축소 (일부 해지/기간 단축)",
    "리스료 변경 (범위 외 변경)",
    "혼합 (범위 축소 + 기타 변경)",
])

st.markdown("---")
st.subheader("기존 리스 정보 (변경일 기준)")
c1, c2, c3, c4 = st.columns(4)
original_liability = c1.number_input("리스부채 잔액", value=2486857, step=1000, key="ml")
original_rou = c2.number_input("사용권자산 잔액", value=2377403, step=1000, key="mr")
original_rate = c3.number_input("최초 할인율 (%)", value=10.0, step=0.1, key="mor")
original_rent = c4.number_input("기존 월/연 리스료", value=1000000, step=10000, key="mrent")

c5, c6 = st.columns(2)
original_term = c5.number_input("최초 리스기간 (년)", value=3, step=1, key="moterm")
elapsed = c6.number_input("경과기간 (년)", value=1, step=1, key="melapsed")
remaining = original_term - elapsed

mod_date = st.date_input("변경일", value=date(2025, 1, 1), key="mdate")

st.markdown("---")

# ── 별도 리스 ──
if "별도" in mod_type:
    st.subheader("별도 리스 정보")
    st.info("기존 리스에 영향 없음. 추가 사용권에 대해 새 리스를 별도 인식합니다.")
    c1, c2, c3 = st.columns(3)
    new_rent = c1.number_input("추가 리스료 (연)", value=900000, step=10000, key="ms_rent")
    new_term = c2.number_input("추가 기간 (년)", value=2, step=1, key="ms_term")
    new_rate = c3.number_input("수정 할인율 (%)", value=12.0, step=0.1, key="ms_rate")

    if st.button("🔢 별도 리스 계산", type="primary", use_container_width=True, key="ms_btn"):
        mr = new_rate / 100
        pv_factor = sum(1 / ((1 + mr) ** i) for i in range(1, new_term + 1))
        new_liability = round(new_rent * pv_factor)
        st.session_state["mod_result"] = {"type": "별도리스", "new_liability": new_liability, "new_rou": new_liability, "new_rate": new_rate}

# ── 기간 연장 ──
elif "기간 연장" in mod_type:
    st.subheader("변경 후 조건")
    c1, c2, c3 = st.columns(3)
    new_rent = c1.number_input("변경 후 리스료 (연)", value=1000000, step=10000, key="me_rent")
    extension = c2.number_input("연장 기간 (년)", value=1, step=1, key="me_ext")
    new_rate = c3.number_input("수정 할인율 (%)", value=12.0, step=0.1, key="me_rate")
    new_remaining = remaining + extension

    residual_value = st.number_input("변경 후 종료시점 추정 잔존가치", value=100000, step=10000, key="me_rv")

    if st.button("🔢 재측정 실행", type="primary", use_container_width=True, key="me_btn"):
        mr = new_rate / 100
        pv_factor = sum(1 / ((1 + mr) ** i) for i in range(1, new_remaining + 1))
        rv_pv = round(residual_value / ((1 + mr) ** new_remaining))
        new_liability = round(new_rent * pv_factor + rv_pv)
        adjustment = new_liability - original_liability
        new_rou = original_rou + adjustment

        st.session_state["mod_result"] = {
            "type": "기간연장", "new_liability": new_liability,
            "adjustment": adjustment, "new_rou": new_rou,
            "gain_loss": 0, "new_rate": new_rate,
        }

# ── 범위 축소 ──
elif "범위 축소" in mod_type:
    st.subheader("축소 정보")
    c1, c2 = st.columns(2)
    decrease_ratio = c1.number_input("축소 비율 (%)", value=50.0, step=1.0, key="md_ratio",
                                      help="예: 50% → 사용 범위가 절반으로 축소")
    new_remaining_yrs = c2.number_input("변경 후 잔여기간 (년)", value=int(remaining), step=1, key="md_remain")

    c3, c4 = st.columns(2)
    new_rent_after = c3.number_input("변경 후 리스료 (연)", value=600000, step=10000, key="md_rent")
    new_rate = c4.number_input("수정 할인율 (%)", value=12.0, step=0.1, key="md_rate")

    if st.button("🔢 재측정 실행", type="primary", use_container_width=True, key="md_btn"):
        ratio = decrease_ratio / 100
        # Step 1: 비례 감소 (최초 할인율 적용)
        rou_decrease = round(original_rou * ratio)
        # 리스부채 비례감소: 최초 할인율로 축소분 PV
        orig_mr = original_rate / 100
        orig_pv_factor = sum(1 / ((1 + orig_mr) ** i) for i in range(1, int(remaining) + 1))
        liability_decrease = round(original_rent * ratio * orig_pv_factor)

        gain_loss = liability_decrease - rou_decrease

        # Step 1 후 잔액
        rou_after_step1 = original_rou - rou_decrease
        liability_after_step1 = original_liability - liability_decrease

        # Step 2: 잔여분 재측정 (수정 할인율)
        new_mr = new_rate / 100
        new_pv_factor = sum(1 / ((1 + new_mr) ** i) for i in range(1, new_remaining_yrs + 1))
        new_liability = round(new_rent_after * new_pv_factor)
        step2_adjustment = new_liability - liability_after_step1
        new_rou = rou_after_step1 + step2_adjustment

        st.session_state["mod_result"] = {
            "type": "범위축소",
            "rou_decrease": rou_decrease, "liability_decrease": liability_decrease,
            "gain_loss": gain_loss,
            "rou_after_step1": rou_after_step1, "liability_after_step1": liability_after_step1,
            "new_liability": new_liability, "step2_adjustment": step2_adjustment,
            "new_rou": new_rou, "new_rate": new_rate,
        }

# ── 리스료 변경 ──
elif "리스료 변경" in mod_type:
    st.subheader("변경 후 조건")
    c1, c2, c3 = st.columns(3)
    new_rent = c1.number_input("변경 후 리스료 (연)", value=950000, step=10000, key="mc_rent")
    new_remaining_yrs = c2.number_input("잔여기간 (년)", value=int(remaining), step=1, key="mc_remain")
    new_rate = c3.number_input("수정 할인율 (%)", value=12.0, step=0.1, key="mc_rate")

    if st.button("🔢 재측정 실행", type="primary", use_container_width=True, key="mc_btn"):
        mr = new_rate / 100
        pv_factor = sum(1 / ((1 + mr) ** i) for i in range(1, new_remaining_yrs + 1))
        new_liability = round(new_rent * pv_factor)
        adjustment = new_liability - original_liability
        new_rou = original_rou + adjustment

        st.session_state["mod_result"] = {
            "type": "리스료변경", "new_liability": new_liability,
            "adjustment": adjustment, "new_rou": new_rou,
            "gain_loss": 0, "new_rate": new_rate,
        }

# ── 혼합 ──
elif "혼합" in mod_type:
    st.subheader("혼합 변경 (범위 축소 + 기타)")
    st.info("범위 축소 모듈에서 축소분을 먼저 처리한 뒤, 나머지 조건 변경을 이 모듈에서 처리하세요.")
    st.markdown("**처리 순서:** 범위 축소(최초 할인율) → 나머지 재측정(수정 할인율)")

# ── 결과 표시 ──
if "mod_result" in st.session_state:
    r = st.session_state["mod_result"]
    st.divider()
    st.subheader(f"📋 {r['type']} 결과")

    if r["type"] == "별도리스":
        c1, c2 = st.columns(2)
        c1.metric("추가 리스부채", f"{r['new_liability']:,}")
        c2.metric("추가 사용권자산", f"{r['new_rou']:,}")
        st.markdown("#### 분개")
        st.code(f"Dr. 사용권자산    {r['new_rou']:>12,}\n    Cr. 리스부채    {r['new_liability']:>12,}")
        st.info("기존 리스는 변동 없이 유지됩니다.")

    elif r["type"] == "기간연장" or r["type"] == "리스료변경":
        c1, c2, c3 = st.columns(3)
        c1.metric("변경 후 리스부채", f"{r['new_liability']:,}", delta=f"{r['adjustment']:+,}")
        c2.metric("변경 후 사용권자산", f"{r['new_rou']:,}", delta=f"{r['adjustment']:+,}")
        c3.metric("리스변경손익", "없음 (ROU 조정)")
        st.markdown(f"#### 분개 (수정 할인율 {r['new_rate']}% 적용)")
        if r['adjustment'] > 0:
            st.code(f"Dr. 사용권자산    {r['adjustment']:>12,}\n    Cr. 리스부채    {r['adjustment']:>12,}")
        elif r['adjustment'] < 0:
            st.code(f"Dr. 리스부채      {-r['adjustment']:>12,}\n    Cr. 사용권자산  {-r['adjustment']:>12,}")

    elif r["type"] == "범위축소":
        st.markdown("#### Step 1: 비례 감소 (최초 할인율)")
        c1, c2, c3 = st.columns(3)
        c1.metric("ROU 감소", f"{r['rou_decrease']:,}")
        c2.metric("리스부채 감소", f"{r['liability_decrease']:,}")
        gl = r['gain_loss']
        c3.metric("리스변경손익", f"{gl:,}", delta="이익" if gl > 0 else ("손실" if gl < 0 else "없음"))

        st.markdown("#### Step 2: 잔여분 재측정 (수정 할인율)")
        c1, c2 = st.columns(2)
        c1.metric("재측정 후 리스부채", f"{r['new_liability']:,}", delta=f"{r['step2_adjustment']:+,}")
        c2.metric("재측정 후 사용권자산", f"{r['new_rou']:,}")

        st.markdown("#### 분개")
        st.markdown("**Step 1 (비례감소 + 손익)**")
        if gl >= 0:
            st.code(f"Dr. 리스부채              {r['liability_decrease']:>12,}\n    Cr. 사용권자산          {r['rou_decrease']:>12,}\n    Cr. 리스계약변경이익    {gl:>12,}")
        else:
            st.code(f"Dr. 리스부채              {r['liability_decrease']:>12,}\nDr. 리스계약변경손실      {-gl:>12,}\n    Cr. 사용권자산          {r['rou_decrease']:>12,}")

        if r['step2_adjustment'] != 0:
            st.markdown(f"**Step 2 (재측정, 수정 할인율 {r['new_rate']}%)**")
            if r['step2_adjustment'] > 0:
                st.code(f"Dr. 사용권자산    {r['step2_adjustment']:>12,}\n    Cr. 리스부채    {r['step2_adjustment']:>12,}")
            else:
                st.code(f"Dr. 리스부채      {-r['step2_adjustment']:>12,}\n    Cr. 사용권자산  {-r['step2_adjustment']:>12,}")

        st.markdown("#### 최종 재무상태표")
        st.dataframe(pd.DataFrame([
            {"구분": "변경 전", "사용권자산": original_rou, "리스부채": original_liability},
            {"구분": "Step1 비례감소", "사용권자산": -r['rou_decrease'], "리스부채": -r['liability_decrease']},
            {"구분": "Step2 재측정", "사용권자산": r['step2_adjustment'], "리스부채": r['step2_adjustment']},
            {"구분": "변경 후", "사용권자산": r['new_rou'], "리스부채": r['new_liability']},
        ]).style.format({"사용권자산": "{:,.0f}", "리스부채": "{:,.0f}"}), use_container_width=True, hide_index=True)
