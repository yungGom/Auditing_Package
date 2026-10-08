## 한눈에 보기

### 1. 이번에 무엇을 했나?
승인된 출처 열 분리 수정을 독립적으로 검토했습니다. 공식 배포파일의 표시 이름과 출처 정보를 원문에서 직접 다시 읽어 빠짐없이 대조하고, 모호한 열과 공백 처리도 별도로 검사했습니다.

### 2. 실제로 무엇이 달라졌나?
출처 정보가 영문 표시 이름으로 잘못 만들어지던 문제가 해결됐습니다. 출처 값은 원래 공백과 위치를 유지한 별도 기록으로 보존합니다. 알 수 없는 열은 임의로 해석하거나 버리지 않고 미확정 기록과 오류로 남깁니다. 검토자는 제품과 원본을 수정하지 않았습니다.

### 3. 확인 결과는 어땠나?
공식 파일의 표시 이름과 출처 정보가 원문과 모두 일치했습니다. 추가된 검사와 독립 경계 검사도 통과했습니다. 기존 항목·역할·표시·참고자료의 선택 정보에서도 불일치를 찾지 못했습니다. 전체 자동검사의 최종 결과는 담당자의 실행 기록과 별도로 확인해야 합니다.

### 4. 아직 남은 문제는?
실제 보고서에 적용할 수 있는지와 당기 이름 공간의 공식 근거는 아직 확인하지 못했습니다. 겹친 식별자, 소속 항목이 빈 이름 자료와 비어 있는 속성도 임의로 확정하지 않았습니다. 전체 차원 검증이나 업무 사용 확인까지 끝난 것은 아닙니다.

### 5. 내가 결정해야 할 게 있나?
승인된 수정은 확인됐습니다. 보고서 종류·기간·정정 여부와 이름 공간의 공식 근거를 확인한 뒤 실제 업무 사용 여부를 별도로 판단해야 합니다. 제품 병합과 업무 수용은 자동검사 통과만으로 승인되지 않습니다.

### 6. 지금 상태는?
이번 출처 열 수정은 확인 완료했습니다. 실제 업무 적용에는 미확인 사항이 남아 있으므로 사람 확인 단계로 넘깁니다. 기본 제품에 병합하거나 업무 수용 완료로 표시하지 않습니다.

## Developer Details

### Independent scope and verdict

Date: 2026-10-08. Reviewer: `issue11_independent_review`. Reviewed uncommitted R6 changes based on `3b488933`; parser `dart-workbook-preview/4`, `taxonomy.py` SHA-256 **`8c1bc2977fd9b5a3ec0abb1214fee8c0f5463145d84cab75ffbdaa907114bdf5`**.

**Bounded approved R6 correction: PASS / no blocking implementation finding. R6 RESOLVED for the tested official source and supported synthetic boundary cases. R1/R2/R5 remain resolved in their previously stated scope. Overall current-report applicability, namespace authority and business acceptance are not PASS.**

The reviewer only read product/test/source files and generated evidence under `reviewer/r6/`. No input workbook, protected artifact, production code or tracked test was changed by reviewer. Earlier `/2` and `/3` failures/reviews remain preserved separately; this report does not erase them.

### Implementation reviewed

- `auditdesk/auditdesk/xbrl_v2/taxonomy.py:88-97`: immutable `TaxonomyLabelSourceField` holds generated ID, optional QName, recognized lexical identity, field name, exact string value, classification and source locator.
- `:123`: appended `label_source_fields=()` default preserves legacy positional snapshot construction. No common-model, storage or recommendation contract is rewritten.
- `:15, :137`: `/4` is included in snapshot identity, invalidating reuse of differently interpreted `/3` snapshots. New source-field IDs also bind snapshot and physical cell coordinates.
- `:174-186`: separate unnormalized Label-sheet string values retain provenance whitespace while existing resource normalization remains unchanged.
- `:319-366`: four explicit metadata headers form the provenance boundary; values are recorded per physical cell, without creating a Label. Unknown columns after that boundary, blank headers with populated values and malformed resource headers produce error diagnostics and `UNRESOLVED` records. Duplicate provenance headers preserve both cells with an error. Explicit language after provenance does not reopen a resource group. Recognizable malformed identity headers keep nonidentity resource/source values without inventing QName/name evidence.

Only taxonomy production behavior and new regression coverage are changed. No protected expectations, accounting truth, skip catalog, timeout, source workbook or other Issue's unmerged implementation is introduced. Previously reused nine files excluding taxonomy are unchanged against `ec256e52d884e798fb880297b41be5be9648aa0c`: core `__init__.py`, `model.py`, `ports.py`, `provenance.py`, `rules.py`, `storage.py`; original core/offline/taxonomy test modules. Git comparisons independently returned exit 0.

### Independent actual official-source comparison

Official source: 13,353,457 bytes; SHA-256 **`d7135781ed425bb2e43a7dafffc3189435bbd16a70fae3d98c258ea8dc9845e7`** before/after reads. Do not substitute the different historical local copy.

`official_full_compare.py` independently reads ZIP/XML relationships/shared strings/cells, verifies exact language merges D3:T3 and U3:AK3, and constructs the expected resource and provenance cell sets. It uses normalized strings only for existing resource/recognized identity comparison and original untrimmed cell strings for source-field value comparison. It checks both set completeness and per-cell field equality; it does not merely compare output counts.

| Measure | Expected / observed | Result |
| --- | ---: | --- |
| ko Label resources | 12,374 / 12,374 | PASS |
| en Label resources | 18,535 / 18,535 | PASS |
| Total actual Label resources | 30,909 / 30,909 | PASS |
| Source fields outside language blocks | 9,467 / 9,467 | PASS, all PROVENANCE |
| Label row/column/language/role/text tuple differences, missing or extra cells | 0 | PASS |
| Source-field physical row/column, recognized lexical identity, header, exact raw value and classification differences, missing or extra cells | 0 | PASS |
| Source-field sheet/snapshot/unique IDs/unique physical cells | all true | PASS |
| Source QName without namespace bindings | none invented | PASS |
| Concepts / RoleTypes / occurrences / References | 9,451 / 2,004 / 68,898 / 6,267 | Selected-field comparisons all match |

Known provenance columns AL/38 `base schema`, AM/39 `systemid`, AN/40 `prohibit`, AO/41 `comment` remain source records when populated. This official input has 9,467 nonempty AL values and zero in the other three columns; synthetic tests therefore also exercise populated values in every metadata column.

Output remains `PARTIAL`, dimensions unknown, `current_applicable=False`. Probes deliberately use `UNVERIFIED_TAXONOMY`, blank applicability fields and no namespace bindings. Existing collision and ambiguity diagnostics persist; they are not converted into verified source truth. The observed duplicate source-ID pair, 16 missing Label identities and 1,829 unknown abstract flags remain unresolved. Source fields with missing identity retain no guessed QName. The exact snapshot diagnostic total differs from the parent's declaration-bearing run by two metadata errors; that is probe-input evidence scope, not a new workbook defect.

### Actual independent commands/results

Runtime Python 3.14, `-B`. Placeholders below denote local evidence paths; no private path or workbook cell text is exported.

| Command | Actual result |
| --- | --- |
| `python -B official_full_compare.py <checkout> <official.xlsx> <reviewer-r6>` | **PASS / exit 0**, 48.814s. Complete resource/source cell-set and raw-value comparison; selected fields of five record classes match. |
| Delegated internal `deep_compare.py` using direct XML census | **PASS / exit 0**; selected fields of 9,451 Concepts, 2,004 Roles, 68,898 occurrences, 30,909 Labels, 6,267 References have zero mismatches. This is field preservation, not full DTS/DRS or reference applicability validation. |
| `python -B -m pytest auditdesk/tests/test_xbrl_v2_taxonomy_label_provenance.py -q -p no:cacheprovider --basetemp=<reviewer-temp>` | **17 PASS / 0 FAIL/ERROR/SKIP**, 3.06s, exit 0. |
| `python -B edges.py <checkout>` | **8 PASS / 0 FAIL/ERROR/SKIP**, 0.508s, exit 0. |
| `python -B scripts/check_protected.py --base origin/main` | **PASS / exit 0**. |
| Original-nine-file Git comparisons against approved source | **PASS / exit 0**, no differences. |
| `git diff --check` | **PASS / exit 0**. |
| Official input and reviewed parser SHA-256 recheck | **PASS**, exact hashes above. |

The eight extra probes cover reordered metadata with empty gaps, equal values across different rows retaining distinct IDs, whitespace-only unknown cells without invented identity, duplicate metadata with explicit language, malformed duplicate identity headers, legacy positional constructor/frozen fields, deterministic version-bound cache/field identities, and unchanged Label normalization alongside exact provenance whitespace. These are reviewer-only evidence, not additional committed test cases or accounting truth.

Parent separately reports final scoped six-module results **115 PASS + 38 subtests PASS / 0 FAIL/ERROR/SKIP**, 22.57s; parent actual-material nine-check probe also agrees. Reviewer independently executed the new 17 tests plus eight edges and official full comparison, not the entire parent combined suite. Parent full strict/aggregate executions were in progress at this report's cutoff; they are **NOT independently verified in this report**, and no prior `/3` aggregate result is transplanted as `/4` evidence. Update the final Verification Report with their actual completed outcomes before final handoff. Missing compatibility catalog materials and business acceptance retain their separate statuses.

### Findings and limits

- **blocking:** none found in the approved R6 implementation slice. This verdict is not an Issue-complete or business-use verdict.
- **nonblocking:** source fields are additive and immutable; legacy snapshot constructor/default and explicit version identity checks passed. No role allowlist or unsupported new accounting semantics is imposed.
- **question / Owner Review:** supply or verify target report type/period/original-versus-correction context and authoritative current namespace evidence before current-report usage.
- **known_gap:** arbitrary DTS/DRS/full network/extension validation, actual company report/browser/DART-editor UAT and unavailable existing compatibility materials remain unverified. Selected fields and source values match; this does not establish accounting-reference applicability or resolved presentation paths without namespace authority.

Keep Issue #11 open and PR draft for Owner Review. No main merge, release or Human Business Acceptance. If implementation changes after the recorded hash, rerun affected comparisons and review before reusing this verdict.
