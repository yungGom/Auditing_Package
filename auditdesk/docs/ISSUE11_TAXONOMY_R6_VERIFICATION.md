## 한눈에 보기

### 1. 이번에 무엇을 했나?

승인하신 추가 오류를 같은 해석기에서 수정했습니다. 공식 당기 자료의 출처 정보가 표시 이름에 섞이지 않도록 구분하고, 원문과 위치가 남는지 실제 원본과 전수 대조했습니다.

### 2. 실제로 무엇이 달라졌나?

표시 이름과 출처 정보를 각각 보관합니다. 출처 값은 공백까지 유지하며 원본 행·열과 항목 식별정보를 함께 남깁니다. 알 수 없는 열이나 잘못된 제목 행의 값도 버리지 않고 미확정 기록과 오류로 남깁니다. 기존 표시 역할 연결과 식별자 중복 처리는 유지합니다.

### 3. 확인 결과는 어땠나?

관련 자동검사 백열다섯 건이 통과했습니다. 공식 자료의 표시 이름 삼만구백구 개와 출처 정보 구천사백육십일곱 개가 원문·위치와 일치했고 독립 검토도 확인했습니다. 출처를 표시 이름으로 잘못 읽던 오류는 해결됐습니다. 공개·합성 자료 전체 자동검사와 최종 보호 검사도 통과했습니다. 다만 기존 엄격 검사의 한 건 실패·일흔여섯 건 건너뜀과 실제 자료 여든한 건의 자료 부족은 남아 있습니다. 실제 업무 수용 완료는 아닙니다.

### 4. 아직 남은 문제는?

검증할 보고서의 회사·기간·최초 제출인지 정정인지 정보와 당기 이름 공간의 공식 근거가 없습니다. 원본 자체의 중복 식별자와 식별 정보가 빈 행은 미확정입니다. 실제 보고서 사용 확인, 회사 확장 기준과 전체 차원 검증도 완료하지 않았습니다. 자료 읽기 수정의 통과를 전체 업무 적용 가능으로 확대하지 않습니다.

### 5. 내가 결정해야 할 게 있나?

이번 추가 수정은 이미 승인하신 범위에서 마쳤습니다. 추가 구현 승인 요청은 없습니다. 다음 실제 보고서 적용 확인에는 검증 대상 회사·기간·제출 유형을 정해야 합니다. 기본 제품 반영과 실제 업무 사용 여부는 별도 승인 사항으로 남깁니다.

### 6. 지금 상태는?

**사람 확인 필요.** 승인한 수정과 검증 결과를 남기고 사람 확인 단계에서 멈춥니다. 기본 제품에 병합하거나 업무 수용 완료로 표시하지 않습니다.

## Developer Details

Date:2026-10-08 KST. Source of Truth:[Issue #11](https://github.com/yungGom/Auditing_Package/issues/11). Related:#9,#12,source PR#13,draft PR#33.

### Authorization, baseline and reused work

Owner explicitly approved the R6 proposal with “제안대로 해주라”: same-parser resource/provenance distinction, raw values/locations, regressions and actual-source revalidation. Recorded in Issue before implementation. This resolves the previous additional-scope decision, not merge or business acceptance.

Dedicated branch/worktree `codex/issue11-taxonomy-audit`; previous commit `3b48893354b3262d9dad010afc23eae58425ed9c`. Exact remote main rechecked `6373a333414f51015f9d1068e32ec2ef7702cbe4`. Original dirty checkout and concurrent #12/#18 were untouched. Earlier dated reports/evidence remain unchanged as history, including the actual R6 failing result.

The exact ten approved PR#13 paths remain the reuse basis. Eight V2-1 dependencies and original Taxonomy test—nine files—remain unchanged. Existing Taxonomy ingestion/record/query behavior was reused; this follow-up changes only `taxonomy.py` in production, adds one source-field test module and updates only the own integrity test's parser-version assertion. No #9 recommendation/CLI, #12 DSD, protected baseline/test expectation, accounting rule, fixtures, gate/catalog/skip/timeout or legacy DB change.

### R6 root cause and correction

Official Label language blocks are D3:T3 (`ko`) and U3:AK3 (`en`). The previous parser carried `en` into AL `base schema`, so9,467source metadata cells became `TaxonomyLabel` resources. The existing exact-source field/count comparison did not prove correct classification; its failure and the independent semantic finding are preserved in the preceding real-material report.

`dart-workbook-preview/4` distinguishes four explicitly observed provenance headers: `base schema`, `systemid`, `prohibit`, `comment`. Encountering provenance stops resource-language carry. A later unknown column or new explicit language cannot silently reopen the resource group; its nonempty values are retained as UNRESOLVED with ERROR diagnostics. Duplicate provenance names preserve both physical columns and produce an ambiguity error. An explicit language on a provenance column is also an error. No new whitelist of valid Label roles, schema URI inference or accounting interpretation is introduced.

New frozen `TaxonomyLabelSourceField` records carry `field_id,qname,prefix,name,field_name,value,classification,source`. `source` retains snapshot/sheet/row/column. `classification` is PROVENANCE for supported source headers, UNRESOLVED for rejected/uncertain column values. Raw source-cell text is retained separately from existing normalized resource text, including leading/trailing/only whitespace. Missing QName/identity does not drop values or invent identity. Provenance does not become namespace authority.

`TaxonomySnapshot.label_source_fields` is an appended default-empty tuple; prior positional constructors remain compatible. Existing Label records and source-sheet locators remain available. Parser version advances `/3`→`/4`, changing snapshot/derived IDs so stored interpretation cannot silently reuse `/3` identity. No cross-version ID equality is promised. The source workbook bytes are unchanged.

Fresh OOXML tests cover all four populated source columns, unknown/blank headers after provenance, explicit new language after provenance, duplicate metadata, language-on-metadata, missing identity, malformed resource/identity header, provenance-only rows, blank values, deterministic IDs, immutability and exact whitespace preservation. No fixture binary/accounting truth was added.

### Actual official-source comparison

Same verified official release132/attachment5,2026-06-30:13,353,457bytes,SHA-256 `d7135781ed425bb2e43a7dafffc3189435bbd16a70fae3d98c258ea8dc9845e7`. [Official download board](https://filer.fss.or.kr/raaf001/search.do). Existing local copy differs and was not overwritten. Release/notice443 general2026half-year applicability and correction exception remain as documented in the previous source-chain report; no target-report dates were invented and no2024namespaces reused.

| Check | Fresh actual result / limit |
| --- | --- |
| Label language/role/text/location |30,909resources,ko12,374+en18,535; exact match to explicit source language blocks, no missing/extra/mismatched tuple. |
| Source lexical identity/header/raw value/classification/location |9,467PROVENANCE fields; exact match, no missing/extra/mismatch. Unique fieldIDs/physical cells, same snapshot/sheet locators; no invented QName. Actual populated fields are all AL `base schema`; AM/AN/AO are empty in this source, their populated behavior is synthetic-tested rather than claimed actual-tested. |
| Prior semantic reproducer, unchanged code |PreviouslyFAIL; nowPASS, no provenance-role Labels. This narrow check is backed by separate exact provenance preservation comparisons, not just removal of false Labels. |
| Existing selected fields |9,451Concepts,2,004Roles,68,898Occurrences,6,267References retained; independent selected-field comparisons have zero mismatches. R5 display Role connection remains correct. Full path/effective-network/DRS correctness is not certified. |
| Parent current declaration |`current_applicable=False`,PARTIAL,dimensionsunknown. Metadata deliberately leaves reporting dates/namespaces empty because target context/bindings not supplied. |
| Diagnostics |232,441parent diagnostics, same codes/counts as previous actual run:invalidapplicabilitydate1,unresolvednamespace162,316,unknownabstract1,829,duplicateID2,duplicateConcept1,ambiguousparent68,249,unresolvedConcept27,missingidentity16. Namespace/parent cascades are not that many independently established source defects. |

The independent probe uses UNVERIFIED_TAXONOMY/empty applicability evidence, giving two extra metadata diagnostics (232,443total); source bytes match but metadata/logicalURI/snapshotID legitimately differ. Source duplicate Concept/ID pair rows3849/9210 is preserved with both differing records. Sixteen identity-missing Label rows and1,829unknown abstract flags remain; no arbitrary repair/deduplication. Actual report UAT, optional extension and full DTS/DRS are NOT RUN/unsupported; current applicability/business acceptance remains unverified.

### Fresh executed checks

Runtime:Python3.14.0,pytest9.1.0,openpyxl3.1.5;`PYTHONUTF8=1`,scoped `PYTHONPATH=<checkout>/auditdesk`,task-owned TEMP/TMP. Commands run from the dedicated checkout. Structured safe results and raw-evidence digests:[evidence](ISSUE11_TAXONOMY_R6_EVIDENCE.json). Evidence names `evidence/` are relative to the task's `real-material/r6`; names `reviewer/r6/` are relative to `real-material`. No raw source values/private paths/author metadata/credentials published.

| Command/scope | Measured result |
| --- | --- |
| Initial new14cases on unchanged `/3`: `python -B -m pytest --noconftest -p no:cacheprovider --basetemp=<task> auditdesk/tests/test_xbrl_v2_taxonomy_label_provenance.py -q -rfEs --junitxml=<report>` |14FAIL/0PASS/ERROR/SKIP,5.39s,exit1. These include missing new projection/version behavior, not14separate defects. |
| Intermediate whitespace/header edges, before exact raw-value correction |2FAIL/1PASS/14deselected,2.16s,exit1. Intermediate `/4`, not original-source baseline; after correction all17newcases pass. Earlier intermediate112PASS22.76s is superseded by final run. |
| Final samepytest options:originalTaxonomy+integrity+officiallayout+labelprovenance+core+offline |115PASS+38subtestsPASS/0FAIL/ERROR/SKIP,22.57s,exit0. Includes original35+integrity14+layout8+new17+core/offline41. |
| Same published8acceptanceprobes |8PASS/exit0; overlapping coverage, not additive unique cases. |
| Same published actualLabel semantic probe |PASS/exit0,30.429s;30909Labels,0provenance-as-Label. Prior actualFAIL retained. |
| Parent explicit actualLabel/provenance source comparison |9checksPASS/exit0,29.232s; compares exact values and locators without exporting them. |
| Independent official comparison/newmodule/edges |Exact actual comparisonPASS48.814s;new17casesPASS3.06s;8independentedgesPASS0.508s. |
| `python -B scripts/test_auditdesk.py` |FAIL/exit1:229PASS/1FAIL/76SKIP/0ERROR,1warning,50.06s. Same `test_g2_smoke_direct`/missing known-generation material. TypeScript/buildPASS. |
| `python -B scripts/test_all.py --timeout 600 --report <report>` |TechnicalGatePASS/exit0,3/3components. AuditDesk225PASS/0FAIL/SKIP/NOT RUN,81compatibilitydeselected,component23.49s;webbuildPASS6.27s;DSDregisteredpublic4/4PASS,COMPLETED451.90s within unchanged600s. Compatibility81BLOCKED: REQUIRED MATERIAL UNAVAILABLE;businessPENDING. |
| `python -B scripts/check_protected.py --base origin/main`;`--staged`;`git diff --cached --check` |BothprotectedchecksandstagedwhitespacePASS/exit0. No protection/threshold change. |

The aggregate's Issue#23-approved public/synthetic result is separate from strict failures/skips and81existing compatibility cases. This standalone officialTaxonomy check does not reclassify missing catalog material. No DSD code/sample/timeout change or Issue#18 resolution is claimed; business acceptance remains PENDING.

### Independent review and Owner Review

Independent Reviewer re-executed the actual source comparison and new synthetic/edge cases, inspected frozen/default-constructor/version and source preservation boundaries. [Independent R6 review](ISSUE11_TAXONOMY_R6_REVIEW.md):R6RESOLVED within approved tested scope, no new blocking finding; earlierR1/R2/R5remain. No additional unmerged dependency was needed. The report preserves its original cutoff before aggregate completion; this verification report supplies subsequent completed results. [Final handoff review](ISSUE11_TAXONOMY_R6_HANDOFF_REVIEW.md):HANDOFF_READY; all21raw-evidence digests and3filehashes match, completed strict/aggregate/protected evidence inspected. This document verdict does not authorize report applicability, business acceptance or merge.

Owner Action:Verification Review of the bounded corrected behavior and evidence. No additional R6 implementation authorization needed. Before later actual-report applicability/UAT, select entity/report period/original-versus-correction and obtain authoritative current namespace evidence. No merge or business acceptance requested here. Keep Issue open and PR draft; stop at Owner Review, no main merge/release/business-complete status.
