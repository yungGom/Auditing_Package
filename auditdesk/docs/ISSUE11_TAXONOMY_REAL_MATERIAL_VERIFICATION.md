## 한눈에 보기

### 1. 이번에 무엇을 했나?

공식 배포처에서 당기 공시 분류 기준을 받아 원본과 읽힌 결과를 전수 대조했습니다. 실제 원본에서 발견한 표시 역할 연결 문제를 수정했습니다. 이전 조사와 승인된 기존 기능 재사용 내역은 그대로 보존했습니다.

### 2. 실제로 무엇이 달라졌나?

공식 원본의 표시 구역을 정확한 역할에 연결합니다. 서로 다른 두 가지 열 배치를 명시적으로 처리하며, 알 수 없는 추가 값은 임의로 버리지 않습니다. 원본을 바꾸거나 충돌 항목 하나를 정답으로 선택하지 않았습니다.

### 3. 확인 결과는 어땠나?

관련 자동검사 아흔여덟 건과 기존 재현 검사 여덟 건이 통과했습니다. 독립 검토에서 표시 역할 연결 수정과 전체 기록의 선택 필드 대조를 확인했습니다. 다만 추가 의미 검증에서 출처 정보 구천사백육십일곱 개가 항목 이름표로 잘못 분류되는 오류를 발견했습니다. 따라서 실제 파일 전체 검증은 실패 상태입니다. 공개·합성 자료 전체 자동검사와 보호 검사는 통과했지만, 기존 엄격 검사는 자료 부족으로 한 건 실패하고 일흔여섯 건을 건너뛰었습니다. 기존 실제 자료 여든한 건도 자료 부족으로 확인하지 못했습니다. 보호 기준을 완화하지 않았습니다.

### 4. 아직 남은 문제는?

이름표 오분류를 추가로 수정해야 합니다. 검증할 보고서의 회사·기간·최초 제출인지 정정인지 정보와 당기 이름 공간의 공식 근거도 필요합니다. 원본의 중복 식별자와 식별 정보가 빈 행은 미확정으로 남겨 두었습니다. 실제 보고서 사용 확인, 회사 확장 기준, 전체 차원 검증과 기존 자료 부족 검사도 완료하지 않았습니다.

### 5. 내가 결정해야 할 게 있나?

있음. 앞서 승인한 두 문제와 별개로 발견한 이름표 오분류까지 수정할지 결정해 주세요. 제안 범위는 같은 해석기에서 출처 열을 이름표로 만들지 않고 출처 원문·위치를 보존하는 수정과 재검사입니다. 회계 기준이나 보호 파일 변경, 다른 작업의 미병합 구현은 필요하지 않습니다. 이번 확인은 제품 병합이나 업무 사용 승인 요청이 아닙니다.

### 6. 지금 상태는?

**사람 확인 필요.** 승인 범위의 수정은 확인했지만, 실제 파일 전체 검증은 추가 오류 때문에 미완료입니다. 추가 수정 범위를 제시하고 사람 확인 단계에서 멈춥니다. 기본 제품에 병합하거나 업무 수용 완료로 표시하지 않습니다.

## Developer Details

Date: 2026-10-08 KST. Source of Truth: [Issue #11](https://github.com/yungGom/Auditing_Package/issues/11).
Related: [#9](https://github.com/yungGom/Auditing_Package/issues/9), [#12](https://github.com/yungGom/Auditing_Package/issues/12), [source PR #13](https://github.com/yungGom/Auditing_Package/pull/13), [draft PR #33](https://github.com/yungGom/Auditing_Package/pull/33).

### Scope, reuse and isolation

- User continuation: “부탁해, 마저 진행해주라” follows clarification that official current-source/version/applicability and actual workbook comparison remain. Public-material investigation and a same-file R2 layout correction were resumed; no source data, protected artifact, accounting rule, threshold, skip/catalog, timeout or other Issue implementation was changed.
- Dedicated independent worktree/branch `codex/issue11-taxonomy-audit`. Latest inspected main remains `6373a333414f51015f9d1068e32ec2ef7702cbe4`; prior approved implementation is `3f2ee38052206d06530aaccd5f055411a2cecdb4`. Original dirty checkout and concurrent #12/#18 work were untouched.
- Main has legacy Taxonomy, not these V2 modules. Exact ten-file reuse from PR #13 `ec256e52d884e798fb880297b41be5be9648aa0c` remains as approved. The eight V2-1 dependency files and original Taxonomy test are unchanged. Only `taxonomy.py` receives production corrections. No `dsd.py`, recommendation, CLI or other mixed-branch change was imported.
- Earlier dated investigation and implementation reports remain historical. This report supersedes their actual-material NOT RUN status only for the checks explicitly executed here; it does not overwrite earlier failures.

### Actual public-source chain

| Check | Executed evidence / conclusion |
| --- | --- |
| Publication | [Official filer download board](https://filer.fss.or.kr/raaf001/search.do), release132 dated2026-06-30, attachment5 `1. DART_Taxonomy_20260630_배포용F.xlsx`. Public list/detail/attachment were inspected, not inferred from a local filename. |
| Retrieval | Cookie session initialized at `/raaa001/goIndex.do`; POST `/raaf001/select.do` with `new_fl_id=132`, `dn_cnt=3466`, `currentPage=1` and empty form fields; POST `/raaf001/download.do` with `new_fl_id=132`, `new_fl_apn_no=5`, exact filename and page1. HTTP200, workbook ZIP verified; error HTML from incomplete initial requests was not accepted as a workbook. |
| Exact bytes | 13,353,457 bytes; SHA-256 `d7135781ed425bb2e43a7dafffc3189435bbd16a70fae3d98c258ea8dc9845e7`; expanded121,946,513 bytes, within unchanged parser bound. |
| General applicability | Release detail and [official notice endpoint](https://filer.fss.or.kr/raaf002/select.do), POST `ntc_no=443`, inspected. New taxonomy applies from2026half-year reports; correction filings retain the existing format. Standard note-structure monitoring is separately described for2026annual reports. These statements do not decide an unspecified target report. |
| Notice evidence | Release HTML SHA-256 `e028b928e880a162e3eddb1888c61bab06868318fc54ef85bd5676c65e037dda`; notice HTML `4bb802ad3011e81c0114a9bffcca3412c294e7f0ca97af6d0774ef242779ca55`. Method/form parameters in structured evidence. HTML contents, cookies, authors and private paths are not published. |
| Existing local copy | Read-only comparison: SHA-256 `4cc40e96de1f6a5bea48cedc494ee0b9b3181f7b42d939fa57efae2542cb0d34`, 13,625,977 bytes; differs from official. No overwrite or claim of identical official bytes. Its extra metadata layout is not an official-source defect. |
| Older official source | English OpenDART notice led to a2024schema ZIP, not the2026workbook. It was not promoted to current authority or used for current namespace bindings. |
| Target applicability | BLOCKED / context not supplied: entity, report period, original-versus-correction and current authoritative namespace declarations. Parent probe intentionally leaves date fields/namespaces empty; `current_applicable=False`. No date range or namespace URI was invented. |

Public download was investigation outside product code. The production parser and core remain offline. No workbook binary or raw source-content snapshot is tracked.

### R5: official presentation layout — RESOLVED

The official476sections use `LinkRole`/`Definition` in A and the value in B. The existing preview supports B/D. Parser `/2` retains68,898occurrences but binds every official occurrence to an empty Role. Independent raw-OOXML comparison confirmed68,898Role/attribute tuple mismatches; all476official table headers actually contain the required fields.

`taxonomy.py` now supports exactly these two observed metadata layouts. Additional populated cells create `MALFORMED_PRESENTATION_METADATA`; malformed Definition rows retain rejection locations. Section/header/stack reset and R1 collision behavior remain. Parser version advances `/2`→`/3` to invalidate reuse of a differently interpreted snapshot. Only the new integrity test's parser-version assertion changes; existing protected and imported test expectations remain unchanged.

Eight new fresh-OOXML tests cover official/existing/mixed sections, both headerless positions, ambiguous Role cells in either layout and unexpected Definition cells. Before:7FAIL/1PASS. After:8PASS within98PASScombined. Independent reviewer adds4passing boundary probes, including distinct roles across layouts. After correction, all68,898official occurrence Role/preferredLabel/arcrole/order tuples match raw source. This is selected-field preservation, not full network/path/DRS certification.

### R6: provenance columns misclassified as Label — BLOCKING / not modified

Further semantic review separates source-field equality from correct resource interpretation:

- Actual language merges are D3:T3 (`ko`) and U3:AK3 (`en`), each17role columns. Nonempty resource cells:12,374ko +18,535en =30,909.
- AL (`base schema`) is outside both language blocks, with9,467nonempty provenance cells. AM `systemid`, AN `prohibit`, AO `comment` have0nonempty cells in this workbook.
- Existing Label loop carries `en` beyond AK and emits9,467ALvalues as `TaxonomyLabel(language='en', role='base schema')`. Output40,376includes these false resources. They retain row/snapshot locators, but their classification is wrong.
- Independent direct-parser semantic assertion **FAIL / exit1**,29.165s. A prior all-field/count match does not make this semantics PASS. Source record counts alone do not establish completeness or valid classification.
- This is a #11 technical interpretation defect; no accounting decision, protected change or other Issue dependency is needed. It is additional to the explicitly approved two fixes, so no production correction is applied before the Owner's additional-scope decision. Proposal: explicit resource-versus-provenance boundary, preserve provenance values/locators, fresh synthetic tests with nonempty metadata columns, repeat official semantic comparison and required checks.

### Actual comparison and fail-closed limits

| Scope | Measured result |
| --- | --- |
| Concepts | 9,451 source records; selected prefix/name/sourceID/type/periodType/abstract fields match. Original ID and lexical identity duplicate at rows3849and9210 has different attributes; both records remain. Unique lexical identities9,450 is not permission to deduplicate. |
| RoleTypes | 2,004 records; sourceID/URI/definition/usedOn fields match. |
| Presentation | 476sections/headers,68,898data records. `/2` Role mismatches68,898; `/3` selected tuples0mismatches. QName expansion/path correctness remains unverified without authoritative namespace bindings. |
| Label | 40,376collected cells match source field tuples, but only30,909are in explicit language/role blocks. 9,467metadata cells are wrongly classified; **semantic FAIL**. Sixteen source rows lack required lexical identity; not silently repaired. |
| Reference | 6,267records; role/named-part tuples match. This preserves source fields, not independent accounting/reference applicability approval. |
| Snapshot | PARTIAL, dimensions unknown, `current_applicable=False`. Parent after probe232,441diagnostics;162,316unresolved-namespace and68,249ambiguous-parent diagnostics mostly cascade from missing bindings, not that many independent source defects. Unknownabstract1,829 remains unknown/warning. Other codes: invalidapplicabilitydate1, duplicateID2, duplicateConcept1, unresolvedConcept27, missingidentity16. |

Independent reviewer intentionally uses UNVERIFIED_TAXONOMY and blank evidence; its diagnostic total232,443 includes two extra metadata errors versus the parent's explicit release declaration. Source hash matches in both runs; metadata/logical URI differ, so snapshot IDs need not match. Current/source validity stays false in both. Full DTS/effective network/DRS, optional company extension, actual report/browser/DART-editor UAT are NOT RUN/unsupported; no UI gate or business acceptance is inferred.

### Executed checks

Runtime: Python3.14.0, pytest9.1.0, openpyxl3.1.5. `PYTHONUTF8=1`; task-owned TEMP/TMP, scoped `PYTHONPATH=<checkout>/auditdesk`. Exact raw evidence digests and structured outcomes are in [evidence](ISSUE11_TAXONOMY_REAL_MATERIAL_EVIDENCE.json). New tests construct fresh OOXML in memory; no data fixture or accounting truth introduced.

| Command / scope | Result |
| --- | --- |
| New official-layout module, unchanged `/2` before fix; `python -B -m pytest --noconftest -p no:cacheprovider --basetemp=<task> auditdesk/tests/test_xbrl_v2_taxonomy_official_layout.py -q -rfEs --junitxml=<report>` |7FAIL/1PASS/0ERROR/SKIP,2.95s,exit1. |
| Same options; original Taxonomy +integrity +official-layout +core +offline modules, `/3` |98PASS/38subtestsPASS/0FAIL/ERROR/SKIP,19.66s,exit0. 35original Taxonomy +14integrity +8layout +41core/offline. |
| Published `ISSUE11_TAXONOMY_ACCEPTANCE_PROBE.py --candidate-root . --output <report>` |8PASS,exit0. Overlaps scoped checks; not additional unique coverage. |
| Independent `/3` raw record assertions / selected fields / extra layout edges |7assertion groupsPASS; all5record classes selected-field mismatch0;4boundary probesPASS. Resource semantic test separately FAIL, as above. |
| Published `ISSUE11_TAXONOMY_LABEL_SEMANTICS_PROBE.py <candidate-root> <official-workbook> <output-json>` |FAIL/exit1,16.735s; same9,467metadata-as-Label records. Read-only reproducer; no source values exported. This expected failure is preserved, not turned into a passing regression. |
| `python -B scripts/test_auditdesk.py` |FAIL/exit1:229PASS/1FAIL/76SKIP/0ERROR,1warning,50.35s Python. Existing `test_g2_smoke_direct`, `_KNOWN_GENERATIONS=[]`, missing known-generation material. TypeScript/buildPASS. Criteria unchanged. |
| `python -B scripts/test_all.py --timeout 600 --report <report>` |Technical Gate PASS/exit0,3/3componentsPASS. AuditDesk225PASS/0FAIL/SKIP/NOT RUN,81compatibility deselected; component25.62s. TypeScript/buildPASS6.39s. DSD_FOOTING4/4registered public samplesPASS,COMPLETED343.00s under unchanged600s. Compatibility81BLOCKED: REQUIRED MATERIAL UNAVAILABLE; Human Business Acceptance PENDING. |
| `python -B scripts/check_protected.py --base origin/main`; `--staged`; `git diff --cached --check` |Both protected checks and staged whitespace checkPASS/exit0 after staging. No protected change. |

The strict failure/skips and81real-material catalog cases are not reclassified by this standalone official Taxonomy check. Issue #23's aggregate public/synthetic gate is separate from strict regression, actual material semantics and Human Business Acceptance. DSD_FOOTING timing is observed under unchanged600s; no DSD change or Issue #18 resolution is claimed.

### Independent review and Owner handoff

Independent Reviewer inspected `/3`, before/after scoped tests, raw OOXML source counts/headers/merges, direct parser results and protected boundaries. [Review](ISSUE11_TAXONOMY_REAL_MATERIAL_REVIEW.md): R5RESOLVED, R6BLOCKING for full actual-file compatibility. [Final document handoff review](ISSUE11_TAXONOMY_REAL_MATERIAL_HANDOFF_REVIEW.md): HANDOFF_READY, all19raw-evidence digests match; completed aggregate/strict/protected results inspected. This approves the accuracy of the handoff, not product compatibility. The previous independent review's acceptance was limited to its then-tested R1/R2 slice; this newly found problem is not retroactively erased.

Owner Action: **Decision Required** on the additional Label/provenance correction, then the actual report context needed for later UAT. Current proposal is fully described above; no merge/business acceptance requested. Keep Issue open and PR draft; stop at **Owner Review**. No main merge, release or business-complete status.
