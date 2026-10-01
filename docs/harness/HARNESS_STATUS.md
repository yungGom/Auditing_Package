# 개발 작업 Harness 현재 상태

## 한눈에 보기

**전체 단계:** 현재 작업 브랜치에는 Issue 한 건을 읽어 변경·자동 검사·독립 검토·결과 보고까지 진행하는 도구가 있습니다. 공통 정책과 반복 검사 절차는 첫 번째 승인 후 기본 코드에 반영됐습니다. 한 건 실행 도구와 이 상태표는 두 번째 변경의 사람 검토를 기다립니다. **지금 사용할 수 있는 부분:** 정해진 양식으로 Issue를 작성하고, 보호 파일 검사와 제품별 검사를 실행하며, 결과와 남은 공백을 구분해 보고할 수 있습니다. **사람이 해야 하는 부분:** 요청과 업무 판단 확인, Pull Request 작성·최종 수용·병합, 수동 화면 확인과 작업 현황판 갱신입니다. 다음으로 효과가 큰 일은 ① 이미 만든 작업 현황판을 수동 운영하기, ② 처음과 마지막 사람 승인 기록을 명확하게 강제하기, ③ 병합 전 필수 검사를 저장소 설정에서 의무화하기입니다.

**판정 기준:** 2026-10-01. PR #4는 Owner Approval 후 main `4e00a1c`에 병합됐습니다. 이 작업 브랜치는 그 main을 반영한 PR #6 검증 대상입니다. Master Dashboard는 실제 존재하지만 자동 상태 갱신은 없습니다. PR #6·#20은 아직 병합하지 않았습니다. 상태 표는 기능 존재와 운영 경계를 설명하며 개별 실행의 PASS를 보증하지 않습니다.

| 구성요소 | 상태 | 현재 동작 | 근거 | 다음 단계 |
| --- | --- | --- | --- | --- |
| Governance policy | ✅ 구현됨 | 공통 업무·보호·검증·보고 규칙을 문서화 | [`POLICY.md`](../../governance/POLICY.md), [`PROTECTED_ARTIFACTS.md`](../../governance/PROTECTED_ARTIFACTS.md) | 실제 GitHub 설정과 계속 대조 |
| 공통 AGENTS 규칙 | ✅ 구현됨 | 공통 정책과 보호 검사로 안내 | [`AGENTS.md`](../../AGENTS.md) | 정책 변경 때 함께 검토 |
| 프로젝트별 AGENTS 규칙 | ✅ 구현됨 | AuditDesk와 DSD_FOOTING의 별도 제약·검사 안내 | [`auditdesk/AGENTS.md`](../../auditdesk/AGENTS.md), [`DSD_footing/AGENTS.md`](../../DSD_footing/AGENTS.md) | 제품별 경계 변경 시 갱신 |
| 업무 요구사항 Intake | 🟡 부분 구현 / 수동 단계 존재 | 쉬운 한국어 요약과 기술 계약 양식이 있으나 작성은 사람 몫 | [Issue 템플릿](../../.github/ISSUE_TEMPLATE/development_task.md), [`development_workflow.md`](development_workflow.md) | 양식 누락·모호한 결정사항을 운영 중 확인 |
| Issue 생성/정리 | 🟡 부분 구현 / 수동 단계 존재 | 템플릿과 열린 Issue 읽기 기능은 있으나 생성·계약 정리는 자동 아님 | [Issue 템플릿](../../.github/ISSUE_TEMPLATE/development_task.md), [`orchestrator_mvp.md`](orchestrator_mvp.md) | Issue 작성·수정 책임 명확화 |
| Owner Approval Gate | 🟡 부분 구현 / 수동 단계 존재 | Issue에 미결정 사항이 명시되면 실행 중단; 모든 최초 승인 기록을 강제하지는 않음 | [`orchestrator_mvp.md`](orchestrator_mvp.md), [`scripts/orchestrator.py`](../../scripts/orchestrator.py) | Issue 검토 후 승인 증거의 필수 조건 결정 |
| Orchestrator | 🟡 부분 구현 / 수동 단계 존재 | 열린 Issue 한 건의 실행 순서와 결과 상태를 관리; 인증·환경 준비와 호출은 수동 | [`scripts/orchestrator.py`](../../scripts/orchestrator.py), [`orchestrator_mvp.md`](orchestrator_mvp.md) | 실제 작업에서 결과 확인·운영 범위 확대 |
| Implementer Agent | ✅ 구현됨 | 별도 쓰기 가능 실행에서 코드 조사·수정; 공식 검사는 Orchestrator 담당 | [`scripts/orchestrator.py`](../../scripts/orchestrator.py), [`orchestrator_mvp.md`](orchestrator_mvp.md) | 환경 경고와 제품 실패를 계속 구분 |
| Automated Tests | 🟡 부분 구현 / 수동 단계 존재 | 제품별 검사와 전체 진입점, CI가 있으나 수동 UI 검사와 알려진 미사용 가능 검사가 남음 | [`test_all.py`](../../scripts/test_all.py), [`test_auditdesk.py`](../../scripts/test_auditdesk.py), [`test_dsd_footing.py`](../../scripts/test_dsd_footing.py), [CI](../../.github/workflows/harness.yml) | 필요한 실제 파일 검사 공백 해결; 건너뜀 숨기지 않기 |
| Project별 Gate | 🟡 부분 구현 / 수동 단계 존재 | DSD_FOOTING 등록 PDF 기준 비교; AuditDesk 코어·웹 빌드 자동, UI 결정은 수동 | [`DSD_footing/GATES.json`](../../DSD_footing/GATES.json), [`auditdesk/GATES.json`](../../auditdesk/GATES.json), [`auditdesk/AGENTS.md`](../../auditdesk/AGENTS.md), [`test_dsd_footing.py`](../../scripts/test_dsd_footing.py) | 수동 게이트와 자동 결과 별도 보고 |
| Reviewer Agent | ✅ 구현됨 | Implementer와 분리된 읽기 전용 검토, verdict·finding 기록 | [`scripts/orchestrator.py`](../../scripts/orchestrator.py), [`review_protocol.md`](review_protocol.md) | 업무 승인과 혼동하지 않기 |
| FAIL → 수정 반복 | 🟡 부분 구현 / 수동 단계 존재 | 수정 가능한 실패·막는 검토 의견에 한해 제한된 재시도 | [`scripts/orchestrator.py`](../../scripts/orchestrator.py), [`orchestrator_mvp.md`](orchestrator_mvp.md) | 횟수 초과·환경/기존 공백은 사람에게 인계 |
| Verification Report | ✅ 구현됨 | 결과 JSON과 보고 양식에 검사·검토·남은 공백 기록 | [`scripts/orchestrator.py`](../../scripts/orchestrator.py), [`report_template.md`](report_template.md) | 업무상 판단에 필요한 사례 설명 보강 |
| Verification Report의 비개발자 요약 | 🟡 부분 구현 / 수동 단계 존재 | 여섯 질문의 한국어 요약을 생성하나 자동 문구는 정형 결과만 설명 | [`scripts/orchestrator_reporting.py`](../../scripts/orchestrator_reporting.py), [`report_template.md`](report_template.md) | 구체적인 업무 변화와 선택지는 사람이 확인 |
| Owner Final Approval Gate | 🟡 부분 구현 / 수동 단계 존재 | 최종 보고·PR에서 수용 판단을 요청; 도구가 승인을 기록하거나 병합을 제어하지는 않음 | [`POLICY.md`](../../governance/POLICY.md), [PR 템플릿](../../.github/pull_request_template.md), [`development_workflow.md`](development_workflow.md) | 최종 결정의 위치·증거를 운영 규칙으로 확정 |
| PR 생성 | 🟡 부분 구현 / 수동 단계 존재 | 인계 절차와 템플릿은 있으나 자동 생성 없음 | [PR 템플릿](../../.github/pull_request_template.md), [`development_workflow.md`](development_workflow.md), [`orchestrator_mvp.md`](orchestrator_mvp.md) | 사람이 Issue 연결과 결과 기재 |
| PR 검증 정보 | 🟡 부분 구현 / 수동 단계 존재 | PR 템플릿이 검사·보호 결과를 요구하고 CI 두 작업이 정의됨; 기록·실행 결과 확인은 필요 | [PR 템플릿](../../.github/pull_request_template.md), [CI](../../.github/workflows/harness.yml) | 실제 PR마다 FAIL/SKIP/NOT RUN 정확히 적기 |
| Merge 전 검증 | 🟡 부분 구현 / 수동 단계 존재 | CI 검사 정의와 CODEOWNERS가 있으나 브랜치 규칙의 강제 적용은 확인되지 않음 | [CI](../../.github/workflows/harness.yml), [적용 한계](enforcement.md), [CODEOWNERS](../../.github/CODEOWNERS) | 저장소 소유자가 필수 검사·검토 규칙 확인/설정 |
| GitHub Project 연동 | 🟡 부분 구현 / 수동 단계 존재 | [Master Dashboard](https://github.com/users/yungGom/projects/1)에 Issue를 수동 등록·갱신; 코드 자동 연동 없음 | 실제 GitHub Project, [`orchestrator_mvp.md`](orchestrator_mvp.md) | 후속 PR #20의 운영 문서는 별도 검토·병합 |
| Agent 간 자동 routing | ❌ 미구현 | Issue 한 건의 고정된 Implementer·Reviewer 순서만 존재; 동적 배정 없음 | [`orchestrator_mvp.md`](orchestrator_mvp.md), [`scripts/orchestrator.py`](../../scripts/orchestrator.py) | 배정 규칙·권한·실패 인계 설계 |
| 전체 end-to-end 자동화 | ❌ 미구현 | Issue 작성/첫 승인, Project, PR 생성, 최종 승인, 병합이 수동 | [`development_workflow.md`](development_workflow.md), [`orchestrator_mvp.md`](orchestrator_mvp.md) | 사람 판단을 남긴 채 단계 연결 설계 |

**알려진 검사 공백:** Issue #23 승인에 따라 공개·합성 반복 검사와 실제 자료 호환성을 분리합니다. `test_all.py`는 전자를 실행하며 후자는 BLOCKED/NOT RUN으로 남깁니다. 실제 자료 검사 완료나 업무 수용을 뜻하지 않습니다. 기존 strict `test_auditdesk.py`와 제품 테스트·기대값은 유지됩니다.

## GitHub Project를 만들 수 있을 때의 상태 열

아래는 최초 Harness 전용 현황판의 **이전 설계안**입니다. 실제 운영 현황은 [Master Dashboard](https://github.com/users/yungGom/projects/1)에서 확인합니다. 자동 이동은 구현하지 않았으며 후속 PR #20의 운영 설명은 별도 반영 대상입니다. `Auditing_Package Harness`라는 Project를 만들거나 같은 목적의 기존 Project를 확인한 뒤, Status 필드와 Board view에 순서대로 적용할 수 있습니다. 각 칸의 이동은 현재 자동화되지 않았습니다. `PR` 칸은 최종 수용 후 병합을 준비하는 상태를 뜻하며, 검증 결과 인계용 Pull Request 자체는 그 전에 열릴 수 있습니다.

| 순서 | Status | 뜻 |
| --- | --- | --- |
| 1 | Intake | 업무 요청 접수 |
| 2 | Issue Drafted | 요구사항 정리 중 |
| 3 | Awaiting Owner Approval | 최초 업무 판단 대기 |
| 4 | Implementing | 변경 작업 중 |
| 5 | Automated Test | 자동 검사 중 |
| 6 | Reviewer | 독립 검토 중 |
| 7 | Verification Report | 결과 보고 준비 중 |
| 8 | Awaiting Final Approval | 최종 업무 수용 대기 |
| 9 | PR | 변경 제안 검토·병합 대기 |
| 10 | Done | 사람의 수용·병합 결정 후 완료 |

상태가 바뀌는 Harness 변경에서는 근거와 다음 단계를 다시 확인합니다. 구조도 함께 바뀐다면 [ARCHITECTURE.md](ARCHITECTURE.md)도 갱신합니다.
