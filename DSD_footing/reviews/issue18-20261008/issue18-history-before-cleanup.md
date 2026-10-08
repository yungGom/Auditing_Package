## 한눈에 보기 — 2026-10-08 원문·출력 보완 결과

### 1. 이번에 무엇을 했나?
합계·계정명·현금흐름 열·기간·연속표와 주주 표제 공백 인식을 보완했습니다. 후속 출력 검토에서 발견한 PDF 표시 누락도 수정하고 독립 검토했습니다. Windows 실행 중 분석 오류가 성공으로 전달되던 문제도 수정했습니다.
### 2. 실제로 무엇이 달라졌나?
끊겼던 연결 75건을 복구했습니다. 서로 다른 합계와 잔액·거래액을 구분하고 주주 비율 합계를 다시 검사합니다. 기본 코드에는 아직 병합하지 않았습니다.
### 3. 확인 결과는 어땠나?
집중 검사 55개와 보호 대상 검사는 통과했습니다. Windows 실행의 실패 전달과 추가 오류 여섯 상황도 독립 검토했습니다. 공식 공개 자료 비교는 네 건 모두 기존 기준과 달라 실패했습니다. 기준값은 변경하지 않았습니다.
### 4. 아직 남은 문제는?
의미 확인이 필요한 12개 금액 칸은 검토 대상으로 유지합니다. FVOCI 주석 행의 역할도 아직 미확정입니다. 출력 기록과 주요 페이지를 확인했습니다. 명령 실행과 오류 전달을 확인했습니다. 별도 화면·업무 자료와 전체 페이지 시각 검토는 미실행입니다.
### 5. 내가 결정해야 할 게 있나?
추가 결정 요청은 없습니다. LG엔솔의 세 기간은 사용자 결정대로 미검증·검토 상태를 유지합니다. 의미가 다른 비교를 자동 연결하거나 기준을 바꾸지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. Owner Review에서 멈춥니다. 병합·배포·기준 변경·종결은 하지 않습니다.

## Developer Details — source-context implementation checkpoint

Published commit `e15e69ad62676604ac0fad3540a8c0e4bcfd86c4` to existing draft [PR #31](https://github.com/yungGom/Auditing_Package/pull/31). [Final report, source delta and verification](https://github.com/yungGom/Auditing_Package/blob/e15e69ad62676604ac0fad3540a8c0e4bcfd86c4/DSD_footing/SOURCE_CONTEXT_OWNER_REVIEW.md). User directly requested the listed source-context corrections and resumed on2026-10-08; existing #27–#30 implementation/test/independent-review authorization persists. Main6373a remains unchanged.

C148→223/U236→161;75/87 lost main cells recovered;89 main candidate sets change,98primary pairs added/0removed. Remaining12 =7previous correction candidates keptreview(5financing net/gross/accountscope,2source-supportedOCI including unresolvedFVOCIrole)+2automaticexclusions+3insufficientOCI. Historical82/2/3 classification is preserved, not blanket accounting acceptance.

Final frozen tests48PASS; official0/4PASS,4/4FAIL,0skips,exit1,10metric deltas. Final-run source/test hashes unchanged; public hashes4/4match; protected/intake/diffPASS. Independent scoped review48PASS,7findings resolved,blocking0; no certification of every relation. GUI/private/Linux/shared suitesNOT RUN. Latest selected output review follows below. No GATES/domain truth/formula/threshold changes or overallTechnicalPASS. #28/#30 behavior retained by existing focused tests.


Latest output follow-up: `356bc72067bf7fdd5633ed8cc6935649fcceaf2f`, existing draft PR #31. [Output/Owner Review report](https://github.com/yungGom/Auditing_Package/blob/356bc72067bf7fdd5633ed8cc6935649fcceaf2f/DSD_footing/OUTPUT_REVIEW_OWNER_REVIEW.md). Fixed PDF overlay loss when internal links clone destination pages before marking; writer-owned page + detached contents prevents loss and shared-stream leakage. Fresh52focusedPASS; fresh official0/4PASS,4FAIL,0skips,exit1; same10metric differences, frozen hashes unchanged. All433source pages preserved;395overlay pages checked;11affected pages rendered. Actual fresh official Humaxp167 also has restored16SKIPmarks+footer. Independent review: blocking0; XLSX384rows/12reviewcells preserved. No rule/baseline/mapping expansion. App UAT/private/Linux/shared suites/all-page visualNOT RUN. Stop Owner Review.


Latest Windows entrypoint follow-up: aeca6ac795f040d87034d9230dbc8ed41a43c7aa. [Evidence/report](https://github.com/yungGom/Auditing_Package/blob/aeca6ac795f040d87034d9230dbc8ed41a43c7aa/DSD_footing/ENTRYPOINT_OWNER_REVIEW.md). Tested main item7: engine2→batch0; candidate now returns2 in both pause modes. Focused55PASS, independent3PASS, combined12-scenario CLI/batch coverage. Prior official4FAIL/same10deltas; no overallTechnicalPASS. Main/accounting decisions unchanged; Owner Review. Evidence-only continuation: corrupt-PDF exit1, missing-Python9009 in both pause modes and usage2:6/6expected, independently repeated. No product change or new official run.

---

## 한눈에 보기 — 2026-10-06 원문별 최종 분류

### 1. 이번에 무엇을 했나?
공개 자료 네 건에서 달라진 연결과 산술검사를 원문과 대조하고 독립 검토했습니다.
### 2. 실제로 무엇이 달라졌나?
끊긴 연결 87건을 추가 수정 필요 82건, 적절한 자동연결 제외 2건, 근거 부족 3건으로 분류했습니다. 제외 항목의 검토 기록은 유지합니다. 이번에는 제품을 변경하지 않았습니다.
### 3. 확인 결과는 어땠나?
원문·집계·목록의 일관성과 독립 분류 검토를 마쳤습니다. 공식 공개 자료 비교는 재실행해 네 건 모두 실패했습니다. 기존 기준은 변경하지 않았습니다.
### 4. 아직 남은 문제는?
합계·계정명·현금흐름 열·기간·연속표 해석과 주주 표제 공백 인식의 보완이 필요합니다. 이 항목들은 아직 수정 전입니다.
### 5. 내가 결정해야 할 게 있나?
사용자가 LG에너지솔루션의 남은 세 기간을 미검증·검토 대상으로 유지하기로 결정했습니다. 해당 선택은 완료됐으며 자동 연결하지 않습니다. 퇴직급여 누적과 당반기 누적 금융자산 손익은 추가 원문에서 구성 근거를 확보했지만 기존 결정대로 검토 상태를 유지합니다. 단순 금액 일치로 자동 승인하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. 원문 분류를 마치고 Owner Review에서 멈춥니다. 병합·배포·기준 변경·종결은 하지 않습니다.

## Developer Details — latest source-row audit

### Owner Decision — 2026-10-06 LGES three periods

Human Owner confirmed in this chat: “미검증·검토 대상 상태를 유지하면 됩니다. >> 이렇게 가는게 낫겠다”. Following the page/row explanation, retain LGES current-half3M2025-04-01–2025-06-30 −7,533millionwon, prior-half3M2024-04-01–2024-06-30 213millionwon and prior-halfcumulative2024-01-01–2024-06-30 1,650millionwon as insufficient-evidence, unverified review candidates. PDF viewerp8/p29 (printedPage7/Page28): OCI FVOCI row versus note5 valuation/disposal FVOCI row. Preserve source coordinates and reason; no verified status or normal automatic linkage from equal amount. This is a direct chat decision transcription, not certification of equivalence, acceptance of remaining fixes, baseline change, merge/deploy permission or Issue closure. Owner Review remains the stopping point. Product unchanged; prior public gate4/4FAIL remains.

Documentation-only commits `237fa12`, `2cea376`, published to existing draft [PR #31](https://github.com/yungGom/Auditing_Package/pull/31). [Complete report and source ledgers](https://github.com/yungGom/Auditing_Package/blob/2cea376/DSD_footing/ISSUE18_PUBLIC_ROW_REVIEW.md). Frozen product comparison main6373a vs76a88c9; product SHA256 unchanged. This checkpoint supersedes blanket public-impact uncertainty in earlier reports; it does not establish product completion or change the historical #18 main classification.

C235→148/U149→236 reproduced. All87 dropped main cells classified82 correction/2 automatic exclusion/3 insufficient;47 retained main records lose65 candidate pairs (45 correction/20 exclusion). All160 removed primary pairs classified135/22/3;22 arithmetic payload changes separately listed. Initial80/2/5 draft revised after independent verification of LGESp28/p32/p44–46; missing extraction never zero-filled. Source-supported two semantic relations remain review candidates, not a generic mapping approval.

Fresh `scripts/test_dsd_footing.py`:0/4PASS,4/4FAIL, exit1,15 unchanged metric deltas, no skips/update flags. Protected/source identity/ledger checksPASS; staged whitespace warning corrected before final diff checkPASS. Independent review covers count/coordinate consistency and representative source mechanisms, plus new bridge evidence; not accounting certification of every cell.18 source pages visually checked; product GUI/render UAT, private compatibility and LinuxNOT RUN. #27 ratio normalization and #29 source-context correction work remain outstanding. #28/#30 product code unchanged. No overall Technical PASS or baseline/merge recommendation.

---

## 한눈에 보기 — 2026-10-04 후속 수정 결과

### 1. 이번에 무엇을 했나?
기간 해석과 빠진 비율 합계 검사를 보완하고, 의미가 다른 비교를 검토 대상으로 유지했습니다.
### 2. 실제로 무엇이 달라졌나?
표의 위치와 기간 근거를 확인하고 잔액과 거래액을 구분합니다. 확인이 필요한 연결은 예외 색인에 후보 위치와 함께 남깁니다.
### 3. 확인 결과는 어땠나?
합성 검사 30개와 보호 대상 검사는 통과했습니다. 독립 검토의 여덟 수정 의견을 해소했습니다. 공개 자료 네 건은 모두 기존 기준과 달라 비교 검사에 실패했습니다.
### 4. 아직 남은 문제는?
자동 연결 감소의 업무 영향과 행별 적정성을 확인해야 합니다. 날짜 근거의 출처 표시에 제한이 있으며 화면·실제 업무 자료 검사는 미실행입니다.
### 5. 내가 결정해야 할 게 있나?
있음. 남은 비교와 공개 자료 변동을 업무 관점에서 검토해야 합니다. 근거 없는 비교는 미검증으로 유지합니다. 기존 기준 변경이나 병합 승인을 권고하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. Owner Review에서 멈춥니다. 병합·배포·종결하지 않습니다.

## Developer Details — latest checkpoint

Commit `76a88c9` published to existing draft [PR #31](https://github.com/yungGom/Auditing_Package/pull/31). [Full final report](https://github.com/yungGom/Auditing_Package/blob/76a88c9/DSD_footing/FOLLOWUP_OWNER_REVIEW.md) contains exact metric deltas, independent reviewed hashes, scope and limitations. This checkpoint supersedes earlier statements that follow-up product work has not started; historical evidence below is preserved.

Checks: focused30 PASS; protected/intake/diff PASS; official registered comparison0/4 PASS,4/4 FAIL, exit1, no skips or baseline updates. C linked235→148, unmatched149→236 /384; 15 registered metric deltas. Per-row business adjudication remains outstanding; no overall Technical PASS. Independent final code review: all eight concrete blockers resolved. Date-anchor coordinates/raw-text traceability limited. GUI/render UAT, private compatibility and Linux NOT RUN. #18 main classification unchanged; branch work does not establish main completion. #28/#30 original regressions rechecked.

---

## 한눈에 보기 — 의미가 다른 비교에 대한 업무 결정

### 1. 이번에 무엇을 했나?
사용자가 거래액과 잔액처럼 의미가 다른 비교를 검토 대상으로 남기도록 결정했습니다.
### 2. 실제로 무엇이 달라졌나?
해당 비교는 자동 정상 연결로 확정하지 않고, 확인이 필요한 항목으로 유지합니다. 금액과 기간이 같다는 이유만으로 연결하지 않습니다.
### 3. 확인 결과는 어땠나?
업무 방향이 정해졌습니다. 이번에는 결정 기록만 반영했으며 제품 수정·검사는 수행하지 않았습니다. 기존 공개 자료 비교 실패는 그대로입니다.
### 4. 아직 남은 문제는?
결정에 맞춘 표시·연결 제어를 구현하고 검증해야 합니다. 기간 오인과 기존 검사 누락 보완도 남아 있습니다.
### 5. 내가 결정해야 할 게 있나?
이번 선택은 완료됐습니다. 향후 특정 비교를 정상 연결하려면 그 관계의 근거와 별도 업무 판단이 필요합니다.
### 6. 지금 상태는?
사람 확인 필요. Owner Review 상태를 유지합니다. 병합·배포·기준 변경은 하지 않았습니다.

## Developer Details — Owner Decision, 2026-10-02

Human Owner's exact current-chat instruction: “검토 대상으로 남겨줘”. This selects manual review for semantically different comparisons, as discussed for transaction/movement versus closing balance. This is a transcription of the direct user decision, not an AI-authored Owner approval or approval of every proposed fix.

Binding follow-up criterion: semantic uncertainty remains an explicit review candidate, C unmatched/unverified with a reason and source coordinates. Do not silently drop it, convert it to zero, label it a proven financial error, or create normal circle/tag/secondary links solely from equal amount/period. Preserve existing output status distinctions; no new status enum or accounting formula approved. Specific future acceptance requires relationship evidence and a separate Owner decision; evidence existence alone does not auto-accept these reviewed items.

Examples retained for manual review: Samsung SCE treasury-share purchase movement versus note20 treasury-share closing balance; LGES OCI component versus note plan-asset return where semantic equivalence remains unconfirmed. This does not block an otherwise valid BS closing→note closing comparison with the same supported endpoint and matching meaning.

No current product implementation change or new tests; PR31 head447508a unchanged, main6373a333 unchanged. Existing #29 product blocker1 and official last gateFAIL0/4PASS4/4FAIL remain. Prior implementation authorization persists; this is not merge/deploy/baseline acceptance or Issue closure. Source of truth #18/DSD-002 and #29; prior reports' request to choose review versus linkage is superseded by this decision.

---

## 이전 방향·조사·검증·승인 기록 (보존)

## 한눈에 보기

### 1. 이번에 무엇을 했나?
기간 해석과 빠진 검사를 보완할 방법을 기존 업무 범위·원문·실패 사례와 대조했습니다. 수정 순서와 확인 조건을 구체화했습니다.
### 2. 실제로 무엇이 달라졌나?
비율 합계 검사를 복원하고, 기간을 원문 근거로 읽는 방향을 권고합니다. 금융상품 이름을 기간으로 읽지 않도록 먼저 막습니다. 이번에는 보완 방향을 검토했으며 제품 수정은 하지 않았습니다.
### 3. 확인 결과는 어땠나?
기간과 금액을 추측해서 맞추는 방식은 배제했습니다. 기존 비율 검사를 없애야 할 업무 근거는 찾지 못했습니다. 앞서 발견한 문제는 아직 남아 있고 공개 자료 비교도 실패 상태입니다.
### 4. 아직 남은 문제는?
제안한 보완을 구현하고 검사해야 합니다. 기간이 같아도 거래액과 잔액을 같은 의미로 비교할 수 있는지는 별도 확인이 필요합니다. 기준값에 맞추려고 연결을 복원하면 안 됩니다.
### 5. 내가 결정해야 할 게 있나?
있음. 거래액과 잔액처럼 의미가 다른 비교는 검토 대상으로 남길지, 근거를 갖춰 연결할지 업무 판단이 필요합니다. 근거가 없는 경우 미검증으로 남기는 방향을 권고합니다. 기존 검사 범위 축소와 현재 결과의 새 기준 채택은 권하지 않습니다. 기존 수정 착수 승인은 유지하며 반복 승인을 요청하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. 후속 방향 검토 결과를 Owner Review로 반환합니다. 병합·배포·기준 변경은 하지 않았습니다.

## Developer Details

### Contract and scope

Report type: root-cause / follow-up design review / Owner handoff, 2026-10-02.
Source of truth: Issue18 / DSD-002; refine existing #27 and #29, no duplicate Issues or fabricated Request IDs. User specifically requested finishing the follow-up direction review. Earlier implementation/test/independent-review authorization remains in force; this document does not invent a new implementation approval gate. Current turn scope is concrete direction review, not a claim proposed product changes are implemented or tested.
Main6373a333414f51015f9d1068e32ec2ef7702cbe4; draftPR31 head447508a5a7eb1f8b4028cf687dfd7167a080a914, unchanged. Source: PUBLIC_IMPACT_OWNER_REVIEW.md, public-impact-results.json, independent-impact-review.txt; nearest AGENTS, governance/POLICY, PROTECTED_ARTIFACTS, DSD_footing/CLAUDE and existing rules inspected.

### Recommendation and options

Recommended: restore existing numeric-sum coverage and repair source-bound period identity. This preserves the approved scope “표시 수치 상호 정합성” including A1 sums. Alternative currency-only narrowing would intentionally discard existing valid ratios and requires an explicit business scope decision; no justification found in existing scope. Reverting to amount-only C matching restores counts while recreating wrong-period verification, so rejected. Accepting all current16 aggregate deltas as replacement expectations before fixes is also rejected.

There is no target to restore all44 old links, C counts235, or every172 old candidate pairs. Some permissive original candidates cross periods or compare movement to balance. Success is verified valid cases plus safely rejected invalid cases, not a chosen aggregate count. Preserve the known #28 unit conversion and #30 zero-count behavior while refining #27/#29.

### #29 period evidence design

|Concern|Proposed behavior|Limit / observable acceptance|
|---|---|---|
|Financial category name mistaken for current|Parse bounded period expressions, not the substring 당기 in 당기손익; separate category header text from period-bearing evidence|Synthetic prior-note/current-main false link must disappear. Category-only header has no period evidence. Matching current title must produce a valid positive control|
|Period metadata model|Represent period kind (instant/movement), explicit side, fiscal/date range, span and evidence status/source separately; distinguish known, unknown, conflicting and not-applicable fields|Unknown fields are not wildcards; absolute mismatches and ambiguous side remain unmatched. A resolved instant cannot silently become a movement. Duration/span is not applicable to an instant and requires no invented duration|
|Merged headers before first retained amount|Traverse physical header cells/actual merged group scope before selecting amount columns; bind each amount to its enclosing period group|Humaxp82 current col4 group governs amountcol5/6, priorcol7 group governs8/9 even when ratio columns4/7 are excluded. No left-label or adjacent-group bleeding|
|Above-table periods|Associate an explicit subsection/table title by page, vertical geometry and structural scope, through intervening unit/narrative only when association is unambiguous|Chosunp33 current heading top175.69→t2top224, prior top520.69→t4top569. Do not assign a page-wide current/prior token to both; intervening subsection/reset prevents carry|
|Multiple tables under one subsection|Preserve subsection period scope while its structural boundaries remain valid; each table records its evidence association|Samsungp32/p33 assets/liabilities under one period heading. A newer heading replaces scope; mixed/unclear grouping remains unknown|
|Continuation across pages|Carry source-header period groups only after compatible grid, label layout, same statement/note section and no conflicting new period/unit evidence are established|Humaxp79→80 and159→160; Chosunp34→35,40→41,61→62. Same column count alone is insufficient. New section, new table group, conflicting header/unit or ambiguous continuation prevents propagation; never search by equal amount|
|Row-based SCE periods|Track explicitly dated row blocks and opening/closing role independently of numeric columns|Samsungp14 2024/2025 blocks must remain separate. Identify prior/current without making purchase flow and treasury-stock balance automatically equivalent|
|Rollforward cell roles|Resolve each row/cell role: 기초/기말 are endpoint balances; 취득/처분 are interval movements. Table-level 당기 중 변동 scopes the interval, not every cell's role|Samsungp48 BS closing→note기말 at the same supported endpoint stays valid. BS closing→취득 with equal amount is rejected. Missing/conflicting row role stays unverified. Do not automatically map 기초 to prior closing or date-offset an endpoint without supporting source relationship|
|Instant versus cumulative semantics|Treat date/instant and duration/span as different axes. Parse report-specific interval evidence where present; normalize notation only when explicit bounds and role support it|Half-year balance-sheet instant is not a half-year flow. LGES cumulative versus 당반기 needs traceable half-year start/end context; absent span is not automatically 누적|
|Conflicting evidence|Check row/column/table/subsection/continuation consistency rather than imposing a universal winning source|Chosunp44 prior subsection with repeated 당기말 caption remains a visible conflict until source meaning is established. Local specificity alone does not justify ignoring contradiction|
|Reference boundaries|Keep existing declared units, signs, MIN_WON and permitted rounding unchanged; preserve note-number range restrictions|Period logic never repairs units/signs by guessing, never converts unmatched to0, and cannot match outside referenced notes|
|Output explainability|Retain main/note source coordinates, raw period text, evidence owner and reason unknown/conflict/mismatch for C candidates|In existing exception index show why a main item remains unmatched. Rejected secondary-note links/near candidates remain period guarded; valid raw evidence can be inspected without developer terminology|

Minimal implementation boundary: use C-local period resolver in refmap.py, enriched with page/table/header/row context, and extend C unmatched evidence delivery in final.py where necessary. Keep shared statements.period_axis/pick_period and B period behavior unchanged unless independently reproduced B work warrants it; avoid broad regex changes that silently change other checks. Added evidence may use normal optional record fields without breaking marks/build consumers. This is a scoped extraction/mapping fix, not a rewrite of accounting formulas.

Explicit business acceptance gaps: LGESp8 OCI component vs p46 plan-asset return requires accounting meaning, not only half-year normalization; SamsungSCE purchase flow vs note20 closing stock needs relationship evidence. In their absence, keep unmatched and report the reason. Instant/movement identification is per amount cell, including all note rollforwards, not a blanket table classification; explicit endpoint balances remain eligible. The current C identity model also has incomplete absolute fiscal identity: “당” alone across unrelated dated scopes is not sufficient. Source-bound context must establish fiscal period before asserting equivalence.

### #27 numeric role and coverage design

Separate numeric roles at the consumers. A reference/sequence column is excluded because of explicit header role, not because values are small. An actual ratio is numeric and can participate in eligible A1 vertical sums; it is excluded from currency B/C comparison and from A2 when it would mix percentage and currency. Percentage-scenario headers such as10%상승시 hold monetary results and remain amount columns. Unknown roles do not automatically receive currency multipliers or monetary assurance.

Avoid simply deleting the percentage guard from shared grid_info: that could send35.68/100 values into monetary B/C matching, particularly with large won multipliers. Avoid using measured sum=100 to decide if a column is a ratio or to declare its components additive; that hides erroneous totals. Derive the role and sum structure from source headings/layout and existing eligible total-row structure first, then calculate using existing A1 and verdict. Do not introduce a company/page/account whitelist.

|Source / control|Required follow-up outcome|Boundary|
|---|---|---|
|Humaxp16t1 shareholder35.68+13.19+51.13|Restore A1 ratio sum100, OK and tick, preserve share-count sum|Existing valid coverage; classification before calculating, no “sum100” classifier|
|Chosunp51t2 composition99.9+0.1, current/prior|Restore both A1 sums100 and marks|No mixed currency+percentage horizontal additions|
|LGESp59/p60 interest totals34/20|Retain both newly added correct amount checks|Small values never alone imply notes/rates|
|Scenario10%상승/하락 and0.25%increase/decrease|Keep monetary scenario columns and original A1 sums|Actual standalone rates stay out of currency comparisons|
|Actual Note/주석/Ref/연번/번호|Continue explicit reference/sequence exclusion|Do not broadly include every numeric column|
|Ratio100 on a page declared 백만원, main amount100M|No B/C monetary match from the ratio even though100×1M meets MIN_WON|Role exclusion occurs before currency multiplier/threshold; includes direct and secondary-note matches|
|Rate table with non-additive/unknown rows|No verified A1 sum without established eligible additive-total structure; an existing candidate with unclear participation remains visible SKIP with reason|Do not create new financial yield aggregation rule or silently delete an ambiguous candidate|
|Ratio components total100, display103|DIFF using same existing verdict and runtime inputs, visible X|Error beyond existing1step; no new percentage rounding threshold authorized|
|Ratio smaller discrepancy|Apply existing protected verdict; record its current rounding behavior transparently|A new percent-specific tolerance is a separate exact-rule Owner decision, not hidden in this fix|
|Audit time/personnel p167/p75|Remain excluded/SKIP; preserve evidence|Do not remove9newSKIP or alter EXCL_TABLE just to improve counts. Report them separately as excluded candidates, not coverage gain|

Smallest safe boundary: core.py consumer role selection around grid_info/check_table, plus explicit monetary-only selection in refmap/tieout consumers if required. Existing arithmetic scope preserved, shared A3/A5 must not start summing percentage components merely because discovery changes. No existing global tolerance/EXCL_TABLE/verdict/A5_RULES/MIN_WON mutation. Candidate delivery can explain exclusions while retaining truthful legacy metrics; metric-definition changes are outside this recommendation. Main count increase can legitimately persist; it is not a blocker merely for adding honest SKIP.

### Execution order and acceptance matrix

1. Add failing synthetic reproductions for the reopened wrong-period link, lost merged/above/continued/row periods and removed ratio sums. Keep existing11method suite expectations. Record before results on PR head before fixes; these new tests are not yet written/run.
2. Repair the false period-success mechanism first, then source-bound mapping with conflict rejection. Positive and negative controls must cover each extraction route; no amount-based period inference.
3. Restore eligible ratio A1 coverage with consumer role separation. Retain small-amount/scenario checks and existing note exclusion, A2 percent-row exception and A3/A5 rules.
4. Expose unresolved period evidence in existing C exception delivery. Retain candidate-only, original source identity and unit/sign data. Confirm rejected matches do not receive circle/tag/near-difference/secondary-reference marks.
5. Execute all new/previous focused tests, intake_check, protected checker and official4sample project gate. Collect production-engine row evidence (instrument the actual loop without changing decisions) to remove earlier diagnostic carry discrepancy. Compare all44lost,38changed-retained,22Achanges and all newly changed records/candidates; counts alone are inadequate.
6. Independent review of fixes and same-version evidence, then Owner Review. If official metrics still differ after correct fixes, retain FAIL and supply exact new before/after per row/metric plus a separately scoped protected-baseline proposal. No required-test bypass or expectation rewrite.

|Case family|Must succeed|Must reject or visibly remain unverified|
|---|---|---|
|Period-category isolation|Valid current title/current amount and prior title/prior amount|Prior category header containing당기손익 linked to current; category-only unknown|
|Date/fiscal identity|Same explicit reporting interval/date identity|Different years/dates, current/prior swapped, instant/flow mismatch|
|Span|Same supported3M/cumulative/half-quarter interval|3M/cumulative mismatches, contradictory metadata, missing span guessed|
|Merged cells|Periods retained even when first physical group cell is nonmonetary|Propagation across next prior/current group or across label cell|
|Subsections|Separatecurrent/prior same-page tables and multi-table scoped group|Page-wide assignment, reset ignored, unrelated nearest text|
|Continuation|Supported same-section stable layout with retained evidence|Same-width unrelated table, new section/unit/period conflict, ambiguous carry|
|Row periods|Prior/currentSCE blocks individually identified|Allrows classifiedcurrent, movement=balance merely equalamount|
|Rollforward amount roles|BS closing→note기말 matching explicit supported endpoint, even under 당기 중 변동 title|BSclosing→취득 equalamount; blanket movement assignment; absent/conflicting rowrole; unsupported 기초/prior-end equivalence|
|Role isolation|Restored3ratio sums and retained2smallinterest sums/scenarios|Notes as sums, percent as won, currency+percentA2, automatic yield sum|
|Ratio multiplier trap|Ratio100 retains eligible A1 numeric sum behavior|Ratio100 on백만원 page falselymatching100M amount in B/C or secondary C linkage|
|Marks/output|Verified candidates marked, unknown visibly documented|Rejected wrongperiod candidate still circled/tagged/secondary linked|

These are proposed behavioral criteria, not invented passing test counts or newly approved accounting expectations. Actual comprehensive semantics remain Owner review where identified above. No blanket acceptance target for recovering every old link.

### Protected impact and verification status

Protected before/after: GATES/samples/golden/truth/CLAUDE/EXCL_TABLE/verdict/A5_RULES/MIN_WON unchanged. No protected mutation is necessary for this design review. Do not predeclare any new metric values; investigate after actual fixes. Existing approved percent-row A2 exception and1step policy preserved.
Applicable design review checks: read-only source/policy/ledger comparison performed. `python -B scripts/check_protected.py --base origin/main`: PASS; `git status --short`: clean isolated checkout. Bundled Windows Python runtime used. No product change in current turn; official gate last executed on same PR head remainsFAIL0/4PASS4/4FAILexit1. Full official rerun, new focused cases, GUI/UAT/render golden, Linux/private-material compatibility NOT RUN this turn; no Technical PASS or implementation completion claimed.
Independent design reviewer `/root/issues27_30_review`: no remaining blocking plan gaps. One initial blocking gap was resolved: table-wide movement classification could wrongly reject BS→note closing balances. Added per-cell rollforward roles with positive closing-endpoint/negative equal-amount purchase controls, missing/conflicting roles visibly unverified, and no unsupported opening/prior-end equivalence. Nonblocking suggestions were incorporated: not-applicable duration separated from unknown; ratio100 under백만원 versus100M monetary amount added to B/C pollution controls. Consumer isolation deemed feasible without protected formula/tolerance changes. This is design review only; no proposed fixes or tests executed. Reopened #29 product code blocker remains1 until implemented and verified. Prior report sanity PASS does not clear it.
No new branch publication, product code edit, protected expectation edit, main change, merge/deploy or Issue closure. Original dirty checkout and isolated clean PR checkout preserved. Direction review stops at Owner Review; proposed next fixes remain concrete work, not accomplished behavior.



---

## 이전 공개 자료 조사·구현·승인 기록 (보존)

## 한눈에 보기

### 1. 이번에 무엇을 했나?
공개 자료 네 건의 달라진 검사 결과를 기본 코드와 수정안에서 행별로 대조했습니다. 기간 표시가 표 밖이나 앞 페이지에 있는 경우도 확인했습니다.
### 2. 실제로 무엇이 달라졌나?
작은 이자비용 두 건이 새로 검사됩니다. 기존 비율 합계 세 건은 검사에서 빠졌습니다. 주석 연결이 줄어 수동 확인 대상이 늘어납니다. 제품은 이번 조사에서 변경하지 않았습니다.
### 3. 확인 결과는 어땠나?
집계 변동의 원인을 재현했습니다. 정상적으로 연결 가능한 자료도 기간을 읽지 못해 보류됩니다. 금융상품 분류 이름을 기간으로 잘못 읽는 문제도 합성 자료에서 재현됐습니다. 기존 비교 검사는 네 건 모두 실패 상태입니다.
### 4. 아직 남은 문제는?
기간 해석을 보완해야 합니다. 비율 합계 검사를 유지할지 업무 범위도 정해야 합니다. 수동 확인 시간과 모든 연결의 회계적 타당성은 측정하거나 확정하지 않았습니다.
### 5. 내가 결정해야 할 게 있나?
있음. 기간 해석과 기존 검사 누락을 보완하는 후속 방향을 검토해야 합니다. 현재 결과를 그대로 새 기준으로 받아들이는 것은 권하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. 조사 결과를 Owner Review로 반환합니다. 병합·배포·기존 기준 변경은 하지 않았습니다.

## Developer Details

### Scope and source identity
Issue #18 / DSD-002; related #27–#30, draft PR #31. Owner asked for additional public-result investigation/business-impact review on 2026-10-02. This is diagnostic evidence, no new product/protected edits. Baseline main6373a333414f51015f9d1068e32ec2ef7702cbe4 versus PR head447508a5a7eb1f8b4028cf687dfd7167a080a914. Frozen implementation report's historical publication rejection is superseded by published draftPR31; no merge.

`public_impact.py` imports baseline and final branch modules separately. Each registered PDF is extracted once and the same text/words/tables/unit declarations feed both versions. A replay uses final.py's checks, indentation positions, period applicability and tolerance0/roundstep1. Method limitation: replay clears carry on every no-table page; final.py can retain it when prose/paragraphs exist. It is not literally the production loop. All per-sample A verdict counters and C link/unmatched counts reproduce previously executed official results, so no observed count discrepancy, but aggregate equality alone cannot establish every row identity. Changed A table rows were independently inspected in source. This diagnostic is not an official gate replacement or a new PASS assertion. Detailed stable source coordinates and raw headers/rows/text are in `public-impact-results.json`; source coordinates below are 1-based PDF pages/table numbers, 0-based extracted row/column. Printed DART Page labels often differ from PDF page by1. Multi-period pages require table-heading geometry, not page-wide inference: reviewer directly verified Chosun p33 heading current top175.69→t2top224, prior top520.69→t4top569. B/public other metrics were unchanged in the final official run; B was not rerun in this diagnostic.

### Findings and business effect

1. **#27: real small-amount coverage improvement**. LGES p59t1r41c4 and p60t1r38c4 are related-party interest expense, totals34/20 (백만원), 38/35 participating rows respectively. Both sums are correct and now OK; previously the entire small numeric column was mistaken for notes. This is2 added OK, not a tolerance change.
2. **#27: existing valid percentage checks removed**. Humax p16t1r4c2 shareholder ratio35.68+13.19+51.13=100; Chosun p51t2r4c2/c4 composition99.9+0.1=100 for current/prior. Three OK disappear entirely, none change OK→SKIP. The new rate-header exclusion explains the loss but does not establish business acceptability. If footing includes ratio sums, this is a coverage regression; if currency-only is intended, that is an explicit scope decision, not automatic baseline acceptance. Monetary values in these tables remain checked.
3. **#27:9 added SKIP, no additional monetary assurance**. Humax p167t2 adds5 A1 SKIP and Chosun p75t2 adds4 A1 SKIP after small headcount/hour columns become numeric. Existing EXCL_TABLE excludes these tables unchanged. Their4 existing A2 SKIP records each have different calculations; still SKIP, not DIFF or new OK. Increase in total does not mean9 useful completed checks. These candidates can increase exception-index clutter and lower the OK ratio without identifying accounting errors.
4. **#29:44 lost linked main amount records**. Samsung19, Humax6, LGES3, Chosun16. Same44 become unmatched; no new linked records. Code reason classification:40 records have only candidate notes with periodNone,2 Samsung SCE records have main periodNone,1 LGES record compares explicit cumulative with unspecified span,1 Chosun prior-FVPL record mixes unknown periods and falsely-current tokens. These are main amount records, not44 distinct accounts/financial errors; current/prior, duplicate capital components and multiple note candidates count separately. Coverage loss is real; correctness of every original permissive candidate is not presumed.
5. **Known recoverable period information ignored**. Samsung p32/p33 financial-category tables have explicit '(1)당기말/(2)전기말' outside the grid; p48/p50/p79 separate '(1)당기/(2)전기' tables. Humax p145 headings explicitly separate current/prior, p82 current/prior merged cells start at a ratio column excluded from numeric columns; period fill begins too far right. p80/p160 continue headers from p79/p159. Chosun p33 has current/prior external headings, p35 continues the header from p34, p41 continues from p40, p62 continues from p61. Other p38/p43/p44 tables use external subsection periods. LGES p66 has prior-half-year table scope visible above the cash-flow column, while column-only merged fill does not assign it. These established examples are **unresolved coverage regressions**, not missing source evidence. Safe restoration must bind scope by geometry/continuation and reject conflicting evidence, not use amount/position guesses.
6. **Notation/meaning needs care**. LGES p8 cumulative current-half OCI versus p46 '당반기' asset-return row is same half-year context but one token includes '누적' and the other omits it; strict tuple inequality loses the link. Whether the specific OCI component is the intended accounting comparison still needs Owner validation. Samsung SCE p14 uses periods in row blocks, not columns; its two lost links are previous-year purchase amounts against note20 previous-year treasury-stock balance. Row period can be determined, but flow-vs-balance semantic acceptance must not be inferred from equal amounts. Chosun p44 prior subsection repeats a '당기말 순자산' column caption, so contextual precedence/conflict rules are necessary.
7. **Wrong-period success still possible (new blocker)**. Broad SIDE_CUR treats '당기손익-공정가치측정 금융자산' as a current-period marker. A note explicitly titled prior-period outside the grid can thus link to a current main amount. Independent reviewer reproduced this in a full synthetic PDF with equal200M amounts: one false current link and prior unmatched. Real Chosun p33 prior table has this misclassified column; a retained wrong current link on the actual four PDFs is NOT demonstrated because values differ. Synthetic reproduction still invalidates blanket period-safety acceptance. Amount equality cannot prove period identity.
8. **Aggregate counts conceal candidate/tick changes**. Another38 still-linked main amount records have changed candidate sets (Samsung10/Humax13/LGES5/Chosun10). Across dropped and changed retained records172 old main→note candidate pairs are removed (49/33/13/77). Pair count is not unique note-cell count. Some removals block real cross-period coincidences; others remove safe duplicate detail/total evidence. Full per-cell coordinates are retained in JSON. C_ok alone cannot validate note tags, secondary links or render equivalence; render/manual accounting UAT remain NOT RUN.

### Exact public metric impact

|Sample|A total|A OK|A SKIP|C linked|C unmatched|
|---|---:|---:|---:|---:|---:|
|Samsung|345→345|325→325|20→20|51→32|56→75|
|Humax|567→571|514→513|48→53|67→61|15→21|
|LGES|395→397|379→381|6→6|82→79|33→36|
|Chosun|380→382|347→345|29→33|35→19|45→61|

Net A total+8 =2 monetaryOK+9SKIP−3 ratioOK; net A_OK−1 and SKIP+9. A_DIFF/SIGN/ROUND unchanged. C coverage combined235→191 linked out of384 referenced main amounts (61.2%→49.7%), unmatched149→193. Company linked ratios47.7%→29.9%,81.7%→74.4%,71.3%→68.7%,43.8%→23.8%. These are tool coverage measures, not accounting error rates. The tool adds44 unmatched main amount records to the review queue; no time estimate, actual human workload increase or unique-task count measured.

### Per-item lost C link ledger

All44 losses individually located below. Technical cause is verified; accounting acceptability remains qualified by context and finding6. “Unresolved” means parser/coverage limitation is evidenced, not a financial misstatement. “Insufficient” is specifically semantic acceptance where equal amounts/period extraction cannot settle comparison meaning.

|ID|Sample|Main PDF p/t/r/c|Label / value|New period|Old candidate note p/t/r/c|Technical cause / status|
|---|---|---|---|---|---|---|
|C01|Samsung|10/1/3/2|1. 현금및현금성자산 / 12,581,632 (×1000000원)|['당', None, None, []]|32/1/1/1; 32/1/1/4|table/subsection period not propagated to amount column; unresolved|
|C02|Samsung|10/1/3/4|1. 현금및현금성자산 / 1,653,766 (×1000000원)|['전', None, None, []]|33/1/1/1; 33/1/1/4|table/subsection period not propagated to amount column; unresolved|
|C03|Samsung|10/1/4/2|2. 단기금융상품 / 12,332,721 (×1000000원)|['당', None, None, []]|32/1/2/1; 32/1/2/4|table/subsection period not propagated to amount column; unresolved|
|C04|Samsung|10/1/4/4|2. 단기금융상품 / 10,187,991 (×1000000원)|['전', None, None, []]|33/1/2/1; 33/1/2/4|table/subsection period not propagated to amount column; unresolved|
|C05|Samsung|10/1/13/2|3. 유형자산 / 155,360,355 (×1000000원)|['당', None, None, []]|48/1/9/6|table/subsection period not propagated to amount column; unresolved|
|C06|Samsung|10/1/13/4|3. 유형자산 / 151,446,870 (×1000000원)|['전', None, None, []]|48/1/1/6; 48/2/9/6|table/subsection period not propagated to amount column; unresolved|
|C07|Samsung|10/1/14/2|4. 무형자산 / 11,233,489 (×1000000원)|['당', None, None, []]|50/1/7/4|table/subsection period not propagated to amount column; unresolved|
|C08|Samsung|10/1/14/4|4. 무형자산 / 10,496,956 (×1000000원)|['전', None, None, []]|50/1/1/4; 50/2/7/4|table/subsection period not propagated to amount column; unresolved|
|C09|Samsung|10/1/21/2|1. 매입채무 / 14,247,155 (×1000000원)|['당', None, None, []]|32/2/1/1; 32/2/1/3|table/subsection period not propagated to amount column; unresolved|
|C10|Samsung|10/1/21/4|1. 매입채무 / 10,287,967 (×1000000원)|['전', None, None, []]|33/2/1/1; 33/2/1/3|table/subsection period not propagated to amount column; unresolved|
|C11|Samsung|10/1/28/2|8. 유동성장기부채 / 268,801 (×1000000원)|['당', None, None, []]|32/2/4/3|table/subsection period not propagated to amount column; unresolved|
|C12|Samsung|10/1/28/4|8. 유동성장기부채 / 22,264,226 (×1000000원)|['전', None, None, []]|33/2/4/3|table/subsection period not propagated to amount column; unresolved|
|C13|Samsung|10/1/32/2|1. 사채 / 7,134 (×1000000원)|['당', None, None, []]|32/2/5/1; 32/2/5/3|table/subsection period not propagated to amount column; unresolved|
|C14|Samsung|10/1/32/4|1. 사채 / 14,530 (×1000000원)|['전', None, None, []]|33/2/5/1; 33/2/5/3|table/subsection period not propagated to amount column; unresolved|
|C15|Samsung|14/1/8/5|2. 자기주식의 취득 / -1,811,775 (×1000000원)|None|67/1/3/2|SCE row period unread; semantic acceptance insufficient|
|C16|Samsung|14/1/8/6|2. 자기주식의 취득 / -1,811,775 (×1000000원)|None|67/1/3/2|SCE row period unread; semantic acceptance insufficient|
|C17|Samsung|15/1/22/2|1. 단기차입금의 순증가(감소) / 4,498,284 (×1000000원)|['당', None, None, []]|79/1/2/2|table/subsection period not propagated to amount column; unresolved|
|C18|Samsung|15/1/22/4|1. 단기차입금의 순증가(감소) / 5,316,919 (×1000000원)|['전', None, None, []]|79/2/2/2|table/subsection period not propagated to amount column; unresolved|
|C19|Samsung|15/1/24/4|3. 사채 및 장기차입금의 상환 / -217,305 (×1000000원)|['전', None, None, []]|79/2/3/2|table/subsection period not propagated to amount column; unresolved|
|C20|Humax|8/1/3/2|현금및현금성자산 / 24,744,232,371 (×1원)|['당', None, None, []]|145/1/1/2; 145/1/1/3|table/subsection period not propagated to amount column; unresolved|
|C21|Humax|8/1/3/4|현금및현금성자산 / 37,437,102,996 (×1원)|['전', None, None, []]|145/2/1/2; 145/2/1/3|table/subsection period not propagated to amount column; unresolved|
|C22|Humax|8/1/17/4|당기손익-공정가치측정금융자산 / 155,212,565,457 (×1원)|['전', None, None, []]|80/1/26/4|continuation has no local header; unresolved|
|C23|Humax|8/1/18/2|관계기업및공동기업투자 / 147,425,769,852 (×1원)|['당', None, None, []]|82/1/16/6; 83/1/14/7; 86/1/14/9|merged period starts at excluded ratio column; unresolved|
|C24|Humax|13/1/4/2|수익비용의 조정 / 91,103,872,621 (×1원)|['당', None, None, []]|160/1/16/1|continuation has no local header; unresolved|
|C25|Humax|13/1/4/4|수익비용의 조정 / 101,109,956,217 (×1원)|['전', None, None, []]|160/1/16/2|continuation has no local header; unresolved|
|C26|LGES|8/1/5/4|(1) 순확정급여부채의 재측정요소 / 1,030 (×1000000원)|['당', '누적', '반기', []]|46/1/5/1|cumulative/span notation mismatch; semantic acceptance insufficient|
|C27|LGES|10/1/26/4|(1) 차입금의 증가 / 1,595,376 (×1000000원)|['전', None, '반기', []]|66/2/4/2|table/subsection period not propagated to amount column; unresolved|
|C28|LGES|10/1/28/4|(1) 차입금의 상환 / -15,704 (×1000000원)|['전', None, '반기', []]|66/2/2/2|table/subsection period not propagated to amount column; unresolved|
|C29|Chosun|8/1/3/2|현금및현금성자산 / 36,008,857 (×1000원)|['당', None, None, []]|33/2/1/1; 33/2/1/4; 35/1/2/1|table/subsection period not propagated to amount column; unresolved|
|C30|Chosun|8/1/3/3|현금및현금성자산 / 86,817,045 (×1000원)|['전', None, None, []]|33/4/1/1; 33/4/1/4; 35/1/2/3|table/subsection period not propagated to amount column; unresolved|
|C31|Chosun|8/1/11/2|유형자산 / 124,588,272 (×1000원)|['당', None, None, []]|38/3/7/9|table/subsection period not propagated to amount column; unresolved|
|C32|Chosun|8/1/12/2|무형자산 / 12,271,790 (×1000원)|['당', None, None, []]|41/1/3/5|continuation has no local header; unresolved|
|C33|Chosun|8/1/12/3|무형자산 / 12,543,519 (×1000원)|['전', None, None, []]|41/2/6/6|table/subsection period not propagated to amount column; unresolved|
|C34|Chosun|8/1/14/2|공동기업투자주식 / 540,108 (×1000원)|['당', None, None, []]|43/1/7/9; 44/3/5/4; 44/3/5/7|table/subsection period not propagated to amount column; unresolved|
|C35|Chosun|8/1/14/3|공동기업투자주식 / 565,854 (×1000원)|['전', None, None, []]|43/1/7/2; 43/2/7/9|table/subsection period not propagated to amount column; unresolved|
|C36|Chosun|8/1/15/3|비유동 당기손익-공정가치 측정 금융자산 / 45,413,861 (×1000원)|['전', None, None, []]|33/4/4/2; 33/4/4/4; 33/4/7/2; 35/1/6/3; 35/1/6/4; 35/3/1/3; 35/3/1/4; 36/1/2/2; 36/1/6/4|unknown + falsely-current FVPL token; unresolved|
|C37|Chosun|8/1/16/2|비유동 기타포괄손익-공정가치 측정 금융자산 / 31,909,539 (×1000원)|['당', None, None, []]|33/2/6/3; 33/2/6/4; 33/2/8/3; 35/1/7/1; 35/1/7/2; 35/2/3/4|table/subsection period not propagated to amount column; unresolved|
|C38|Chosun|8/1/16/3|비유동 기타포괄손익-공정가치 측정 금융자산 / 64,683,778 (×1000원)|['전', None, None, []]|33/4/5/3; 33/4/5/4; 33/4/7/3; 35/1/7/3; 35/1/7/4; 35/3/2/4|table/subsection period not propagated to amount column; unresolved|
|C39|Chosun|8/1/25/2|단기차입금 / 196,351,416 (×1000원)|['당', None, None, []]|33/3/2/1; 33/3/2/3; 35/1/11/1|table/subsection period not propagated to amount column; unresolved|
|C40|Chosun|8/1/25/3|단기차입금 / 258,612,700 (×1000원)|['전', None, None, []]|33/5/2/1; 33/5/2/3; 35/1/11/3|table/subsection period not propagated to amount column; unresolved|
|C41|Chosun|10/1/11/2|지분법손익 / 7,975,319 (×1000원)|['당', None, None, []]|43/1/8/5|table/subsection period not propagated to amount column; unresolved|
|C42|Chosun|10/1/11/3|지분법손익 / -11,454,205 (×1000원)|['전', None, None, []]|43/2/8/5|table/subsection period not propagated to amount column; unresolved|
|C43|Chosun|13/1/4/2|조정 / 36,474,976 (×1000원)|['당', None, None, []]|62/1/7/1|continuation has no local header; unresolved|
|C44|Chosun|13/1/4/3|조정 / 34,541,180 (×1000원)|['전', None, None, []]|62/1/7/2|continuation has no local header; unresolved|

### Per-item A evidence ledger

|Sample|p/t/r/c / kind|Before|After|Displayed/calculated after (or removed)|
|---|---|---|---|---|
|Humax|16/1/4/2 / A1|OK|absent|100.0 / 100.0|
|Humax|167/2/3/- / A2|SKIP|SKIP|39.0 / 66.0|
|Humax|167/2/4/- / A2|SKIP|SKIP|414.0 / 414.0|
|Humax|167/2/5/- / A2|SKIP|SKIP|1480.0 / 2989.0|
|Humax|167/2/6/11 / A1|absent|SKIP|76.0 / 79.0|
|Humax|167/2/6/2 / A1|absent|SKIP|80.0 / 88.0|
|Humax|167/2/6/3 / A1|absent|SKIP|50.0 / 53.0|
|Humax|167/2/6/4 / A1|absent|SKIP|87.0 / 88.0|
|Humax|167/2/6/5 / A1|absent|SKIP|86.0 / 87.0|
|Humax|167/2/6/- / A2|SKIP|SKIP|1894.0 / 3403.0|
|LGES|59/1/41/4 / A1|absent|OK|34.0 / 34.0|
|LGES|60/1/38/4 / A1|absent|OK|20.0 / 20.0|
|Chosun|51/2/4/2 / A1|OK|absent|100.0 / 100.0|
|Chosun|51/2/4/4 / A1|OK|absent|100.0 / 100.0|
|Chosun|75/2/3/- / A2|SKIP|SKIP|42.0 / 75.0|
|Chosun|75/2/4/- / A2|SKIP|SKIP|625.0 / 984.0|
|Chosun|75/2/5/- / A2|SKIP|SKIP|1886.0 / 3744.0|
|Chosun|75/2/6/2 / A1|absent|SKIP|73.0 / 81.0|
|Chosun|75/2/6/3 / A1|absent|SKIP|48.0 / 50.0|
|Chosun|75/2/6/4 / A1|absent|SKIP|78.0 / 79.0|
|Chosun|75/2/6/5 / A1|absent|SKIP|89.0 / 90.0|
|Chosun|75/2/6/- / A2|SKIP|SKIP|2511.0 / 4728.0|

### Input identity

|Registered public file|Pages|SHA256|
|---|---:|---|
|삼성전자_감사보고서.pdf|120|b9207f0f02e251658f523d2e26f84d7bf6b2e5e0187e5cb95aa73e552c884203|
|[휴맥스홀딩스]연결감사보고서(2025.03.19).pdf|168|b27fc753cbc3bbe221a5b5cdfb1d82126fe8130804aed0379ea4c5f5aeace792|
|[LG에너지솔루션]반기검토보고서(2025.08.14).pdf|69|a2efb0fb669fa9601b9a2886f99b6837fce27b2545e89000bc90a941960e8975|
|[조선내화]연결감사보고서(2026.03.19).pdf|76|8c2b59e4830901ed9455ce6ebe35f2269cbe93937004418c2df2daba1c45a41d|

### Verification and Owner Review boundary

- Diagnostic `python -B review_outputs/issue18/public_impact.py`: complete4/4, no skipped samples; A and C counters agree with previous final official run. Additional text-only extraction appended predecessor headers. No baseline edit. Runtime pdfplumber0.11.9/Windows; same source bytes.
- `python -B scripts/check_protected.py --base origin/main` from isolated checkout: PASS in this investigation. `git status --short` clean; final PR head unchanged. Original dirty checkout preserved.
- Last applicable official gate remains FAIL,0/4PASS,4/4FAIL,exit1 (`gates27-30-v3.log`). No new full official run because no product changes; no relabeling as PASS. Prior focused11-method PASS remains historical evidence; it misses these newly found period and coverage cases.
- Full repository suite, GUI/manual UAT, render golden, private-material compatibility: NOT RUN here. No financial/material misstatement or Human Business Acceptance conclusion.
- Independent reviewer `/root/issues27_30_review` separately checked A source sums and C scope examples; reviewer synthetic wrong-period linkage reproduced. Reopened code acceptance blocker1 on #29 supersedes earlier code blockers0. Final evidence retained in `independent-impact-review.txt` (including geometry and precise synthetic setup/results). Reviewer independently recomputed22 A changes/44 drops/38 retained changes/172 removed pairs and combined C235→191/149→193; final report sanity review has no blocking report finding. No actual real-sample wrong retained link claimed. Source-based findings support Owner Review handoff, not acceptance.

Recommended next scoped work: (1) reject financial category names as period markers; (2) bind explicit table/subsection/continuation/row periods with source traceability and conflict rejection; (3) normalize half/cumulative only with supported report context, no arbitrary missing-token default; (4) decide ratio-sum scope and preserve valid checks accordingly, without approving current removals implicitly; (5) avoid representing extra excluded-hour/person candidates as coverage gains. Add failing cases for these mechanisms before product fixes, then rerun affected checks and all4 registered samples plus independent review. Any later protected expectations proposal needs exact approved before/after; current findings argue against accepting current16 metric deltas unchanged.

Owner Review: investigation complete; follow-up implementation NOT performed this turn. No baseline update, merge, deployment or Issue closure. #27/#29 remain unresolved acceptance candidates; #28/#30 have no observed new public count impact, not universal compatibility proof. Historical #18 main classification remains1solved/4unresolved/8insufficient; investigating PR deltas does not mark main defects solved.



---

## 이전 조사·수정·게시 기록 (보존)

## 한눈에 보기 — 2026-10-02 검토용 게시 완료

### 1. 이번에 무엇을 했나?
추가 게시 승인을 받고 준비된 변경을 검토용 초안으로 게시했습니다.
### 2. 실제로 무엇이 달라졌나?
네 문제의 수정과 검토 보고서를 저장소에서 함께 확인할 수 있습니다. 기본 코드는 변경하지 않았습니다.
### 3. 확인 결과는 어땠나?
게시된 내용은 검증했던 내용과 동일합니다. 합성 검사11개·보호 검사는 통과했고, 공개 자료 비교4건은 모두 실패한 상태입니다. 게시가 검사 통과를 의미하지 않습니다.
### 4. 아직 남은 문제는?
미검증 증가와 기존 정상 판정 변화의 추가 확인이 필요합니다. 업무 수용과 기존 기준 변경은 미승인입니다.
### 5. 내가 결정해야 할 게 있나?
있음. 공개 자료 변동의 추가 조사와 업무 영향을 검토해야 합니다. 게시 승인은 완료됐으며 병합·배포는 승인하지 않았습니다.
### 6. 지금 상태는?
사람 확인 필요. 초안으로 Owner Review에서 멈춥니다.

## Developer Details — publication checkpoint
Draft [PR #31](https://github.com/yungGom/Auditing_Package/pull/31), base main6373a333414f51015f9d1068e32ec2ef7702cbe4, head447508a5a7eb1f8b4028cf687dfd7167a080a914 on codex/dsd-issues27-30.2commits,6files, no new product edits. User explicitly answered “부탁해” to the question naming this branch/destination and draft-PR-only scope. Approved push succeeded; draftPR created and attached to the current chat.
Earlier automatic-review rejection/NOT DONE publication paragraphs below and in the frozen report are historical, superseded by this successful checkpoint. No workaround was used; explicit approval was received first.
Existing local evidence retained:11focusedPASS, protectedPASS, registeredDSD0/4PASS/4FAIL/exit1; no overallTechnicalPASS/businessacceptance. No new CI outcome claimed at creation. No baseline/checker/settings changes, no main push/merge/deploy/Issue closure. Owner Review remains pending; parent/children stay open. Dashboard/child Request-ID registration remains manual pending.


---

## 이전 검증·승인 기록 (보존)

## 한눈에 보기 — 2026-10-02 수정 검토 결과

### 1. 이번에 무엇을 했나?
승인받은 네 문제를 별도 작업 사본에서 수정하고 수정 전후 검사와 독립 검토를 진행했습니다.
### 2. 실제로 무엇이 달라졌나?
작은 금액도 검사하고, 본표의 단위를 맞춰 비교하며, 기간이 다른 주석 금액은 연결하지 않습니다. 산술검사 0건은 제한된 분석으로 안내합니다. 기본 코드에는 아직 반영하지 않았습니다.
### 3. 확인 결과는 어땠나?
합성 검사 11개와 보호 대상 검사는 통과했습니다. 등록 공개 자료 4건의 비교 검사는 모두 실패했습니다. 독립 검토의 코드 차단 의견은 해소됐지만 전체 검사 통과 상태는 아닙니다.
### 4. 아직 남은 문제는?
공개 자료에서 늘어난 미검증과 기존 정상 판정 변화의 원인·업무 영향은 추가 확인이 필요합니다. 상위 조사의 근거부족 8개 항목도 그대로 남습니다.
### 5. 내가 결정해야 할 게 있나?
있음. 실패한 공개 자료 비교의 후속 조사와 업무 영향을 검토해야 합니다. 검토 자료의 저장소 게시도 별도 승인이 필요합니다. 기존 기준 변경이나 병합·배포는 승인하지 않은 상태입니다.
### 6. 지금 상태는?
사람 확인 필요. Owner Review에서 멈췄습니다. 요청은 열린 상태로 유지합니다.

## Developer Details — current implementation checkpoint

Local branch codex/dsd-issues27-30, main baseline6373a333414f51015f9d1068e32ec2ef7702cbe4. Implementation8e1ea0edd368708f20f20104e8f4e1be9b5114b7; final local report HEAD447508a5a7eb1f8b4028cf687dfd7167a080a914. No current-main completion or business acceptance claimed. Parent DSD-002 unchanged; child unique IDs/Project registration remain manual pending.

- Before focused unittest8methods: failures10/errors1 (including subtests).
- Final python -B -m unittest discover -s DSD_footing -p test_issue27_30.py -v:11methodsPASS, exit0. Windows synthetic-only evidence.
- python -B scripts/check_protected.py --base origin/main:PASS. No GATES/golden/ERRORS/RENDER_GATES/threshold/formula/checker change.
- python -B scripts/test_dsd_footing.py:FAIL,exit1;0/4PASS,4/4FAIL,none skipped;16 registered metric deltas. Additional A coverage/SKIP/displacedOK and reduced C links require per-row review; accounting correctness of every changed public check/link NOT VERIFIED.
- intake_check.py PASS; git diff --check PASS after final report formatting correction. Full test_all.py, manual GUI/UAT/render golden/platform compatibility NOT RUN; no overallTechnicalPASS.
- Independent read-only reviewer /root/issues27_30_review: final11methodsPASS plus adversarial period/source/unit/rate-header cases; three blocking mechanisms resolved; code blockers0. Final report sanity check suitable for Owner Review with required gateFAIL, not merge readiness.
- Artifact: DSD_footing/ISSUES27_30_REVIEW.md in isolated local checkout, with full16metric before/after table. Logs retained locally outside tracked code. No product source posted through a workaround.
- Attempted git push to https://github.com/yungGom/Auditing_Package, branch codex/dsd-issues27-30, rejected by automatic approval review: authorization lacked explicit remote publication/destination. Remote branch publication/draftPR NOT DONE; no alternate code-publication workaround, no main push/merge/deploy/close. Explicit publication approval requested separately after local work completed.

Next action: Owner Review of changed public results and decision on follow-up investigation; optional explicit approval to publish the already prepared branch as a draft PR. Any protected baseline proposal requires a separate exact before/after decision and valid enforced integration procedure.


---

## 이전 조사·접수·승인 기록 (보존)

## 한눈에 보기

### 1. 지금 무슨 문제가 있나?
과거에 모아 검토한 PDF 검사·표시 문제들이 현재 코드에서 각각 해결됐는지 한곳에서 확인하기 어렵습니다. 일부는 작업 브랜치에 기록이 있지만, 기본 브랜치 반영과 검증 상태는 별개입니다.

### 2. 왜 업무상 문제인가?
이미 고친 문제를 다시 의뢰하거나, 남은 문제를 완료로 오해할 수 있습니다. 검토 결과가 실제로 사용자에게 전달됐는지도 확인해야 합니다.

### 3. 어떻게 해결하려고 하나?
현재 코드와 변경 이력, 열린 변경 제안을 항목별로 대조합니다. 확인된 미완료 항목은 각각 독립된 Issue로 분리하고, 해결 근거가 없는 항목은 완료로 표시하지 않습니다.

### 4. 내가 결정해야 할 게 있나?
분류와 후속 작업 범위를 검토해 주세요. 회계·보호 기준 변경은 이번 조사에서 요청하지 않습니다.

### 5. 성공했다고 볼 기준
- 아래 과거 항목마다 현재 코드·검사·병합 근거를 기록합니다.
- 해결·미해결·근거 부족을 구분합니다.
- 미해결 작업은 중복 없이 별도 Issue로 관리합니다.
- 이미 열린 PDF 출력 문제 Issue #8과 겹치는 부분은 새로 만들지 않습니다.

### 6. 지금 어디까지 됐나?
사람 확인 필요. 현재 main에서 13개 항목을 재검증했습니다. 해결 1개·미해결 4개·근거부족 8개이며, 미해결은 #27~#30으로 분리했습니다. Owner Review에서 멈췄습니다.

## Acceptance criteria

Reconcile these historical review items against current code and merged/open PRs; these are **investigation targets, not claims of open defects**:

- 판단 파일 불일치/덮어쓰기
- 원본 교체 뒤 과거 분석 마크 적용
- 표시 금액 열과 주석번호 오인
- 본표 간 단위 환산
- 당기/전기 교차매칭
- 검사 결과 전달 누락
- 실패 상태 전달
- 저장 실패 후 출력
- marks만 존재할 때 복구
- 분석 시각
- 산술검사 0건 예외
- 캐시 정책
- 렌더 골든 불일치

For each: code location, evidence branch/commit, test result, merged/default-branch presence, current status, next action. Do not change golden/GATES/ERRORS/RENDER_GATES or product logic merely to make this audit pass.

## Progress

- Backfill investigation from the Human Owner's legacy DSD_FOOTING list and repository history.
- `fix/dsd-footing-review-remediation` contains historic UI/render/marks/gate work, but branch code alone is not proof of default-branch completion.
- Current separate Issue #8 and draft PR #10 cover PDF export consistency (TC-020); do not duplicate that work here.
- Current triage: CLI analysis timestamp resolved (narrow scope); four main defects reproduced and assigned #27–#30; eight evidence gaps remain. Issue18 stays open for Owner Review.

## Verification Report

Per-item current verification completed within the available main scope; see the dated evidence matrix below. Protected check PASS; official DSD registered samples 4/4 PASS, 96 metrics unchanged. Four concrete defects reproduced despite baseline gate PASS. GUI/UAT and main render golden checks NOT RUN. Independent review PASS/blocking0. No repository-wide Technical PASS or business acceptance claimed.

## Developer Details

Request ID: **DSD-002** (immutable; assigned after Project-wide uniqueness check).
Master Dashboard: https://github.com/users/yungGom/projects/1


Project/component: DSD_FOOTING historical review backlog audit.
Related: #8, PR #10; repository branches `fix/dsd-footing-review-remediation`, `feat/auditdesk-xbrl-orchestration`.
Protected artifacts affected: none for this investigation.

Next action: Owner Review of evidence matrix and child Issues #27–#30. Evidence-gap items remain unconfirmed; #8/PR10 reused. Human decision required: review classification/follow-up scope. No merge/release/close.

## Required tests

Read-only code/PR/Issue evidence audit first. Run applicable DSD_FOOTING tests only for confirmed implementation follow-ups; none claimed in this inventory.

## Human decision required

Read-only triage complete. Owner Review of classifications and follow-up scope pending. Protected/accounting rule changes require separate approval.

## Definition of done

Each listed historic topic has an evidence-backed state and a separate Issue only where current work remains.

## 2026-10-02 Current-main verification and Owner Review

## 한눈에 보기

### 1. 이번에 무엇을 했나?
과거 풋팅 문제 13개를 현재 기본 코드와 과거 수정 기록으로 재검증했습니다.
### 2. 실제로 무엇이 달라졌나?
제품은 바꾸지 않았습니다. 재현되는 문제와 아직 확인할 수 없는 문제를 구분했습니다.
### 3. 확인 결과는 어땠나?
해결 1개, 미해결 4개, 근거부족 8개입니다. 합성 자료에서 금액 열 제외, 단위 비교, 기간 교차매칭, 산술검사 0건 오류를 재현했습니다. 공개 샘플 반복 검사는 별도 결과로 기록합니다.
### 4. 아직 남은 문제는?
화면·판단 저장·복구·캐시의 과거 보완은 기본 코드에 없습니다. 이것만으로 과거 결함이 지금 재현됐다고 단정하지 않았습니다. 출력 문제는 기존 요청에서 계속 관리합니다.
### 5. 내가 결정해야 할 게 있나?
있음. 분류와 후속 작업 범위를 검토해 주세요. 회계 기준이나 보호 기준을 바꾸는 결정은 요청하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. Owner Review에서 멈춥니다. 병합·배포·요청 종결은 하지 않습니다.

## Developer Details

Report type: verification / historical reconciliation / owner handoff
Source of truth: Issue #18, DSD-002. Checked 2026-10-02 Asia/Seoul.
Baseline: remote main confirmed through GitHub fetch_commit(main): `6373a333414f51015f9d1068e32ec2ef7702cbe4`, identical to origin/main. Local main `62762e5` and dirty `test/auditdesk-e2e-uat` are NOT the audit baseline.
Isolated tracked checkout: review_outputs/issue18/checkout, detached at exact main. Original dirty checkout preserved. Product/protected files unchanged. No client data; synthetic PDFs and registered public DART samples only.

Classification rule: 해결 requires current-main implementation plus observed applicable behavior; 미해결 requires a concrete current-main reproduction; 근거부족 means historic scenario/implementation/baseline or current behavioral evidence is missing. Missing newer UI is not itself proof that its former bug occurs in the older CLI.

| # | Historical topic | Current main location / evidence | Historical branch / commit and default presence | Current verification | State / next action |
|---|---|---|---|---|---|
|1|판단 파일 불일치/덮어쓰기|No ui/api.py or 판단.json flow in main|fix/dsd-footing-review-remediation committed HEAD 62762e5 includes UI; additional integrity edits/tests are uncommitted; not main|NOT RUN: main cannot execute those UI scenarios|근거부족. Preserve legacy changes; obtain scoped reviewed integration and mismatch/overwrite fixtures|
|2|원본 교체 뒤 과거 분석 마크 적용|main has no marks.py or source hash/marks recovery flow|Legacy ui/api.py/marks.py modifications uncommitted, not main|NOT RUN: no corresponding main API|근거부족. Verify hash mismatch/replaced-source behavior when integrating UI|
|3|표시 금액 열과 주석번호 오인|core.is_note_col/grid_info: comma-free values <100 excluded regardless of amount header|Original engine ad5a4d3 remains main; legacy core.py/test_numeric_matching.py fixes uncommitted|Synthetic 10+20 versus displayed 40 under 당기: numeric cols [], arithmetic checks 0 (expected col1, DIFF)|미해결. Separate amount-column issue; preserve explicit note/percentage/sequence exclusions|
|4|본표 간 단위 환산|tieout.collect/add/run retain raw amounts without units|Legacy tieout.py unit fix uncommitted; main original B pipeline|Synthetic B8 원1,000 versus 천원1,000 incorrectly OK twice; 원1,000,000 versus 천원1,000 incorrectly 차이 twice|미해결. Separate unit-comparison issue; unknown unit must remain unverified|
|5|당기/전기 교차매칭|refmap.collect_notes/build.match has no period comparison|Main dd72a6d/aec3b37 cover B period axis/guards; do not fix C matching. Legacy refmap.py period fix uncommitted|Synthetic swapped note columns: links2/unmatched0; correct columns also links2/unmatched0. B cumulative axis selection separately returns current1/prior3|미해결. Separate C period issue; retain existing B period guards|
|6|검사 결과 전달 누락|final.py writes B_본표간연계, F_일관성, C7_주석참조 etc.; no UI coverage panel|Legacy analysis_status.py/test_phase3_delivery.py untracked; not main|Code confirms XLSX delivery; full historic omission scenario NOT RUN|근거부족. Distinguish XLSX results from UI completion/coverage claims|
|7|실패 상태 전달|foot.py uses runpy; run.bat invokes python then pause without preserving exit status|Legacy resilience/entry-point tests untracked; not main|Zero-case CLI exit1 observed; Windows GUI and batch propagation NOT RUN|근거부족. Reproduce exact caller contract before declaring missing propagation defect|
|8|저장 실패 후 출력|No judgment/export_final flow in main|PR10 draft/open/merged=false; base feat/auditdesk-xbrl-orchestration, head fe36f2c; save failure fix reported there, not main|Historical PR reports22PASS; not rerun here and not main completion evidence|근거부족. Existing Issue8/PR10; do not create duplicate|
|9|marks만 존재할 때 복구|No marks.py/render.py/ui in main|Legacy recovery/cache edits and tests uncommitted; not main|NOT RUN: no recovery API|근거부족. Scoped recovery reproduction/integration required|
|10|분석 시각|final.RUN_TS and 요약/실행 일시|8abc7c3 implemented CLI version/time stamp and is ancestor of main|Synthetic zero-case XLSX contains execution time 2026-10-02 11:23 (local host observed). Report date uses Asia/Seoul. Stored minute precision; no claim about newer UI timestamps|해결 (CLI analysis execution timestamp only). UI-specific provenance remains outside this conclusion|
|11|산술검사 0건 예외|final.py console uses stat['OK']/tot without guard; XLSX guarded|Legacy final.py zero-case correction uncommitted; not main|Synthetic text PDF/no numeric table: exit1 ZeroDivisionError after PDF and XLSX already created; --quiet variant NOT RUN|미해결. Separate zero-count CLI issue; partial outputs must not imply success|
|12|캐시 정책|main CLI recomputes; no compatibility.py/cache reuse UI|Legacy compatibility.py and cache tests untracked; not main|NOT RUN: historic policy needs source/options/engine/render fingerprint scenarios|근거부족. Do not call absence of caching a cache defect; review policy and integration separately|
|13|렌더 골든 불일치|main draws inline in final.py; no render_gate.py/RENDER_GATES.json|PR10 historical runtime recheck reports5/5PASS with original golden, not main; legacy diagnostics untracked|NOT RUN: main has no registered render golden. Metric gates are not pixel/byte golden tests|근거부족. Obtain exact baseline/runtime comparison; no golden or renderer edits|

### Reproduction and evidence
`recheck.py` imports ONLY main core/tieout/refmap/statements. `legacy_numeric_fixture.py` is a read-only copy of the existing uncommitted public/synthetic fixture helper; its unittest assertions are not executed. No legacy product modules are loaded. `recheck-results.json` and `zero-cli.log` preserve actual observed results. These are audit reproductions, not newly approved accounting expectations or product regression-suite PASS.
Command: bundled Python `-B review_outputs/issue18/recheck.py`. Successful diagnostic execution; four current product defects observed. No product fix attempted.
Protected command: bundled Python `-B scripts/check_protected.py --base origin/main` in isolated checkout: PASS. Evidence `protected.log`.
Applicable official command: bundled Python `-B scripts/test_dsd_footing.py` in isolated checkout: PASS, 4/4 registered samples, 24 metrics each (96 total) unchanged; evidence `dsd-gates.log`. No GATES_UPDATE or --update-gates.
Full test_all.py: NOT RUN, unrelated product suites outside read-only DSD inventory. No repository-wide Technical PASS claimed.
Manual GUI/UAT: NOT RUN; main has no newer UI. No human business acceptance inferred.
Independent review: /root/issue18_review, read-only review PASS, blocking0. Nonblocking suggestion to retain matched-column detail; swapped/correct control and source inspection already support C-period classification.
PR10 historical evidence is explicitly historical, not this-run PASS. Protected inventory document's statement that ERRORS.json is absent matches main, although newer branches contain it.
No Issue8 duplication. Confirmed residual defects receive independent child Issues after deduplication; evidence gaps remain in Issue18 rather than invented defect tickets.
Master Dashboard status synchronization is manual per main workflow. Target Owner Review / Owner Action: review classification and child scope; never Done automatically.




### Confirmed remaining work — deduplicated children
- [#27 [DSD_FOOTING] 작은 표시 금액도 산술검사에서 빠지지 않도록 수정](https://github.com/yungGom/Auditing_Package/issues/27)
- [#28 [DSD_FOOTING] 본표마다 다른 금액 단위를 맞춰 비교](https://github.com/yungGom/Auditing_Package/issues/28)
- [#29 [DSD_FOOTING] 당기 금액을 전기 주석과 연결하지 않도록 수정](https://github.com/yungGom/Auditing_Package/issues/29)
- [#30 [DSD_FOOTING] 산술검사가 없는 보고서도 오류 없이 처리](https://github.com/yungGom/Auditing_Package/issues/30)

No product fix/PR/merge/release or Issue closure in this investigation. Parent Request ID DSD-002 preserved. Child Project registration and new unique Request IDs pending manual Dashboard operation; no unverified ID assigned.


## 2026-10-02 Owner Approval — 착수 범위

Human Owner가 현재 채팅에서 직접 승인했습니다:
> Issue #18의 분류와 #27~#30의 수정 착수를 승인해. Harness 절차에 따라 수정·검증·독립 검토까지 진행하고, Owner Review에서 멈춰. 병합·배포는 하지 마.

승인 범위: #18 조사 분류 수용 및 #27–#30 수정 착수·검증·독립 검토. 최종 업무 수용, 보호 기준 변경, 병합·배포·Issue 종결은 승인에 포함되지 않습니다. 이 기록은 채팅의 실제 지시를 전사한 것이며 별도 Owner 댓글로 위장하지 않습니다.
