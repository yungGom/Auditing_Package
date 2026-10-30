# Shared AI development policy (v1.1)

This is the common governance source for Codex, Claude Code, and human contributors. Project-specific domain rules in existing `CLAUDE.md`, specs, and gate ledgers still apply. Do not weaken them to satisfy a check. If instructions conflict, stop the affected change and ask the Human Owner.

## Work contract

1. Start from a GitHub Issue. Record the problem, business rule and owner, acceptance criteria, reproduction, affected protected artifacts, required tests, and human decision. The Issue is the task source of truth; chat can clarify it but must not silently replace it.
   An agent session is a temporary execution context, not the task identity. Use the Issue for decisions, progress and detailed evidence. A GitHub Project may summarize current status, owner action and next action, but must point back to the Issue; do not treat a Project draft item or session title as a replacement contract. Give each Request ID only after checking existing Project items for duplicates, then never reuse or change it.
   Put a Human-readable Summary in Korean before Developer Details in every Issue. The Human Owner must be able to understand the current problem, business impact, solution direction, decisions they need to make, observable success criteria, and current status in 30 seconds without reading Developer Details. Use short sentences and plain Korean; explain the business consequence before implementation. Keep branch, PR, push, fixture, regression, baseline, snapshot, atomic publish, golden, orchestrator, Technical PASS, code names, function names, and file names in Developer Details by default. Retain the complete technical contract and verification requirements there, consistent with the summary. Use plain status labels such as 준비 중, 개발 중, 테스트 중, 사람 확인 필요, 완료 후보, and 완료.
2. Inspect relevant code, current branch, uncommitted work, existing instructions, and gate baselines. Preserve unrelated work and product behavior.
3. For a bug, first reproduce it with the smallest meaningful failing test or gate case. For a feature, add behavioral tests for its acceptance criteria. Implement the smallest change that meets the contract.
4. Fail closed on source identity, period, unit, sign, missing input, ambiguous mapping, and data export. Never convert unknown or unmatched data to zero or silently mark it verified.
5. Treat the inventory in `governance/PROTECTED_ARTIFACTS.md` as read-only. If a protected artifact or accounting rule must change, STOP before editing. Report the reason, expected impact, exact before/after, and evidence to the Human Owner. Approval is a separate decision; an Implementer does not update the baseline to turn a failure green.
6. Run the applicable project tests and full regression via `python scripts/test_all.py` for shared changes. Run `python scripts/check_protected.py --base origin/main`. A missing dependency, missing fixture, failed gate, skipped required test, or unrun check is not a Technical PASS.
   Under the explicit [Issue #23 Owner Decision](https://github.com/yungGom/Auditing_Package/issues/23#issuecomment-5923919699), the default aggregate reports the reproducible public/synthetic Technical Gate separately from real-material compatibility. PASS applies only to the stated executed scope; missing compatibility material is BLOCKED: REQUIRED MATERIAL UNAVAILABLE, available but unexecuted checks are NOT RUN. Do not infer real-file compatibility or Human Business Acceptance from a Technical Gate PASS. The explicit compatibility catalog and its four pure-test marker overrides define the Owner-approved scope; changing that classification requires a new explicit Owner Decision and independent review, never moving a newly failing test out of the Technical Gate. Automatic protected-check registration for this new catalog is a separate exact-diff Owner decision; no checker allowlist is widened here. Existing product expectations/protected truth stay unchanged; unexpected skips, collection errors or unrun technical checks block that gate.
7. Have a reviewer inspect the diff and evidence independently. Resolve blocking findings, rerun affected and full applicable checks, and repeat review. Return the result to the Human Owner for business acceptance. Technical results do not approve accounting treatment, merge, deployment, or release.

## Issue Title Rule

- 새 Issue 제목은 `[프로그램명] 쉽고 직관적인 업무 내용` 형식의 한국어로 작성합니다. 프로그램명은 Master Dashboard의 Project 분류와 맞춥니다.
- 업무 담당자가 제목만 보고 문제, 원하는 변화 또는 확인할 일을 이해할 수 있게 씁니다. 개발 용어는 쉬운 업무 표현으로 풀고, 작업 범위와 완료 여부를 과장하지 않습니다.
- 세부 개발 코드, TC 번호, Request ID, 버전 표기, 선행 Issue 번호는 제목에 넣지 않습니다. 해당 식별자와 의존 관계는 본문의 Developer Details 또는 관련 기록에 보존합니다.
- 기존 Issue의 제목을 정리할 때는 Issue 번호·URL·본문·연결 관계와 Project 분류·상태를 유지합니다. 같은 작업을 새 Issue로 다시 만들지 않습니다.
- 예: `[AuditDesk] 다른 작업의 XBRL 결과가 섞이지 않도록 수정`.
- 제목 작성 규칙의 기준 위치는 이 절입니다. 다른 문서나 템플릿에는 규칙을 복제하지 말고 필요 시 이 절을 참조합니다.

## Data and result reporting

- Every interim and final Harness report starts with the six-question Korean `## 한눈에 보기` from `docs/harness/report_template.md`: work done, actual change, check result, remaining problems, Human Owner decision, and plain-language status. This applies to implementation, verification, root-cause, UAT, Reviewer, Human Approval, PR, and Orchestrator reports. The Human Owner must understand the result and their decision from this section alone. Use short sentences and plain Korean; keep workflow terms, paths, functions, commands, exact counts, and all technical evidence below `## Developer Details`. Never hide FAIL, SKIP, NOT RUN, known gaps, or new regressions in either layer.
- An automatic status summary uses only safe structured outcomes. If it cannot explain a specific business change or approval option, say so plainly and require a separately reviewed owner-facing report before business acceptance. Never copy arbitrary Issue, agent, log, or client text into a public summary.
- Use synthetic fixtures or explicitly public DART filings. Never place client data, credentials, client numbers, or client file paths in prompts, issues, logs, or commits.
- AuditDesk's `dsd_workbench` and DSD_FOOTING remain offline. Public OpenDART receipt belongs only to `dart_explorer` under its existing boundary.
- Report: goal/root cause; files and behavior; before/after reproduction; exact commands and PASS/FAIL/SKIP/NOT RUN counts; protected-artifact check; reviewer findings and fixes; manual checks; remaining risks; and the Human Owner decision needed. Use `docs/harness/review_protocol.md`.
