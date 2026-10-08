## 한눈에 보기

### 1. 이번에 무엇을 했나?
당기 공시 원문을 읽는 기능을 별도로 검토했습니다. 원문 보존, 표와 주석의 연결, 빈칸과 부호, 불명확한 정보의 처리 방식을 확인했습니다.

### 2. 실제로 무엇이 달라졌나?
병합된 한 셀이 덮는 서로 다른 열에 같은 번호가 생기는 문제를 고쳤습니다. 주석 구역이 중첩되면 같은 원문을 두 주석으로 확정하지 않고 미확인으로 남깁니다. 표 제목처럼 보이는 문맥도 확정 제목으로 취급하지 않도록 표시했습니다. 주석·인용 안에서 XML 선언처럼 보이는 글자도 원문으로 보존하도록 경계 처리를 추가 확인했습니다.

### 3. 확인 결과는 어땠나?
최종 합성 자료 검사와 보호 자료 검사는 통과했습니다. 발견한 두 차단 문제도 수정 후 별도 검사에서 해결됐습니다. 저장소 전체 검사는 시간 초과로 실패했고, 엄격 검사는 실제 자료 부족에 따른 실패와 건너뜀이 남았습니다. 전체 검증이나 업무 수용이 끝난 상태는 아닙니다.

### 4. 아직 남은 문제는?
실제 자료 확인과 추천 기능 연결이 남았습니다. 이어진 표·전치된 표의 의미, 단위 환산, 실제 기간 길이는 확정하지 않습니다. 전체 검사의 시간 초과와 자료 부족 문제도 해결되지 않았습니다. 변경 전 기본 코드에서도 같은 전체 검사 결과를 독립적으로 확인했습니다.

### 5. 내가 결정해야 할 게 있나?
있음. 제한된 원문 해석 결과를 검토한 뒤 실제 공시자료 확인과 상위 추천 기능 연결의 진행을 판단해 주세요. 병합이나 실제 업무 수용은 별도 승인 사항입니다. 보호 자료나 회계 기준 변경 승인을 요청하는 내용은 없습니다.

### 6. 지금 상태는?
사람 확인 필요.

## Developer Details

Report type: independent read-only reviewer.
Reviewer: /root/issue12_reviewer; implementation: /root.
Issue: https://github.com/yungGom/Auditing_Package/issues/12, body and visible comments fetched independently on 2026-10-08.
Worktree: work/issue12; branch codex/issue12-dsd-semantic; reviewed main base 6373a333414f51015f9d1068e32ec2ef7702cbe4.
Implementation commit finally reviewed: 62cbd13298200e8df6f5c9342e022954c2086ce1.

### Verdict

Scoped technical review PASS after fixes. No unresolved blocking finding in the reviewed synthetic DSD contract. Repository-wide Technical Gate is FAIL/incomplete as detailed below; this report does not approve that gate. This is not full production compatibility, accounting approval, integration approval, merge permission, or Human Business Acceptance. The reviewer changed no product files, posted no Issue/PR comments and performed no merge.

### Contract and reuse

Read root/project AGENTS.md, governance/POLICY.md, governance/PROTECTED_ARTIFACTS.md, root/project CLAUDE.md, auditdesk/README.md, GATES.json, relevant DSD pipeline specification, docs/harness/review_protocol.md and report_template.md. Reviewed new source, tests, XBRL_DSD_INPUT.md and staged 13-file inventory.

Independent SHA-256 comparison against ec256e52 verified all 9 entries in `.task-evidence/reuse.json`: six V2-1 modules and core/offline/DSD tests. This includes the 8-file common V2-1 copy plus the prior DSD test. `dsd.py` is intentionally modified and versioned `bounded-dsd-v2`; the additional projection is `issue12-structure-v1`. No taxonomy or recommendation implementation is imported. Existing model/ports are unchanged from PR #13; no dependence on unmerged Issue #11 implementation was found.

Existing legacy scanner/grid work remains untouched. The change reuses the PR #13 bounded raw parser and adds a separate projection; no repack, original DSD, legacy DB, thresholds or existing protected test expectations changed.

### Findings and resolutions

| ID | Severity | Evidence | Resolution |
| --- | --- | --- | --- |
| B1 | blocking, resolved | A table with one `TD COLSPAN="2"` produced two COLUMN subjects with the same ID because identity used only kind/raw spans. `probe-initial.json`: 1 FAIL/8 PASS. | ID now includes parent and index as well as spans. Added regression; independent final probe confirms distinct IDs while both columns retain the same physical cell anchor. |
| B2 | blocking, resolved | Two nested SECTION elements titled `주석` produced two semantic notes from one marked heading at offset 66, without a note ambiguity diagnostic. `probe-nested-red.json`: 1 FAIL/9 PASS. | Overlapping explicit note scopes retain physical sections/blocks but do not assert semantic notes; `UNKNOWN:nested_note_scopes` is returned. Added regression; independent final probe passes. |
| N1 | nonblocking, addressed | `table.title`/`table_title` are the latest preceding TITLE context, which may be a section title; pipeline specification states actual statement titles can appear in TD tables. | Documented this limit and added `UNKNOWN:table_title_semantics:*` per table. The #9 consumer must not treat the field as an approved table meaning. |
| B3 | implementer-found post-review regression, resolved | Broad declaration validation rejected literal `<?xml version="2.0"?>` inside comments/CDATA. Implementer `.task-evidence/declaration-literal-red.log` records 2 FAIL before the fix. | Only a genuine initial XML prolog is validated/rewritten. Expat validates misplaced or incomplete declarations. Independent checks verify literals and offsets, retained processing instructions, and continued rejection of 9 invalid actual-declaration cases. |

No unresolved accounting-meaning question was used to invent a value. Missing evidence stays None/UNKNOWN, and conflicting requested metadata cannot hide source evidence.

### Independent checks

Commands below ran with system Python 3.14. `PYTHONDONTWRITEBYTECODE=1`; test temp/cache outputs were directed to the reviewer folder. The checks used synthetic raw ZIP bytes only.

- `python reviewer_probe.py` — initial B1 reproduction: 8 PASS/1 FAIL; after B1 and newly added B2 probe: 9 PASS/1 FAIL; original final: 10 PASS/0 FAIL; post-declaration re-review: 13 PASS/0 FAIL. Evidence: `probe-initial.json`, `probe-nested-red.json`, `probe-final.json`, `probe-declaration-final.json`.
- From auditdesk: `python -m pytest tests/test_xbrl_v2_core.py tests/test_xbrl_v2_offline.py tests/test_xbrl_v2_dsd.py tests/test_xbrl_v2_dsd_structure.py -q -p no:cacheprovider --basetemp <reviewer-folder>/pytest-declaration-final-tmp` — post-declaration final: 85 passed, 45 subtests passed, 0 FAIL/SKIP in 41.15s (`scoped-declaration-final-independent.log`). Original final before the 2 added literal tests: 83 passed, 45 subtests passed, 0 FAIL/SKIP (`scoped-final-independent.log`).
- `python scripts/check_protected.py --base origin/main --staged` — PASS after 13 product/document/test files were staged, repeated PASS with the final declaration delta staged. Evidence: `protected-staged-final.log`, `protected-declaration-staged-final.log`. Earlier unstaged check also passed; final staged checks supersede its limited untracked view.
- `git diff --cached --check` — PASS, no output.
- SHA-256 read comparison of reused files versus `git show ec256e52:<path>` — 9/9 identical. Evidence: `reuse-independent.json`.

Independent probes checked raw spans after `&cr;`, literal escaped entities and multibyte text; blank/nil/sign/scale preservation; source hashes and input immutability; requested versus observed conflicts; repeated-table locality; nested-table rejection; merged-column identity; and missing declarations remaining unknown.

Implementation evidence also reviewed: `.task-evidence/structure-raw-red.log` records 10 failed/8 passed before the initial fixes; `.task-evidence/scoped.log` records the earlier 81-pass scope. These earlier failures are reproduction evidence, not final failures concealed as PASS.

### Required repository checks, implementer execution independently read

- `python scripts/test_all.py` aggregate, `.task-evidence/baseline-all.json` and `.task-evidence/baseline-fixed-all.json`: `technical_gate=FAIL`; selected AuditDesk Python 225 PASS/0 FAIL/0 SKIP, web build PASS, DSD_FOOTING FAIL with reason TIMEOUT. Implementation reports its 600-second deadline was reached after the first sample's 24 metrics passed; incomplete remaining samples are not PASS. This is a repository-wide acceptance blocker, not a failure in the new 85-test scoped parser check.
- Same aggregate: `real_material_compatibility.status=BLOCKED: REQUIRED MATERIAL UNAVAILABLE`, 81 blocked, 0 PASS; `human_business_acceptance=PENDING`.
- `python scripts/test_auditdesk.py`, `.task-evidence/final-fixed-auditdesk.log`: FAIL, 229 passed / 1 failed / 76 skipped, web build PASS. `test_version_check.py::test_g2_smoke_direct` fails on `assert _KNOWN_GENERATIONS` because the required real DSD-generation list is empty. Required skips remain incomplete checks; they are not reclassified as PASS.
- Clean-main comparison is complete. Reviewer independently read `work/main-baseline/.task-evidence/all.json` and `auditdesk.log` and compared them to task `baseline-fixed-all.json` and `final-fixed-auditdesk.log`. Technical status/reason/counts/selected node checks and the entire real-material compatibility section are equal. Strict counts, failure ID and web result also match: 229 PASS/1 FAIL/76 SKIP, same `test_g2_smoke_direct` failure, web PASS. DSD_FOOTING elapsed 600.72s for task and 602.0s for clean main; both FAIL/TIMEOUT. Evidence: `main-comparison-independent.json`. No new selected-suite regression was observed; incomplete PDF checks still cannot establish complete PDF equivalence. No protected expectations or timeout/gate classifications were changed to hide these results.
- Reviewed `auditdesk/docs/XBRL_DSD_VERIFICATION.md`: scoped counts/limits and whole-suite FAIL/BLOCKED status agree with source evidence. The report's exact FAIL/SKIP list contains 77 entries and matches the detailed task JUnit node IDs (1 FAIL/76 SKIP). No scope/count correction requested. A separate CP949 ZIP text/locator spot check also passed (`supplementary-cp949.log`); this supplements the fixed 13-probe count and does not add to the reported 85-test suite.

### Remaining risks and scope

Supported synthetic structures are explicit SECTION-N sections, marked numbered note headings, P/TITLE blocks, physical TABLE/TR/TD/TH/TE/TU grids with ROWSPAN/COLSPAN anchors, empty cells/paragraphs/notes, outside text and classified/unclassified provenance. Column spans can be disjoint; ROW/COLUMN cell_ids reference original anchors rather than duplicate numeric facts.

Units, scale and 3-month/YTD extent remain source clues. Numeric strings are not converted or filled with zero. Comparative columns retain CURRENT/PRIOR role when explicitly identifiable but remain part of CURRENT_DSD source. Raw ZIP identity, parser profile and character locators bind the output; relocation changes only logical_uri.

Nested/malformed unsupported tables are rejected explicitly. Ragged grids, continuation/transposition and title semantics remain diagnostic. Marker-less/fused or nested note boundaries remain unknown. Real DSD compatibility, editor generations, performance at production limits, actual accounting interpretation and #9/#11 integration were NOT RUN by the reviewer.

The legacy whole-suite harness does not automatically include the new auditdesk/tests directory, so the separate scoped invocation is required evidence. Do not infer that an unchanged aggregate passed these new tests. Baselines and protected truth are unchanged.

### Owner Review handoff

Owner should review the limited read-only ingestion contract, select authorized/public real-file compatibility material if that next step is wanted, and decide whether to proceed with #9's separately tested adapter. Consumers must honor UNKNOWN/CONFLICT and avoid double-counting BLOCK/COLUMN structures as facts. A common-interface change would require the parallel-session dependency and Owner Decision described in the Issue. Stop at Owner Review; no main merge or business-acceptance completion is authorized.
