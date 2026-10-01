# Issue #23 검증보고서

## 한눈에 보기

### 1. 이번에 무엇을 했나?
자료가 없어도 반복할 수 있는 검사와 실제 자료로 확인해야 하는 검사를 나눴습니다. 너무 오래 걸리는 검사도 중단하도록 보완했습니다.
### 2. 실제로 무엇이 달라졌나?
새 작업환경에서 기본 검사를 실행할 수 있습니다. 실제 자료 확인이 끝나지 않은 부분은 따로 표시합니다.
### 3. 확인 결과는 어땠나?
반복 검사와 보호 기준 확인, 독립 검토가 통과했습니다. 새 작업환경과 온라인 검사에서도 같은 결과를 확인했습니다.
### 4. 아직 남은 문제는?
실제 자료가 필요한 확인은 완료되지 않았습니다. 선행 변경에도 이번 보완을 반영해야 합니다.
### 5. 내가 결정해야 할 게 있나?
있음. 이번 운영 결과를 확인하고 수용할지 판단해야 합니다. 실제 자료로 확인하지 않은 기능까지 승인한 것으로 취급하지 않습니다.
### 6. 지금 상태는?
완료 후보. 실제 자료 확인과 최종 업무 수용은 남아 있습니다.

## Developer Details

### Contract / scope

Source of Truth: [Issue #23](https://github.com/yungGom/Auditing_Package/issues/23), [Owner Decision](https://github.com/yungGom/Auditing_Package/issues/23#issuecomment-5923919699). Implementation: draft [PR #24](https://github.com/yungGom/Auditing_Package/pull/24), branch `codex/harness-v1-closeout`, code commit `b3889d24311ee375331947b61670763d23411c52`; parent closeout baseline `e1bf714c736926f78f1aadf0423651e9a984f8ab`.

No AuditDesk/DSD_FOOTING business code, existing product test files/expectations, GATES, golden, fixtures, protected checker policy or accounting rules changed. No customer/private input imported. The Pilot synthetic generator/test was not copied or changed. There is no merge, branch-protection change, new routing layer or Project automation.

### Before / after

Before: clean full AuditDesk suite had 221 PASS / 1 FAIL / 84 SKIP; unavailable real-generation files failed `test_g2_smoke_direct`. Full `test_all.py` returned 1. All tests were required in one undifferentiated gate, with no child timeout or structured NOT RUN report.

After: explicitly reviewed 80 material-dependent selectors are separately assessed, not executed by the Technical Gate (81 collected cases in a clean checkout). Four existing pure numeric tests previously inherited a material availability mark; the Technical wrapper removes only that inherited module mark for those exact four tests and retains their original assertions and any own/new marks. They join the 221 runnable tests, yielding 225. All other new tests enter the Technical Gate by default. Missing/renamed catalog selectors, collection errors, unexpected Technical SKIP, NOT RUN or missing/inconsistent evidence fail closed.

The new aggregate executes existing public/synthetic tests, locked Web UI build and four registered public DSD_FOOTING sample comparisons. Default exit 0 means only scoped Technical PASS. Missing real material is `BLOCKED: REQUIRED MATERIAL UNAVAILABLE`; available/unassessed and unexecuted material checks remain `NOT RUN`. Actual-material PASS is never synthesized. The existing strict `scripts/test_auditdesk.py` remains available unchanged in semantics, still treating missing/failed/skipped required real checks as incomplete.

No boolean authorization flag executes arbitrary local material. `auditdesk_partition.py --mode compatibility` is assessment only, returns 2 for incomplete compatibility, and does not run the actual tests. Actual public files require separately verified source/use-rights/path/SHA and a controlled execution of the existing strict suite. Discovery in the existing real-generation tests is untouched. Future compatibility-catalog classification changes require a new Owner Decision and independent review.

### Timeout / evidence

Each official check defaults to 600 seconds, with a finite positive timeout required. Windows children are created suspended, assigned to a kill-on-close Job Object, then resumed. Closing the Job terminates descendants even after normal root exit; setup failure does not run an uncontained child. POSIX uses process groups. TIMEOUT is FAIL; failed cleanup is `CLEANUP_FAILED`, never success. Other official checks continue and aggregate each outcome. Missing executables/dependencies are NOT RUN, blocking the selected Technical Gate. Unselected projects are explicitly NOT RUN.

JSON preserves check IDs, statuses, counts and non-sensitive diagnostics (material category, reason, exit code, duration). Pytest parameter labels become opaque case numbers; raw parameter paths, credentials and file content are not retained. UTF-8 report and ASCII-escaped console JSON have the same meaning. Console process feedback escapes unencodable characters instead of discarding them. Safe JSON evidence is uploaded to CI; missing setup/cancelled execution has no PASS evidence. Existing child stdout is console feedback, not persisted raw JSON evidence.

Orchestrator rejects missing/invalid structured `test_all.py` evidence even with exit 0, forwards compatibility gaps to its independent Reviewer, detects disappearing compatibility rows as regressions, and retains `TASK_PASS_WITH_KNOWN_GAPS` / exit 2 / pending business acceptance. Existing DONE, FAILED and HUMAN_APPROVAL tests remain. No Issue #5 live-run was performed in this task.

### Verification evidence

- `python -B -m unittest discover -s scripts/tests -q`: 117 PASS after final missing-material tests. Windows timeout descendant, cleanup failure, unavailable tool, malformed/missing evidence, catalogue deletion, pure-test inclusion, privacy, CP949 and Orchestrator known-gap regressions included.
- `python -B scripts/check_protected.py --base origin/main`: PASS on implementation and Reviewer fixes. No allowlist/protection relaxation.
- Local fresh detached tracked-only checkout, locked `npm ci --no-audit --no-fund`, isolated new pytest basetemp. No legacy untracked caches or actual DSD added.
- Code `894a343`: local clean `python -B scripts/test_all.py --timeout 600 --report ../issue23-clean-final-report.json` PASS / exit 0; AuditDesk225PASS/0FAIL/0SKIP, WebPASS, DSD4/4PASS. Compatibility80BLOCKED/1NOTRUN; the single NOTRUN was a runtime-only scaffold fixture availability check, corrected with repository-relative prerequisite existence checks in `b3889d2`.
- `894a343` [PR CI 36816407325](https://github.com/yungGom/Auditing_Package/actions/runs/36816407325) and [push CI 36816404028](https://github.com/yungGom/Auditing_Package/actions/runs/36816404028): both SUCCESS, protected and regression SUCCESS. CI artifact confirmed225PASS, all3Technical componentsPASS, DSD4/4PASS, compatibility80BLOCKED/1NOTRUN, HumanAcceptancePENDING.
- Final `b3889d2` [PR CI 36817159632](https://github.com/yungGom/Auditing_Package/actions/runs/36817159632) and [push CI 36817153909](https://github.com/yungGom/Auditing_Package/actions/runs/36817153909): both SUCCESS; protected/regression SUCCESS. Artifact confirms AuditDesk225PASS/0FAIL/0SKIP, WebPASS, DSD4/4PASS, real-material81BLOCKED/0PASS/0NOTRUN, business acceptance PENDING. CI unit117PASS. Latest local fresh full execution on `b3889d2`: `python -B scripts/test_all.py --timeout 600 --report ../issue23-clean-final-v3.json`, exit 0; AuditDesk225PASS/0FAIL/0SKIP, WebPASS, DSD4/4PASS, real-material81BLOCKED/0PASS/0NOTRUN. Separate `python -B ../scripts/auditdesk_partition.py --mode compatibility --report ../../issue23-clean-compatibility-v3.json` from clean `auditdesk/`: 306 deselected, real-material81BLOCKED, exit 2 (incomplete, not PASS).
- Markdown relative links / changed paths / `git diff --check`: PASS. Changed paths are Harness scripts/tests/workflow/policy/docs only. No new Mermaid diagram in this implementation.

### Independent Reviewer

Read-only review found and corrected: four pure calculation tests incorrectly classified as material-dependent; raw parameter IDs leaking paths; boolean public-material authorization unable to prove provenance; unreliable descendant cleanup; missing/malformed evidence falsely allowing completion; compatibility row disappearance. Final implementation review: PASS, blocking0. Last scaffold availability follow-up was independently checked against the existing fixture source and `b3889d2` diff: PASS, blocking0. Final report independently reviewed after local/CI completion: PASS, blocking0; two clarity corrections applied. Evidence above is observed, not inferred. Known gaps and nonblocking risk remain below.

### PR readiness re-evaluation

| PR | Actual HEAD / base | Checks on that HEAD | Current readiness |
| --- | --- | --- | --- |
| #4 | `0d3351f` / main | protected SUCCESS, regression FAILURE; draft, MERGEABLE | BLOCKED |
| #6 | `cfb01bd` / docs/ai-development-harness-v1 | protected SUCCESS, regression FAILURE; draft, MERGEABLE | BLOCKED — #4 dependency and approved gate absent |
| #20 | `08e53b6` / feat/orchestrator-mvp | protected SUCCESS, regression FAILURE; draft, MERGEABLE | BLOCKED — #6 dependency and approved gate absent |

A green successor PR #24 does not clear predecessors. Safe next path: review the minimal approved gate backport to #4, forward-sync #6/#20 without forced conflict resolution, rerun each head's protected/regression checks and independent review, then Owner decides acceptance/draft removal/merge in order #4→#6→#20. Actual upstream branches were not silently rewritten or merged here. Main required checks cannot be claimed configured before workflow deployment and actual success.

### Remaining risks / Human Business Acceptance

Actual DSD generations/editor/live-receipt/taxonomy/cache compatibility are not verified without the required approved public material. Synthetic/public Technical PASS is not that compatibility or accounting/business acceptance. New compatibility-catalog automatic checker registration is not yet present; it relies on explicit POLICY Owner Decision and independent review. Changing the protected checker manifest requires a separate exact-diff Owner decision; it was not edited here.

Owner action: review this implementation's scoped operating result; separately decide/prepare the required authorized public-material compatibility scope; approve the integration path for predecessor PRs. Missing real-material evidence cannot support final acceptance of changes requiring it.
