## 한눈에 보기

### 1. 이번에 무엇을 했나?
합계·계정명·현금흐름 열·기간·연속표와 주주 표제 공백 인식을 보완했습니다. 후속 출력 검토에서 발견한 PDF 표시 누락도 수정했습니다.
### 2. 실제로 무엇이 달라졌나?
서로 다른 수익·비용 합계를 구분하고, 잔액과 재무현금흐름을 열별로 읽습니다. 3개월·누적 기간의 시작일과 종료일을 분리하며, 확인 가능한 연속표의 머리글을 이어 읽습니다. 끊겼던 연결 75건을 복구했습니다. 주주 비율 합계도 다시 검사합니다.
### 3. 확인 결과는 어땠나?
출력 보완 후 집중 검사 52개와 보호 대상 검사는 통과했습니다. 공식 공개 자료 비교는 네 건 모두 기존 기준과 달라 실패했습니다. 기준은 변경하지 않았습니다. 전체 통과나 업무 수용으로 판단하지 않습니다.
### 4. 아직 남은 문제는?
의미 확인이 필요한 12개 금액 칸은 검토 대상으로 남습니다. 기준 차이와 출력물을 확인했으며, 실제 화면·업무 자료와 전체 페이지 시각 검토는 남습니다. PDF의 주석 미성립은 예외 색인과 함께 확인해야 합니다.
### 5. 내가 결정해야 할 게 있나?
지금 추가 결정은 요청하지 않습니다. LG엔솔의 세 기간은 사용자 결정대로 미검증·검토 대상으로 유지했습니다. 구성 근거를 찾았던 두 항목과 의미가 다른 비교도 기존 검토 상태를 유지합니다. 자동 연결이나 기준 변경 승인을 요청하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. 독립 검토와 최종 공개 자료 비교를 마치고 Owner Review에서 멈춥니다. 병합·배포·기준 변경·요청 종결은 하지 않습니다.

## Developer Details

Latest output follow-up: [OUTPUT_REVIEW_OWNER_REVIEW.md](OUTPUT_REVIEW_OWNER_REVIEW.md). It records the PDF merge defect and fix,52focusedPASS, fresh official4FAIL with the same ten metric differences,433source-page/395overlay-page preservation and11rendered page checks. Below remains the source-context implementation history; its48-test and output-NOT-RUN entries describe the earlier checkpoint, not the latest output status. No baseline approval or automatic mapping expansion is inferred.

Date: 2026-10-08 Asia/Seoul. Source of truth: Issue #18 / DSD-002, implementation follow-ups #27/#29; preserve #28/#30. Existing draft PR #31. Product comparison: previous reviewed branch head2cea376 (implementation76a88c9) versus this follow-up. Historical main6373a classification is not changed by branch work.

### Changed behavior

- `core.py`: normalize whitespace in shareholder headings before deciding that ownership percentages share a denominator. `주 요 주 주` now has the same treatment as `주주`; independent subsidiary percentages remain review-only and percentages do not enter monetary B/C matching.
- `refmap.py`: preserve full labels for semantic identity; display labels remain short. Bind plain totals to source-owned row groups or a single explicit table title. A trailing subgroup total is not a grand total solely because it is last; an enclosing total requires already closed groups. Financial income/cost groups remain separate.
- Explicit financing-flow columns are movements even with borrowing account labels. Spaced opening/closing headers retain endpoint roles. Bounded financial-asset/liability accounts and receivables remain balances despite embedded 수익/상각/매출. Source-supported noncurrent provision residual after current-portion deduction remains a closing balance. Equity-method income totals use their explicit column identity.
- Maintain narrowly stated source identities for revenue, financial cost, discontinued loss and operating cash generation wording. Continuing-operation tax lines use the statement's explicit continuing-result closure followed by discontinued result, never amount-based inference. Same-item guard remains; net/gross or differently scoped financing amounts are not generically aliased.
- Bind fiscal dates separately by side and exact duration/instant; do not union prior annual closing into prior half-year flows. Quarter ordinal is not a three-month duration: printed calendar ranges are validated. Invalid dates, contradictory headers and ambiguous local span cannot be rescued from neighboring headers. Store raw date-caption page/line evidence.
- New subsection headings clear preceding narrative period ownership. New page/geometry boundaries clear stale titles. Adjacent-page continuation requires the same note section, open donor, declared unit, compatible column layout and no conflicting local scope; allow at most2PDF-point interior boundary rounding with unchanged outer boundaries. One-row donors can supply physical headers to the actual continuation's numeric columns; store donor page/table.
- Review candidates retain account/total identities, source title/header/donor/date evidence and coordinates. No company/page/value whitelist, threshold, formula, unit, sign or rounding relaxation. No unmatched-as-zero conversion and no normal link from numeric equality alone.

### Public source comparison

|자료|이전 연결|현재 연결|이전 미검증|현재 미검증|복구한 과거 누락|후보 추가/제거|
|---|---:|---:|---:|---:|---:|---:|
|삼성전자|30|46|77|61|16|17/0|
|휴맥스|52|67|30|15|15|29/0|
|LG에너지솔루션|43|75|72|40|32|37/0|
|조선내화|23|35|57|45|12|15/0|

Totals: C148→223, unmatched236→161 /384 referenced main amount cells. Restore75 of87 historically lost main cells;14 already-linked main cells gain extra valid candidates.89 main records change candidate sets:98 primary candidate pairs added,0 removed. These are sample-specific observed results, not a target count or financial certification. Full before/after coordinates, exact periods/roles and original table text/geometry for changed relations are in `reviews/issue18-20261008/source-context-delta.json`. Diagnostic uses identical cached extraction from the four SHA256-identified registered PDFs for the actual frozen and changed refmap.build; it does not replace the official runner or certify generated tickmarks/secondary links.

### Remaining review records

The prior87-cell classification remains historical evidence; no silent rewrite of82/2/3. Of82 correction candidates,75 regain automatic primary links after source-context correction. Five financing cells have corrected source roles/periods but unresolved same-item/net-gross scope. Two source-supported OCI relations retain their existing Owner review, including the still-unresolved parser role of the FVOCI category row. All seven remain unlinked review candidates under existing Owner decisions. This is not seven missing numeric matches or an approval request to weaken the guard.

- LGES three insufficient-evidence periods, Owner confirmed review on2026-10-06: PDFviewerp8 OCI FVOCI row vs p29 valuation/disposal FVOCI row, current3M−7,533; prior3M213; priorcumulative1,650millionwon. They remain unlinked with candidate positions/reasons. Currentcumulative−10,154 and defined-benefit cumulative1,030 also retain their earlier review status despite stronger composition evidence.
- Samsung treasury-share purchase flow versus prior closing stock balance:2cells remain automatically excluded and reviewable.
- Financing movement relations: Samsung current/prior short-term borrowing net movement (2cells), prior bonds/long-term borrowing repayment (1cell); LGES prior borrowing increase versus bond financing movement and prior borrowing repayment versus short-term financing movement (2cells). Cell role and dates are now read correctly, but net/gross/account scope is not automatically equated. Preserve review reasons and coordinates; no generic sign/value-derived alias.

### Verification and limits

- `python -B -m unittest discover -s DSD_footing -p 'test_*.py' -v`:48methodsPASS (30existing+18new). New positive/negative controls cover spaced shareholder totals and bad totals, income/cost group separation, subtotal/grandtotal, financing/endpoint roles, bounded receivables, exact dates/duration, invalid calendar dates, conflicting spans, new-subsection reset, side-by-side title reset, one-row continuation and incompatible grid, OCI non-equivalence, investment closing totals.
- Before implementation: initial7test methods reproduced3failures/4errors (two test fixtures initially lacked the two numeric rows required by unchanged extraction; corrected before final verification). Subsequent independent adversarial controls found and fixed period-rescue, last-subgroup, stale-title, quarter-duration, receivable-role, invalid-instant and invalid-header defects. Root delta review also fixed2otherwise-lost investment closing candidates. These intermediate failures are not final evidence.
- Initial Oct8 focused run had sandbox TEMP write errors; rerun with task-owned workspace TEMP resolved them. Do not treat missing execution as passing. Latest logs are local `source-context-tests.log` and protected check output.
- `python -B scripts/test_dsd_footing.py`: final frozen v2 run0/4PASS,4/4FAIL,0skips,exit1. Ten baseline metric deltas: Samsung C51→46/U56→61; Humax A_total567→572/A_SKIP48→53; LGES A_total395→397/A_OK379→381/C82→75/U33→40; Chosun A_total380→384/A_SKIP29→33. All other registered metrics unchanged. Humax shareholder ratio OK restored; extra excluded A1 records and valid small interest checks explain remaining A changes as in prior arithmetic ledger. No protected baseline update or overall Technical PASS. Evidence `reviews/issue18-20261008/verification.json`; local full log `source-context-final-v2-gates.log`.
- Product source/test SHA256 values in `source-context-final-v2-hashes.json` match post-run hashes exactly. No product edits during that final official run. Earlier development/mixed-version official runs are provisional and not final acceptance evidence.
- Protected artifacts/checker/domain rules/GATES/public PDFs unchanged. `python -B scripts/check_protected.py --base origin/main` PASS; `git diff --check` PASS. No `--update-gates` or `GATES_UPDATE`.
- Independent read-only reviewer `/root/issues27_30_review`: final48methodsPASS, exact source/test SHA256 match, seven concrete adversarial findings resolved, no remaining blocking finding in reviewed changed scope. Reviewer read complete delta metadata and representative source mechanisms; not accounting certification of every changed/unchanged relation. Final evidence `reviews/issue18-20261008/independent-review.txt`. Documentation caveat corrected: the FVOCI category parser role remains unresolved even though period/composition evidence improved.
- Shared repository suites, final rendered tickmark comparison, GUI/manual UAT, private compatibility and Linux NOT RUN. This is offline DSD engine scope; no AuditDesk/shared-module changes. Existing synthetic zero-output and unit controls still run in the48methods.

### Product SHA256

- `core.py`: `7a5fe2f4eb50231da584b5e236b4fcfddd4538afd9129ee40e8d0cb89bd012fc`
- `refmap.py`: `4bdd32a456c97989cc4bdd606a9c417ae322f661f309a850723c38d7531af210`
- `test_source_context.py`: `36b0d20eef17d4183b8675f25960d7a9b385c524923780d496ba03320d31d049`

### Owner boundary

User's 2026-10-06 decision to keep the three LGES periods unverified is recorded in `ISSUE18_PUBLIC_ROW_REVIEW.md` and Issue18. Current user authorized source-context fixes and resumption; existing implementation/test/independent-review authorization persists. No overall business acceptance, protected baseline approval, merge/deploy permission or Issue closure is inferred. Stop at Owner Review with remaining review records visible.
