# Harness 운영 방법

## 한눈에 보기

### 1. 이번에 무엇을 했나?
요청부터 결과 확인까지 담당자가 할 일을 정리했습니다.
### 2. 실제로 무엇이 달라졌나?
여러 대화를 찾지 않고 요청 기록과 현황판에서 할 일을 확인할 수 있습니다.
### 3. 확인 결과는 어땠나?
현황판과 담당자 확인 화면은 있습니다. 개발 절차의 기본 코드 반영과 전체 검사 완료는 아직입니다.
### 4. 아직 남은 문제는?
현황은 사람이 갱신해야 합니다. 실제 자료 확인이 필요한 검사도 남아 있습니다.
### 5. 내가 결정해야 할 게 있나?
있음. 요청 내용과 결과를 확인하고 업무상 받아들일지 기록해 주세요.
### 6. 지금 상태는?
운영 준비 중. 이 문서는 수동 운영 안내이며 정식 운영 완료 선언이 아닙니다.

## 새로운 요청이 생겼을 때

1. **요청 기록 만들기**: GitHub Issue를 만들고 실제 문제·업무 영향·원하는 변화·성공 기준·담당자 결정을 쉬운 한국어로 씁니다. 상세 개발 정보는 아래에 둡니다.
2. **쉬운 제목**: [정책의 제목 규칙](../../governance/POLICY.md#issue-title-rule)에 따라 작성합니다. 기존 같은 요청이 있으면 새로 만들지 않습니다.
3. **고유 번호**: 담당 실행자가 현황판의 같은 분류 번호를 모두 조회해 다음 번호를 부여합니다. 번호는 Issue에도 기록합니다. 삭제·취소된 번호도 재사용하지 않습니다. 여러 사람이 동시에 등록하면 번호 충돌을 확인하고 발급 담당자에게 맡깁니다.
4. **현황판 등록**: Issue URL을 [Master Dashboard](https://github.com/users/yungGom/projects/1)에 추가합니다. Project 분류, Request ID, Status=Issue Drafted, Current Summary, Next Action, Last Evidence를 채웁니다. 우선순위는 근거가 없으면 비워 둡니다. 정식 작업을 현황판의 메모만으로 관리하지 않습니다.
5. **요청 승인**: 담당자가 확인할 내용이 있으면 Awaiting Owner Approval / Issue Review 또는 Decision Required로 표시합니다. Owner는 Issue 댓글에 승인 범위와 미승인 범위를 기록합니다. 미결정 업무·보호 변경은 진행하지 않습니다.
6. **개발**: 담당 실행자가 승인 계약을 읽고 Implementing으로 갱신합니다. 실제 수행을 위해 세션을 엽니다. 기존 사용자 변경을 보존합니다.
7. **검사**: 공식 검사 담당자가 명령과 PASS/FAIL/SKIP/NOT RUN, 자료 부족과 새 문제를 Issue에 기록하고 Automated Test 상태를 갱신합니다. 환경 오류를 제품 실패로 혼동하지 않습니다.
8. **별도 검토**: 구현과 분리된 읽기 전용 검토자가 요청·차분·검사 증거를 확인합니다. Reviewing 상태로 표시합니다. 막는 의견은 수정·재검사 후 재검토합니다.
9. **결과 보고**: Verification Report 상태에서 쉬운 한국어 요약을 맨 위에 놓고 실제 증거를 아래에 남깁니다. 필요한 화면 확인은 UAT Required로 따로 표시합니다.
10. **최종 승인**: Awaiting Final Approval / Verification Review로 표시합니다. Owner는 결과의 업무상 수용·반려·추가 확인을 Issue에 기록합니다.
11. **통합 준비**: 승인 후 PR 상태로 표시하고 연결된 변경 제안을 검토·병합합니다. 결과 전달용 초안은 그 전에 열 수 있습니다. approval·required check를 우회하지 않습니다.
12. **완료**: 승인 범위의 검사·별도 검토·업무 수용·필요한 병합을 확인한 뒤 Issue를 닫고 Done / None / Next Action=없음으로 갱신합니다. 병합만 보고 미실행 업무 확인을 완료라고 쓰지 않습니다.

## 내가 평소 확인할 화면

- [문용 Inbox](https://github.com/users/yungGom/projects/1/views/2): 지금 직접 확인하거나 결정할 일. 완료와 담당자 행동 없는 항목은 제외합니다.
- [진행 중](https://github.com/users/yungGom/projects/1/views/3): 구현·검사·검토·보고·통합 준비 상태.
- [막힌 작업](https://github.com/users/yungGom/projects/1/views/4): 다음 행동이 필요한 이유를 봅니다.
- [완료](https://github.com/users/yungGom/projects/1/views/5): 어떤 범위를 완료했는지 Issue에서 확인합니다.

## 언제 세션을 열어야 하나

진행상황은 Issue와 현황판에서 확인합니다. 세션은 조사·구현·검사·별도 검토를 실행할 때 엽니다. 세션 이름을 요청 번호나 상태보다 중요한 기준으로 삼지 않습니다. 실행 종료 시 상세 결과는 Issue에, 현재 상태만 현황판에 옮깁니다.

## 완료의 의미

검사 통과는 업무 수용과 다릅니다. 필수 검사에 실패·건너뜀·미실행이 있으면 전체 기술 검증 통과라고 쓰지 않습니다. 일부 작업이 확인됐더라도 실제 자료 검증 공백을 함께 적습니다. 사람은 실제 업무에 맞는 결과인지 별도로 판단합니다.

## Blocked의 의미

멈춘 이유, 필요한 증거, 다음 행동을 할 사람을 Issue에 적고 Status=Blocked로 표시합니다. 사람이 결정해야 하면 Owner Action=Decision Required, 담당 개발자가 해결해야 하면 None으로 두되 Next Action에 담당 역할과 행동을 적습니다. 날짜가 오래됐다는 이유로 완료로 바꾸지 않습니다.

## Developer Details

### 수동 운영 책임

| 시점 | 갱신 담당 | Issue 증거 / Project 값 |
| --- | --- | --- |
| 새 요청 | 접수 담당 | 계약·고유 ID / 분류·Issue Drafted |
| 승인·정책 결정 | Owner 기록 후 실행 담당 | 승인 댓글 / Implementing 또는 Blocked |
| 구현·검사·검토 | 해당 담당자가 증거 기록 후 현황 담당 | 파일·명령·결과·finding / 해당 상태와 다음 행동 |
| 보고·화면 확인 | 검증 담당, Owner | 쉬운 요약·미확인 시나리오 / Verification Review 또는 UAT Required |
| 최종 수용·병합 | Owner 기록 후 통합 담당 | 수용 댓글·병합 commit / PR 이후 완료 조건 충족 시 Done |

Owner Action의 None은 업무 승인이 끝났다는 뜻이 아니라 **지금 Owner에게 요청한 행동이 없다**는 뜻입니다. Issue Review=요청 확인, Decision Required=정책 결정, Verification Review=결과 확인, UAT Required=실제 화면 확인, PR Review=통합 변경 확인, Other=구체적 다른 행동을 Issue에 명시합니다. Current Summary는 짧은 한국어 1~3문장, Next Action은 담당 역할과 실제 행동, Last Evidence는 최근 근거와 Issue 링크를 둡니다. 단계 변경 직후 담당자가 수동 갱신합니다. 동일 Issue에 여러 실행 공간이 있어도 현황판 항목은 하나입니다.

Project는 비공개이며 권한 있는 계정이 볼 수 있습니다. 모든 상태 이동·등록·완료는 수동입니다. 자동화 추가는 이번 범위가 아닙니다. 1~2주 후 수동 운영 부담을 보고 등록·상태 이동·완료·Inbox 알림·Agents API를 검토할 수 있으며 우선순위는 아직 정하지 않습니다.

[병합 마무리 계획](HARNESS_V1_CLOSEOUT.md) · [개발 절차](development_workflow.md) · [현황](HARNESS_STATUS.md)

### 승인된 검사 분리 운영

[Issue #23 승인](https://github.com/yungGom/Auditing_Package/issues/23#issuecomment-5923919699) 이후 기본 `python scripts/test_all.py --report <결과.json>`는 공개·합성 Technical Gate입니다. 실제 자료 결과는 별도 `real_material_compatibility`에서 PASS/FAIL/SKIP/NOT RUN/BLOCKED를 확인합니다. exit 0만 보고 실제 호환성이나 업무 수용을 완료로 갱신하지 않습니다. 자료 의존 변경은 승인된 공개 자료로 별도 호환성 검사·필요한 화면 UAT를 실행한 후 Owner가 결정합니다. 고객·비공개 자료는 repository/CI 반입 금지입니다.

검사 결과 파일에는 검사 ID·상태·집계만 기록합니다. Technical Gate에서 자료 부족 외 새 실패·skip·실행 불가가 있으면 차단합니다. 실제 자료가 없으면 BLOCKED, 존재하더라도 미실행이면 NOT RUN입니다. 새 자료의 공개 출처·재배포 근거는 별도 승인합니다. 기존 전체 검사 명령은 유지합니다.

새 runner는 실제 자료의 상태 확인만 합니다. `--mode compatibility`도 검사 실행을 뜻하지 않습니다. 기존 `python scripts/test_auditdesk.py`의 실제 자료 검사는 출처·사용 권한·경로·SHA를 확인한 공개 자료가 별도로 승인된 통제 환경에서 수행합니다. 필요한 자료가 없는 기본 실행의 성공은 실제 호환성 완료가 아닙니다. 단순 승인 옵션으로 로컬 자료를 공개 자료라고 가정하지 않습니다.
