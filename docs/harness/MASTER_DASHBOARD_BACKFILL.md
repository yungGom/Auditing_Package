# 전체 개발 요청 현황판: 복원 기록과 설정안

## 한눈에 보기

Auditing_Package의 개발 요청은 **GitHub Issue를 기준 기록**으로 삼습니다. Project는 Issue의 현재 상태·다음 행동을 한눈에 보여 주는 현황판이며, 검사 로그나 업무 판단의 원본이 아닙니다. 2026-09-30 현재 공개 Issue 6건을 확인하고, Issue가 없던 작업 6건을 [#14](https://github.com/yungGom/Auditing_Package/issues/14)–[#19](https://github.com/yungGom/Auditing_Package/issues/19)로 복원했습니다. **GitHub Project는 아직 생성되지 않았습니다.** 아래 값은 Issue와 PR 근거로 정리한 *등록 초안*이며 실제 Project 필드값이 아닙니다.

## 등록 전 확인 기준

1. 동일 목적의 기존 Project가 있는지, 비공개 Project까지 인증된 계정으로 확인합니다.
2. 기존 Project의 Request ID를 먼저 읽고 중복 없이 새 ID를 부여합니다. 부여한 ID는 변경하거나 재사용하지 않습니다. 그 전까지 Issue 번호가 임시 식별자입니다.
3. 현재 코드 → 병합 PR → 열린 PR → Issue → 검사 결과 → Harness 문서 → 과거 기록 순으로 근거를 확인합니다. 브랜치·세션 이름만으로 완료를 판정하지 않습니다.
4. 정식 작업은 Issue와 연결합니다. Project Draft Item만으로 업무 계약을 보관하지 않습니다.
5. Project에는 짧은 한국어 현재 요약·다음 행동·최근 근거만 놓고, 상세 검증·승인 이력은 Issue에 둡니다.

## 기존 Issue와 Backfill 후보

**아래 Status·Owner Action은 제안값입니다.** 실제 Project가 생성되면 최신 Issue·PR·코드를 다시 확인한 뒤 입력해야 합니다. `None`은 업무 담당자에게 **지금 즉시 요청할 행동이 없다**는 뜻이며, 최종 업무 수용이 불필요하다는 뜻이 아닙니다. 우선순위는 근거 있는 업무 결정 전까지 임의 부여하지 않습니다.

| Issue | Project | 제안 Status | 제안 Owner Action | 현재 요약 / 다음 행동 | 근거 |
| --- | --- | --- | --- | --- | --- |
| [#5](https://github.com/yungGom/Auditing_Package/issues/5) | AuditDesk | PR | None | 합성 예제 검사는 통과하고 해당 범위는 수용됨. 실제 파일 호환성은 별도 [#17](https://github.com/yungGom/Auditing_Package/issues/17). 합성 변경의 통합 경로 확인 | #5 승인 댓글·검증 댓글, 로컬 커밋 `eb3f98a` |
| [#7](https://github.com/yungGom/Auditing_Package/issues/7) | AuditDesk | Verification Report | None | 작업별 결과 혼합 방지 수정·전용 검사 완료. 변경 제안과 업무 확인은 별도 | #7 본문, 로컬 커밋 `e7ca24f`; 전체 게이트는 기존 실패·건너뜀 |
| [#8](https://github.com/yungGom/Auditing_Package/issues/8) | DSD_FOOTING | Verification Report | UAT Required | PDF 출력 상태 고정 변경의 초안 PR이 열려 있음. 실제 화면 확인과 업무 수용이 남아 아직 최종 PR 단계가 아님 | [초안 PR #10](https://github.com/yungGom/Auditing_Package/pull/10), #8 본문 |
| [#9](https://github.com/yungGom/Auditing_Package/issues/9) | XBRL | Verification Report | None | 당기 우선 추천 경로의 초안 PR이 열려 있음. 실제 자료 정확도와 최종 수용이 남아 아직 최종 PR 단계가 아님 | [초안 PR #13](https://github.com/yungGom/Auditing_Package/pull/13), #9 본문·댓글 |
| [#11](https://github.com/yungGom/Auditing_Package/issues/11) | XBRL | Verification Report | None | 분류체계 선행 기능의 제한된 검사·독립 검토 완료. 상위 #9 및 실제 자료 검증을 계속 확인 | #11 댓글, [PR #13](https://github.com/yungGom/Auditing_Package/pull/13) |
| [#12](https://github.com/yungGom/Auditing_Package/issues/12) | XBRL | Verification Report | None | 공시 원문 해석 선행 기능의 제한된 검사·독립 검토 완료. 상위 #9 및 실제 자료 검증을 계속 확인 | #12 댓글, [PR #13](https://github.com/yungGom/Auditing_Package/pull/13) |
| [#14](https://github.com/yungGom/Auditing_Package/issues/14) | Harness | Blocked | Other | 현황판 설정 대기. GitHub Projects 인증·쓰기 권한 확인 후 기존 Project부터 조회 | #14, `gh auth status`의 invalid token, 로그아웃된 브라우저 |
| [#15](https://github.com/yungGom/Auditing_Package/issues/15) | Harness | Blocked | None | 공통 보호·검사 절차는 초안에 있음. 기존 전체 검사 공백과 병합 강제 설정 확인이 남음 | [초안 PR #4](https://github.com/yungGom/Auditing_Package/pull/4), [적용 한계](enforcement.md) |
| [#16](https://github.com/yungGom/Auditing_Package/issues/16) | Harness | Blocked | None | 한 건 실행 도구와 쉬운 보고 문서는 게시됨. 선행 PR #4와 전체 검사 공백 해결 후 검토·수용 | [초안 PR #6](https://github.com/yungGom/Auditing_Package/pull/6), [상태 문서](HARNESS_STATUS.md) |
| [#17](https://github.com/yungGom/Auditing_Package/issues/17) | AuditDesk | Blocked | None | 실제 파일 호환성 자료의 공개 출처·배포 근거가 미확정. 승인 가능한 후보 조사 | #5 별도 작업 결정, #17 |
| [#18](https://github.com/yungGom/Auditing_Package/issues/18) | DSD_FOOTING | Issue Drafted | None | 과거 통합 리뷰 13개 항목의 현재 완료 여부를 코드·PR별로 재확인 중 | #18, `fix/dsd-footing-review-remediation` 이력; #8과 중복 방지 |
| [#19](https://github.com/yungGom/Auditing_Package/issues/19) | AuditDesk | Issue Drafted | None | 연결·검토·작업 흐름·화면 확인의 브랜치/기본 브랜치 차이를 조사 중 | #19, [AuditDesk 요청 대장](../../auditdesk/docs/REQUEST_LEDGER.md) |

현재 **12개 Issue 후보**: DSD_FOOTING 2, AuditDesk 4, XBRL 3, Harness 3. 제안상 Blocked는 4건(#14–#17), 즉시 Owner Action 후보는 2건(#8의 화면 확인, #14의 인증)입니다. 이것은 **실제 Project 통계가 아닙니다**. #8의 화면 확인도 PR·테스트 상황을 다시 읽고 담당자와 시나리오를 정한 뒤 진행해야 합니다.

병합된 [PR #2](https://github.com/yungGom/Auditing_Package/pull/2)와 [PR #3](https://github.com/yungGom/Auditing_Package/pull/3)는 각각 AuditLink와 조회 모집단 도구의 과거 결과입니다. [PR #1](https://github.com/yungGom/Auditing_Package/pull/1)은 병합되지 않았습니다. 이들은 이번 12개 Issue에 **아직 포함되지 않았습니다**. 전 제품 요청을 완전히 복원하려면 기존 Issue/Project 항목과 기본 브랜치 결과를 더 대조한 뒤, 필요한 경우 별도 정식 Issue를 만들어야 합니다. 로컬 브랜치의 존재는 병합이나 업무 수용의 증거가 아닙니다.

## Master Dashboard 설정안 — 아직 미적용

| Field | Type | Options 또는 사용 원칙 |
| --- | --- | --- |
| Request ID | Text | Project 전체 중복 확인 뒤 부여; 한 번 부여하면 불변 |
| Project | Single Select | DSD_FOOTING, AuditDesk, XBRL, Harness, Common. AuditLink·Audit Toolbox 등 실제 저장소 프로젝트를 추가할 때 동일 명칭을 사용 |
| Status | Single Select | Intake, Issue Drafted, Awaiting Owner Approval, Implementing, Automated Test, Reviewing, Verification Report, Awaiting Final Approval, PR, Blocked, Done |
| Owner Action | Single Select | None, Issue Review, Decision Required, Verification Review, UAT Required, PR Review, Other |
| Current Summary | Text | 현재 상태를 쉬운 한국어 1–3문장으로. 개발 로그 복사 금지 |
| Next Action | Text | 다음 실제 행동 하나를 짧게 기록 |
| Priority | Single Select | High, Medium, Low. 근거 없으면 비워 둠 |
| Work Type | Single Select | Bug, Feature, Investigation, Policy Decision, UAT, Documentation, Harness, Refactor, Other |
| Last Evidence | Text | 마지막 검사·검토 결과의 짧은 요약; 상세는 Issue |

| View | Type / filter |
| --- | --- |
| 📊 Master Dashboard | 기본 Table; Request ID, Project, Title, Status, Owner Action, Current Summary, Next Action, Priority 우선 표시 |
| 👤 문용 Inbox | Table; `Owner Action != None` 및 `Status != Done`, 가능하면 Priority·Updated 순 |
| 🚧 In Progress | Implementing, Automated Test, Reviewing, Verification Report, PR |
| ⛔ Blocked | `Status = Blocked`; Current Summary·Next Action 표시 |
| ✅ Done | `Status = Done` |
| DSD_FOOTING / AuditDesk / XBRL / Harness | 각 `Project` 값으로 필터한 별도 View |
| Status Board | Board; `Status`별 열. 승인 단계와 Blocked를 구분 |

## Issue와 Project의 동기화 책임

| 단계 | 현재 방식 | 목표 방식과 필요한 증거 |
| --- | --- | --- |
| Issue 생성 → Project 등록 | 수동 / Project 없음 | 등록 후 Issue Drafted. Issue 없는 정식 Draft Item 금지 |
| 첫 업무 승인 → Implementing | 수동 Issue 댓글 | 승인자의 결정과 범위를 Issue에 남긴 뒤 Project 상태 변경 |
| Implementer 완료 → Automated Test | Orchestrator 내부 순서 자동, Project 반영 없음 | 코드·검사 준비 증거를 Issue에 기록하고 상태 변경 |
| 검사 완료 → Reviewing | Orchestrator 내부 순서 자동, Project 반영 없음 | 공식 검사 결과를 Issue에 기록하고 상태 변경 |
| Reviewer 완료 → Verification Report | Orchestrator 내부 순서 자동, Project 반영 없음 | verdict와 차단 의견을 Issue에 기록하고 상태 변경 |
| 보고서 → 최종 승인 대기 | 보고 작성 수동/반자동, Project 반영 없음 | 업무용 요약과 결정사항을 Issue에 게시하고 Owner Action 설정 |
| 최종 승인 → PR | 수동 | 승인 댓글 확인 뒤 PR 단계로 이동; PR은 더 일찍 초안으로 열릴 수도 있음 |
| Merge → Done | 수동 / 자동 연동 없음 | 실제 병합과 업무 수용을 확인한 뒤 Done. CI 성공만으로 Done 금지 |

Project 접근이 복구되기 전에는 자동 연동을 구현됐다고 표시하지 않습니다. 상태 전환은 나중에 추가할 수 있으나, Issue 승인·검사·검토 증거의 의미를 바꾸어서는 안 됩니다.
