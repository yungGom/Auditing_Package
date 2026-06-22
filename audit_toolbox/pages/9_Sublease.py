"""전대리스 (K-IFRS 1116호 문단 B58, 부록 B)"""
import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

st.set_page_config(page_title="전대리스", page_icon="🔀", layout="wide")
st.title("🔀 전대리스")
st.caption("K-IFRS 1116호 문단 B58 | 원리스(리스이용자) + 전대리스(리스제공자) 이중 구조")

with st.expander("📖 전대리스 처리 기준", expanded=False):
    st.markdown("""
    **구조:**
    ```
    [원소유자] ──원리스──→ [중간자(A)] ──전대──→ [최종이용자(B)]
                           리스이용자              리스제공자
    ```

    **핵심 (문단 B58):** 전대리스 분류 시 기초자산 = **사용권자산** (실물자산이 아님)

    **금융리스 전대:**
    - 사용권자산 제거 → 리스채권(전대 순투자) 인식
    - 차이 = 전대리스 처분손익
    - 원리스 리스부채는 유지

    **운용리스 전대:**
    - 사용권자산 중 전대 부분 → **투자부동산으로 재분류**
    - 전대 리스료수익 정액 인식
    - 원리스 리스부채·감가상각 계속 인식
    """)

st.divider()

# ── 원리스 정보 ──
st.subheader("원리스 정보 (A회사 = 리스이용자)")
c1, c2, c3, c4 = st.columns(4)
head_rent = c1.number_input("원리스 연 리스료", value=600000, step=10000, key="sub_hr")
head_term = c2.number_input("원리스 기간 (년)", value=4, step=1, key="sub_ht")
head_rate = c3.number_input("원리스 할인율 (%)", value=10.0, step=0.1, key="sub_hrate")
head_rv = c4.number_input("원리스 잔존가치", value=0, step=10000, key="sub_hrv")

c5, c6 = st.columns(2)
head_restoration = c5.number_input("복구비용 추정액", value=250000, step=10000, key="sub_hrest")
head_useful_life = c6.number_input("경제적 내용연수 (년)", value=10, step=1, key="sub_hul")

# ── 전대리스 정보 ──
st.subheader("전대리스 정보 (A회사 = 리스제공자)")
c1, c2, c3, c4 = st.columns(4)
sub_rent = c1.number_input("전대 연 리스료 (수취)", value=520000, step=10000, key="sub_sr")
sub_term = c2.number_input("전대 기간 (년)", value=3, step=1, key="sub_st")
sub_rate = c3.number_input("전대 할인율 (%)", value=10.0, step=0.1, key="sub_srate")
sub_rv = c4.number_input("전대 잔존가치", value=0, step=10000, key="sub_srv")

sub_start_year = st.number_input("전대 시작 연차 (원리스 기준)", value=2, min_value=1, key="sub_start",
                                  help="예: 2 = 원리스 2년차 초부터 전대 시작")

sub_class = st.radio("전대리스 분류", ["금융리스", "운용리스"], horizontal=True, key="sub_class")
sub_area_ratio = st.number_input("전대 면적 비율 (%)", value=100.0, step=1.0, key="sub_area",
                                  help="100% = 전부 전대, 40% = 일부만 전대") / 100

base_dt = st.date_input("기준일", value=date(2025, 12, 31), key="sub_base")

if st.button("🔢 전대리스 계산", type="primary", use_container_width=True, key="sub_run_btn"):
    hmr = head_rate / 100
    smr = sub_rate / 100

    # ── 원리스 계산 ──
    h_pv_factor = sum(1 / ((1 + hmr) ** i) for i in range(1, head_term + 1))
    h_rv_pv = round(head_rv / ((1 + hmr) ** head_term)) if head_rv > 0 else 0
    head_liability = round(head_rent * h_pv_factor + h_rv_pv)

    # 복구충당부채
    rest_pv = round(head_restoration / ((1 + hmr) ** head_term)) if head_restoration > 0 else 0

    head_rou = head_liability + rest_pv
    dep_period = min(head_term, head_useful_life)
    annual_dep = round(head_rou / dep_period) if dep_period > 0 else 0

    # 원리스 상각표
    h_schedule = []
    h_bal = head_liability
    r_bal = head_rou
    for yr in range(1, head_term + 1):
        interest = round(h_bal * hmr)
        principal = head_rent - interest
        dep = annual_dep if yr <= dep_period else 0
        h_schedule.append({
            "연도": yr, "리스부채(기초)": h_bal, "이자비용": interest,
            "리스료지급": head_rent, "원금상환": principal,
            "리스부채(기말)": max(0, round(h_bal - principal)),
            "감가상각비": dep,
            "ROU(기초)": r_bal, "ROU(기말)": max(0, round(r_bal - dep)),
        })
        h_bal = max(0, round(h_bal - principal))
        r_bal = max(0, round(r_bal - dep))

    # ── 전대 시작 시점의 원리스 잔액 ──
    sub_start_idx = sub_start_year - 1  # 0-based
    if sub_start_idx > 0 and sub_start_idx < len(h_schedule):
        rou_at_sub_start = h_schedule[sub_start_idx - 1]["ROU(기말)"]
        liab_at_sub_start = h_schedule[sub_start_idx - 1]["리스부채(기말)"]
    else:
        rou_at_sub_start = head_rou
        liab_at_sub_start = head_liability

    rou_subleased = round(rou_at_sub_start * sub_area_ratio)

    # ── 전대리스 계산 ──
    s_pv_factor = sum(1 / ((1 + smr) ** i) for i in range(1, sub_term + 1))
    s_rv_pv = round(sub_rv / ((1 + smr) ** sub_term)) if sub_rv > 0 else 0

    if sub_class == "금융리스":
        # 전대리스채권 = 전대 리스료 PV + 잔존가치 PV
        sub_receivable = round(sub_rent * s_pv_factor + s_rv_pv)
        disposal_gain = sub_receivable - rou_subleased

        # 전대 이자수익 스케줄
        s_schedule = []
        s_bal = sub_receivable
        for yr in range(1, sub_term + 1):
            s_interest = round(s_bal * smr)
            s_receipt = sub_rent
            s_principal = s_receipt - s_interest
            s_schedule.append({
                "연도": sub_start_year + yr - 1, "리스채권(기초)": s_bal,
                "이자수익": s_interest, "리스료수취": s_receipt,
                "원금회수": s_principal, "리스채권(기말)": max(0, round(s_bal - s_principal)),
            })
            s_bal = max(0, round(s_bal - s_principal))

        st.session_state["sub_result"] = {
            "class": "금융리스",
            "head_rou": head_rou, "head_liability": head_liability,
            "head_schedule": h_schedule, "annual_dep": annual_dep,
            "rou_at_sub": rou_at_sub_start, "rou_subleased": rou_subleased,
            "sub_receivable": sub_receivable, "disposal_gain": disposal_gain,
            "sub_schedule": s_schedule, "rest_pv": rest_pv,
            "sub_start_year": sub_start_year, "sub_area_ratio": sub_area_ratio,
        }

    else:  # 운용리스
        # ROU → 투자부동산 재분류
        investment_property = rou_subleased
        sub_annual_income = sub_rent  # 정액
        # 투자부동산 감가상각 (원리스 잔여기간)
        remaining_head = head_term - sub_start_year + 1
        ip_annual_dep = round(investment_property / remaining_head) if remaining_head > 0 else 0

        st.session_state["sub_result"] = {
            "class": "운용리스",
            "head_rou": head_rou, "head_liability": head_liability,
            "head_schedule": h_schedule, "annual_dep": annual_dep,
            "rou_at_sub": rou_at_sub_start, "rou_subleased": rou_subleased,
            "investment_property": investment_property,
            "sub_annual_income": sub_annual_income,
            "ip_annual_dep": ip_annual_dep, "rest_pv": rest_pv,
            "sub_start_year": sub_start_year, "sub_area_ratio": sub_area_ratio,
        }

if "sub_result" in st.session_state:
    r = st.session_state["sub_result"]
    st.divider()
    st.subheader(f"📋 전대리스 결과 ({r['class']})")

    # 원리스 요약
    st.markdown("#### 원리스 (A = 리스이용자)")
    c1, c2, c3 = st.columns(3)
    c1.metric("리스부채 (개시일)", f"{r['head_liability']:,}")
    c2.metric("사용권자산 (개시일)", f"{r['head_rou']:,}")
    c3.metric("연간 감가상각비", f"{r['annual_dep']:,}")

    with st.expander("원리스 상각표"):
        st.dataframe(pd.DataFrame(r["head_schedule"]).style.format(
            {k: "{:,.0f}" for k in ["리스부채(기초)", "이자비용", "리스료지급", "원금상환", "리스부채(기말)", "감가상각비", "ROU(기초)", "ROU(기말)"]}
        ), use_container_width=True, hide_index=True)

    st.markdown(f"#### 전대 시작 시점 ({r['sub_start_year']}년차 초)")
    c1, c2 = st.columns(2)
    c1.metric("전대 대상 ROU 잔액", f"{r['rou_subleased']:,}")
    c2.metric(f"전대 면적 비율", f"{r['sub_area_ratio']*100:.0f}%")

    if r["class"] == "금융리스":
        st.markdown("#### 전대리스 (A = 리스제공자, 금융리스)")
        c1, c2, c3 = st.columns(3)
        c1.metric("리스채권 (전대 순투자)", f"{r['sub_receivable']:,}")
        c2.metric("제거된 ROU", f"{r['rou_subleased']:,}")
        dg = r['disposal_gain']
        c3.metric("전대리스 처분손익", f"{dg:,}", delta="이익" if dg > 0 else ("손실" if dg < 0 else "없음"))

        st.markdown("#### 전대 개시일 분개")
        if dg >= 0:
            st.code(f"Dr. 리스채권(전대)      {r['sub_receivable']:>12,}\n    Cr. 사용권자산      {r['rou_subleased']:>12,}\n    Cr. 전대리스처분이익  {dg:>12,}")
        else:
            st.code(f"Dr. 리스채권(전대)      {r['sub_receivable']:>12,}\nDr. 전대리스처분손실    {-dg:>12,}\n    Cr. 사용권자산      {r['rou_subleased']:>12,}")

        st.markdown("#### 전대 이자수익 스케줄")
        st.dataframe(pd.DataFrame(r["sub_schedule"]).style.format(
            {k: "{:,.0f}" for k in ["리스채권(기초)", "이자수익", "리스료수취", "원금회수", "리스채권(기말)"]}
        ), use_container_width=True, hide_index=True)

        # 통합 손익
        st.markdown("#### 연도별 통합 손익 효과")
        combined = []
        for yr in range(1, max(len(r['head_schedule']), 1) + 1):
            h = r['head_schedule'][yr - 1] if yr <= len(r['head_schedule']) else None
            s = next((x for x in r['sub_schedule'] if x['연도'] == yr), None)
            interest_exp = h['이자비용'] if h else 0
            dep_exp = h['감가상각비'] if h else 0
            interest_inc = s['이자수익'] if s else 0
            disp = r['disposal_gain'] if yr == r['sub_start_year'] else 0
            net = -interest_exp - dep_exp + interest_inc + disp
            combined.append({
                "연도": yr, "이자비용(원리스)": -interest_exp, "감가상각비": -dep_exp,
                "이자수익(전대)": interest_inc, "처분손익": disp, "순손익": net,
            })
        st.dataframe(pd.DataFrame(combined).style.format(
            {k: "{:,.0f}" for k in ["이자비용(원리스)", "감가상각비", "이자수익(전대)", "처분손익", "순손익"]}
        ), use_container_width=True, hide_index=True)

    else:  # 운용리스
        st.markdown("#### 전대리스 (A = 리스제공자, 운용리스)")
        c1, c2, c3 = st.columns(3)
        c1.metric("투자부동산 (재분류)", f"{r['investment_property']:,}")
        c2.metric("전대 연간 리스료수익 (정액)", f"{r['sub_annual_income']:,}")
        c3.metric("투자부동산 연간 감가상각비", f"{r['ip_annual_dep']:,}")

        st.markdown("#### 전대 개시일 분개 (투자부동산 재분류)")
        st.code(f"Dr. 투자부동산          {r['investment_property']:>12,}\n    Cr. 사용권자산      {r['investment_property']:>12,}")
        st.caption("※ 전대가 운용리스이므로 사용권자산을 투자부동산으로 재분류 (변경손익 없음)")

        st.markdown("#### 매기 분개 (연말)")
        h_yr = r['head_schedule'][r['sub_start_year'] - 1] if r['sub_start_year'] <= len(r['head_schedule']) else None
        h_int = h_yr['이자비용'] if h_yr else 0
        st.code(
            f"[원리스 이자]\nDr. 이자비용          {h_int:>12,}\n    Cr. 리스부채      {h_int:>12,}\n\n"
            f"[원리스 리스료 지급]\nDr. 리스부채          {head_rent - h_int:>12,}\n    Cr. 현금          {head_rent:>12,}\n\n"
            f"[전대 리스료 수취]\nDr. 현금              {r['sub_annual_income']:>12,}\n    Cr. 운용리스료수익  {r['sub_annual_income']:>12,}\n\n"
            f"[투자부동산 감가상각]\nDr. 감가상각비        {r['ip_annual_dep']:>12,}\n    Cr. 감가상각누계액  {r['ip_annual_dep']:>12,}"
        )

        # 통합 손익
        st.markdown("#### 연도별 통합 손익 효과")
        combined = []
        for yr in range(1, len(r['head_schedule']) + 1):
            h = r['head_schedule'][yr - 1]
            is_sub_active = yr >= r['sub_start_year'] and yr < r['sub_start_year'] + sub_term
            interest_exp = h['이자비용']
            dep_exp = r['ip_annual_dep'] if is_sub_active else h['감가상각비']
            sub_inc = r['sub_annual_income'] if is_sub_active else 0
            net = -interest_exp - dep_exp + sub_inc
            combined.append({
                "연도": yr, "이자비용(원리스)": -interest_exp,
                "감가상각비": -dep_exp,
                "리스료수익(전대)": sub_inc, "순손익": net,
            })
        st.dataframe(pd.DataFrame(combined).style.format(
            {k: "{:,.0f}" for k in ["이자비용(원리스)", "감가상각비", "리스료수익(전대)", "순손익"]}
        ), use_container_width=True, hide_index=True)

    # 재무상태표 요약
    st.markdown("#### 전대 후 재무상태표 요약")
    if r["class"] == "금융리스":
        remaining_rou = r['rou_at_sub'] - r['rou_subleased']
        st.dataframe(pd.DataFrame([
            {"항목": "사용권자산 (잔여분)", "금액": remaining_rou},
            {"항목": "리스채권 (전대)", "금액": r['sub_receivable']},
            {"항목": "리스부채 (원리스)", "금액": -r['head_schedule'][r['sub_start_year']-1]['리스부채(기초)']},
        ]).style.format({"금액": "{:,.0f}"}), use_container_width=True, hide_index=True)
    else:
        st.dataframe(pd.DataFrame([
            {"항목": "투자부동산 (전대분)", "금액": r['investment_property']},
            {"항목": "사용권자산 (잔여분)", "금액": r['rou_at_sub'] - r['rou_subleased']},
            {"항목": "리스부채 (원리스)", "금액": -r['head_schedule'][r['sub_start_year']-1]['리스부채(기초)']},
        ]).style.format({"금액": "{:,.0f}"}), use_container_width=True, hide_index=True)
