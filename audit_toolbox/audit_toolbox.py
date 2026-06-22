"""
Audit Toolbox - Main Launcher
"""
import streamlit as st
import socket

st.set_page_config(page_title="감사 도구 모음", page_icon="🔧", layout="wide")

st.title("🔧 감사 도구 모음")
st.caption("K-IFRS 리스 재계산 · 감가상각비 재계산 · PDF 도구 · 의사록 OCR")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🔍 리스 식별 판단")
    st.markdown("계약 조건 → 리스 여부 판정")
    st.page_link("pages/1_Lease_Identify.py", label="열기 →", icon="🔍")

    st.markdown("### 🏢 리스이용자 기본")
    st.markdown("리스부채 · ROU · 보증금 · 복구충당")
    st.page_link("pages/4_Lessee_Basic.py", label="열기 →", icon="🏢")

    st.markdown("### 🏦 리스제공자")
    st.markdown("금융/운용 분류 + 재계산")
    st.page_link("pages/7_Lessor.py", label="열기 →", icon="🏦")

    st.markdown("### 🏗️ 감가상각 재계산")
    st.markdown("원장 매핑 → 재계산 → 차이분석")
    st.page_link("pages/10_Depreciation.py", label="열기 →", icon="🏗️")

with col2:
    st.markdown("### 🏷️ 면제 판단")
    st.markdown("단기리스 · 소액자산 면제")
    st.page_link("pages/2_Lease_Exemption.py", label="열기 →", icon="🏷️")

    st.markdown("### 📈 변동리스료")
    st.markdown("지수/요율 연동 재측정")
    st.page_link("pages/5_Variable_Lease.py", label="열기 →", icon="📈")

    st.markdown("### 🔁 판매후리스")
    st.markdown("매각손익 안분 + 리스백")
    st.page_link("pages/8_Sale_Leaseback.py", label="열기 →", icon="🔁")

    st.markdown("### 📄 PDF 도구")
    st.markdown("이름변경 · 도장 · 번호찍기")
    st.page_link("pages/11_PDF.py", label="열기 →", icon="📄")

with col3:
    st.markdown("### 📐 할인율 산정")
    st.markdown("내재이자율 / 증분차입이자율")
    st.page_link("pages/3_Discount_Rate.py", label="열기 →", icon="📐")

    st.markdown("### 🔄 리스변경")
    st.markdown("기간연장 · 범위축소 · 혼합")
    st.page_link("pages/6_Lease_Modification.py", label="열기 →", icon="🔄")

    st.markdown("### 🔀 전대리스")
    st.markdown("원리스 + 전대 이중 구조")
    st.page_link("pages/9_Sublease.py", label="열기 →", icon="🔀")

    st.markdown("### 📋 의사록 OCR 정리")
    st.markdown("주총/이사회 의사록 → 엑셀 정리")
    st.page_link("pages/12_OCR.py", label="열기 →", icon="📋")

    st.markdown("### 📨 조회 모집단 완전성")
    st.markdown("분개장·명세서 → 금융기관 조회 대상 추출")
    st.page_link("pages/13_Confirmation_Population.py", label="열기 →", icon="📨")

st.divider()

st.markdown("### 🗺️ K-IFRS 16 Total Package 로드맵")
st.markdown("""
- **✅ 리스이용자:** 리스식별 · 면제판단 · 할인율 · 기본재계산 · 변동리스료 · 리스변경
- **✅ 리스제공자:** 금융/운용 분류 + 재계산
- **✅ 특수거래:** 판매후리스 · 전대리스
- **✅ 기타 도구:** 감가상각 재계산 · PDF 도구 · 의사록 OCR 정리
""")

st.divider()

st.markdown("### 🔒 보안 및 데이터 처리 안내")

with st.expander("이 프로그램은 외부로 데이터를 전송하지 않습니다 — 상세 설명", expanded=True):

    st.markdown("""
    #### 1. 네트워크 접속 범위

    이 프로그램은 **`localhost` (127.0.0.1)에서만 실행**됩니다.
    외부 IP에서 접속할 수 없고, 인터넷으로 데이터가 나가지 않습니다.

    `run.bat` 실행 파일에 아래 옵션이 포함되어 있어 외부 접속이 원천 차단됩니다:

    ```
    --server.address localhost          (로컬만 허용)
    --browser.gatherUsageStats false    (사용 통계 수집 비활성화)
    ```
    """)

    st.markdown("""
    #### 2. 직접 확인하는 방법

    프로그램 실행 중 명령 프롬프트를 하나 더 열고 아래 명령어를 입력하면:

    ```
    netstat -an | findstr 8501
    ```

    아래처럼 **127.0.0.1만 LISTENING** 상태인 것을 확인할 수 있습니다:

    ```
    TCP    127.0.0.1:8501    0.0.0.0:0    LISTENING
    ```
    """)

    st.markdown("""
    #### 3. 데이터 흐름

    ```
    [내 컴퓨터 엑셀/PDF] → [Python 처리 (localhost)] → [결과 엑셀/PDF 다운로드]
                          ↑                          ↑
                     외부 전송 없음              외부 전송 없음
    ```

    - 업로드한 파일: 브라우저 → 같은 컴퓨터의 Python 프로세스로 전달 (네트워크 미경유)
    - 외부 API 호출, 클라우드 저장, 원격 서버 통신: **전혀 없음**
    - 의사록 OCR도 로컬 EasyOCR 엔진 사용 (단, 모델은 최초 1회 다운로드)
    """)

    st.markdown("""
    #### 4. 의존성 패키지 안전성

    | 패키지 | 용도 | 네트워크 사용 |
    |---|---|---|
    | streamlit | 로컬 웹 UI | localhost만 |
    | pandas | 데이터 처리 | 없음 |
    | openpyxl | 엑셀 읽기/쓰기 | 없음 |
    | python-dateutil | 날짜 계산 | 없음 |
    | PyMuPDF | PDF 처리 | 없음 |
    | easyocr | 한글 OCR 엔진 | 최초 모델 다운로드 1회만 |
    | pdf2image | PDF → 이미지 변환 | 없음 |
    | Pillow | 이미지 처리 | 없음 |
    | tqdm | 진행률 표시 | 없음 |
    """)

    st.markdown("#### 5. 현재 상태 실시간 확인")
    try:
        hostname = socket.gethostname()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(('127.0.0.1', 8501))
        s.close()
        if result == 0:
            st.success(f"✅ 현재 127.0.0.1:8501 (localhost)에서만 실행 중입니다. (호스트: {hostname})")
        else:
            st.info(f"포트 8501 상태 확인 중... (호스트: {hostname})")
    except:
        st.info("네트워크 상태 확인은 실행 환경에서만 가능합니다.")

st.divider()
st.caption("왼쪽 사이드바에서도 각 도구로 이동할 수 있습니다.")
