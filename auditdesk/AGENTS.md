# AuditDesk-specific contract

Read `auditdesk/README.md`, the relevant specs in `auditdesk/docs/`, and `auditdesk/GATES.json` alongside the root `AGENTS.md`. This folder also contains a separate AuditLink v2 app in `backend/` and `frontend/`; its tests are not part of the AuditDesk core entrypoint.

- Keep `dsd_workbench` completely offline. Do not add network dependencies or imports to `dsd_tool`. Keep `dart_explorer` for public DART receipt, with file/cache transfer across the boundary. Run `test_offline.py` with the full core suite.
- Preserve original DSD identity checks, byte-preserving no-change behavior, precise offset edits, and explicit unmatched/unknown output. Accounting recommendations require a person's confirmation.
- Treat `GATES.json` as the existing manually maintained quality ledger. Do not change a status without a recorded quantitative or manual basis. Do not claim the UI gates passed from a Python test result.
- From the repository root run `python scripts/test_auditdesk.py` for core and web UI checks. `auditdesk/webui` needs dependencies installed from its lockfile (`npm ci`) before the build check. For the separate AuditLink v2, run its own backend pytest and frontend checks when changing those directories; document those commands in the task report.
- Use `auditdesk/docs/IMPL_CHECKLIST.md` and `REQUEST_LEDGER.md` when a change affects an existing request or gate. Record which manual browser or DART editor checks remain for a change to UI or real-file behavior.
