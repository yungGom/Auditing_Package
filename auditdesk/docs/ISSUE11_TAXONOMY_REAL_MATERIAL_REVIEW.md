## 한눈에 보기

### 1. 이번에 무엇을 했나?
공식 배포파일의 표시 구역을 읽는 수정과 새 검사를 독립적으로 검토했습니다. 원문과 읽기 결과를 다시 전수 대조하고, 이름 자료의 열이 실제로 어떤 뜻인지 추가 확인했습니다.

### 2. 실제로 무엇이 달라졌나?
표시 구역의 역할을 놓치던 문제는 해결됐습니다. 다만 출처를 담은 열까지 영문 표시 이름으로 잘못 읽는 별도 문제가 발견됐습니다. 검토자는 제품이나 원본 자료를 변경하지 않았습니다.

### 3. 확인 결과는 어땠나?
표시 역할과 선택 속성은 원문과 모두 일치했고 새 합성 검사와 독립 추가 검사도 통과했습니다. 그러나 이름 자료의 의미 검사는 실패했습니다. 기존의 개수·필드 일치만으로 실제 이름 자료 해석까지 통과했다고 볼 수 없습니다. 전체 자동검사 결과는 담당자의 별도 최종 기록을 따라야 합니다.

### 4. 아직 남은 문제는?
출처 메타데이터를 표시 이름과 구별하면서 원문과 위치를 보존해야 합니다. 같은 식별자가 겹친 항목, 소속 항목이 빈 이름 자료, 공식 이름 공간 근거와 실제 보고서 적용 여부도 미확인 상태로 남습니다. 이런 항목을 임의로 합치거나 확정하면 안 됩니다.

### 5. 내가 결정해야 할 게 있나?
출처 열 오분류 문제를 별도 제한 범위로 고칠지 승인해야 합니다. 이는 회계 기준을 새로 판단하는 문제가 아니라 자료를 읽는 방식의 문제입니다. 다른 작업의 미병합 변경이나 보호 기준 변경은 필요하지 않습니다. 실제 보고서 적용 여부와 업무 수용은 별도로 확인해야 합니다.

### 6. 지금 상태는?
표시 역할 수정은 확인됐지만 실제 자료 해석 전체는 추가 문제 때문에 막혀 있습니다. 사람 확인이 필요하며 병합하거나 업무 수용 완료로 표시할 수 없습니다.

## Developer Details

### Scope and verdict

- Independent reviewer: `issue11_independent_review`; review date 2026-10-08.
- Checkout HEAD before uncommitted official-layout fix: `3f2ee38052206d06530aaccd5f055411a2cecdb4`; reviewed parser `dart-workbook-preview/3`, file SHA-256 `573d2f440469994d795c60557ee2cedfc1a8ea839b39df6ea09b82f69f0dfa3a`.
- Read-only implementation review plus independent actual-material probes. Reviewer writes are confined to reviewer evidence; no product/test/protected file or input workbook was changed by reviewer.
- **R5: RESOLVED for the observed official A/B and existing B/D Presentation metadata layouts.** Original R1/R2 status is unchanged; no new source-ID or missing-section-header regression was observed.
- **Actual official workbook compatibility: BLOCKING because of new R6.** Field equality is not a Label-resource semantics PASS. New R6 implementation is NOT RUN / not performed while additional Owner scope decision is pending.
- No accounting mapping, protection baseline change, business acceptance, main merge or release approval is implied.

### Source and applicability boundary

Official public workbook independently hashed after all reads: 13,353,457 bytes; SHA-256 `d7135781ed425bb2e43a7dafffc3189435bbd16a70fae3d98c258ea8dc9845e7`. It differs from the preexisting local copy (SHA-256 `4cc40e96de1f6a5bea48cedc494ee0b9b3181f7b42d939fa57efae2542cb0d34`). The two inputs are not interchangeable and no claim about who changed the local copy is made.

Previously read saved official FSS release/notice evidence identifies the final 2026-06-30 distribution and application beginning with 2026 half-year reports; corrections retain their existing format. The reviewer did not independently perform a second network download. The specific reporting type/period/correction status and authoritative namespace declarations remain **BLOCKED: NOT VERIFIED**. No current QName authority is inferred from prefixes or a prior release. Direct probes deliberately use `UNVERIFIED_TAXONOMY`, empty applicability fields and no namespace bindings; `current_applicable=False`, `PARTIAL`, dimensions unknown.

### R5 resolution and bounded diff review

`auditdesk/auditdesk/xbrl_v2/taxonomy.py:240-277` recognizes explicit A/B or B/D LinkRole/Definition pairs and rejects additional populated metadata cells rather than choosing a role. Parser version increases to `/3`; the integrity test version assertion is the only change in that existing added test module. The eight new synthetic cases cover official and mixed layouts, headerless sections and extra populated metadata cells. Original nine reuse files excluding taxonomy remain unchanged against their approved source; no other Issue implementation is introduced.

Official raw OOXML contains 476 Presentation section/header pairs and 68,898 occurrence records. The previous `/2` direct role/attribute comparison failed for every occurrence. With `/3`, all 68,898 Role URI/preferredLabel/arcrole/order tuples agree with the declared raw source, and erroneous role/depth/rejected-metadata diagnostics from that layout disappear. This resolves the observed layout defect; it does not establish arbitrary DTS/DRS validation or accounting meaning.

### R6 — BLOCKING: provenance columns become English Labels

- Exact code: `auditdesk/auditdesk/xbrl_v2/taxonomy.py:308-313` carries the last explicit language past its group; `:321-325` creates a Label for every nonempty header/value after the identity columns.
- Independently read official OOXML language merges are **D3:T3 (ko)** and **U3:AK3 (en)**. Header row is 4. The four following columns are metadata outside these language groups.

| Column | Header | Nonempty data cells | Current `/3` result |
| --- | --- | ---: | --- |
| AL / 38 | base schema | 9,467 | Incorrect `en` / `base schema` Label |
| AM / 39 | systemid | 0 | Same collection route; no populated value in this input |
| AN / 40 | prohibit | 0 | Same collection route; no populated value in this input |
| AO / 41 | comment | 0 | Same collection route; no populated value in this input |

The true nonempty cells inside the explicit language/Label-role blocks are **12,374 ko + 18,535 en = 30,909**. Current output has **40,376** Label records, including **9,467** source metadata cells. Direct parser reproduction confirms all 9,467 false Labels have language `en`, role `base schema` and source column 38. Their row/snapshot locators are retained, but preserving their location does not make their classification correct.

`after/official/label-header-semantics.json` records only structural headers/counts. `after/official/label-parser-semantics.json` records direct parser counts and merge boundaries. Neither exports cell content values. The expected validity assertion fails with exit 1 in 29.165s, saved after collecting evidence. The parser's 232,443 diagnostics in this probe reflect deliberately missing authority/context; count differences versus another probe's supplied metadata are not new source defects.

The earlier raw count and field-comparison outputs remain valid as **all nonempty column-field preservation comparisons**, but their 40,376 measure is not the valid Label resource count. They must be qualified by this finding and must not be presented as actual Label semantics PASS. R6 exists independently of namespace resolution or applicability uncertainty, because it follows the official structural language boundaries and source-metadata headers.

Classification: **#11 technical defect**, not new accounting judgment. It needs no other Issue's unmerged code or protected truth change. It is outside the earlier limited R1/R2 fix and R5 layout fix, so the reviewer makes no implementation change. Proposed separate bounded Owner decision: distinguish declared Label role blocks from the four provenance columns, preserve provenance value/location explicitly, keep ambiguous/unsupported columns diagnostic rather than dropping them, and add fresh synthetic regressions plus a repeat actual-file comparison. Do not guess schema URIs from source text or silently discard unknown columns.

### Executed independent checks

Commands use Python 3.14 with `-B`; runtime and local input paths are omitted from this public-safe report. Results are scoped to the reviewed `/3` file hash.

| Check | Actual result | Limit |
| --- | --- | --- |
| `python -B raw_census.py <official.xlsx> <output>` | COMPLETED / exit 0 | Independent ZIP/XML counts, not semantic approval |
| `python -B parser_compare.py <checkout> <official.xlsx> <directory>` | 7 assertion groups PASS / exit 0; 25.541s | Bytes/counts/locators/collisions/fail-closed capability; Label count is raw column cells, qualified by R6 |
| `python -B deep_compare.py <checkout> <official.xlsx> <directory>` | PASS / exit 0; zero selected-field mismatches in all five record classes | Preserves selected raw fields; does not classify Label roles correctly by itself |
| `python -B official_edges.py <checkout>` | 4 PASS, 0 FAIL/ERROR/SKIP | Mixed distinct Role URI, ambiguous metadata, unknown role, trailing headerless section |
| `python -B -m pytest auditdesk/tests/test_xbrl_v2_taxonomy_official_layout.py -q -p no:cacheprovider --basetemp=<reviewer-temp>` | 8 PASS in 1.27s; exit 0 | Synthetic official-layout regressions; no real workbook fixture committed |
| `python -B label_parser_semantics.py <checkout> <official.xlsx> <output>` | **FAIL / exit 1**; 29.165s | R6 directly reproduced; 9,467 metadata records misclassified |
| `python -B scripts/check_protected.py --base origin/main` | PASS / exit 0 | No protected artifact/rule definition changed |
| Official input SHA-256 after probes | PASS / unchanged | Source was not modified |

Parent separately reports the combined scoped run as 98 PASS with 38 subtests; reviewer did not rerun that full combined suite. Parent reports current strict run 229 PASS / 1 FAIL / 76 SKIP, 50.35s and UI build PASS, session exit 1. These are parent-reported, not an independent full-suite rerun. The strict failure is the previously known generation-catalog condition, not hidden or marked PASS. The new aggregate execution was still running at report time; **NOT independently verified / no aggregate PASS claimed here**. Earlier `/2` aggregate results must not be transplanted as `/3` execution evidence. Missing existing compatibility materials remain BLOCKED, business acceptance PENDING.

### Remaining source uncertainties and handoff

Both examined inputs retain the Concepts repeated source ID at rows 3849/9210, differing lexical attribute tuples, 16 Label rows without concept identity, and 1,829 blank abstract flags. References have repeated targets that are not automatically duplicate errors. These observations are retained, not resolved by assumption. Current QName/parent resolution cannot be certified without official namespace evidence.

Keep Issue #11 open and PR draft. Record R5 resolved and R6 blocking separately; request the bounded new R6 scope decision before product edits. After any authorized fix, rerun affected synthetic and actual semantics probes, appropriate full checks and independent review. Stop at Owner Review with no merge or business acceptance. Original before reports/results are preserved; this is a separate after-review record.
