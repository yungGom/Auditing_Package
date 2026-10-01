# DSD_FOOTING-specific contract

Read `governance/POLICY.md`, `governance/PROTECTED_ARTIFACTS.md`, `DSD_footing/CLAUDE.md`, `GATES.json`, and the root `AGENTS.md` before work. The existing detailed accounting rules and approved exceptions in `CLAUDE.md` remain authoritative for this project.

- Keep the pipeline fully offline. Use synthetic fixtures or the already registered public DART sample PDFs. Never ingest private client numbers into repository or agent context.
- Preserve `OK`, `ROUND`, `DIFF`, `SKIP (?)`, and `SIGN` distinctions. Unmatched is not zero; sign agreement by absolute value alone is not an `OK`.
- Before a bug fix, record a reproducing case and expected accounting judgment. Afterward run `python scripts/test_dsd_footing.py` from the repository root. It checks every sample and tolerance registered in `GATES.json` using temporary copies, so generated tickmark PDFs and exception indexes do not overwrite project files.
- `run_gates.py` can skip comparison for an unregistered sample or a different tolerance. Such a skip is not regression evidence. Never use `--update-gates` or `GATES_UPDATE=1` during verification. Baseline changes require a reason, before/after metrics, and human accounting approval.
- A remaining `DIFF` or `SKIP` is not automatically a failed regression if it matches the registered baseline, but it must remain visible in the report and receive human review where appropriate.
