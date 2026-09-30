## 한눈에 보기

<!-- 쉬운 한국어와 짧은 문장으로 작성하세요. 이 부분만 읽어도 결과와 결정사항을 이해할 수 있어야 합니다. 기술 정보는 Developer Details에 보존하세요. -->

### 1. 이번에 무엇을 했나?

### 2. 실제로 무엇이 달라졌나?

### 3. 확인 결과는 어땠나?

<!-- 통과, 실패, 건너뜀, 미실행을 구분하세요. -->

### 4. 아직 남은 문제는?

### 5. 내가 결정해야 할 게 있나?

<!-- '없음' 또는 '있음'을 명시하세요. 필요하면 선택지와 장단점을 쉬운 말로 적으세요. -->

### 6. 지금 상태는?

<!-- 준비 중 / 개발 중 / 테스트 중 / 사람 확인 필요 / 완료 후보 / 완료 / 문제 발견 / 추가 작업 필요 중 하나를 적으세요. -->

## Developer Details

<!-- 아래 기술 증거와 위 한국어 요약이 일치해야 합니다. -->

## Change and reason

Issue: #<!-- number; required source of truth -->
Root cause or goal:
Files and user-visible behavior:

## Evidence

Reproduction or acceptance examples:
Exact commands and results (PASS/FAIL/NOT RUN, counts):
Gate baseline and exception changes:
Protected artifact check (`python scripts/check_protected.py --base origin/main`):
Manual browser/editor checks:

## Review and handoff

Harness 문서 동기화 (해당하는 경우 확인):

- [ ] Harness 구조가 바뀌었다면 `docs/harness/ARCHITECTURE.md`를 함께 검토·갱신했다.
- [ ] Harness 구현 상태가 바뀌었다면 `docs/harness/HARNESS_STATUS.md`의 근거와 다음 단계를 함께 검토·갱신했다.

Reviewer findings and fixes:
Remaining risks or skipped checks:
Human business acceptance needed:

Technical PASS is unavailable while any required test is FAIL, SKIP, or NOT RUN.

<!-- Never include private client data, credentials, or real client numbers. -->
