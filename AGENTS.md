# Auditing_Package agent entrypoint

Read `governance/POLICY.md` before any repository work. It is the single source for the shared development contract used by Codex and Claude Code. Then read the nearest project `AGENTS.md`, applicable `CLAUDE.md`, README, specs, and gate records. Project-specific accounting rules remain in their existing documents. If applicable rules conflict, stop the affected change and report the conflict to the Human Owner.

The protected artifact inventory and enforcement instructions are in `governance/PROTECTED_ARTIFACTS.md`. Start work from a GitHub Issue with explicit acceptance criteria. Run `python scripts/check_protected.py --base origin/main` and the applicable entrypoint in `scripts/` before reporting technical results. No failed, skipped, or unrun required check is a Technical PASS.
