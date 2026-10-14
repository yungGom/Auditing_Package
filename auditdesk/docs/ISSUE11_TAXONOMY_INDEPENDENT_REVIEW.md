## 한눈에 보기

### 1. 이번에 무엇을 했나?
당기 공시 기준을 읽는 기존 후보 기능을 독립적으로 검토했습니다. 중복 식별자와 표 구역 누락을 별도 합성 자료로 확인했습니다.

### 2. 실제로 무엇이 달라졌나?
제품 코드는 바꾸지 않았습니다. 이미 있는 읽기 기능을 다시 만들 필요는 없지만, 가져오기 전에 두 가지 문제를 고쳐야 한다는 근거를 확보했습니다. 원래 항목 식별자 중복을 놓치고, 두 번째 표 구역의 제목 행이 없으면 그 구역을 조용히 빼먹습니다.

### 3. 확인 결과는 어땠나?
추가 검사 여덟 건 중 다섯 건은 통과하고 세 건은 실패했습니다. 반복 표시 항목의 개별 보존, 이름 공간 구분, 중복 표시 기준 차단, 이름·참고 근거의 출처 보존은 확인했습니다. 보호 대상 변경 검사는 통과했습니다. 전체 검증이 통과한 상태는 아닙니다.

### 4. 아직 남은 문제는?
기존 후보는 아직 기본 제품에 반영되지 않았고 공통 선행 기능에 의존합니다. 추가 검사의 실패 세 건은 두 종류의 수정으로 해결해야 합니다. 회사 확장 기준을 당기 회사·연결 구분·기간에 맞춰 검증하는 기능과 실제 공시자료의 적용 가능성은 확인되지 않았습니다.

### 5. 내가 결정해야 할 게 있나?
필요한 공통 선행 기능과 이번 읽기 기능만 분리해서 가져온 뒤 문제를 고치는 경로를 권합니다. 다른 작업의 원문 해석·추천 기능은 포함하지 않습니다. 다른 작업의 미반영 변경을 가져오는 결정이므로 명시적인 승인이 필요합니다. 회사 확장 기준까지 이번 범위에 포함할지도 별도로 정해야 합니다.

### 6. 지금 상태는?
사람 확인 필요입니다. 코드 반입은 중단한 상태이며, 후보에 해결해야 할 검토 지적이 남아 있습니다. 기본 제품 병합이나 업무 수용 완료를 승인하지 않습니다.

## Developer Details

### Review identity and scope

- Reviewer: independent read-only reviewer, `issue11_independent_review`.
- Contract: [Issue #11](https://github.com/yungGom/Auditing_Package/issues/11), current body and [existing verification comment](https://github.com/yungGom/Auditing_Package/issues/11#issuecomment-5903094603) read through the GitHub connector.
- Main / Issue #11 worktree HEAD: `6373a333414f51015f9d1068e32ec2ef7702cbe4`.
- Investigated PR #13 candidate HEAD: `ec256e52d884e798fb880297b41be5be9648aa0c`.
- Source directory: `work/pr13-review`; implementation worktree: `work/issue11`; reviewer-generated artifacts only: `work/reviewer-only`.
- Candidate source, original tests, `.git`, protected files, accounting rules and baselines were not edited. Both worktrees returned empty `git status --short` after probes.
- Read repository/root and AuditDesk instructions, `governance/POLICY.md`, `governance/PROTECTED_ARTIFACTS.md`, `docs/harness/review_protocol.md`, relevant README and V2 recommendation scope documentation.

### Verdict

**BLOCKING — candidate cannot yet be accepted for the complete Issue #11 acceptance criteria.** Two defect categories were reproduced in three failing acceptance probes. Import is independently blocked by the user's explicit dependency stop condition until Owner Decision. No merge or business acceptance is implied.

### Findings

#### R1 — blocking — source identifiers are discarded, so duplicates have no explicit outcome

- Files: `auditdesk/auditdesk/xbrl_v2/taxonomy.py:185`, `:191`, `:202`, `:206`, `:212`, `:213`; original test input `auditdesk/tests/test_xbrl_v2_taxonomy.py:11` and `:16` includes source `id` columns.
- Evidence: Concepts records with two distinct expanded QNames in the same namespace receive the same source `id='cash'`; result remains `current_applicable=True`, `diagnostics=[]`, two records. RoleTypes rows with distinct Role URIs receive the same source `id='r'`; result remains `current_applicable=True`, `diagnostics=[]`, two roles.
- Cause: concept duplication is checked only by expanded QName; Role duplication is checked only by Role URI. Source `id` values are neither stored in their dataclasses nor checked.
- Contract: Issue #11 requires explicit outcomes for duplicate identifiers and source identity must fail closed under POLICY. Distinct generated row IDs do not explain duplicated source IDs.
- Suggested resolution: preserve supplied source identifiers, diagnose duplicates within demonstrable source identity scope, retain both records as evidence, and prevent unresolved identity from being usable as current authority. Do not guess a multi-schema identity scope absent source evidence. Add both behavioral cases. This requires no change to protected expectations or accounting judgments.
- Independent probes: `test_duplicate_concept_source_identifier_is_explicit` FAIL; `test_duplicate_role_source_identifier_is_explicit` FAIL. The conservative false-applicability expectation follows the fail-closed source identity policy; an explicit supported outcome must at minimum replace silent acceptance.

#### R2 — blocking — missing header in a later presentation section silently removes that section

- Files: `auditdesk/auditdesk/xbrl_v2/taxonomy.py:223`, `:224`, `:232`, `:253`.
- Evidence: start from fresh two-section workbook; remove only row 8, which is the second section's presentation column header. Role marker and two nonempty concept rows remain. Result drops from four occurrences to two, but `current_applicable=True`, `diagnostics=[]`.
- Cause: each LinkRole resets `h=None`; nonempty rows with no recognized header are silently skipped. The final emptiness check sees first-section occurrences and cannot detect the lost section.
- Contract: explicit outcomes for missing headers and completeness/rejection diagnostics. Silent denominator reduction can make an incomplete current candidate universe look usable.
- Suggested resolution: track each presentation section's header and data-row disposition; report absent/ambiguous section headers and retain rejection locations. Keep legitimate blank/Definition metadata rows supported. Add later-section and final-section regression cases; do not infer missing header structure.
- Independent probe: `test_every_presentation_section_requires_a_header` FAIL.

#### R3 — question / known_gap — optional current extension applicability is outside the implemented candidate

- Files: `auditdesk/auditdesk/xbrl_v2/taxonomy.py:18`, `:131`; `auditdesk/docs/XBRL_V2_RECOMMENDATION.md`, Current limitations.
- Evidence: `TaxonomyMetadata` has version/report date and source role, but no entity or connected/separate scope. `CURRENT_EXTENSION` is explicitly rejected with `NON_CURRENT_SOURCE`. Different namespace URIs within the supplied current standard workbook remain distinguishable, but that is not an extension package applicability check.
- Existing documentation explicitly declares current company extension package ingestion unimplemented, as does the original partial-capability boundary.
- Owner question: retain this as an explicit unsupported optional input for the separated slice, or require extension applicability implementation before Issue #11 can reach completion? Do not label unsupported extension ingestion as PASS. Until decided, report it as known_gap; do not claim full scope acceptance.

#### R4 — nonblocking / known_gap — blank occurrence relationship attributes remain blank

- File: `auditdesk/auditdesk/xbrl_v2/taxonomy.py:252`.
- Evidence: individually blank `arcrole` or `order` in one populated occurrence produces no diagnostic, keeps `current_applicable=True`, and stores the blank value. Parser does not manufacture relationship values. This review did not assert these probes as mandatory failures because the limited workbook preview does not claim effective network validation.
- Suggested improvement: explicit unknown relationship metadata diagnostics would help consumers; any richer structural eligibility rule must stay within the approved workbook preview scope.

### Confirmed reusable behavior and acceptance coverage

| Acceptance area | Independent evidence / limit |
| --- | --- |
| Namespace collision and expansion | Separate declared namespaces with same local name stay distinct; original code marks repeated prefix declarations ambiguous. Additional distinct-namespace probe PASS. |
| Duplicate QName / Role URI | Original code detects duplicate expanded QName and Role URI. Independent Role URI duplicate probe PASS. Raw source IDs remain R1. |
| Repeated QName / Role / path | Original repeated sections yield four distinct occurrence IDs. Same Cash QName/Role/path appears twice, both retained. Independent probe PASS. |
| Label / role / reference provenance | Resource language/role, named reference parts, snapshot/sheet/row source retained. Independent probe PASS. |
| Source bytes / dates / current-first authority | SHA-256, caller evidence, release date range and source role checks visible in code. Prior role cannot pass the current-only parser. Caller declaration consistency is not regulatory release approval. |
| Completeness / missing header | Later-section header disappearance violates AC: R2. |
| Partial dimensions | `capabilities='PARTIAL'`, `dimensions_known=False`; no DRS or no-dimension proof claimed. |
| Raw bytes → graph → query | Parser materializes immutable graph-like tuples and taxonomy tests query them; broader recommendation query integration exists only in PR #13 under #9 and depends on #12. Do not import it for this Issue without the separate authorization. This review did not run #9 integration. |
| Current extension | Unsupported role is explicitly rejected (probe PASS for safe rejection); entity/scope/period validation remains known_gap. |
| Real material | No fresh real workbook applicability or accounting verification performed by this reviewer. Existing public-workbook failure reported in #11 remains unresolved evidence, never PASS. |

### Minimal reuse boundary for Owner Decision

Direct parser imports require only `ExpandedQName` and `stable_id` from `model.py:10` and `:33`, plus package `__init__.py`. However, reusing only three modules cannot pass the existing V2 offline test as written: `auditdesk/tests/test_xbrl_v2_offline.py:17` requires at least five V2 modules. That rule must not be reduced to make the import pass.

The proposed **ten-file coherent dependency-and-taxonomy slice** is reasonable and preserves the existing core contract/test boundary:

1. `auditdesk/auditdesk/xbrl_v2/__init__.py`
2. `auditdesk/auditdesk/xbrl_v2/model.py`
3. `auditdesk/auditdesk/xbrl_v2/ports.py`
4. `auditdesk/auditdesk/xbrl_v2/provenance.py`
5. `auditdesk/auditdesk/xbrl_v2/rules.py`
6. `auditdesk/auditdesk/xbrl_v2/storage.py`
7. `auditdesk/tests/test_xbrl_v2_core.py`
8. `auditdesk/tests/test_xbrl_v2_offline.py`
9. `auditdesk/auditdesk/xbrl_v2/taxonomy.py`
10. `auditdesk/tests/test_xbrl_v2_taxonomy.py`

The first eight form the unchanged reviewed V2-1 dependency unit; the last two are Issue #11's candidate to be corrected for R1/R2 with new synthetic tests. This is larger than the direct import minimum but smaller and safer than PR #13 wholesale. It excludes `dsd.py`, `recommendation.py`, `__main__.py`, #12 DSD tests, #9 recommendation/integration tests, other unrelated PR changes and protected files. Storage is imported only by preserved core tests; the Taxonomy parser does not instantiate stores or migrate existing databases. Owner must explicitly approve this dependency reuse before implementation/import.

### Commands and results

- `python -B work/reviewer-only/probe.py` from project root, `require_escalated`: **5 PASS, 3 FAIL, 0 SKIP, exit 1**. Runtime assertions took 0.032 seconds after environment startup. Each input is fresh in-memory synthetic OOXML, not tracked data. Outputs: `probe-results.json` and this report. Three intentional acceptance failures are evidence of candidate defects, not Harness environment failures.
- Same probe initially launched in sandbox: Python location resolution failure; rerun with authorized escalation completed. No acceptance result was inferred from the failed launch.
- `python -B scripts/check_protected.py --base origin/main` from `work/issue11`, `require_escalated`: **PASS, exit 0**, `PROTECTED CHECK PASS: no protected artifact or rule definition changed`.
- `git -C work/issue11 rev-parse HEAD` / `git -C work/pr13-review rev-parse HEAD`: matched reviewed commits above.
- `git -C work/issue11 status --short` and `git -C work/pr13-review status --short`: clean.
- Original taxonomy/core/offline suite: **NOT RUN by independent reviewer**; parent implementer is separately rerunning official suite. Historical 35 taxonomy PASS and 57 prerequisite PASS in Issue comment are not this review's results.
- `scripts/test_auditdesk.py`, `scripts/test_all.py`, Node/build checks and real-file checks: **NOT RUN by independent reviewer**; parent report must state actual executed results and limitations.
- Gate baseline: unchanged. Protected check does not prove candidate AC or business acceptance.

### Remaining Owner Review boundary

Owner Decision needed on the bounded dependency import and unsupported optional extension scope. After approval: isolate import, fix R1/R2, run the new regressions plus preserved official checks and applicable full Harness, obtain independent re-review, publish updated verification evidence, and return to Owner Review. Do not merge main, mark real-material checks PASS, or declare business acceptance.
