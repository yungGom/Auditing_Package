## 한눈에 보기

### 1. 이번에 무엇을 했나?

승인하신 기존 공통 기능과 당기 공시 분류 기준 읽기 기능만 가져왔습니다. 기존 후보에서 발견한 원본 식별자 중복과 표시 구역 누락, 두 문제를 수정했습니다.

### 2. 실제로 무엇이 달라졌나?

항목과 표시 역할의 원본 식별자가 남습니다. 식별자가 겹치면 두 원본을 보존하고 문제 위치를 표시합니다. 표시 구역의 제목 행이 없으면 해당 구역과 읽지 못한 행을 명시하며, 문제가 있는 결과를 당기 적용 가능으로 확정하지 않습니다. 정상 구역과 분류·표시·참조 근거는 유지합니다.

### 3. 확인 결과는 어땠나?

관련 자동검사 아흔 건이 통과했습니다. 독립 재현 검사 여덟 건과 경계 검사 일곱 건도 통과했고, 독립 검토의 새 차단 지적은 없습니다. 보호 대상 변경 검사도 통과했습니다. 공개·합성 자료를 대상으로 한 전체 자동검사와 화면 빌드는 통과했습니다. 다만 기존 기능의 엄격한 검사는 자료 부족으로 한 건 실패하고 일흔여섯 건을 건너뛰었으며, 실제 자료 여든한 건은 자료 부족으로 확인하지 못했습니다. 전체 업무 검증 완료는 아닙니다.

### 4. 아직 남은 문제는?

실제 당기 공시자료의 출처·버전·적용 가능성과 실제 보고서 확인은 완료하지 않았습니다. 회사 확장 기준 입력과 전체 분류체계·차원 검증은 지원 범위에 포함되지 않습니다. 기존 전체 검사에 남은 실패와 자료 부족은 별도로 남습니다. 따라서 전체 기능의 검증 완료나 실제 업무 수용 완료로 표시하지 않습니다.

### 5. 내가 결정해야 할 게 있나?

있음. 승인한 두 문제의 수정 결과와 남은 검증 범위를 검토해 주세요. 이번 수정 범위를 검토 결과로 받아들이되 실제 자료 확인을 다음 단계로 남길 수 있습니다. 실제 업무 사용 가능 여부까지 판단하려면 공식 당기 자료와 적용 근거를 확보해 추가 확인해야 합니다. 기본 제품 반영과 업무 수용 승인은 별도입니다.

### 6. 지금 상태는?

**사람 확인 필요.** 승인 범위의 구현과 독립 검토를 마치고 사람 확인 단계에서 멈춥니다. 기본 제품에 병합하지 않았습니다.

## Developer Details

Report type: approved implementation / verification / Owner Review. Date: 2026-10-08 KST.
Source of Truth: [Issue #11 / XBRL-002](https://github.com/yungGom/Auditing_Package/issues/11).
Related: [#9](https://github.com/yungGom/Auditing_Package/issues/9), [#12](https://github.com/yungGom/Auditing_Package/issues/12), [source PR #13](https://github.com/yungGom/Auditing_Package/pull/13), [draft PR #33](https://github.com/yungGom/Auditing_Package/pull/33).

### Authorization, baseline and isolation

- Owner decision recorded in Issue #11: “위 10개 파일을 제한적으로 가져와 두 문제를 수정하는 범위입니다 >> 부탁해”. This resolves the dependency stop only for the ten manifest paths, unchanged eight-file V2-1 dependency unit and R1/R2 Taxonomy corrections with new synthetic regressions.
- Latest remote main: `6373a333414f51015f9d1068e32ec2ef7702cbe4`. Source candidate: PR #13 exact head `ec256e52d884e798fb880297b41be5be9648aa0c`; source PR remains unmerged. Prior docs-only commit: `77954d4de34df2b48bbbde9156471c512877ccde`.
- Dedicated branch `codex/issue11-taxonomy-audit` in an independent worktree backed by a separate clone; execution and evidence are confined to the task's `review_outputs/issue11/` area. The original dirty checkout and concurrent #12/#18 work were not edited, staged, stashed or reset.
- Reviewed Issue #11 body/comments/decision/acceptance criteria, #9/#12, PR #13 and preceding branches, root/AuditDesk AGENTS and CLAUDE, POLICY, protected inventory, README/GATES, relevant specs and Harness procedures. Existing dated investigation reports are retained, not retroactively changed to passing results.

### Existing work, reuse and actual change

| Classification | Result |
| --- | --- |
| Main before this work | Legacy Taxonomy/Harness exist; the ten V2 source/test paths are absent. No existing main V2 implementation was duplicated. |
| Unmerged source | PR #13 already implements the immutable workbook preview, current metadata/hash/version identity, expanded QName, Role/path occurrences, Label/Reference resources and explicit PARTIAL capability. Reused rather than rebuilt. |
| Approved dependency reuse | Six core modules `__init__,model,ports,provenance,rules,storage` and original core/offline tests: eight files unchanged, exact manifest SHA-256 and Git source equality verified. |
| Approved Taxonomy reuse | `taxonomy.py` corrected below; original `test_xbrl_v2_taxonomy.py` remains byte-for-byte unchanged. Nine of ten imported files remain exactly equal to the manifest source. |
| New work | One new integrity test module, 14 behavioral cases; R1/R2 production changes only in Taxonomy; updated verification and independent review evidence. |
| Explicit exclusions | #12 `dsd.py`, #9 recommendation/CLI and tests, unrelated UI/product history, protected artifacts, accounting rules, gate thresholds and legacy databases. No whole mixed commit was cherry-picked. |
| Validation still required | Real official workbook source/version/namespace/applicability; actual-report UAT. Optional extension and full DTS/effective network/DRS remain unsupported/unverified. |

Initial import verified all ten original manifest hashes before editing. Final hashes are retained in the new implementation evidence; only `taxonomy.py` differs. The source manifest and the earlier failing probe results retain their original meaning.

### R1 / R2 resolution

- **R1 — original IDs:** appended immutable `source_id` fields preserve provided Concept/Role identifiers separately from generated IDs. Collisions within each workbook record kind produce ERROR diagnostics at every conflicting original row, preserving all records and setting `current_applicable=False`. Different prefixes/namespaces are not guessed to mean separate XSD documents. Cross-kind equality is not asserted to be a full XSD uniqueness violation; this remains a workbook preview, not schema validation.
- **R2 — presentation completeness:** every explicit LinkRole section is checked when it closes, including the final empty/headerless section. A missing recognizable header gets an explicit section diagnostic; nonempty rejected rows keep source locations. Only the supported Definition metadata layout and blank rows may precede a header. Later valid sections and resource evidence survive, but the snapshot remains inapplicable when any ERROR exists. Columns are never guessed.
- Parser version changes from `dart-workbook-preview/1` to `/2`, so changed interpretation cannot silently reuse the prior snapshot identity. New optional fields have defaults; existing positional construction remains compatible.
- Valid fresh workbook still yields two Concepts, one Role, four distinct occurrence IDs, three Labels and one Reference. `capabilities=PARTIAL`, `dimensions_known=False`. Caller evidence consistency is not independent official-source or accounting approval.

### Acceptance criteria mapping

| Issue criterion | Executed evidence / limitation |
| --- | --- |
| Namespace collision, identifiers, repeated QName/Role/path, bad headers and workbook | Original 35 Taxonomy cases plus new 14 cases and independent probes. Both source-ID collision types and missing later/middle/final headers fail closed with locations. |
| Prior-as-current and applicability evidence | Original metadata/date/hash/current-role tests retained and passing; independent extension probe explicitly rejects unsupported extension. Actual official applicability NOT RUN. |
| Type/periodType/abstract, languages/roles/reference provenance, deterministic identity/order | Original graph assertions and independent evidence-preservation/replay probes pass. New source IDs and rejection locators are retained. |
| Raw workbook → graph → query | Fresh in-memory OOXML construction, parse and tuple queries in existing tests/probes; no tracked workbook fixture or accounting truth introduced. No #9 recommendation engine imported. |
| Workbook-only dimensions/full networks | PARTIAL and unknown dimensions remain explicit; no no-dimension, full DTS/DRS or effective-network PASS claimed. |

### Executed checks and baseline comparison

Runtime: Python 3.14.0, pytest 9.1.0, openpyxl 3.1.5. `PYTHONUTF8=1`; scoped tests use `PYTHONPATH=<checkout>/auditdesk`. Unique task-owned TEMP/TMP directories; approved runtime execution. Web dependencies installed from the unchanged lockfile using `npm.cmd ci --no-audit --no-fund`.

| Command / scope | Measured result |
| --- | --- |
| Before production edit: `python -B -m pytest --noconftest -p no:cacheprovider --basetemp=<unique> auditdesk/tests/test_xbrl_v2_taxonomy_integrity.py -q -rfEs --junitxml=<report>` | **13 FAIL / 1 PASS / 0 ERROR/SKIP**, 6.23s, exit 1 on the original imported parser. Failures include projection/version boundary cases, not thirteen separate product defects. |
| After fix: same pytest options with `test_xbrl_v2_taxonomy.py`, `test_xbrl_v2_taxonomy_integrity.py`, `test_xbrl_v2_core.py`, `test_xbrl_v2_offline.py` | **90 PASS / 0 FAIL/ERROR/SKIP, 38 subtests PASS**, 30.36s, exit 0. 35 original Taxonomy +14 new integrity +41 core/offline; these scopes overlap independent probes and must not be added as unique coverage. JUnit includes subtest entries. |
| Reviewer: `python -B auditdesk/docs/ISSUE11_TAXONOMY_ACCEPTANCE_PROBE.py --candidate-root . --output <report>` | **8 PASS / 0 FAIL/ERROR/SKIP**, exit 0; same earlier eight probes were 5 PASS /3 FAIL. |
| Reviewer: `python -B <reviewer>/post_fix_edges.py .` | **7 PASS / 0 FAIL/ERROR/SKIP**, exit 0, 1.109s. Supported metadata, rejected extra/leading rows, multi-namespace IDs, interleaved collisions and graph/resource preservation. |
| `python -B scripts/check_protected.py --base origin/main`; `--staged`; `git diff --cached --check` | Both protected checks and whitespace check PASS. Final publication check recorded below. No baseline or protected expectation changed. |
| `python -B scripts/test_auditdesk.py` | **FAIL / exit 1**: 229 PASS /1 FAIL /76 SKIP /0 ERROR, 1 warning, Python 96.27s. Same known-generation failure (`assert _KNOWN_GENERATIONS`, actual `[]`). Required skipped tests keep the strict result incomplete. Web TypeScript/build PASS, build exit 0. |
| `python -B scripts/test_all.py --timeout 600 --report <report>` | **Technical Gate PASS / exit 0**, 3/3 components PASS. AuditDesk approved partition: 225 PASS /0 FAIL/SKIP/NOT RUN, 81 compatibility cases deselected, pytest 34.85s/component 39.25s. Web TypeScript/build PASS, component 16.31s. DSD_FOOTING registered public samples **4/4 PASS**, component 469.65s, COMPLETED within the unchanged 600s limit. Real-material assessment **81 BLOCKED: REQUIRED MATERIAL UNAVAILABLE**, 0 PASS/FAIL/SKIP/NOT RUN. Human Business Acceptance PENDING. |
| Actual workbook applicability, real-report UAT, optional extension entity/scope/period, full DTS/DRS | NOT RUN / unsupported as applicable. No real-material PASS. Human Business Acceptance PENDING. |

Same-main baseline from the preceding investigation: strict AuditDesk 229 PASS /1 FAIL /76 SKIP, UI build PASS; full aggregate AuditDesk partition 225 PASS with 81 deselected, UI PASS, DSD_FOOTING FAIL/TIMEOUT at 602.13s, 81 real-material cases BLOCKED. The known strict failure is `dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct` with unavailable known-generation material. Final results above are fresh measurements, not copied baseline results. This run's DSD samples completed in 469.65s: no DSD code, sample, baseline or timeout was changed, and no causal claim that Taxonomy repaired that earlier timeout or Issue #18 is made. No existing skip/catalog/threshold was altered. Old PR #13 267-count history is not this main's baseline. Aggregate PASS covers only the Issue #23-approved public/synthetic Technical Gate; strict entrypoint FAIL and real-material BLOCKED remain explicit. No blanket 'all required tests passed' claim.

### Independent review and manual limits

Independent Reviewer `issue11_independent_review` inspected the approved import, Taxonomy delta, before/after logs/XML, hashes, exclusion boundaries and protected checks. Verdict: **R1 RESOLVED, R2 RESOLVED; no new blocking finding in the approved implementation slice; suitable for Owner Review**. See [implementation review](ISSUE11_TAXONOMY_IMPLEMENTATION_REVIEW.md). The reviewer independently executed 15 probes; full Harness execution belongs to the implementer and is reported separately. The eight-case acceptance probe is published and reproducible; the seven additional edge cases are local read-only reviewer evidence, described individually in that report, not an additional committed test module.

Remaining R3 known gap: current extension is explicitly rejected; entity/scope/period support is not added. Remaining R4 nonblocking limit: blank arcrole/order preserved without a separate unknown-metadata warning; no effective-network validity is claimed. No new accounting judgment or protected-file decision is requested.

No manual public workbook/report UAT occurred. A human must establish official current source/version, reporting period, namespace declarations and applicability before actual report acceptance. API/backend parsing checks do not prove UI gates or real DART editor behavior.

### Final handoff

Evidence: [measured results and hashes](ISSUE11_TAXONOMY_IMPLEMENTATION_EVIDENCE.json), [same eight post-fix probes](ISSUE11_TAXONOMY_POST_FIX_PROBE_RESULTS.json), [source import manifest](ISSUE11_TAXONOMY_REUSE_MANIFEST.json). Full local logs/XML are retained with SHA-256 digests in the published evidence; raw product logs and local paths are not published. Final staged/base protected checks and whitespace check **PASS**, exit 0. Latest implementation commit is linked in Issue #11 and draft PR #33; the report does not self-reference a commit hash that would change its own commit.

STOP at **Owner Review**. Keep Issue #11 open and PR #33 draft. No main merge, release, real-material acceptance or business-complete status. Owner Action: Verification Review. The Owner decides acceptance of this bounded correction and the next real-material verification step separately from merge/business acceptance.
