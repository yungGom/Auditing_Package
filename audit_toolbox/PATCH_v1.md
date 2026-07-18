# PATCH 1 — 참조 3파일 배치 + 런처 링크 + 회귀 테스트 고정

> 목표: 검증 구현(부록 A 3파일)을 그대로 배치해 **기능 동등성**을 확보하고,
> HANDOFF 5장 회귀 케이스를 pytest로 고정한다.

## 배치 위치 결정

HANDOFF은 `yungGom/Auditing_Package` 저장소 내 `audit_toolbox`를 대상으로 명시했으나,
실제 동작 중인 `audit_toolbox` 멀티페이지 앱은 저장소가 아니라 아래 경로에 존재한다.

```
C:\Users\moonyong\OneDrive - 서현회계법인\바탕 화면\자동화모음\audit_toolbox\audit_toolbox\
```

런처 `audit_toolbox.py`의 `col3` 블록·페이지 번호 체계(…12_OCR.py)가 모두 이 경로에만 존재하므로,
HANDOFF의 통합 지점(col3 끝, 13번 페이지)이 실재하는 **이 경로에 배치**했다.
※ 이 경로는 git 추적 대상이 아님 → 버전관리 필요 시 저장소로 별도 복사 검토(미결).

## 변경 내역

| 파일 | 작업 | 비고 |
|---|---|---|
| `fi_detector.py` | 신규 | 부록 A.1 그대로 (탐지 엔진) |
| `report_builder.py` | 신규 | 부록 A.2 그대로 (Excel 2시트 빌더) |
| `pages/13_Confirmation_Population.py` | 신규 | 부록 A.3 그대로 (Streamlit 페이지) |
| `audit_toolbox.py` | 수정 | `col3` 블록 끝에 📨 조회 모집단 완전성 링크 추가 |
| `test_confirmation_population.py` | 신규 | 회귀 테스트 (pytest/standalone 겸용) |

## 검증 게이트

- **회귀 테스트 (5장 9케이스)**: ✅ 통과
  - 실행: `python test_confirmation_population.py` (pytest 미설치 환경 대응, 완전 오프라인)
  - 결과: `10 passed, 0 failed`
    - case1 지점·법인격 롤업 / case2 계정추적 후보 / case3 노이즈 제외 /
      case4 미매칭 안전망 / case5 온라인 유형 충돌 방지 / case6 명칭 변형 매칭 /
      case7a·7b 전기 병합·변형 흡수 / case8 온라인 전화번호 제거 / case9 원본 보존
  - (5장은 9개 케이스 — case7을 a/b 2개로 분리해 총 10개 테스트 함수)
- **구문/임포트**: ✅ `py_compile` 통과 (4개 파일), streamlit 1.55.0 존재 확인
- **런처 링크**: ✅ `col3` 블록에 `pages/13_Confirmation_Population.py` page_link 추가

## 환경 메모

- venv: `.venv/Scripts/python.exe` (Python 3.14.0), pandas 2.3.3, openpyxl 3.1.5, streamlit 1.55.0
- pytest 미설치 → 테스트는 표준 `assert` + `__main__` 러너로 외부 설치 없이 실행 가능하게 작성.
  pytest 설치 시 `pytest test_confirmation_population.py`로도 동일 수집·실행됨.

## 미수행 (수동 확인 권장)

- Streamlit 실제 구동 스크린샷(업로드→매핑→탐지→다운로드)은 대화형 실행이 필요해 미첨부.
  `run.bat` 실행 후 사이드바 "📨 조회 모집단 완전성" 진입으로 확인 가능.

## 다음 단계

- PATCH 2: Phase H1 헤더행 자동 탐지 (우선순위 H1 → H3 → H2).
- 착수 전 HANDOFF 7장 열린 결정 확인 필요(매핑 프로파일 저장 위치 등) — PATCH 3 시점.
