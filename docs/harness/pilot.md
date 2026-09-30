# Pilot: one bounded AuditDesk Issue

Pilot queue item: [Issue #5](https://github.com/yungGom/Auditing_Package/issues/5), **a fresh public checkout cannot pass `test_g2_smoke_direct` because the real-file generation fixtures are absent**. This is independently reproducible and does not require inventing an accounting rule.

1. Record the reproduction from a clean checkout: `python scripts/test_auditdesk.py` reports the missing `_KNOWN_GENERATIONS` fixture, with 229 passed, 1 failed, and 76 skipped at the v1 baseline. Exact counts can change; attach the fresh run.
2. Human Owner decides which explicitly public DSD files may be used locally and whether a synthetic substitute is acceptable for the direct G2 smoke. Do not put private data in the Issue or repository. Do not alter existing expected values or gate records as an Implementer.
3. Once the owner supplies the fixture decision, the Implementer writes a before/after reproduction and a narrow plan on the Issue. Any protected fixture or existing test edit triggers STOP and separate Human Owner action under `governance/PROTECTED_ARTIFACTS.md`.
4. Run `python scripts/check_protected.py --base origin/main`, the AuditDesk entrypoint, and then `python scripts/test_all.py`. A skipped test remains an incomplete Technical PASS. Have an independent reviewer inspect the diff and logs.
5. Link the PR to the Issue, report known exceptions and manual checks, and ask the Human Owner for business acceptance. Close the Issue only after the decision.

This pilot is **prepared, not executed**. The owner fixture decision is required before an agent can close the current test gap safely.
