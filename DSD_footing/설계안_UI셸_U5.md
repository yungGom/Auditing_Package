# UI 셸 U-5 설계안 — 상세 패널 + 판단 버튼

U-4 완료(30e448b). 이 설계안은 구현 전 승인용이다. **승인 전 `ui/` 변경 없음.**

## 0. 선행 진단 결과 (구현 전 조사, 실측)

조선내화 반기연결 18건 재분석(`final.py ... --quiet`, 산출물은 확인 후 즉시 삭제) 실측.

**(a) `counterparts=[]`/`null` 아코디언 억제 분기 — 실데이터로 검증 가능, 합성 불필요**

| counterparts 상태 | 건수 |
|---|---|
| `[]` (빈 배열) | 8 |
| `null` | 0 |
| 값 있음 (1건) | 8 |
| 값 있음 (2건) | 2 |

`null`은 스키마상 발생하지 않는다(`l2_marks.py`/`marks.py`가 항상 배열을 만듦 — L1 마크도
`"counterparts": []`로 고정 직렬화). U-3의 `table_label` 미확인 분기와 달리 **이번엔 합성 테스트가
필요 없다** — 8건이 실제로 `[]`를 갖고 있어 "아코디언 자체를 그리지 않음" 요구사항을 실측으로
바로 확인할 수 있다. `null` 방어 코드는 넣되(`counterparts == null`도 `[]`와 동일 취급), 이 경로
자체는 현재 스키마에서 도달 불가능하다는 점을 게이트 보고서에 그대로 밝힌다.

**(b) `operands` 있는 마크 — 18건 중 4건**

전부 `cross:A5:p8:t1:r12:c2~c5` (반기연결손익계산서 세전이익 가감구조 검증 1건이 4개 열로 나뉜
것). 4건 모두 `operands` 5개(영업이익/기타수익/기타비용/금융수익/금융비용), 각 항목에
`label`/`value`/`sign`/`bbox([x0,top,w,h])`. L2 마크(10건)는 `operands`가 전부 `[]` — L2는
성분 가감이 아니라 표간 대사라 애초에 해당 없음. **operands 하이라이트 게이트는 이 4건으로
전수 검증한다.**

**(c) 마크 필드 확인 (설계에 필요한 것만)**

- `shown_value`/`computed_value`/`delta`/`formula` — L1 diff에 전부 채워짐. L1 unverified는
  `computed_value: null`, `delta`에 사유 문장(`SKIP_REASON_TEXT`)이 대신 들어있음.
- L2 마크는 `computed_value` 없음(L1 전용 필드). 비교 대상은 `shown_value` vs
  `counterparts[].amount`이고, `counterparts[].sign_flipped: true`일 때 표시 부호가 반대다.
- 출처 정보: `source.check/table/row/col`, `account`, `table_label`, `paper_no`(현재 전건
  `null`).
- 이력 정보: `verified_at`(도구 실행 시각, 전건 값 있음), `reviewed_at`/`reviewed_by`/`comment`/
  `note`(전건 `null` — 아직 회계사가 아무도 안 봤다는 뜻, 정상).
- `document.counts` = `{ok:130, diff:14, unverified:4, recon:58, prose:109, typo:2}`.

## 1. 범위 재확인

U-5 스펙 그대로. `operands` 하이라이트는 상세 패널의 산식(`formula`) 표시부 클릭으로 트리거.
U-6(최종 출력·marks.json 저장) 없음 — 판단 결과는 메모리에만.

## 2. 레이아웃 — 3열

`body`를 `#sidebar | #main | #detailPanel` 3분할로 바꾼다. `#detailPanel`은 마크 미선택 시
빈 상태(`"항목을 선택하세요"`) 표시, 폭 고정(예: 320px, `min-width`로 잘림 방지 — 스펙의
"금액 잘림 금지, 부족하면 두 줄"과 함께 CSS `white-space: normal`로 처리).

새 파일: `ui/web/detail.js`(로직) + `ui/web/detail.css`(스타일). `index.html`에
`<aside id="detailPanel">...</aside>` 추가, 스크립트 태그 추가.

**버스 연결**: `detail.js`는 `sidebar.js`가 이미 내는 `selectionChanged`를 그대로 구독한다.
`bus.js`는 이벤트당 리스너 배열이라(`listeners.get(event) || []`) 이미 여러 구독자를 지원 —
`viewer.js`가 구독하는 것과 별개로 `detail.js`가 같은 이벤트에 붙어도 코드 변경 불필요.
선택 상태의 소유자는 여전히 `sidebar.js` 하나다(U-4 계약 불변).

## 3. 검증 내역 — 문자 단위 차이 강조

**L1 diff**: `shown_value`와 `computed_value`를 우측 정렬(회계 금액 표기 관행 — 자리수가 다르면
짧은 쪽 앞에 공백 패딩) 후 자리별로 비교, 다른 자리만 적색. 예:
```
공시   (3,405,862)
재계산 (1,478,450)
        ^^^      ^
```
콤마·괄호·부호는 비교 문자에 포함(그 자리가 달라도 강조 대상 — 예: 괄호 유무 차이도 회계상
의미 있는 차이). **소수·단수 처리는 이미 `core.verdict(tol)`이 끝낸 결과값을 문자열로 받는
것뿐이라 이 UI는 반올림 판단을 하지 않는다** — 표시된 문자열을 그대로 비교.

**L1 unverified**: `computed_value`가 없으므로 강조 대상 없음. `delta`(사유 문장)만 그대로
표시.

**L2**: `shown_value` vs 각 `counterparts[].amount`. `sign_flipped: true`인 항목은 비교 전
부호만 UI에서 반전 표시하지 않고, **원래 표시된 `amount` 그대로 두고 "부호 반전 적용됨" 배지를
붙인다**(스펙 요구사항 — 회계사가 나중에 검증 가능해야 하므로 UI가 부호를 미리 뒤집어 "일치"로
보이게 만들면 안 됨). 문자 강조는 `amount`와 `shown_value`를 절대값 문자열 기준으로 정렬해
비교하고, 부호 자체의 불일치는 강조하지 않는다(배지가 이미 알림).

## 4. 아코디언 3종

| 아코디언 | 기본 상태 | 내용 |
|---|---|---|
| 대사 대상 (counterparts) | `level=="L2"`면 펼침, 아니면 접힘. `[]`면 아코디언 자체 미생성 | 각 항목: tag 칩 + label + amount + page + sign_flipped 배지 |
| 출처 | 접힘 | 면 / 표 / 계정과목 / 조서번호(`paper_no`, 없으면 "미배정") |
| 검토 이력 | 접힘 | `verified_at`(도구 실행) / `reviewed_at`·`reviewed_by`(회계사 확정, 현재 전건 null) / 기존 `comment`·`note` |

`counterparts[].tag`("주15" 임시값) 칩은 이번에 실제 렌더해서 폭·가독성을 육안 확인 후 보고한다
(스펙 요구사항 그대로) — `max-width` + 말줄임 + `title` 툴팁으로 1차 구현하고, 실측 후 필요하면
조정을 다시 보고한다.

## 5. 판단 버튼 — 상태값 매핑, 승인 필요

기존 `status`는 3-state(`pending`/`approved`/`removed`, CLAUDE.md 결정 12)뿐이고, 이건
**렌더링 조건**("removed가 아니면 그린다")과 묶여 있다. "이상없음/확인함"(A)과
"차이아님/해당없음"(R)을 이 3-state에 어떻게 얹을지는 U-6(최종 PDF)의 의미까지 건드리는
결정이라 임의로 정하지 않는다.

**A안 — `approved` 하나로 통일, 판단 방향은 별도 필드**
`status`는 A/R 둘 다 `"approved"`로만 바꾸고, 새 필드 `judgment: "confirmed"|"rejected"`를
추가해 방향을 구분. 지면에는 A/R 둘 다 원래 마크(X 등)가 그대로 남는다 — "회계사가 봤다"는
사실만 반영, 마크 자체는 조서에서 지워지지 않는다.
`[되돌리기 쉬움]` — 필드 추가만, 기존 렌더 조건 무영향.
**증상**: R 처리(도구 오탐 판정)해도 최종 PDF에 X가 그대로 남는다 — 나중에 이게 오탐이었다는
건 색인 엑셀이나 회계사 코멘트로만 알 수 있다.

**B안 — 기존 3-state 그대로 재사용**
A(이상없음/확인함) → `status="approved"`. R(차이아님/해당없음) → `status="removed"`(도구가
틀렸으니 지면에서 마크를 뺀다 — 결정 11 "마크는 삭제 대신 removed로 바꾼다"와 정확히 합치).
새 필드 불필요, `render.py`의 기존 조건(`status != "removed"`)이 그대로 맞물린다.
`[되돌리기 쉬움]` — 스키마 변경 없음.
**증상**: R 처리하면 최종 PDF에서 그 X/? 표시가 사라진다. "도구가 이 항목을 지적했지만 회계사가
검토해서 오탐으로 판정했다"는 이력이 지면 자체에는 안 남고 marks.json(향후 U-6에서 저장 시)에만
남는다 — 지면만 보는 사람은 애초에 지적이 없었던 것처럼 보인다.

**C안 — 4-state로 스키마 확장** (`pending`/`confirmed`/`rejected`/`removed`)
가장 명시적이지만 `marks.py`/`render.py` 스키마·R-1 골든 재기준선이 필요해 이번 스코프(U-5는
`ui/`만) 밖이다. U-6 착수 시 다시 검토 대상으로만 등재.
`[되돌리기 어려움]` — 스키마 변경 + 골든 재기준선.

**추천**: B안. 이유는 기술 장단점이 아니라 결과로: 되돌리기 가장 쉽고(스키마 무변경), U-5가
메모리에만 두는 지금 단계에선 어차피 아무것도 영구화되지 않아 위험이 없다. 다만 "R 판정이 지면
표시를 지운다"는 게 회계 실무 관점에서 맞는 동작인지는 감사 판단 문제라 확정은 요청드린다.
A/B/C 중 선택 부탁드린다.

## 6. 검토메모 입력

판단 버튼 옆에 `<textarea>`. 확정 시(A 또는 R 클릭) 입력값을 그 마크의 `comment` 필드에
메모리 상에서만 반영(빈 문자열이면 `null` 유지). `reviewed_at`/`reviewed_by`는 이번 단계에서
채우지 않는다 — 로그인/사용자 식별 체계가 없어 값을 채우면 거짓 정보가 된다. U-6에서 저장
체계를 설계할 때 같이 정할 것.

## 7. 판단 후 자동 이동

N키 로직(`sidebar.js`의 `pending`+`diff` 필터, page 오름차순, 순환)을 그대로 재사용 — 판단 시
해당 마크의 `status`가 바뀌므로 그 필터에서 자연히 빠진다. 판단 확정 직후 같은 필터를 다시
계산해 다음 항목으로 `selectMark(next, {switchToDiffTab: true})` 호출. **목록이 비면**(더 이상
미검토 차이 없음) 선택을 해제하고 상세 패널에 "미검토 차이 없음" 완료 상태를 표시한다(빈
화면이 아니라 명시적 완료 문구 — 침묵 없음 원칙과 같은 이유).

## 8. `operands` 하이라이트

`operands[].bbox`는 `[x0, top, w, h]` 형식(마크의 `bbox`와 동일 규약, CLAUDE.md 결정 12).
`hit.js`에 순수 변환 헬퍼 하나만 추가한다:
```js
export function bbox4ToRect([x0, top, w, h]) {
  return { x0, top, x1: x0 + w, bottom: top + h };
}
```
이후 `pdfRectToViewport(bbox4ToRect(op.bbox), curViewport)`로 링과 동일한 변환 경로를 태운다
(새 좌표식을 만들지 않는다 — U-4에서 지킨 원칙 유지). 상세 패널의 산식 표시를 클릭하면
`viewer.js`에 `emit("highlightOperands", mark.operands)` → `#markOverlay`에 성분별 사각형을
추가로 그린다(링과 별개 CSS 클래스, 선택 해제·페이지 이동 시 같이 지움).

## 9. 파일 변경 계획

| 파일 | 변경 |
|---|---|
| `ui/web/index.html` | `#detailPanel` 추가, `detail.js`/`detail.css` 로드 |
| `ui/web/detail.js` | 신규 — 상세 패널 렌더, 판단 버튼, 메모 입력, 자동 이동, operands 클릭 emit |
| `ui/web/detail.css` | 신규 — 패널 레이아웃, 문자 강조, 아코디언, 배지, 판단 버튼(채움/취소선) |
| `ui/web/hit.js` | `bbox4ToRect()` 순수 함수 추가만 |
| `ui/web/viewer.js` | `highlightOperands` 이벤트 구독 → 오버레이 추가 그리기. `__dsdDebug`에 필요 시 조회 함수 추가(테스트용, 상태 변경 함수는 여전히 미노출) |
| `ui/web/sidebar.js` | 무변경(선택 소유권 그대로), 필요 시 카운터 재계산 트리거 정도만 확인 |
| `marks.py`/`render.py`/`final.py`/`core.py` | **무수정** |

## 10. 게이트 계획

| # | 방법 |
|---|---|
| 1 | 18건 각각 선택 → 패널 필드가 marks.json 값과 문자열 일치 (CDP, 전수) |
| 2 | L2 10건 → 대사 대상 아코디언 기본 펼침 + counterparts 항목 수 일치 (CDP, 전수) |
| 3 | counterparts=[] 8건 → 아코디언 미생성 DOM 확인 (CDP, 전수, **실데이터**) |
| 4 | 판단 버튼 라벨: diff 14건은 "이상없음/차이아님", unverified 4건은 "확인함/해당없음" (CDP, 전수) |
| 5 | 판단 → 다음 미검토 diff 이동, 마지막 항목 판단 후 완료 상태 표시 (CDP, 시나리오) |
| 6 | 판단 직후 상단 카운터(`renderCounters`가 쓰는 live count) 즉시 갱신 (CDP) |
| 7 | operands 4건 → 클릭 시 성분 5개 bbox가 정확한 좌표에 그려지는가, 링과 같은 변환식 사용 확인 (CDP) |

시각 판단 체크리스트(자동 불가): 금액 두 줄 표시가 실제로 안 잘리는지, 문자 강조가 실제로
읽히는지, "주15" 칩 폭.

## 11. 게이트 보호

- `ui/` 아래만 수정(§9 표 그대로).
- 구현 후 `render_gate.py`·`glyph_gate.py`·`run_gates.py` 재실행 — 무변경 확인(이번 단계는
  판정/렌더 코드를 안 건드리므로 결과 불변이 나와야 정상, 실측으로 확인).
- 샘플 산출물(`samples/*_marks.json` 등)은 진단 후 즉시 삭제 완료(이 문서 작성 전 이미 정리).

---

**승인 요청 사항**: §5(판단 버튼 상태값 매핑 A/B/C, 추천 B) 하나뿐이다. 나머지는 스펙을 그대로
따른 구현 계획이라 별도 승인 없이 진행 가능하지만, 전체 설계안에 대한 승인도 함께 부탁드린다.
