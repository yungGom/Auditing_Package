# 개발 작업 Harness 현재 상태

## 한눈에 보기

**전체 단계:** 현재 작업 브랜치에는 Issue 한 건을 읽어 변경·자동 검사·독립 검토·결과 보고까지 진행하는 도구가 있습니다. GitHub의 기본 브랜치에 배포됐다는 뜻은 아닙니다. **지금 사용할 수 있는 부분:** 정해진 양식으로 Issue를 작성하고, 보호 파일 검사와 제품별 검사를 실행하며, 결과와 남은 공백을 구분해 보고할 수 있습니다. [Master Dashboard](https://github.com/users/yungGom/projects/1)에 요청 15건을 연결해 현재 상태와 다음 행동을 볼 수 있습니다. **사람이 해야 하는 부분:** 요청과 업무 판단 확인, Pull Request 작성·최종 수용·병합, 수동 화면 확인과 Project 현황 갱신입니다. 현재 우선 마무리할 일은 ① 실제 자료 검사 공백의 처리 계약 확인, ② 선행 변경의 안전한 병합, ③ 실제 성공 검사를 확인한 뒤 병합 보호 설정입니다. 자동화 추가는 이번 범위가 아닙니다.

**판정 기준:** 2026-09-30에 조사한 `feat/orchestrator-mvp`의 `cfb01bd`, GitHub Issue·PR과 [실제 Project](https://github.com/users/yungGom/projects/1) 설정. 아래 상태는 그 **조사 시점의 구현과 확인된 원격 상태**를 뜻하며, 기본 브랜치 반영·실제 업무 승인을 뜻하지 않습니다. 2026-10-01 운영 준비 재조사에서는 #4/#6/#20 모두 초안·회귀 CI 실패, main protection 없음·rulesets 없음, closeout 요청 #23 추가로 총 15건을 확인했습니다. 상세 근거는 [마무리 계획](HARNESS_V1_CLOSEOUT.md)에 있습니다. [이전 architecture 조사 기록](architecture_history.md)은 더 이른 기준의 자료이므로 현재 판정에는 사용하지 않았습니다.

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
| Merge 전 검증 | 🟡 부분 구현 / 수동 단계 존재 | CI 검사 정의와 CODEOWNERS가 있으나 2026-10-01 main 보호 없음·rulesets 없음 확인 | [CI](../../.github/workflows/harness.yml), [적용 한계](enforcement.md), [CODEOWNERS](../../.github/CODEOWNERS) | 저장소 소유자가 필수 검사·검토 규칙 확인/설정 |
| GitHub Project 연동 | 🟡 부분 구현 / 수동 단계 존재 | [Master Dashboard](https://github.com/users/yungGom/projects/1), 필드·저장 화면·Issue 연결은 실제 구성됨. 코드에서 자동 갱신은 없음 | [Project](https://github.com/users/yungGom/projects/1), [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md) | 자동 전환 전 Issue 근거·권한·오류 처리 설계 |
| Master Request Registry | 🟡 부분 구현 / 수동 단계 존재 | Issue 14건을 Project에 연결하고 중복 없는 Request ID를 부여. 새 Issue 등록은 수동 | [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md), [Project](https://github.com/users/yungGom/projects/1) | 남은 과거 작업을 근거별 조사하고 새 요청 등록 절차 운영 |
| Owner Inbox | 🟡 부분 구현 / 수동 단계 존재 | Owner Action·Done 제외 필터의 저장 화면을 구성. 항목 값은 사람이 갱신 | [Project Inbox](https://github.com/users/yungGom/projects/1), [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md) | 화면 표시와 담당자 행동을 운영 중 검증·갱신 |
| Project status update | 🟡 부분 구현 / 수동 단계 존재 | 초기 상태는 Issue·PR 근거로 수동 입력. Orchestrator 자동 갱신 없음 | [Project](https://github.com/users/yungGom/projects/1), [동기화 책임](MASTER_DASHBOARD_BACKFILL.md) | 단계별 증거를 확인한 수동 갱신 유지 후 자동화 검토 |
| Issue → Project registration | 🟡 부분 구현 / 수동 단계 존재 | 기존 Issue 14건 연결 완료. 이후 새 Issue 자동 등록 없음 | [Project](https://github.com/users/yungGom/projects/1), [`development_workflow.md`](development_workflow.md) | 새 Issue 생성 시 사람이 Project에 등록 |
| Verification → Project status update | 🟡 부분 구현 / 수동 단계 존재 | 현재 검증 근거를 Project 요약에 수동 반영. 자동 연결 없음 | [`scripts/orchestrator.py`](../../scripts/orchestrator.py), [동기화 책임](MASTER_DASHBOARD_BACKFILL.md) | 검증 증거 확인 후 수동 갱신, 자동화는 별도 설계 |
| Merge → Done update | 🟡 부분 구현 / 수동 단계 존재 | 병합 PR #2·#3의 과거 작업을 수동으로 Done 분류. 새 병합의 자동 전환 없음 | [#21](https://github.com/yungGom/Auditing_Package/issues/21), [#22](https://github.com/yungGom/Auditing_Package/issues/22), [동기화 책임](MASTER_DASHBOARD_BACKFILL.md) | 실제 병합·수용 범위를 확인한 뒤 수동 전환 |
| Backfill | 🟡 부분 구현 / 수동 단계 존재 | 기존 Issue 6건 재사용, 미기록 작업 8건을 Issue로 복원·Project 연결. 세부 DSD/AuditDesk 이력은 조사 중 | [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md), [#18](https://github.com/yungGom/Auditing_Package/issues/18), [#19](https://github.com/yungGom/Auditing_Package/issues/19) | 완료 추측 없이 항목별 근거를 계속 확인 |
| Agent 간 자동 routing | ❌ 미구현 | Issue 한 건의 고정된 Implementer·Reviewer 순서만 존재; 동적 배정 없음 | [`orchestrator_mvp.md`](orchestrator_mvp.md), [`scripts/orchestrator.py`](../../scripts/orchestrator.py) | 배정 규칙·권한·실패 인계 설계 |
| 전체 end-to-end 자동화 | ❌ 미구현 | Issue 작성/첫 승인, Project, PR 생성, 최종 승인, 병합이 수동 | [`development_workflow.md`](development_workflow.md), [`orchestrator_mvp.md`](orchestrator_mvp.md) | 사람 판단을 남긴 채 단계 연결 설계 |

**알려진 검사 공백:** [`enforcement.md`](enforcement.md)는 현재 공개 체크아웃에서 AuditDesk의 실제 파일이 없어 전체 CI 회귀 검사가 실패할 수 있다고 명시합니다. 부분 작업의 성공과 저장소 전체의 기술 검증 통과를 혼동하지 않습니다. 실제 검사 결과는 해당 실행의 보고서에서 확인해야 하며, 이 문서의 상태 표가 개별 테스트의 PASS를 보증하지는 않습니다.

## GitHub Project 운영 경계

[Master Dashboard](https://github.com/users/yungGom/projects/1)에 요청한 9개 업무 필드, 제품별·상태별 저장 화면과 상태 보드를 구성했습니다. 11개 Status에는 별도 `Blocked`가 포함됩니다. [Backfill 기록](MASTER_DASHBOARD_BACKFILL.md)은 14개 Issue의 근거와 수동/자동 동기화 경계를 설명합니다. **화면은 실제로 있지만 자동 라우팅·상태 갱신은 없습니다.** `PR` 상태는 최종 수용 뒤 병합을 준비하는 단계로 쓰되, 검증 결과를 전달할 초안 PR은 그 전에 열릴 수 있습니다.

상태가 바뀌는 Harness 변경에서는 근거와 다음 단계를 다시 확인합니다. 구조도 함께 바뀐다면 [ARCHITECTURE.md](ARCHITECTURE.md)도 갱신합니다.

## 수동 운영 준비

[OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)는 등록·번호·담당자 행동·완료·막힘의 수동 운영 책임을 설명합니다. #23/HARNESS-004는 정식 운영 마무리 요청입니다. 승인 전 조사 시점에는 전체 실패가 남아 있었습니다. 아래 최신 승인 구현과 검증보고서는 기본 검사 통과를 확인했지만 실제 자료 호환성·업무 수용·기본 브랜치 반영은 완료로 선언하지 않습니다. [현재 병합 경로와 결정안](HARNESS_V1_CLOSEOUT.md)을 함께 확인합니다.

## Issue #23 승인 구현 — 2026-10-01

자료가 없는 새 환경의 반복 검사와 실제 자료 확인을 분리했습니다. [`test_all.py`](../../scripts/test_all.py)는 공개·합성 Technical Gate와 실제 자료별 BLOCKED/NOT RUN을 각각 보고합니다. 실제 자료 확인·업무 수용·기본 브랜치 배포는 여전히 수동이며 완료로 표시하지 않습니다. 새 runner는 자료 상태만 확인하고 실제 자료 검사를 자동 실행하지 않습니다. 기존 [`test_auditdesk.py`](../../scripts/test_auditdesk.py)는 엄격한 전체 검사로 유지됩니다.

- 명시적 자료 검사 목록: [`auditdesk_compatibility.json`](../../scripts/auditdesk_compatibility.json), 80 selectors. 기존 자료 없는 empty/parameterized 사례는 81건이며 새 테스트는 기본 Technical scope입니다.
- 자료가 필요 없는 기존 계산 검사 4개는 그대로 실행합니다. 기대값을 바꾸거나 검사를 새 합성 성공으로 대체하지 않습니다.
- 새 시간 제한·실행하지 못한 검사·결과 근거 검사: [`harness_process.py`](../../scripts/harness_process.py), [`harness_evidence.py`](../../scripts/harness_evidence.py).
- 검사 범위 목록의 변경에는 새 Owner Decision이 필요합니다. 보호 checker 자동 등록은 보호 정책의 정확한 변경 승인 후 별도로 처리합니다.
- PR별 실제 검사 결과와 병합 가능 상태는 [Issue #23](https://github.com/yungGom/Auditing_Package/issues/23) 최신 검증보고서를 따릅니다. 위 초기 red 기록은 승인 구현 전 조사 이력입니다.

최신 승인 구현과 실제 검사 결과는 [Issue #23 검증보고서](ISSUE_23_VERIFICATION.md)를 함께 읽습니다. 기본 검사 통과와 실제 자료 81건 미확인, 선행 PR의 미반영 상태를 구분합니다.
