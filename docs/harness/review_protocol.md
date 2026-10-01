# Review and result protocol

The reviewer should be independent of the implementation pass when practical. Review the task contract and changed diff, then check:

1. Acceptance examples and a failing-before/passing-after reproduction for bugs.
2. Source identity, period, unit, sign, rounding, unmatched values, and visible exceptions where relevant.
3. Offline and data-handling boundaries; no client material in prompts, logs, fixtures, or commits.
4. Tests that actually ran, their scope and results, skipped/manual checks, and any baseline changes. A missing test, skipped required test, or comparison bypass is a blocker, not a pass.
5. `scripts/check_protected.py` result and whether any protected path, expected test value, exception, or threshold changed. If so, stop the Implementer work and request the Human Owner's before/after decision.
6. Unrelated work and existing product behavior preserved.

Mark findings `blocking`, `nonblocking`, or `question`, with file, evidence, and suggested resolution. The implementer resolves blocking findings; the reviewer checks the fix and rerun evidence. An unresolved question about accounting meaning goes to the domain owner.

## Final report format

Use `report_template.md` for Reviewer findings, Human Approval requests, UAT results, intermediate updates, and final handoffs. The six-question Korean summary must come first; it must disclose failures and outstanding decisions without requiring the owner to read the technical section. Preserve the full evidence below it:

```text
## 한눈에 보기
### 1. 이번에 무엇을 했나?
### 2. 실제로 무엇이 달라졌나?
### 3. 확인 결과는 어땠나?
### 4. 아직 남은 문제는?
### 5. 내가 결정해야 할 게 있나?
### 6. 지금 상태는?

## Developer Details
Goal / root cause:
Changed behavior and files:
Reproduction or acceptance examples:
Tests: exact command — PASS/FAIL/NOT RUN; count and key result
Gate baseline: unchanged / changed with approved reason / not applicable
Protected artifact check: exact command and PASS/FAIL
Review: reviewer, findings, fixes, remaining blockers
Manual checks: completed / pending and who must perform them
Remaining risks and known exceptions:
Business acceptance needed: explicit decision or none
```

For a Reviewer result, include the verdict and each finding's severity and evidence in Developer Details. For UAT, include the operator, scenario, expected and observed result, and untested steps. For Human Approval, put the decision and plain-language options with tradeoffs in question 5, then record exact protected before/after and gate impact in Developer Details. Do not call an unfinished or unrun check complete.

Technical PASS means the stated automated checks passed. Business acceptance remains a human decision. Never say “all tests passed” when a required suite was not run.
