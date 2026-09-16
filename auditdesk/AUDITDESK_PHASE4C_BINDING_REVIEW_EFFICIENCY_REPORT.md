# AuditDesk Phase 4C Binding Review Efficiency Report

작성일: 2026-09-16. 브랜치: `feat/auditdesk-binding-review-efficiency`.
최종 확정: 전체 Python **507 passed / 0 failed / 0 skipped / 0 errors**, 미확인 0개. UI 26개, TypeScript, production build 및 diff 검사가 통과했다. 검토 도구 구현 완료와 실자료 전체 검토 완료는 구분한다. Commit/push하지 않았다.

## 1. Review queue model

기존 Studio → 계정 매핑 → 제출 준비 · Golden binding 화면에 검토 큐를 연결했다. Phase 4B `binding.py`의 후보 생성, 단건 검증, coverage, Golden 생성 의미와 Phase 4 `golden.py`는 변경하지 않았다. 새 `binding_review.py`는 기존 draft의 원문·후보·결정에서 검토용 상태를 계산한다.

상태 우선순위는 Stale → Conflict → Confirmed → High / Medium / Low / Source insufficient다. 수동 확정도 검증에 통과하면 Confirmed에 포함되며 별도 수동 건수를 제공한다. stale에서는 기존 결정이 있어도 현재 유효한 확정으로 집계하지 않는다. 기존 M-40 gate 자체는 그대로이며 stale 시 생성이 차단된다.

대상 순서는 기존 Golden 시트/행/열 순서를 유지한다. 상태·본문/주석·시트·Role·자료형·예외를 조합해 필터링할 수 있다. Role/자료형 필터는 미확정에서는 현재 후보들의 속성, 확정에서는 선택한 요소의 속성을 사용한다. 상태 및 전체 coverage는 필터에 따라 전체 분모가 바뀌지 않는다.

## 2. Confidence grouping

기존 문자열 유사도와 후보 순위를 변경하지 않았다. High 검토 큐는 높은 문자열 점수 자체가 아니라 다음 **추가적인 현재 근거**가 있는 경우에만 제공한다.

- 현재 원천의 Prefix+Name, Role, DataType, Period가 현재 taxonomy 출현과 정확히 일치.
- 원천 및 taxonomy scope가 선택한 보고 범위와 정확히 일치.
- 단일 원천 후보/단일 taxonomy 후보이고 동일 QName의 다른 Role이 없음.
- 현재 source context의 회사/기간/단위/차원을 기존 `_validate`로 검증.
- 차원 signature가 일치하거나, 현재 원천이 차원 없음 `[]`을 명시하고 해당 Role에 DOMAIN 축이 없음. 알 수 없는 차원을 임의로 `[]`로 바꾸지 않음.
- 현재 layout hash에 귀속된 명시적 대상 셀 근거가 있음.
- source snapshot hash 일치 및 conflict/stale 0.

High는 자동 승인이 아니다. 회사 확장 요소는 별도 예외 큐에서 수동 검토하며 batch 그룹에서 제외한다. 같은 QName이 여러 Role에 존재하면 이번 구현에서는 일괄 그룹에서 제외한다. 근거가 일부만 있으면 기존 후보 상태에 따라 Medium/Low, taxonomy 또는 원문 후보가 없으면 Source insufficient로 남긴다.

## 3. Batch review logic

High 항목을 QName/Role/DataType/Period 및 회사·scope·기간·단위·차원 context가 같은 그룹으로 묶는다. 사용자는 그룹 근거와 대상 목록에서 선택 항목 또는 그룹 전체를 미리 볼 수 있다. 체크박스 선택이나 미리보기는 저장하지 않는다. 검토 근거를 입력하고 **선택 항목 일괄 확정 / 그룹 전체 확정** 버튼을 누를 때만 저장한다.

대상 셀·원문 셀 ID·실제 원문 표시값·taxonomy 출현을 미리보기에서 함께 보여준다. 일반 단건 확정/취소/수동 선택도 그대로 유지한다. batch 결정에는 검토자, 시각, source block, 검토 근거, batch ID가 기록된다. 단건 취소 시 해당 셀만 미확정으로 돌아간다.

명시적 배치 근거의 입력은 Phase 4B의 선택적 **현재 원천 index JSON**을 확장한다. 기존 index도 그대로 수용하지만 대상 근거가 없으면 High로 올리지 않는다.

```json
{
  "dsd_sha256": "현재 DSD hash",
  "taxonomy_sha256": "현재 taxonomy hash",
  "layout_sha256": "현재 배치 hash",
  "report": {"company": "...", "scope": "...", "period_end": "...", "fiscal_number": "..."},
  "facts": [{
    "source_id": "원문 시작:끝",
    "source_evidence": "현재 원천 및 대상 검토 근거",
    "prefix": "...", "name": "...", "role": "...",
    "data_type": "monetary", "period": "INSTANT",
    "dimensions": [], "context": {"company": "...", "scope": "...", "instant": "...", "unit": "KRW", "dimensions": []},
    "review_target_ids": ["시트명:행:열"]
  }]
}
```

위 예시는 계약 설명이며 실제 QName/기간/차원을 채운 자료가 아니다. report는 해당 draft 입력과 정확히 같아야 한다. `review_target_ids`가 있으면 현재 layout hash 및 존재하는 대상 ID를 검사한다. 이 명시적 원천 연결은 새 자동 매칭 알고리즘이 아니다. 확인되지 않은 대상 좌표를 index에 기입해 coverage를 채워서는 안 된다.

## 4. Exception queues

복수 후보, 기간 불일치, 자료형 불일치, dimension 불확실, 회사 확장 요소, 동일 QName 복수 Role, 원천 부족, 배치 후보 없음, stale, conflict를 각각 제공한다. 항목이 여러 예외에 속할 수 있으므로 예외 수를 합산해 전체 셀 수로 해석하지 않는다. 미확정 기본 필터를 유지하면서 시트/Role/자료형 범위를 좁힐 수 있다.

## 5. Keyboard / fast review workflow

1. 기존 입력 경로로 후보 생성 또는 저장 검토 불러오기.
2. 상단 전체 지표와 예외 큐를 확인하고 필터 선택.
3. 대상 셀과 원문/Top N/근거를 같은 화면에서 검토.
4. 단건 확정 후 기본적으로 다음 미확정으로 이동. 이 동작은 체크박스로 해제할 수 있다. 필터는 유지된다.
5. 이전/다음 미확정 버튼, 현재 위치/필터 대상 수/전체 수, 시트별·본문/주석별 진행률 제공.
6. 입력 폼 밖에서 Alt+↑/↓ 이동, Alt+1~4 Top N 선택, Ctrl+Enter 단건 확정, Alt+Backspace 확정 취소. 입력/IME 조합/키 반복에는 적용하지 않고 batch 승인 단축키는 제공하지 않는다.

필터를 바꾸면 현재 대상이 포함되지 않을 경우 첫 해당 대상으로 이동한다. 더 이상 필터 내 미확정이 없으면 단건 상세 선택을 비운다. 이미 확정한 항목의 취소/수정은 Confirmed 또는 전체 필터에서 가능하다. 수동 taxonomy 선택과 저장 오류 후 재시도는 기존 경로를 유지한다.

실자료 응답 측정에서 원문·taxonomy·배치 전체를 매번 반환하면 약 32MB가 됨을 확인했다. 새 화면의 단건/batch 저장은 `compact: true`를 보내 변경된 결정(취소는 null), revision, 현재 coverage/큐 상태만 받고 이미 읽은 원문·후보는 유지한다. 기존 API의 기본 전체 응답 계약은 유지했다. ID 또는 revision이 맞지 않는 응답은 병합하지 않는다.

## 6. Safety / transaction design

`POST /api/studio/bindings/{id}/batch-preview`는 대상 수, 동일 근거 조건, 영향 시트/Role, source hashes, conflict 0, stale 0, 대상별 결정 내용을 반환한다. revision/hash/대상/결정 내용을 포함한 결정적 미리보기 token을 생성한다. token은 보안 인증이 아니라 미리보기와 저장 내용의 일치 확인용이다.

`POST /api/studio/bindings/{id}/batch-confirm`은 SQLite `BEGIN IMMEDIATE` 안에서 최신 draft를 다시 읽는다. revision이 다르면 409, 근거 부족·원천 변경·미리보기 불일치·잘못된 항목이면 422다. 모든 항목을 기존 단건 `_validate`로 검사하고, 변경 후 hash를 한 번 더 확인한 다음 한 번의 payload UPDATE로 저장한다. 중간 오류는 transaction을 rollback한다. 부분 확정은 없다.

다른 항목에 conflict가 있어도 일괄 저장은 막는다. 따라서 전체 conflict/stale가 있으면 batch-reviewable 및 그룹 목록도 0으로 표시한다. 사용자 별 인증 체계나 네트워크 협업 프로토콜은 추가하지 않았다. 기존 로컬 저장 모델과 revision 방식에 따른다.

## 7. Metrics

기록: required, candidate available, no candidate, high/medium/low confidence, source insufficient, conflict, confirmed, manually assigned, batch confirmed, remaining, stale, batch reviewable, individual review remaining.

- overall confirmation % = 현재 유효한 confirmed / required.
- candidate coverage % = 원문 배치 후보가 하나 이상 있는 대상 / required. 기존 3,191 baseline과 같은 정의다.
- high-confidence reviewable % = 현재 batch 대상 / required.
- manual-review-required % = (required − 현재 confirmed − batch 대상) / required.

candidate available은 taxonomy/기간/차원 검토 완료를 뜻하지 않는다. 단건/일괄 결정 저장 시 `review_metrics` snapshot을 payload에 기록하고, 읽을 때 현재 원천 hash로 다시 계산한다. 과거 결정이 원천 변경 때문에 유효하지 않게 된 경우 예전 snapshot을 현재 coverage로 표시하지 않는다.

## 8. Golden gate integration

기존 M-40 구현을 변경하지 않았다. batch도 동일 `_validate`를 사용한다. 99/100 확정에서는 생성이 거부되고, 100/100 + conflict 0 + stale 0에서만 허용된다. 통합 fixture에서 실제 API 후보 생성 → 미리보기 → 명시적 batch 확정 → 나머지 정적 원문 단건 확정 → 실제 BIFF8 Excel/taxonomy 생성까지 검증했다. 출력 문자열이 DSD 원문이고 수식 0개임을 확인했다. 검토 정보는 기존 별도 review.json에만 남는다.

## 9. Prior mapping suggestion

같은 회사/scope의 과거 사용자 확정을 참조한다. 현재 taxonomy에 같은 QName 및 Role이 존재하고, 원문 레이블과 block identity가 같거나 원문 section/headers가 같은 경우 **이전 확정 기반 후보**를 현재 대상의 Top N 위에 별도로 표시한다. 기존 추천 점수/순위 배열은 재작성하지 않는다.

과거 결정·기간·차원을 자동 저장하거나 승계하지 않는다. 후보 버튼은 현재 source/taxonomy만 선택하고 현재 기간/단위/차원/검토 근거는 비워 재검토하게 한다. 삭제된 현재 요소 또는 다른 회사/scope는 재사용하지 않는다. 새로운 검토의 decisions는 빈 상태에서 시작한다. 현재 자료와 실제 전기 검토 DB를 비교한 실사용 검증은 없으며 fixture/API 회귀로 검증했다.

## 10. 코스맥스 실자료 검토량 감소 분석

Phase 4B의 코스맥스 당기 DSD/taxonomy/layout snapshot을 사용하고 세 원천 파일의 현재 SHA256 일치를 재확인했다. 후보 생성 엔진이 변경되지 않았으므로 동일한 5,732 DSD source / 1,346 taxonomy 출현 / 5,638 target에 새 검토 projection을 적용했다. 두 번의 큐 생성 결과가 동일했고 최초 측정은 약 0.52초였다. 실제 원본 및 사용자 결정은 수정하지 않았다.

| 지표 | 결과 |
|---|---:|
| Required | 5,638 |
| Candidate available | 3,191 (56.60%) |
| No layout candidate | 2,447 |
| High confidence | 0 |
| Batch-reviewable | 0 |
| Medium | 3,115 |
| Low | 36 |
| Source insufficient | 2,487 |
| Conflict / Stale | 0 / 0 |
| Confirmed / Manual / Batch confirmed | 0 / 0 / 0 |
| Individual review remaining | 5,638 |
| Golden gate | 차단 |

원문 후보가 있는 3,191개 중 40개는 taxonomy 후보가 없어 Source insufficient에 포함된다. 따라서 Source insufficient 2,487과 no-layout 2,447은 같은 지표가 아니다.

예외 건수: 복수 후보 3,191, dimension 불확실 5,638, 동일 QName 복수 Role 3,136, 회사 확장 후보 포함 1,481, 자료형 불일치 후보 포함 62. 기간 불일치 0은 기간 검증 완료가 아니라 현재 기간 정보가 불확실하다는 뜻이다. 예외는 중복 집계된다.

**실자료에서 검토해야 하는 고유 셀 수 감소는 0개다.** 현재 자료에는 고확신 일괄확정에 필요한 명시적 원천·기간·차원·대상 근거가 부족하다. 사용자 검토 시간을 실제로 단축한 비율은 측정하지 않았다. 이번 개선은 큐/필터/빠른 이동/명시적 그룹 도구이며 전체 42시트 자동화나 검토 완료라고 표현하지 않는다.

읽기 전용 응답 직렬화 측정: 전체 32,248,894 bytes → compact 3,409,463 bytes (**89.43% 감소**). JSON 직렬화는 해당 실행에서 0.706초 → 0.075초였다. 이는 동일 snapshot의 계산/직렬화 측정이며 네트워크·브라우저·사람의 검토 시간 benchmark가 아니다. 최초 불러오기는 전체 응답이며 compact 상태도 약 3.4MB여서 대규모 사용성 한계는 남는다.

## 11. Phase 1~4B 회귀 결과

완료된 전체 일반 묶음 및 최종 API 재검증의 고유 ID를 대조했다. Phase 1 **38 passed**, Phase 2 **56 passed**, Phase 3 **15 passed**, Phase 4 **18 passed**, Phase 4B **25 passed**로 기존 Phase 회귀 총 **152 passed**다. Phase 4B와 새 Phase 4C를 함께 실행한 대상 회귀는 41 passed (25 + 16)였다. 기존 테스트 삭제·기대값 완화·코어 복원은 없었다.

## 12. 전체 테스트 결과

구현 전 Python 13개는 새 모듈/라우터 부재로 failed, UI 3개는 새 helper 부재로 failed였다. 최초 Python 실행의 임시 폴더 권한 오류는 실패 재현에 포함하지 않고, workspace 내부 전용 basetemp에서 다시 재현했다.

추가 실패 재현: 전체 conflict가 있는데 batch-reviewable 1로 표시되는 경우, 필터 변경 후 제외된 대상 유지, 이전 후보 선택 시 static 셀 종류 유지. 각 실패를 확인하고 수정했다. 기본 후보/일괄확정뿐 아니라 storage UPDATE 실패 rollback, 실파일 API 생성, 기존 UI 호환성을 검사했다.

실자료 응답 크기 확인 후 compact 저장 응답/API 취소/클라이언트 병합 실패 테스트를 추가하고 수정했다. 마지막 API 변경에 직접 관련된 Phase 4B/4C 41개를 재실행해 41 passed를 확인했다. 전체 집계에서는 해당 ID의 이전 결과를 대체하며 추가로 더하지 않는다. UI의 취소 병합, 원문 유지, 잘못된 검토 ID 거부도 검사했다.

| 검증 | 결과 |
|---|---|
| Phase 4C Python | 16 passed |
| Phase 4C UI | 7 passed |
| 전체 UI (Phase 1/2/3/4B/4C) | 26 passed / 0 failed / 0 skipped |
| TypeScript | PASS (`tsc --noEmit --incremental false`) |
| Production build | PASS (Vite production, TypeScript 별도 선행) |
| Full Python | 507 passed / 0 failed / 0 skipped / 0 errors; 미확인 0 |
| 실제 브라우저 / Excel / DART | NOT TESTED |

전체 Python은 장시간 taxonomy 7 / notes 6 / worksheet 2와 나머지 492개를 서로 중복 없이 나눠 실행한다. 이전 Phase 4B에서 발생한 진단 출력 중 access violation을 피하기 위해 이번 실행은 faulthandler 진단 플러그인만 비활성화했다. 테스트 내용·통과 기준·실자료 입력을 변경하거나 skip하지 않았다.

최종 네 묶음 모두 종료 코드 0: taxonomy **7 passed**, notes **6 passed**, worksheet **2 passed**, 나머지 **492 passed**. 나머지 492개 중 마지막 API 수정에 관련된 41개는 최신 재실행 결과로 대체했다. 따라서 **492 − 41 + 41 + 7 + 6 + 2 = 507개**이며 중복 합산은 없다. 수집 ID와 JUnit의 이름/순서/개수를 대조했고 미확인 ID가 없으며 최종 Python 및 UI 소스 hash가 검증 대상과 일치한다. 기존 fixture deprecation 2개와 기본 Excel 스타일 경고 1개는 그대로다.

UI에서는 stale의 저장된 확정을 `저장된 확정 (현재 무효)`로 표시하는 실패도 재현 후 수정했다. 현재 유효한 확정과 오래된 저장 결정을 혼동하지 않도록 한다. 실제 브라우저 화면 검증을 대신하는 결과는 아니다.

## 13. 실제 사용성 한계

- 5,638개 사용자 확정은 여전히 필요하다. 빠른 검토 기능의 실제 회계사 사용 시간/오류율은 미측정이다.
- 현재 원천 index를 작성·검토하는 별도 UI는 없다. 이미 검토된 current source index에 필요한 명시적 배치 근거를 제공할 수 있는 경우만 High batch가 가능하다.
- 후보의 의미가 불명확하거나 단위/차원이 누락된 항목을 자동으로 해결하지 않는다. Raw XBRL/IXD 자동 수입, 새 회계 매칭 규칙은 추가하지 않았다.
- Role의 DOMAIN 존재 및 명시적 원천 근거 검사는 완전한 XBRL 차원 네트워크 검증이 아니다.
- 본문/주석 분류는 현재 Golden의 시트 이름 관례(숫자 주석명/주석 접두)를 사용한다. 임의 명명의 다른 회사 layout에서는 실제 구조와 대조가 필요하다.
- 수천 개 항목의 native select/그룹 목록을 유지했다. 대규모 가상 스크롤·페이지 재설계·실제 브라우저 성능 검증은 하지 않았다.
- revision/hash 확인 후 외부 원천 파일이 바뀌면 다음 조회/생성에서 stale로 차단된다. 외부 Excel 편집기를 잠그지는 않는다.

## 14. 다음 단계와 변경 범위

다음 검증 단계는 실제 회계사의 대표 시트 검토 소요 시간 측정, 명시적 당기 원천 근거 확보, 실제 브라우저와 Excel/DART 확인이다. 이는 본 Phase 완료를 주장하기 위해 추정하거나 자동 확정으로 대체하지 않았다.

Phase 4C 제품 5개: `auditdesk/binding_review.py`, `auditdesk/routers/binding_api.py`, `webui/src/BindingReview.tsx`, `webui/src/ReviewQueue.tsx`, `webui/src/bindingReviewQueue.ts`.
회귀 2개: `tests/test_phase4c_review.py`, `webui/tests/phase4c.test.cjs`. 보고서 1개: 이 파일.

기존 `CLAUDE.md`, 기존 감사 보고서 두 개, `auditlink-v2/.claude/`, `DSD_footing/.claude/`는 작업 대상에서 제외한다. 로그/JUnit/임시 DB/Excel/JSON은 ignored `.pytest_cache/phase4c`, production 산출물은 ignored `auditdesk/static`에 둔다. Commit/push하지 않는다.

기존 사용자 파일 5개의 작업 전 SHA256 일치를 확인했다. 기존 `binding.py`, `golden.py`, Phase 4B Python/UI 테스트의 diff는 없다. staged 파일은 없다. 신규 파일과 추적 파일의 공백 검사를 통과했다.

Phase 4C 변경량은 보고서 제외 제품/테스트 7개 **+704 / -9**이며 보고서 1개가 추가된다. 일반 tracked-only `git diff --stat`에는 신규 파일이 빠지고 기존 사용자 `CLAUDE.md`(+72/-22)가 포함되므로 이를 Phase 4C 변경량으로 합산하지 않는다. 제품 코드는 5개, 테스트는 2개로 범위를 유지했다.

검증 근거는 ignored `.pytest_cache/phase4c/`의 `full-nodeids.json`, `full-groups.json`, 그룹별 JUnit, `revalidated.xml`, `revalidated-source-hashes.json`, `ui-source-hashes.json`, `final-results.json`, `ui-final.log`, `build.log`, `cosmax-review.json`, `view-probe.json`에 분리했다. 이 파일들은 제품 변경에 포함하지 않는다.

## Phase 4C completion status

- M-43: 구현/회귀 PASS
- M-44: 명시적 그룹 검토 구현/회귀 PASS; 실자료 batch 대상 0
- M-45: 예외 큐 구현/회귀 PASS
- M-46: 빠른 검토 UI 회귀 PASS; 실제 작업 시간 개선 미측정
- M-47: transaction/revision/hash/preview 회귀 PASS
- M-48: 지표 계산/저장 구현 및 실자료 측정 PASS
- M-49: 기존 gate 유지 및 실파일 생성 회귀 PASS
- M-50: 현재 유효성 확인 후 미확정 참고 후보 표시 회귀 PASS
- Required: 5,638
- Candidate: 3,191 (56.60%)
- High confidence: 0
- Batch-reviewable: 0
- Individual review remaining: 5,638
- Confirmed: 0
- Golden gate: 실자료 차단; fixture 99% 차단 / 100% 통과
- Full Python suite: 507 passed / 0 failed / 0 skipped / 0 errors; 미확인 0
- UI regression: 26 passed
- TypeScript: PASS
- Production build: PASS
- git diff --check: PASS
- Remaining risks: 실자료 검토 건수 감소 0, 실제 검토 시간/브라우저 미검증, 현재 원천 근거 확보 필요
