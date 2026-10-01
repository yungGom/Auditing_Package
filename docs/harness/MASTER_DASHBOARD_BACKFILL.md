# 전체 개발 요청 현황판: 복원 기록과 설정안

## 한눈에 보기

Auditing_Package의 개발 요청은 **GitHub Issue를 기준 기록**으로 삼습니다. [Master Dashboard](https://github.com/users/yungGom/projects/1)는 Issue의 현재 상태·다음 행동을 한눈에 보여 주는 현황판이며, 검사 로그나 업무 판단의 원본이 아닙니다. 초기2026-09-30 복원 시점에 기존 Issue 6건을 재사용하고, Issue가 없던 작업 8건을 [#14](https://github.com/yungGom/Auditing_Package/issues/14)–[#19](https://github.com/yungGom/Auditing_Package/issues/19), [#21](https://github.com/yungGom/Auditing_Package/issues/21)–[#22](https://github.com/yungGom/Auditing_Package/issues/22)로 복원했습니다. **14건 모두 실제 Project에 연결했습니다.** Project ID는 `PVT_kwHODHEC7M4BlLOK`입니다. 현황판은 수동으로 갱신하며 자동 동기화가 된다고 주장하지 않습니다.

## 등록·갱신 기준

1. 인증된 계정에서 기존 Project가 0건임을 확인하고 새 Project 하나를 만들었습니다. 새 항목을 만들 때는 이 Project를 재사용합니다.
2. Project 안의 Request ID가 비어 있음을 확인하고 중복 없이 새 ID를 부여했습니다. 부여한 ID는 변경하거나 재사용하지 않습니다. 기존 작업 코드 `AD-03`과 `TC-020`은 별도 이력 식별자로 유지하며 새 Request ID로 덮어쓰지 않습니다.
3. 현재 코드 → 병합 PR → 열린 PR → Issue → 검사 결과 → Harness 문서 → 과거 기록 순으로 근거를 확인합니다. 브랜치·세션 이름만으로 완료를 판정하지 않습니다.
4. 정식 작업은 Issue와 연결합니다. Project Draft Item만으로 업무 계약을 보관하지 않습니다.
5. Project에는 짧은 한국어 현재 요약·다음 행동·최근 근거만 놓고, 상세 검증·승인 이력은 Issue에 둡니다.

## 기존 Issue와 Backfill 후보

**아래 Status·Owner Action은 실제 Project에 입력한 값입니다.** `None`은 업무 담당자에게 **지금 즉시 요청할 행동이 없다**는 뜻이며, 최종 업무 수용이 불필요하다는 뜻이 아닙니다. 우선순위는 근거 있는 업무 결정 전까지 비워 두었습니다.

| Issue | Project | Status | Owner Action | 현재 요약 / 다음 행동 | 근거 |
| --- | --- | --- | --- | --- | --- |
| [#5](https://github.com/yungGom/Auditing_Package/issues/5) | AuditDesk | PR | None | 합성 예제 검사는 통과하고 해당 범위는 수용됨. 실제 파일 호환성은 별도 [#17](https://github.com/yungGom/Auditing_Package/issues/17). 합성 변경의 통합 경로 확인 | #5 승인 댓글·검증 댓글, 로컬 커밋 `eb3f98a` |
| [#7](https://github.com/yungGom/Auditing_Package/issues/7) | AuditDesk | Verification Report | None | 작업별 결과 혼합 방지 수정·전용 검사 완료. 변경 제안과 업무 확인은 별도 | #7 본문, 로컬 커밋 `e7ca24f`; 전체 게이트는 기존 실패·건너뜀 |
| [#8](https://github.com/yungGom/Auditing_Package/issues/8) | DSD_FOOTING | Verification Report | UAT Required | PDF 출력 상태 고정 변경의 초안 PR이 열려 있음. 실제 화면 확인과 업무 수용이 남아 아직 최종 PR 단계가 아님 | [초안 PR #10](https://github.com/yungGom/Auditing_Package/pull/10), #8 본문 |
| [#9](https://github.com/yungGom/Auditing_Package/issues/9) | XBRL | Verification Report | None | 당기 우선 추천 경로의 초안 PR이 열려 있음. 실제 자료 정확도와 최종 수용이 남아 아직 최종 PR 단계가 아님 | [초안 PR #13](https://github.com/yungGom/Auditing_Package/pull/13), #9 본문·댓글 |
| [#11](https://github.com/yungGom/Auditing_Package/issues/11) | XBRL | Verification Report | None | 분류체계 선행 기능의 제한된 검사·독립 검토 완료. 상위 #9 및 실제 자료 검증을 계속 확인 | #11 댓글, [PR #13](https://github.com/yungGom/Auditing_Package/pull/13) |
| [#12](https://github.com/yungGom/Auditing_Package/issues/12) | XBRL | Verification Report | None | 공시 원문 해석 선행 기능의 제한된 검사·독립 검토 완료. 상위 #9 및 실제 자료 검증을 계속 확인 | #12 댓글, [PR #13](https://github.com/yungGom/Auditing_Package/pull/13) |
| [#14](https://github.com/yungGom/Auditing_Package/issues/14) | Harness | Awaiting Final Approval | Verification Review | Project·필드·저장 화면·Issue 연결과 검증 완료. 요청 분류·상태에 대한 최종 확인 대기 | [Project](https://github.com/users/yungGom/projects/1), [초안 PR #20](https://github.com/yungGom/Auditing_Package/pull/20) |
| [#15](https://github.com/yungGom/Auditing_Package/issues/15) | Harness | Blocked | None | 공통 보호·검사 절차는 초안에 있음. 기존 전체 검사 공백과 병합 강제 설정 확인이 남음 | [초안 PR #4](https://github.com/yungGom/Auditing_Package/pull/4), [적용 한계](enforcement.md) |
| [#16](https://github.com/yungGom/Auditing_Package/issues/16) | Harness | Blocked | None | 한 건 실행 도구와 쉬운 보고 문서는 게시됨. 선행 PR #4와 전체 검사 공백 해결 후 검토·수용 | [초안 PR #6](https://github.com/yungGom/Auditing_Package/pull/6), [상태 문서](HARNESS_STATUS.md) |
| [#17](https://github.com/yungGom/Auditing_Package/issues/17) | AuditDesk | Blocked | None | 실제 파일 호환성 자료의 공개 출처·배포 근거가 미확정. 승인 가능한 후보 조사 | #5 별도 작업 결정, #17 |
| [#18](https://github.com/yungGom/Auditing_Package/issues/18) | DSD_FOOTING | Issue Drafted | None | 과거 통합 리뷰 13개 항목의 현재 완료 여부를 코드·PR별로 재확인 중 | #18, `fix/dsd-footing-review-remediation` 이력; #8과 중복 방지 |
| [#19](https://github.com/yungGom/Auditing_Package/issues/19) | AuditDesk | Issue Drafted | None | 연결·검토·작업 흐름·화면 확인의 브랜치/기본 브랜치 차이를 조사 중 | #19, [AuditDesk 요청 대장](../../auditdesk/docs/REQUEST_LEDGER.md) |
| [#21](https://github.com/yungGom/Auditing_Package/issues/21) | AuditLink | Done | None | 회계연도 간 고객 복사 기능은 기본 코드에 병합됨. 당시 별도 화면 확인 여부는 미확인 | [병합 PR #2](https://github.com/yungGom/Auditing_Package/pull/2), 현재 코드 |
| [#22](https://github.com/yungGom/Auditing_Package/issues/22) | Audit Toolbox | Done | None | 외부조회 대상 검토 도구는 기본 코드에 병합됨. 이번에 새 실제 자료 검사는 하지 않음 | [병합 PR #3](https://github.com/yungGom/Auditing_Package/pull/3), 현재 코드 |

실제로 부여한 Request ID: #5 AD-001, #7 AD-002, #17 AD-003, #19 AD-004; #8 DSD-001, #18 DSD-002; #9 XBRL-001, #11 XBRL-002, #12 XBRL-003; #14 HARNESS-001, #15 HARNESS-002, #16 HARNESS-003; #21 AUDITLINK-001, #22 TOOLBOX-001. **14개가 모두 고유합니다.** 기존 작업 코드 AD-03·TC-020은 Issue 이력에 그대로 남습니다.

초기2026-10-01 확인 당시 **14개 Issue 항목**: DSD_FOOTING 2, AuditDesk 4, XBRL 3, Harness 3, AuditLink 1, Audit Toolbox 1. Blocked는 3건(#15–#17), 지금 Owner Action은 2건(#8의 화면 확인, #14의 현황판 결과 확인)입니다. #8의 화면 확인은 PR·테스트 상황을 다시 읽고 담당자와 시나리오를 정한 뒤 진행해야 합니다.

병합된 [PR #2](https://github.com/yungGom/Auditing_Package/pull/2)와 [PR #3](https://github.com/yungGom/Auditing_Package/pull/3)는 각각 #21·#22로 복원했습니다. [PR #1](https://github.com/yungGom/Auditing_Package/pull/1)은 병합되지 않아 완료로 등록하지 않았습니다. 과거 DSD_FOOTING·AuditDesk 세부 항목은 #18·#19에서 현재 코드와 계속 대조합니다. 로컬 브랜치의 존재는 병합이나 업무 수용의 증거가 아닙니다.

## Master Dashboard 실제 설정

| Field | Type | Options 또는 사용 원칙 |
| --- | --- | --- |
| Request ID | Text | Project 전체 중복 확인 뒤 부여; 한 번 부여하면 불변 |
| Project | Single Select | DSD_FOOTING, AuditDesk, XBRL, Harness, Common, AuditLink, Audit Toolbox |
| Status | Single Select | Intake, Issue Drafted, Awaiting Owner Approval, Implementing, Automated Test, Reviewing, Verification Report, Awaiting Final Approval, PR, Blocked, Done |
| Owner Action | Single Select | None, Issue Review, Decision Required, Verification Review, UAT Required, PR Review, Other |
| Current Summary | Text | 현재 상태를 쉬운 한국어 1–3문장으로. 개발 로그 복사 금지 |
| Next Action | Text | 다음 실제 행동 하나를 짧게 기록 |
| Priority | Single Select | High, Medium, Low. 근거 없으면 비워 둠 |
| Work Type | Single Select | Bug, Feature, Investigation, Policy Decision, UAT, Documentation, Harness, Refactor, Other |
| Last Evidence | Text | 마지막 검사·검토 결과의 짧은 요약; 상세는 Issue |

| 실제 저장 View | Type / filter |
| --- | --- |
| 📊 Master Dashboard | 기본 Table; Request ID, Project, Title, Status, Owner Action, Current Summary, Next Action, Priority 우선 표시 |
| 👤 문용 Inbox | Table; `-owner-action:None -status:Done`, Priority 오름차순·Updated 내림차순. 세션 표시는 숨김 |
| 🚧 In Progress | Implementing, Automated Test, Reviewing, Verification Report, PR |
| ⛔ Blocked | `Status = Blocked`; Current Summary·Next Action 표시 |
| ✅ Done | `Status = Done` |
| DSD_FOOTING / AuditDesk / XBRL / Harness / AuditLink / Audit Toolbox | 각 `Project` 값으로 필터한 별도 View |
| Status Board | Board; `Status`별 열. 승인 단계와 Blocked를 구분 |

## Issue와 Project의 동기화 책임

| 단계 | 현재 방식 | 목표 방식과 필요한 증거 |
| --- | --- | --- |
| Issue 생성 → Project 등록 | 수동. 기존 14건 연결 완료; 이후 새 Issue는 자동 등록되지 않음 | 등록 후 Issue Drafted. Issue 없는 정식 Draft Item 금지 |
| 첫 업무 승인 → Implementing | 수동 Issue 댓글 | 승인자의 결정과 범위를 Issue에 남긴 뒤 Project 상태 변경 |
| Implementer 완료 → Automated Test | Orchestrator 내부 순서 자동, Project 반영 없음 | 코드·검사 준비 증거를 Issue에 기록하고 상태 변경 |
| 검사 완료 → Reviewing | Orchestrator 내부 순서 자동, Project 반영 없음 | 공식 검사 결과를 Issue에 기록하고 상태 변경 |
| Reviewer 완료 → Verification Report | Orchestrator 내부 순서 자동, Project 반영 없음 | verdict와 차단 의견을 Issue에 기록하고 상태 변경 |
| 보고서 → 최종 승인 대기 | 보고 작성 수동/반자동, Project 반영 없음 | 업무용 요약과 결정사항을 Issue에 게시하고 Owner Action 설정 |
| 최종 승인 → PR | 수동 | 승인 댓글 확인 뒤 PR 단계로 이동; PR은 더 일찍 초안으로 열릴 수도 있음 |
| Merge → Done | 수동 / 자동 연동 없음. #21·#22는 병합·현재 코드 근거로 과거 구현 완료로 분류; 당시 별도 UAT는 주장하지 않음 | 실제 병합과 업무 수용 범위를 확인한 뒤 Done. CI 성공만으로 Done 금지 |

Project 화면과 필드는 설정됐지만 **상태 전환 자동화는 없습니다.** 기본 하위 Issue 자동 등록도 껐으며 활성 Project workflow는 없습니다. Issue 승인·검사·검토 증거를 확인한 사람이 Project 요약을 갱신해야 합니다. 현황판을 만들었다는 사실만으로 제품 개발이나 전체 검사가 완료된 것은 아닙니다. Project는 비공개이며 권한 있는 계정으로 접근합니다.


## 2026-10-01 통합 재검증 현황

위14건 표는 최초 복원 이력입니다. 현재 Project API는15개 실제 Issue 항목과15개 고유 Request ID를 확인했습니다. 추가 항목은 [Issue #23](https://github.com/yungGom/Auditing_Package/issues/23), HARNESS-004(운영 마무리)입니다. 제품별 수는 DSD_FOOTING2·AuditDesk4·XBRL3·Harness4·AuditLink1·Audit Toolbox1입니다.9개 업무 필드·12개 저장 화면(상태 보드 포함)을 재확인했으며 Inbox 필터는 `-owner-action:None -status:Done`입니다. 상태 갱신은 계속 수동입니다.

PR #4·#25·#6은 승인 후 main에 병합됐습니다. #15의 공통 검사 구현은 반영됐지만 기본 브랜치의 강제 검사 설정은 별도 확인·결정 대상입니다. #16의 도구 구현도 반영됐지만 실제 자료 호환성 완료를 주장하지 않습니다. 최신 main 보호 설정은404(Branch not protected), rulesets빈목록으로 확인했으며 변경하지 않았습니다. #14의 현황판 분류·상태 수용과 PR #20 병합은 아직 대기입니다. 기존POLICY의 현황판/제목 규칙 추가분은 main 대비 보호 검사 대상으로 남아 별도 Owner 판단이 필요합니다. 새 자동화·제품 변경·기존 기준 완화는 하지 않습니다.
