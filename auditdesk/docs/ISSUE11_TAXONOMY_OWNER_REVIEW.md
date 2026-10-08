## 한눈에 보기

### 1. 이번에 무엇을 했나?

당기 공시 분류 기준을 읽는 기존 기능이 어디에 있는지 확인하고, 기존 검사와 독립 검토를 다시 수행했습니다. 이미 만들어진 기능을 다시 만들지 않았습니다.

### 2. 실제로 무엇이 달라졌나?

제품 코드는 변경하지 않았습니다. 기존 후보에서 원본 식별자 중복을 놓치는 문제와 표시 구역을 조용히 누락하는 문제를 발견했습니다. 필요한 공통 기능만 분리해 재사용할 범위와 수정할 내용을 정리했습니다.

### 3. 확인 결과는 어땠나?

기존 분류체계 검사 35건과 공통 기능을 포함한 검사 76건은 통과했습니다. 두 수치는 서로 겹칩니다. 독립 추가 검사에서는 5건 통과, 3건 실패가 나왔습니다. 실패는 두 종류의 수정 필요사항입니다. 기존 공시 작성 도구의 엄격한 검사는 1건 실패·76건 건너뜀이 남았습니다. 별도 공개·합성 자료 검사 225건과 화면 빌드는 통과했지만, PDF 검사가 제한 시간을 넘겨 전체 결과는 실패입니다. 실제 자료 81건도 자료가 없어 확인하지 못했습니다. 따라서 이번 기능의 완료나 전체 검사 통과를 선언하지 않습니다.

### 4. 아직 남은 문제는?

기본 제품에는 이번 기능과 공통 선행 기능이 없습니다. 기존 후보는 다른 작업의 미반영 공통 코드에 의존하므로, 요청하신 중단 조건에 따라 코드 반입을 멈췄습니다. 두 문제의 수정, 당기 적용 가능성의 실제 자료 확인, 회사 확장 기준 확인이 남았습니다.

### 5. 내가 결정해야 할 게 있나?

**필요한 공통 기능과 이번 분류체계 읽기 기능만 분리해서 재사용하는 경로를 권합니다.** 총 10개 파일입니다. 이미 만든 기능을 활용하면서 동시에 진행 중인 공시 원문 해석·추천 기능을 제외할 수 있습니다. 승인 후 두 문제를 수정하고 다시 검사·독립 검토해야 합니다. 선행 공통 기능의 별도 승인·반영을 기다리는 대안도 가능하지만 작업이 지연됩니다.

이번 승인은 재사용·수정 작업 범위에 대한 결정입니다. 기본 제품 병합이나 실제 공시 업무 수용 승인은 별도로 남습니다. 회사 확장 기준 입력은 기존 제한 범위처럼 명시적으로 미지원 처리하는 경로를 권하며, 지원이 필요하면 회사·기간·연결 구분을 확인하는 계약을 먼저 정해야 합니다.

### 6. 지금 상태는?

**사람 확인 필요.** 필요한 선행 코드의 반입 결정과 발견된 문제의 수정을 남긴 채 Owner Review에서 멈춥니다.

## Developer Details

Report type: investigation / verification / human approval. Date: 2026-10-08 KST.
Source of Truth: [Issue #11 / XBRL-002](https://github.com/yungGom/Auditing_Package/issues/11). Related: [#9](https://github.com/yungGom/Auditing_Package/issues/9), [#12](https://github.com/yungGom/Auditing_Package/issues/12), [draft PR #13](https://github.com/yungGom/Auditing_Package/pull/13).

### Baseline and isolation

- Remote main checked using `git ls-remote`: `6373a333414f51015f9d1068e32ec2ef7702cbe4`, 2026-10-02 merge of PR #20.
- Original local main: `62762e5bc86e25ff5214c826b9a3634a0bdfcb90`; original checkout HEAD: `b0e83b00a3a0a5defe2ee7bea93a9f601519e2c2`. Local main is divergent and was not reset or updated. Original status command reports a work-tree configuration error; no clean-state claim is made for that checkout.
- Dedicated branch `codex/issue11-taxonomy-audit` starts at exact remote main in an independent worktree backed by a separately cloned Git repository. No shared user working files were staged, stashed, copied or edited.
- PR #13 inspected at exact `ec256e52d884e798fb880297b41be5be9648aa0c` in a separate detached review worktree. PR base is `codex/current-first-foundation` at `713d4e5a6dad431cf71d3cef48c23e448d894ed6`, not main. PR remains draft/open/unmerged. GitHub review submissions/inline threads were empty when checked; prior AI review evidence remains in the existing Issue/verification report.
- Read root/AuditDesk AGENTS and CLAUDE entrypoints, POLICY, protected inventory/manifest, README, GATES, Harness workflow/review/report/orchestrator documents. No policy, gate, expectation, accounting rule, fixture or legacy DB was changed.

### Existing implementation classification

| Classification | Evidence and scope |
| --- | --- |
| In main | Legacy taxonomy/DART/DSD features and Harness. No `auditdesk/auditdesk/xbrl_v2` or V2 task tests at this main. Legacy graph/label code is not the Issue #11 V2 parser and is not reused. |
| Existing but unmerged | PR #13 contains V2-1 core, `taxonomy.py`, 35 Taxonomy tests, #12 DSD parser and #9 recommendation/CLI. Reimplementing the parser is unnecessary. |
| Already bounded and reusable | Immutable QName/Role/occurrence/Label/Reference tuples, SHA-256 and metadata/parser identity, repeat occurrence IDs, prior-source rejection, date/evidence consistency, PARTIAL and dimensions unknown. |
| Requires real-material verification | Official source/version/applicability/namespace evidence, real workbook ambiguity, production reporting correctness, DART compatibility. Historical public-workbook structural failure is not a fresh real-material PASS. |
| Actual candidate defects | Duplicate original Concepts/RoleTypes identifiers lack outcomes; a later presentation section without a header silently disappears. |
| Unsupported optional capability | Current extension ingestion and entity/scope/period applicability; full DTS/effective network/DRS. These remain unsupported, never implied by workbook-only PASS. |

### Independent findings and failing-before evidence

Reviewer: separate read-only `issue11_independent_review`; verdict **BLOCKING**. Full report: [ISSUE11_TAXONOMY_INDEPENDENT_REVIEW.md](ISSUE11_TAXONOMY_INDEPENDENT_REVIEW.md).

- **R1 blocking:** distinct Concepts QNames with the same source `id`, and distinct Role URIs with the same source `id`, both return `current_applicable=True` with no diagnostic. Source identifiers are not retained or checked (`taxonomy.py:185-213`). Two failing probes. Proposed change: retain original IDs, diagnose collisions with source locations, preserve conflicting records, fail closed without inventing schema scope.
- **R2 blocking:** remove only the second presentation section's header from fresh OOXML; occurrences fall from 4 to 2 while `current_applicable=True` and diagnostics are empty (`taxonomy.py:223-253`). One failing probe. Proposed change: validate every section, report missing headers and rejected row locations, preserve coverage instead of guessing columns.
- **R3 known_gap/question:** `CURRENT_EXTENSION` is explicitly rejected; metadata has no entity/scope contract. Recommend keeping this optional input explicitly unsupported in the bounded slice; no extension PASS or full Issue acceptance until the boundary is confirmed.
- **R4 nonblocking:** blank arcrole/order is preserved but has no unknown-metadata diagnostic. No effective-network validation is claimed.

No production fix was applied: the user explicitly prohibits importing essential unmerged dependencies without an Owner Decision. The user's follow-up “뭐가 더 낫겠어?” requests a recommendation, not authorization. New reproducers are investigative synthetic inputs, not altered existing test truth. No passing-after evidence exists yet.

### Exact proposed reuse decision

Source for every file: PR #13 exact head above. [ISSUE11_TAXONOMY_REUSE_MANIFEST.json](ISSUE11_TAXONOMY_REUSE_MANIFEST.json) records all ten SHA-256 values and confirms absence from main.

Unchanged coherent V2-1 dependency unit (8 files):

- `auditdesk/auditdesk/xbrl_v2/{__init__,model,ports,provenance,rules,storage}.py`
- `auditdesk/tests/test_xbrl_v2_{core,offline}.py`

Issue #11 candidate (2 files, requires R1/R2 correction and additional synthetic behavioral tests):

- `auditdesk/auditdesk/xbrl_v2/taxonomy.py`
- `auditdesk/tests/test_xbrl_v2_taxonomy.py`

The direct import needs only `ExpandedQName` and `stable_id` from model plus package initialization. The coherent eight-file dependency unit preserves the existing core/offline regression contracts; the offline test requires at least five modules. Do not lower that criterion. Taxonomy parsing never instantiates stores or migrates legacy DBs.

Excluded: `dsd.py`, `recommendation.py`, V2 CLI, #12/#9 tests, earlier product/SQLite/UI history and protected paths. Do not cherry-pick the mixed PR #13 implementation commit wholesale. Import only the manifest paths after explicit approval, verify the eight dependency hashes, then make Issue #11 changes. Source PR #13 and other sessions remain unchanged.

### Executed checks

Runtime: Python 3.14.0, pytest 9.1.0, openpyxl 3.1.5. Unique temporary directories; existing `npm ci` lockfile used only inside isolated main worktree. Commands below are run with `PYTHONUTF8=1`; scoped PR #13 tests use its `auditdesk` directory as PYTHONPATH. Execution startup restrictions were retried with authorized escalation; failed/incomplete launches are not PASS evidence.

| Command and checkout | Result |
| --- | --- |
| Main: `python -B scripts/check_protected.py --base origin/main` and `python -B scripts/check_protected.py --staged` | PASS for the staged five-file documentation/reproducer delta; initial same-main PASS also retained. `git diff --cached --check` PASS. No protected/product files changed. |
| PR #13 candidate: `python -B -m pytest --noconftest -p no:cacheprovider --basetemp=<unique> tests/test_xbrl_v2_taxonomy.py -q -rfEs` | 35 PASS, 0 FAIL/SKIP, 15.85s. |
| PR #13 candidate: same command with `tests/test_xbrl_v2_taxonomy.py tests/test_xbrl_v2_core.py tests/test_xbrl_v2_offline.py --junitxml=<report>` | 76 PASS, 69 subtests PASS, 0 FAIL/SKIP, 65.18s. Includes the above 35; do not add them together. |
| Independent synthetic acceptance probe | 5 PASS, 3 FAIL, 0 SKIP; R1/R2 reproduced. These additional failures block Issue completion despite original suite PASS. |
| Initial sandbox run of original combined suite | 36 PASS, 40 FAIL, 40 teardown ERROR, 64 subtests PASS, 499.77s; temporary-directory access denied. Same unchanged tests rerun with authorized runtime access yielded the 76 PASS above. This failed environment attempt is retained and is not candidate acceptance evidence. |
| Main: `python -B scripts/test_auditdesk.py` | FAIL, exit 1: 229 PASS, 1 FAIL, 76 SKIP; Python 206.28s. Web UI build PASS. Failure: `dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct`, missing known-generation materials. |
| Main: `python -B scripts/test_all.py --timeout 600 --report <report>` | FAIL, exit 1. Approved AuditDesk Technical partition: 225 PASS/0 FAIL/SKIP/NOT RUN, 81 deselected for separate compatibility assessment; pytest 74.85s, component 84.0s. Web build PASS, component 30.27s. DSD_FOOTING component FAIL/TIMEOUT, 602.13s against existing 600s bound. Actual-material assessment: 81 BLOCKED: REQUIRED MATERIAL UNAVAILABLE, 0 PASS/FAIL/SKIP/NOT RUN. Business acceptance PENDING. |
| PR #13: `python -B scripts/check_protected.py --base origin/main`, entire historical stack | FAIL, exit 1, 8 inherited protected/control differences: `.github/workflows/harness.yml`, `governance/POLICY.md`, `scripts/test_all.py`, `DSD_footing/CLAUDE.md`, `DSD_footing/ERRORS.json`, `DSD_footing/GATES.json`, and the two Chosun Refractories interim PDFs. These are not proposed for import and were not edited. The earlier historical report's five differences used an older main; do not reuse that count for today's comparison. |
| Actual workbook applicability, extension, DTS/DRS, real-report UAT | NOT RUN; no input acceptance or real-material PASS claimed. |

The old 267/1/76 record belongs to the earlier PR #13 product foundation, not this main. Current main baseline has 229/1/76 in the strict entrypoint. No product implementation changed in this run, so there is no before/after fix regression claim. Issue #23's public/synthetic Technical Gate remains distinct from the strict all-material entrypoint and real-material compatibility.

The aggregate's timed-out DSD component records `exit_code=0` but `status=FAIL` and `reason=TIMEOUT`; those explicit status/reason fields control the result. Do not promote the exit field to PASS. This is an observed baseline execution limit, not a reproduced Issue #11 product regression. No PDF baseline, exception, timeout criterion or unrelated Issue #18 code was changed, and no DSD sample count is claimed passed for the incomplete aggregate.

Final documentation handoff review: the independent Reviewer checked the five staged report/reproducer files, ten source hashes and exclusions. Its publication conditions (measured aggregate result, final protected result, public-path cleanup and strict-suite scope wording) are addressed here. Final independent document verdict: READY FOR OWNER REVIEW, no remaining document blocker; final main/staged protected checks both PASS. Candidate verdict remains BLOCKING on R1/R2. The report is an Owner Decision package, not completion of implementation.

The published reproducer [ISSUE11_TAXONOMY_ACCEPTANCE_PROBE.py](ISSUE11_TAXONOMY_ACCEPTANCE_PROBE.py) accepts an explicit `--candidate-root <repository root>` and optional `--output <json>`; it reads the candidate's unchanged original synthetic workbook helper. It generates OOXML in memory and does not extract files or access the network. Run with `python -B ... --candidate-root <PR13 checkout> --output <local result>`. The generalized script independently reconfirmed 5 PASS / 3 FAIL / 0 ERROR/SKIP. [ISSUE11_TAXONOMY_PROBE_RESULTS.json](ISSUE11_TAXONOMY_PROBE_RESULTS.json) retains the observed candidate outcomes, including the silent 4-to-2 occurrence reduction.

### Owner Review and next action

Status: **Awaiting Owner Approval / Owner Review**; Owner Action: **Decision Required**. Issue stays open; no main merge, release or business acceptance.

Recommended decision: authorize only the ten listed files and new Issue #11 synthetic regressions, keep the eight V2-1 dependency files unchanged, fix R1/R2 in Taxonomy, keep optional extension explicitly unsupported, execute all Issue-required checks, independent re-review, and return to Owner Review again. Alternative: approve/integrate V2-1 separately first, then resume #11. No protected artifact change is proposed or authorized by this decision.
