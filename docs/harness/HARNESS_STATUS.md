# 개발 작업 Harness 현재 상태

## 한눈에 보기

**전체 단계:** 현재 작업 브랜치에는 Issue 한 건을 읽어 변경·자동 검사·독립 검토·결과 보고까지 진행하는 도구가 있습니다. GitHub의 기본 브랜치에 배포됐다는 뜻은 아닙니다. **지금 사용할 수 있는 부분:** 정해진 양식으로 Issue를 작성하고, 보호 파일 검사와 제품별 검사를 실행하며, 결과와 남은 공백을 구분해 보고할 수 있습니다. 전체 작업 현황판을 위한 공개 Issue 12건을 조사·복원했으나, GitHub Project 자체는 인증 대기 중입니다. **사람이 해야 하는 부분:** 요청과 업무 판단 확인, Pull Request 작성·최종 수용·병합, 수동 화면 확인과 Project 현황 갱신입니다. 다음으로 효과가 큰 일은 ① 인증 후 기존 Project를 확인하고 현황판 만들기, ② 처음과 마지막 사람 승인 기록을 명확하게 강제하기, ③ 병합 전 필수 검사를 저장소 설정에서 의무화하기입니다.

**판정 기준:** 2026-09-30에 조사한 `feat/orchestrator-mvp`의 `cfb01bd` 및 같은 날 GitHub Issue·PR 목록. 아래 상태는 그 **조사 시점의 구현과 확인된 원격 상태**를 뜻하며, 기본 브랜치 반영·GitHub 설정 적용·실제 업무 승인을 뜻하지 않습니다. [이전 architecture 조사 기록](architecture_history.md)은 더 이른 기준의 자료이므로 현재 판정에는 사용하지 않았습니다.

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
| GitHub Project 연동 | ❌ 미구현 | 코드 연동 없음. 공개 목록에서 Project가 보이지 않았고, 비공개 Project는 인증 실패로 조회하지 못함. 실제 Project 생성·필드·View 설정 전 | [`orchestrator_mvp.md`](orchestrator_mvp.md) (연동 범위 밖), [Project 설정안](MASTER_DASHBOARD_BACKFILL.md) | 인증 후 기존 비공개 Project 확인, 중복 없이 Master Dashboard 생성 |
| Master Request Registry | 🟡 부분 구현 / 수동 단계 존재 | Issue 12건을 조사·복원했으나 Project에 등록되지 않음; 고유 Request ID 미부여 | [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md), [현황판 Issue #14](https://github.com/yungGom/Auditing_Package/issues/14) | Project 목록·기존 ID 확인 뒤 불변 ID 부여·Issue 연결 |
| Owner Inbox | ❌ 미구현 | 즉시 사람 행동 후보는 기록했지만 필터 View는 없음 | [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md) | Owner Action 필드와 Done 제외 필터를 실제로 구성·검증 |
| Project status update | ❌ 미구현 | Orchestrator와 Project 간 상태 갱신 없음 | [`orchestrator_mvp.md`](orchestrator_mvp.md), [동기화 책임](MASTER_DASHBOARD_BACKFILL.md) | Issue 증거와 Project 상태를 먼저 수동 일치시킨 뒤 자동화 검토 |
| Issue → Project registration | ❌ 미구현 | Issue는 생겼으나 Project 항목 연결 기능·설정 없음 | [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md), [`development_workflow.md`](development_workflow.md) | Project 생성 뒤 기존 Issue 12건부터 연결 |
| Verification → Project status update | ❌ 미구현 | 검증 결과는 Issue/보고서에 남아도 Project에는 반영되지 않음 | [`scripts/orchestrator.py`](../../scripts/orchestrator.py), [동기화 책임](MASTER_DASHBOARD_BACKFILL.md) | 검증 증거 확인 후 수동 갱신, 자동화는 별도 설계 |
| Merge → Done update | ❌ 미구현 | 병합·업무 수용 확인과 Project Done 연결 없음 | [`development_workflow.md`](development_workflow.md), [동기화 책임](MASTER_DASHBOARD_BACKFILL.md) | 실제 병합·수용 근거를 확인하는 전환 규칙 마련 |
| Backfill | 🟡 부분 구현 / 수동 단계 존재 | 열린 Issue 6건 재사용, 근거가 있던 미기록 작업 6건을 Issue로 복원; 과거 병합 PR·세부 DSD/AuditDesk 항목은 추가 조사 필요 | [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md), [#14](https://github.com/yungGom/Auditing_Package/issues/14)–[#19](https://github.com/yungGom/Auditing_Package/issues/19) | 완료 추측 없이 남은 이력 확인, Project에 연결 |
| Agent 간 자동 routing | ❌ 미구현 | Issue 한 건의 고정된 Implementer·Reviewer 순서만 존재; 동적 배정 없음 | [`orchestrator_mvp.md`](orchestrator_mvp.md), [`scripts/orchestrator.py`](../../scripts/orchestrator.py) | 배정 규칙·권한·실패 인계 설계 |
| 전체 end-to-end 자동화 | ❌ 미구현 | Issue 작성/첫 승인, Project, PR 생성, 최종 승인, 병합이 수동 | [`development_workflow.md`](development_workflow.md), [`orchestrator_mvp.md`](orchestrator_mvp.md) | 사람 판단을 남긴 채 단계 연결 설계 |

**알려진 검사 공백:** [`enforcement.md`](enforcement.md)는 현재 공개 체크아웃에서 AuditDesk의 실제 파일이 없어 전체 CI 회귀 검사가 실패할 수 있다고 명시합니다. 부분 작업의 성공과 저장소 전체의 기술 검증 통과를 혼동하지 않습니다. 실제 검사 결과는 해당 실행의 보고서에서 확인해야 하며, 이 문서의 상태 표가 개별 테스트의 PASS를 보증하지는 않습니다.

## GitHub Project 설정 대기

[Master Dashboard Backfill 기록](MASTER_DASHBOARD_BACKFILL.md)에 9개 필드, 요청한 저장 View, 11개 Status(별도 `Blocked` 포함), Issue별 등록 초안과 수동/자동 동기화 경계를 정리했습니다. 이는 **설정 완료된 현황판이 아닙니다.** Project 접근이 복구되면 실제 Project·기존 ID를 먼저 확인하고 등록해야 합니다. `PR` 상태는 최종 수용 뒤 병합을 준비하는 단계로 쓰되, 검증 결과를 전달할 초안 PR은 그 전에 열릴 수 있습니다.

상태가 바뀌는 Harness 변경에서는 근거와 다음 단계를 다시 확인합니다. 구조도 함께 바뀐다면 [ARCHITECTURE.md](ARCHITECTURE.md)도 갱신합니다.
