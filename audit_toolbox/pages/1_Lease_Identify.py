"""리스 식별 판단 (K-IFRS 1116호 문단 9~11, B9~B33)"""
import streamlit as st
from datetime import date

st.set_page_config(page_title="리스 식별", page_icon="🔍", layout="wide")
st.title("🔍 리스 식별 판단")
st.caption("K-IFRS 1116호 문단 9~11 | 계약 조건을 입력하면 리스 여부를 판정합니다")

with st.expander("📖 판단 기준 요약", expanded=False):
    st.markdown("""
    **리스의 정의 (문단 9):** 대가와 교환하여 식별되는 자산의 사용 통제권을 일정 기간 이전하는 계약

    **4단계 판단:**
    1. 식별되는 자산이 있는가?
    2. 공급자에게 실질적 대체권이 있는가?
    3. 고객이 경제적 효익의 대부분을 얻는가?
    4. 고객이 자산의 사용을 지시할 권리가 있는가?
    """)

st.divider()

# ── 입력 ──
st.subheader("계약 정보 입력")
c1, c2 = st.columns(2)
with c1:
    contract_name = st.text_input("계약명", "건물 임대차계약")
    counterparty = st.text_input("거래상대방", "")
    contract_date = st.date_input("계약일", value=date(2025, 1, 1))
with c2:
    contract_period = st.text_input("계약기간", "3년")
    contract_amount = st.text_input("계약금액", "")
    notes = st.text_area("메모", height=68)

st.divider()
st.subheader("판단 항목")

# Q1: 식별되는 자산
st.markdown("#### Q1. 식별되는 자산이 있는가? (문단 B13~B20)")
with st.expander("판단 지침"):
    st.markdown("""
    - 계약에 **명시적 또는 묵시적으로 특정**되는 자산이 있는가?
    - 자산의 물리적으로 구별되는 부분 또는 용량의 대부분을 사용하는가?
    - 예: 특정 층의 사무실, 특정 차량, 특정 기계장치
    - 반례: "서버 용량 중 일부" (물리적으로 구별 불가)
    """)
q1 = st.radio("식별되는 자산 존재 여부", ["예 - 계약에서 자산이 특정됨", "아니오 - 특정되는 자산 없음"], key="q1")

# Q2: 실질적 대체권
q2 = None
if "예" in q1:
    st.markdown("#### Q2. 공급자에게 실질적 대체권이 있는가? (문단 B14~B19)")
    with st.expander("판단 지침"):
        st.markdown("""
        **실질적 대체권 = 아래 두 가지 모두 충족:**
        - 공급자가 사용기간 전체에 걸쳐 **대체 자산으로 교체할 실질적 능력**이 있음
        - 공급자가 대체권 행사로 **경제적 효익**을 얻음

        **실질적이지 않은 경우:**
        - 고객 동의 없이 교체 불가
        - 교체 비용이 과도하여 현실적으로 불가능
        - 대체 자산을 적시에 조달할 수 없음
        """)
    q2 = st.radio("공급자의 실질적 대체권", [
        "아니오 - 대체권 없음 또는 실질적이지 않음",
        "예 - 실질적 대체권 있음 (교체 능력 + 경제적 효익)"
    ], key="q2")

# Q3: 경제적 효익
q3 = None
if q2 and "아니오" in q2:
    st.markdown("#### Q3. 고객이 경제적 효익의 대부분을 얻는가? (문단 B21~B23)")
    with st.expander("판단 지침"):
        st.markdown("""
        - 사용기간 동안 자산의 사용으로 얻는 경제적 효익의 **대부분**(substantially all)
        - 직접 사용, 전대, 생산물 판매 등 모든 형태 포함
        - 계약 범위 내에서의 효익만 고려 (계약 범위 밖 제3자 권리 제외)
        """)
    q3 = st.radio("고객의 경제적 효익 대부분 취득", [
        "예 - 대부분의 경제적 효익을 고객이 얻음",
        "아니오 - 고객이 대부분의 효익을 얻지 못함"
    ], key="q3")

# Q4: 사용 지시권
q4 = None
if q3 and "예" in q3:
    st.markdown("#### Q4. 고객이 자산의 사용을 지시할 권리가 있는가? (문단 B24~B30)")
    with st.expander("판단 지침"):
        st.markdown("""
        **아래 중 하나 충족 시 "예":**

        **(a) 사용 방법과 목적을 지시 (문단 B25)**
        - 고객이 자산의 사용 방법과 목적을 결정할 수 있음
        - 예: 어떤 화물을 운송할지, 언제 운송할지 결정

        **(b) 사용 방법이 미리 결정됨 + 고객이 운영/설계 결정 (문단 B26)**
        - 자산의 사용 방법이 계약 전에 이미 결정되어 있으나
        - 고객이 자산을 **운영**하거나 운영 방법을 지시
        - 또는 고객이 자산을 사용 전에 사용 방법이 정해지도록 **설계**
        """)
    q4 = st.radio("고객의 사용 지시권", [
        "예(a) - 고객이 사용 방법과 목적을 지시",
        "예(b) - 사용방법 미리 결정 + 고객이 운영 또는 설계 결정",
        "아니오 - 공급자가 자산의 사용을 지시"
    ], key="q4")

# ── 판단 결과 ──
st.divider()
st.subheader("📋 판단 결과")

if "아니오" in q1:
    is_lease = False
    decision = "Q1 단계: 식별되는 자산 없음"
    ref = "K-IFRS 1116호 문단 B13"
elif q2 and "예" in q2:
    is_lease = False
    decision = "Q2 단계: 공급자에게 실질적 대체권 있음"
    ref = "K-IFRS 1116호 문단 B14~B19"
elif q3 and "아니오" in q3:
    is_lease = False
    decision = "Q3 단계: 고객이 경제적 효익의 대부분을 얻지 못함"
    ref = "K-IFRS 1116호 문단 B21~B23"
elif q4 and "아니오" in q4:
    is_lease = False
    decision = "Q4 단계: 고객이 자산의 사용을 지시할 권리 없음"
    ref = "K-IFRS 1116호 문단 B24~B30"
elif q4 and "예" in q4:
    is_lease = True
    sub = "(a) 사용 방법/목적 지시" if "예(a)" in q4 else "(b) 운영/설계 결정"
    decision = f"Q4 단계: 고객이 사용 지시권 보유 — {sub}"
    ref = "K-IFRS 1116호 문단 B25" if "예(a)" in q4 else "K-IFRS 1116호 문단 B26"
else:
    is_lease = None
    decision = "판단 미완료 — 위의 질문에 모두 답해주세요"
    ref = ""

if is_lease is True:
    st.success(f"### ✅ 리스에 해당합니다\n\n**결정 경로:** {decision}\n\n**근거:** {ref}")
    st.info("→ 다음 단계: **단기/소액 면제 판단** 또는 **할인율 산정** 후 **리스이용자 재계산**으로 이동")
elif is_lease is False:
    st.error(f"### ❌ 리스에 해당하지 않습니다\n\n**결정 경로:** {decision}\n\n**근거:** {ref}")
    st.info("→ 리스가 아니므로 K-IFRS 1116호 적용 대상이 아닙니다. 일반 비용/서비스 계약으로 처리합니다.")
else:
    st.warning(decision)

# 판단 요약 테이블
if is_lease is not None:
    st.markdown("#### 판단 경과")
    steps = []
    steps.append({"단계": "Q1. 식별 자산", "답변": "예" if "예" in q1 else "아니오", "근거": "문단 B13~B20"})
    if q2: steps.append({"단계": "Q2. 실질적 대체권", "답변": "아니오" if "아니오" in q2 else "예", "근거": "문단 B14~B19"})
    if q3: steps.append({"단계": "Q3. 경제적 효익", "답변": "예" if "예" in q3 else "아니오", "근거": "문단 B21~B23"})
    if q4: steps.append({"단계": "Q4. 사용 지시권", "답변": q4.split(" - ")[0], "근거": "문단 B24~B30"})
    steps.append({"단계": "결론", "답변": "★ 리스" if is_lease else "★ 리스 아님", "근거": ref})

    import pandas as pd
    st.dataframe(pd.DataFrame(steps), use_container_width=True, hide_index=True)
