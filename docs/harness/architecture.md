# AI development harness v1 — architecture and baseline

## Current repository at baseline

Inspected `main` at `7cd756b` (2026-09-27). The repository has no root `AGENTS.md`, `.github` templates, or GitHub Actions workflow at this baseline. It has a root `CLAUDE.md` focused on AuditLink, a detailed `DSD_footing/CLAUDE.md`, and project READMEs and gate ledgers. The harness adds files and leaves those sources intact.

| Scope | Existing evidence | Entry point in this harness |
| --- | --- | --- |
| AuditDesk offline DSD core | `auditdesk/dsd_workbench/dsd_tool/tests/`; `test_offline.py` enforces forbidden network imports | `python scripts/test_auditdesk.py` |
| AuditDesk public DART explorer | `auditdesk/dart_explorer/tests/` | same |
| AuditDesk React web UI | `auditdesk/webui/package.json`: `build` = TypeScript check + Vite build; no automated browser suite | same; manual UI gates still apply |
| DSD_FOOTING PDF engine | `DSD_footing/GATES.json` has four public sample PDFs; `run_gates.py` compares metrics and exits 1 on mismatch | `python scripts/test_dsd_footing.py` |
| AuditLink v2 inside `auditdesk/` | separate `backend/tests`, `frontend/package.json` | excluded from primary entrypoint; test when touched |

`auditdesk/GATES.json` records patch-level quality decisions and is not a test runner. `DSD_footing/GATES.json` is a metric snapshot. Neither may be auto-updated by the harness. README test counts and gate counts are historical claims, not fresh run results.

The public checkout does not include every real-file fixture used by AuditDesk. On a fresh clone, `test_version_check.py::test_g2_smoke_direct` fails because `_KNOWN_GENERATIONS` is empty; other fixture-dependent tests skip. Keep this visible as an incomplete regression baseline. Supply approved public fixtures through the existing local fixture path before claiming the complete suite passed; do not change the test to hide the gap.

## Layers

```text
Human: requirement and accounting acceptance
    ↓
Issue/task contract: scope, examples, acceptance criteria, risks
    ↓
Implementer: inspect → reproduce → change → local tests
    ↓
Automated entrypoints: AuditDesk + DSD_FOOTING
    ↓
Reviewer: diff, data boundary, test evidence, domain assumptions
    ↳ blocking finding → implementer fixes → tests and review repeat
    ↓
Human: accept, reject, or refine the business rule
```

The root `AGENTS.md` owns the shared workflow. Project `AGENTS.md` files point to existing domain documents and record project-specific test gates. `scripts/test_all.py` composes entrypoints without changing product code. Issue and PR templates carry the task and evidence contract. Future projects can add a local `AGENTS.md` and independently runnable test script, then register it in the aggregator.

This v1 documents a repeatable handoff. It does not automatically create agents, open PRs, set branch protection, run CI, or decide accounting acceptability. Those can be added after the local entrypoints have been exercised on the target development machine.
