# Enforcement setup and limits

## Source of truth

`AGENTS.md` alone would give Codex a simple entrypoint, but Claude Code uses `CLAUDE.md`; maintaining identical full policies in both files would drift. We chose `governance/POLICY.md` as the common source. Root `AGENTS.md` and root `CLAUDE.md` point to it, while project-specific `AGENTS.md` and `DSD_footing/CLAUDE.md` keep their existing detail. If a product rule and the common workflow conflict, stop the affected work and ask the Human Owner.

## Controls

| Control | Action | Limit |
| --- | --- | --- |
| `scripts/check_protected.py` | Compares changed paths and selected AST rule definitions with the base; nonzero on a protected change | Known selected symbols, not every possible semantic rule change; reviewer still inspects code |
| Git `pre-commit` | Blocks staged protected changes | Opt-in via `python scripts/install_hooks.py`; `--no-verify` can bypass |
| Git `pre-push` | Runs protected check and `test_all.py` | Opt-in, potentially several minutes; can be bypassed |
| Claude Code `PreToolUse` | Blocks direct Write/Edit to protected files | Fast feedback only; shell edits and other tools need Git/CI checks |
| GitHub Actions `protected-artifacts` | Runs checker against `origin/main`, using base branch code/manifest after the bootstrap merge | Workflow on this new PR is bootstrap; default branch must receive it |
| GitHub Actions `regression` | Installs declared dependencies and runs `python scripts/test_all.py` | Current public checkout has missing AuditDesk fixtures, so this must remain red until resolved |

GitHub treats skipped jobs as successful for some required-check decisions. Keep both jobs unconditional: no path filter, no `continue-on-error`, and no step that converts failure to zero. The AuditDesk runner fails on any pytest skip as well as a failure. A DSD gate comparison bypass is prevented by using every registered sample and tolerance from `GATES.json`.

Untracked local files are checked when staged by the pre-commit hook and after commit by CI. Run `git add` before using `--staged` as local evidence; the unstaged comparison covers tracked changes.

## Repository settings still required

After this workflow reaches the default branch, the repository owner should configure the `main` branch ruleset to require a pull request, require code-owner review, require the `protected-artifacts` and `regression` checks, and disallow ordinary bypasses. `CODEOWNERS` requests `@yungGom` for protected paths; it does not by itself make review mandatory. The rulesets API returned no rulesets at inspection time; the GitHub connection returned 403 for branch-protection details and cannot change those settings. The PR alone therefore does not make merge rejection mandatory.

Do not mark PR #4 ready or merge it on a red regression check. The known AuditDesk fixture gap must be resolved using approved public data without changing expected results. GitHub Actions and Claude hook details follow [GitHub's required-check documentation](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks) and [Claude Code's hooks reference](https://code.claude.com/docs/en/hooks).
