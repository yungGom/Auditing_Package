## 한눈에 보기

### 1. 이번에 무엇을 했나?
승인된 범위로 가져온 당기 공시 기준 읽기 기능을 다시 독립 검토했습니다. 앞서 발견한 원문 식별자 중복과 표시 구역 누락 문제가 해결됐는지 확인했습니다.

### 2. 실제로 무엇이 달라졌나?
원래 식별자를 보존하고 중복된 원본 행마다 문제를 표시합니다. 제목 행이 없는 표시 구역은 조용히 빼먹지 않고 해당 구역과 읽지 못한 행의 위치를 남깁니다. 정상 항목과 근거는 그대로 보존합니다.

### 3. 확인 결과는 어땠나?
독립 재검사 여덟 건과 추가 경계 검사 일곱 건이 모두 통과했습니다. 앞서 실패한 세 사례도 통과했습니다. 관련 검사 아흔 건과 공개·합성 자료 전체 자동검사는 통과했습니다. 보호 대상 변경 검사도 통과했습니다. 다만 엄격한 기존 기능 검사는 한 건 실패하고 일흔여섯 건을 건너뛰었으며, 실제 자료 여든한 건은 자료 부족으로 확인하지 못했습니다. 전체 업무 검증 완료는 아닙니다.

### 4. 아직 남은 문제는?
실제 공시자료의 당기 적용 가능성, 회사 확장 기준, 전체 분류체계 검증은 확인하지 않았습니다. 엄격한 검사의 기존 실패와 자료 부족은 남아 있습니다. 이전에 제한 시간을 넘긴 공개 PDF 검사는 이번에 완료됐지만, 해당 코드 변경 없이 실행 시간이 달라진 결과입니다. 다른 작업의 문제를 해결했다는 뜻은 아닙니다.

### 5. 내가 결정해야 할 게 있나?
이번에 승인한 재사용·두 문제 수정 범위는 지켜졌습니다. 추가 구현 승인을 요청할 새 문제는 발견하지 않았습니다. 전체 검사 결과와 실제 자료의 미확인 범위를 포함한 최종 보고를 보고 병합 여부를 별도로 판단해야 합니다.

### 6. 지금 상태는?
이번 두 문제의 수정은 독립 검토에 적합합니다. 전체 검증과 업무 수용은 별도입니다. 기본 제품에 병합하거나 실제 업무 수용 완료로 표시하지 않고 사람 확인 단계로 넘겨야 합니다.

## Developer Details

### Review scope, authorization and verdict

- Reviewer: independent read-only `issue11_independent_review`.
- Owner authorization relayed for this resumed turn: “위 10개 파일을 제한적으로 가져와 두 문제를 수정하는 범위입니다 >> 부탁해”. Parent records this as Issue #11 Human Decision. The earlier pre-authorization stop is therefore resolved only for the specified bounded import and R1/R2 corrections.
- Source candidate: `ec256e52d884e798fb880297b41be5be9648aa0c`.
- Reviewed implementation checkout HEAD before its new commit: `77954d4de34df2b48bbbde9156471c512877ccde`; `origin/main`: `6373a333414f51015f9d1068e32ec2ef7702cbe4`.
- Re-read checkout AGENTS, POLICY, AuditDesk contract and protected inventory. Existing scope/instructions reviewed in the initial independent pass remain applicable.
- **Verdict: R1 RESOLVED; R2 RESOLVED. No new blocking finding in the approved implementation slice. Scoped independent review is acceptable for Owner Review.** This is neither full Harness PASS nor real-material compatibility, business acceptance, merge or release approval.
- Reviewer did not edit tracked code/tests or the implementation staging area. Generated reviewer artifacts live only in sibling `reviewer-final/`.

### Change and boundary verification

- `taxonomy.py:15`: parser version changes to `dart-workbook-preview/2`, correctly changing snapshot identity and preventing the changed interpretation from silently reusing a v1 snapshot.
- `taxonomy.py:57`, `:65`, `:187-221`, `:230-232`: Concept and Role source IDs are preserved independently of generated IDs. Duplicate IDs within each record kind retain original records and generate ERROR diagnostics for every conflicting source row. No separate schema-document scope is guessed from namespace prefixes. Missing optional source IDs remain empty; no invented source ID is introduced.
- `taxonomy.py:239-265`, `:287`: every explicit presentation section is closed and checked for a recognizable header. Nonempty uninterpretable rows receive rejection locations. The supported Definition metadata layout and blank rows remain allowed. An incomplete section does not erase valid occurrences from a later section, but ERROR diagnostics prevent current applicability for the snapshot.
- The approved ten source files are imported; only Taxonomy changes against the original source. One new integrity test file is added. `git diff --name-status 77954d4 -- auditdesk/auditdesk/xbrl_v2 auditdesk/tests` shows exactly these eleven additions.
- Original six core modules, original core/offline tests and original taxonomy test are unchanged against `ec256e5`: exact `git diff --exit-code` comparison over those nine paths returned 0. Parent's initial import manifest hash check is additional evidence; reviewer independently verified Git source equality after correction.
- No `dsd.py`, `recommendation.py`, CLI, #9/#12 tests, accounting rule, gate, fixture, threshold, policy or unrelated product change is part of the staged implementation slice. Taxonomy does not instantiate storage or migrate an existing database.

### Resolution of previous findings

| Finding | Status | Independent evidence |
| --- | --- | --- |
| R1 source ID duplicates silently accepted | RESOLVED | Previous Concepts/RoleTypes duplicate-ID probes now PASS; conflicting records and both row locations remain. Interleaved duplicate groups and different namespaces also independently tested. |
| R2 later presentation header silently drops data | RESOLVED | Previous missing-second-header probe now PASS; snapshot is inapplicable, first section remains intact, rejected rows 8/9 and the failed section are explicit. Additional malformed metadata and leading unclassified row probes also PASS. |
| R3 optional current extension applicability | known_gap, unchanged | CURRENT_EXTENSION remains explicitly unsupported. No implementation expansion or new extension approval demand. Entity/scope/period validation is not claimed. |
| R4 blank arcrole/order diagnostics | nonblocking, unchanged | Blanks remain preserved as in the original workbook preview; no effective network validation is claimed. |

### Tests actually executed by this reviewer

Commands below use the available Python 3.14 runtime with `-B` and authorized `require_escalated`, from the isolated checkout. Write targets are outside the candidate checkout, under `reviewer-final/`. No client material or tracked input fixtures are used.

1. `python -B auditdesk/docs/ISSUE11_TAXONOMY_ACCEPTANCE_PROBE.py --candidate-root . --output ../reviewer-final/acceptance-probe-final.json`
   - **8 PASS / 0 FAIL / 0 ERROR / 0 SKIP, exit 0**.
   - Same eight assertions as the earlier independent review; previous result was 5 PASS / 3 FAIL.
   - Confirms repeated QName/Role/path occurrences, namespace separation, duplicate Role URI rejection, resource provenance, unsupported extension safe rejection, and R1/R2 fixes.
2. `python -B ../reviewer-final/post_fix_edges.py .`
   - **7 PASS / 0 FAIL / 0 ERROR / 0 SKIP, exit 0**; unittest assertions plus input construction 1.109s.
   - Cases: valid Definition metadata with blanks; Definition-like row with extra populated evidence rejected; leading nonempty unclassified row diagnosed; same source ID across namespaces keeps both expanded names but fails closed; interleaved collisions report every row exactly once; duplicate-ID snapshot preserves hash/type/period/abstract/occurrence/label/reference facts; missing-header snapshot retains unaffected graph and resource facts plus rejection locations.
   - Result: `edge-results.json`.
3. `python -B scripts/check_protected.py --base origin/main`
   - **PASS**: `PROTECTED CHECK PASS: no protected artifact or rule definition changed`.
4. `python -B scripts/check_protected.py --staged`
   - **PASS**, same explicit protected-check message.
5. `git diff --cached --check`
   - **PASS**, no whitespace errors.
6. `git diff --exit-code ec256e52d884e798fb880297b41be5be9648aa0c -- <six core modules + original core/offline/taxonomy tests>`
   - **PASS, exit 0**; approved dependency unit and original tests unchanged.

Independent counts are 15 tests, not a second full Harness run. Do not add these to implementation test counts as unique product coverage without considering overlap.

### Implementation evidence inspected, not rerun by reviewer

- `evidence/integrity-before.log`: **13 FAIL / 1 PASS, 6.23s** on the original parser; retained as failing-before evidence. Thirteen failures are not thirteen independent product defects; several cover source-ID projection or the parser-version boundary.
- `evidence/scoped-final.log`: **90 PASS, 38 subtests PASS, 30.36s**, no failures/skips/errors. Includes original taxonomy 35, new integrity 14 and unchanged core/offline 41. JUnit records 128 entries because it includes 38 subtests; this is not 128 top-level tests.
- `evidence/scoped-final.xml`: `errors=0`, `failures=0`, `skipped=0`, agrees with the console result above.
- Full `scripts/test_auditdesk.py` and `scripts/test_all.py`: **NOT RUN by this reviewer**; executed by the parent implementation pass. Final measured logs and structured results have now been independently inspected; see the final handoff evidence section below.
- Previous same-main strict baseline (229 PASS / 1 FAIL / 76 SKIP), aggregate public/synthetic partition (225 PASS and web build PASS), DSD timeout and 81 blocked compatibility cases remain historical parent evidence. Fresh final results are separately confirmed below; the Taxonomy correction does not establish a cause for changed DSD runtime.

### Remaining limits and Owner Review

- Actual-material applicability, official namespace/source-release verification, current company extension ingestion, full DTS/effective network/DRS and real-report UAT: **NOT RUN / unsupported** as applicable. No fresh public workbook or actual current-report acceptance is claimed.
- Current-first workbook preview still has `PARTIAL` capability and dimensions unknown. Safe source rejection is distinct from proving a full report valid.
- No new protected baseline, accounting judgment or scope decision is needed for the two reviewed fixes. Parent has executed and reported the full applicable checks, retaining the strict failure/skips and missing materials explicitly. Stop at Owner Review. Human decides merge and business acceptance separately.

### Final measured Harness and document handoff review

The final verification report, implementation evidence JSON, post-fix eight-probe JSON and proposed PR #33 body were inspected after full execution completed. **Document handoff verdict: ACCEPTABLE for Owner Review; no new blocking finding.** This approves the accuracy and boundary of the handoff, not merging or business acceptance. No production code/test changed after the independent implementation review.

- Strict `scripts/test_auditdesk.py`: **FAIL / exit 1**, 229 PASS / 1 FAIL / 76 SKIP / 0 ERROR, one warning, 96.27s; unchanged known-generation material failure. TypeScript/web build PASS. This result remains explicit in the six-question Korean summary and technical evidence.
- Aggregate `scripts/test_all.py --timeout 600`: **Issue #23-approved public/synthetic Technical Gate PASS / exit 0**, three of three components PASS. AuditDesk partition: 225 PASS, 81 compatibility cases deselected, no FAIL/SKIP/NOT RUN, pytest 34.85s and component 39.25s. Web component PASS, 16.31s. DSD_FOOTING component PASS/COMPLETED, exit 0, 469.65s within the unchanged 600s bound; raw console confirms **4/4 registered public samples passed**.
- Real-material compatibility: **81 BLOCKED: REQUIRED MATERIAL UNAVAILABLE**, no real-material PASS. Human Business Acceptance **PENDING**. Scoped Technical Gate PASS neither waives the strict failure/skips nor establishes current workbook/report validity.
- Earlier DSD timeout remains historical evidence. No DSD source, sample, baseline or timeout was changed. Neither this review nor the final report claims Taxonomy fixed that timing variability or resolved Issue #18.
- Published implementation evidence contains ten final source/test SHA-256 values. Reviewer compared all ten with checkout bytes: **10/10 match**; exactly nine remain unchanged from the approved source. Seven published raw-log/XML/JSON digests were compared with local evidence: **7/7 match**. Published post-fix eight-probe JSON exactly matches the independent reviewer's original result file.
- New documents and PR body preserve the ten-file reuse boundary, one new integrity test module, absence of #9/#12 imports, PARTIAL capability, unsupported extension/DRS, missing real-material validation and no-merge/Owner Review boundary. The seven local edge probes are explicitly reviewer evidence, not a claimed new committed test module.
- No final-execution placeholders or personal local paths remain in the inspected new documents. The source investigation documents and old failing results are retained as historical records.
- Final staged protected check independently rerun: **PASS**, explicit protected-check output. Final staged whitespace check: **PASS**. Parent also confirms final base and staged checks exit 0. Reviewer modified only this sibling report and other reviewer-owned evidence; tracked implementation/docs remain under the implementer's control.

Proceed with the reviewed implementation/evidence handoff and keep Issue #11 open, PR #33 draft/open, merge/release/business acceptance unapproved. Owner must separately decide acceptance of the bounded correction and the next real-material verification step.
