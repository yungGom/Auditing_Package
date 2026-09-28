"""Pilot #1 scoped task completion without agent, network, or product fixtures."""
from argparse import Namespace
from pathlib import Path
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orchestrator as orch
import orchestrator_results as results

TASK = "auditdesk/dsd_workbench/dsd_tool/tests/test_synthetic_g2.py"
SMOKE = "dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct"
SKIP = "dsd_workbench/dsd_tool/tests/test_version_check.py:49: existing generations missing"


def pilot_issue():
    return {"number": 5, "state": "OPEN", "title": "Pilot #1",
            "url": "https://github.com/example/repo/issues/5",
            "body": ("## Problem\nSynthetic regression alongside unavailable real files.\n"
                     "## Required tests\n`python scripts/test_auditdesk.py`\n"
                     "`python scripts/test_all.py`\n"
                     "## Task required checks\n`" + TASK + "`\n"
                     "## Known unavailable gates\n`" + SMOKE + "`\n"
                     "## Human decision required\nnone\n")}


def args(dry=False):
    return Namespace(repo="example/repo", issue=5, issue_json=None, dry_run=dry,
                     max_attempts=2, agent_timeout=30, test_timeout=30,
                     no_comment=True, report=None, python_candidate=[])


def runtime():
    return {"ready": True, "error_code": "NONE",
            "selected_executable": "C:/sandbox/python.exe"}


def reg(script, *, failed=True, extra=()):
    return {"step": script, "status": "FAIL" if failed else "PASS",
            "exit_code": 1 if failed else 0, "passed": 236,
            "failed": int(failed) + len(extra), "skipped": 76 if failed else 0,
            "errors": 0, "failures": ([SMOKE] if failed else []) + list(extra),
            "skip_sites": [SKIP] if failed else [],
            "components": ({"auditdesk_pytest": int(failed), "webui_build": 0}
                           if script == "scripts/test_auditdesk.py"
                           else {"auditdesk": int(failed), "dsd_footing": 0,
                                 "auditdesk_pytest": int(failed), "webui_build": 0})}


def task_pass():
    return {"step": TASK, "status": "PASS", "exit_code": 0,
            "passed": 5, "failed": 0, "skipped": 0, "errors": 0,
            "failures": [], "skip_sites": [], "components": {}}


class ScopedResultsTests(unittest.TestCase):
    def test_issue5_dry_run_separates_checks_and_gaps(self):
        with patch.object(orch, "get_issue", return_value=pilot_issue()), \
             patch.object(orch, "agent") as agent:
            report = orch.run(args(dry=True))
        self.assertEqual(report["state"], "READY")
        self.assertEqual(report["task_required_checks"][0]["path"], TASK)
        self.assertEqual(len(report["regression_checks"]), 2)
        self.assertEqual(report["known_unavailable_gates"], [SMOKE])
        self.assertEqual(report["task_result"], "NOT_RUN")
        agent.assert_not_called()

    def test_issue_cannot_supply_arbitrary_task_command(self):
        body = pilot_issue()["body"].replace(TASK, "scripts/test_all.py --disable-warnings")
        with self.assertRaises(ValueError):
            results.task_paths(body)

    def test_current_issue5_acceptance_contract_is_scoped_without_editing_issue(self):
        body = ("## Acceptance criteria\n"
                "- Add only `auditdesk/dsd_workbench/dsd_tool/tests/fixture_generators/"
                "build_version_fixture.py` and `" + TASK + "`.\n"
                "- Preserve the paths of all existing real-file tests.\n"
                "## Reproduction\n"
                "`test_version_check.py::test_g2_smoke_direct` is unavailable.\n")
        self.assertEqual(results.task_paths(body), [TASK])
        self.assertEqual(results.known_gate_ids(body),
                         {"test_version_check.py::test_g2_smoke_direct"})
        gaps, regressions, unclassified = results.compare(
            [reg("scripts/test_auditdesk.py")],
            [reg("scripts/test_auditdesk.py")], results.known_gate_ids(body))
        self.assertEqual(regressions, [])
        self.assertEqual(unclassified, [])
        self.assertEqual(gaps[0]["failed_tests"], [SMOKE])

    def test_known_baseline_allows_task_review_without_technical_pass(self):
        regression = ["scripts/test_auditdesk.py", "scripts/test_all.py"]
        baseline = [reg(x) for x in regression]
        after = [reg(x) for x in regression]
        replies = iter([
            {"decision": "PASS", "summary": "task complete", "findings": []},
            {"decision": "PASS", "summary": "task diff approved", "findings": []},
        ])
        with patch.object(orch, "get_issue", return_value=pilot_issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=runtime()), \
             patch.object(orch, "_scoped_checks", side_effect=[baseline, [task_pass()], after]), \
             patch.object(orch, "agent", side_effect=lambda *a, **k: next(replies)) as agent, \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "worktree_fingerprint", return_value=[]):
            report = orch.run(args())
        self.assertEqual(report["state"], "TASK_PASS_WITH_KNOWN_GAPS")
        self.assertEqual(report["attempts"], 1)
        self.assertEqual(report["task_result"], "PASS")
        self.assertEqual(report["repository_result"], "FAIL")
        self.assertEqual(report["reviewer_result"], "PASS")
        self.assertEqual(report["new_regressions"], [])
        self.assertEqual(agent.call_count, 2)
        self.assertEqual(report["blocker_class"], "EXISTING_BASELINE")

    def test_existing_baseline_implementer_blocker_does_not_retry(self):
        baseline = [reg("scripts/test_auditdesk.py"), reg("scripts/test_all.py")]
        replies = iter([
            {"decision": "BLOCKER", "blocker_class": "EXISTING_BASELINE",
             "summary": "real fixture unavailable", "findings": []},
            {"decision": "PASS", "summary": "task reviewed", "findings": []},
        ])
        with patch.object(orch, "get_issue", return_value=pilot_issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=runtime()), \
             patch.object(orch, "_scoped_checks",
                          side_effect=[baseline, [task_pass()], baseline]), \
             patch.object(orch, "agent", side_effect=lambda *a, **k: next(replies)) as agent, \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "worktree_fingerprint", return_value=[]):
            report = orch.run(args())
        self.assertEqual(report["state"], "TASK_PASS_WITH_KNOWN_GAPS")
        self.assertEqual(report["attempts"], 1)
        self.assertEqual(agent.call_count, 2)

    def test_new_failure_blocks_partial_completion_and_retries_implementation(self):
        regression = ["scripts/test_auditdesk.py", "scripts/test_all.py"]
        baseline = [reg(x) for x in regression]
        new_id = "dsd_workbench/dsd_tool/tests/test_other.py::test_new"
        after = [reg(x, extra=(new_id,)) for x in regression]
        checks = [baseline, [task_pass()], after, [task_pass()], after]
        with patch.object(orch, "get_issue", return_value=pilot_issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=runtime()), \
             patch.object(orch, "_scoped_checks", side_effect=checks), \
             patch.object(orch, "agent", return_value={"decision": "PASS",
                           "summary": "implemented", "findings": []}) as agent, \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "worktree_fingerprint") as fingerprint:
            report = orch.run(args())
        self.assertEqual(report["state"], "FAILED")
        self.assertEqual(report["attempts"], 2)
        self.assertEqual(report["blocker_class"], "IMPLEMENTATION")
        self.assertTrue(report["new_regressions"])
        self.assertEqual(agent.call_count, 2)
        fingerprint.assert_not_called()

    def test_regression_skip_identity_and_component_changes_fail_closed(self):
        baseline = [reg("scripts/test_auditdesk.py")]
        after = [reg("scripts/test_auditdesk.py")]
        after[0]["skip_sites"] = ["different test skipped"]
        after[0]["components"]["webui_build"] = 1
        _, new, _ = results.compare(baseline, after, {SMOKE})
        self.assertTrue(any("new skipped sites" in item for item in new))
        self.assertTrue(any("webui_build PASS became FAIL" in item for item in new))

    def test_missing_component_or_lost_passes_cannot_be_known_gap(self):
        baseline = [reg("scripts/test_auditdesk.py")]
        after = [reg("scripts/test_auditdesk.py")]
        after[0]["components"] = {}
        after[0]["passed"] = 0
        _, regressions, _ = results.compare(baseline, after, {SMOKE})
        self.assertTrue(any("result unavailable" in item for item in regressions))
        self.assertTrue(any("passed test count decreased" in item for item in regressions))

    def test_scoped_runner_requests_failure_and_skip_node_summaries(self):
        with patch.object(orch, "command", return_value=subprocess.CompletedProcess(
                [], 1, "1 failed, 2 passed, 3 skipped", "")) as command:
            orch._scoped_checks(["scripts/test_auditdesk.py"], runtime(), 30, task=False)
        self.assertIn("-rfEs", command.call_args.kwargs["env"]["PYTEST_ADDOPTS"])

    def test_missing_baseline_component_cannot_be_accepted_as_known_gap(self):
        baseline = [reg("scripts/test_auditdesk.py")]
        baseline[0]["components"] = {}
        _, regressions, unclassified = results.compare(baseline, baseline, {SMOKE})
        self.assertEqual(regressions, [])
        self.assertTrue(any("baseline webui_build result unavailable" in item
                            for item in unclassified))

    def test_full_harness_requires_nested_auditdesk_component_evidence(self):
        baseline = [reg("scripts/test_all.py")]
        baseline[0]["components"].pop("webui_build")
        _, regressions, unclassified = results.compare(baseline, baseline, {SMOKE})
        self.assertEqual(regressions, [])
        self.assertTrue(any("baseline webui_build result unavailable" in item
                            for item in unclassified))

    def test_incomplete_baseline_evidence_stops_after_review_as_environment(self):
        baseline = [reg("scripts/test_auditdesk.py"), reg("scripts/test_all.py")]
        baseline[0]["components"] = {}
        replies = iter([
            {"decision": "PASS", "summary": "implemented", "findings": []},
            {"decision": "PASS", "summary": "reviewed task", "findings": []},
        ])
        with patch.object(orch, "get_issue", return_value=pilot_issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=runtime()), \
             patch.object(orch, "_scoped_checks",
                          side_effect=[baseline, [task_pass()], baseline]), \
             patch.object(orch, "agent", side_effect=lambda *a, **k: next(replies)) as agent, \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "worktree_fingerprint", return_value=[]):
            report = orch.run(args())
        self.assertEqual(report["state"], "FAILED")
        self.assertEqual(report["blocker_class"], "ENVIRONMENT")
        self.assertEqual(report["attempts"], 1)
        self.assertEqual(report["reviewer_result"], "PASS")
        self.assertEqual(agent.call_count, 2)

    def test_reviewer_environment_or_human_blocker_does_not_retry(self):
        baseline = [reg("scripts/test_auditdesk.py"), reg("scripts/test_all.py")]
        for category, expected_state in (("ENVIRONMENT", "FAILED"),
                                         ("HUMAN_DECISION", "HUMAN_APPROVAL")):
            with self.subTest(category=category):
                replies = iter([
                    {"decision": "PASS", "summary": "task implemented", "findings": []},
                    {"decision": "BLOCKER", "blocker_class": category,
                     "summary": "review blocked", "findings": ["blocker"]},
                ])
                with patch.object(orch, "get_issue", return_value=pilot_issue()), \
                     patch.object(orch, "changed_files", return_value=[]), \
                     patch.object(orch, "runtime_preflight", return_value=runtime()), \
                     patch.object(orch, "_scoped_checks",
                                  side_effect=[baseline, [task_pass()], baseline]), \
                     patch.object(orch, "agent", side_effect=lambda *a, **k: next(replies)) as agent, \
                     patch.object(orch, "protected_check", return_value=(True, "PASS")), \
                     patch.object(orch, "worktree_fingerprint", return_value=[]):
                    report = orch.run(args())
                self.assertEqual(report["state"], expected_state)
                self.assertEqual(report["attempts"], 1)
                self.assertEqual(agent.call_count, 2)

    def test_undeclared_existing_baseline_is_not_partial_pass_or_retry(self):
        baseline = [reg("scripts/test_auditdesk.py"), reg("scripts/test_all.py")]
        unknown = "dsd_workbench/dsd_tool/tests/test_other.py::test_existing"
        baseline[0]["failures"].append(unknown)
        replies = iter([
            {"decision": "PASS", "summary": "task implemented", "findings": []},
            {"decision": "PASS", "summary": "task approved", "findings": []},
        ])
        with patch.object(orch, "get_issue", return_value=pilot_issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=runtime()), \
             patch.object(orch, "_scoped_checks",
                          side_effect=[baseline, [task_pass()], baseline]), \
             patch.object(orch, "agent", side_effect=lambda *a, **k: next(replies)) as agent, \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "worktree_fingerprint", return_value=[]):
            report = orch.run(args())
        self.assertEqual(report["state"], "FAILED")
        self.assertEqual(report["blocker_class"], "EXISTING_BASELINE")
        self.assertEqual(report["attempts"], 1)
        self.assertEqual(report["reviewer_result"], "PASS")
        self.assertTrue(report["unclassified_baseline"])
        self.assertEqual(agent.call_count, 2)

    def test_scoped_clean_repository_remains_done(self):
        clean = [reg(x, failed=False) for x in
                 ("scripts/test_auditdesk.py", "scripts/test_all.py")]
        with patch.object(orch, "get_issue", return_value=pilot_issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=runtime()), \
             patch.object(orch, "_scoped_checks",
                          side_effect=[clean, [task_pass()], clean]), \
             patch.object(orch, "agent", return_value={"decision": "PASS",
                          "summary": "approved", "findings": []}), \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "worktree_fingerprint", return_value=[]):
            report = orch.run(args())
        self.assertEqual(report["state"], "DONE")
        self.assertEqual(report["repository_result"], "PASS")
        self.assertEqual(report["reviewer_result"], "PASS")

    def test_partial_state_exit_code_is_nonzero(self):
        report = {"issue": 5, "state": "TASK_PASS_WITH_KNOWN_GAPS",
                  "reason": "known gaps — 합성 PASS", "attempts": 1, "evidence": []}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "report.json"
            output = io.StringIO()
            with patch.object(orch, "run", return_value=report), \
                 patch.object(sys, "stdout", output), \
                 patch.object(sys, "argv", ["orchestrator", "5", "--dry-run",
                                           "--no-comment", "--report", str(target)]):
                code = orch.main()
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output.getvalue()),
                             json.loads(target.read_text(encoding="utf-8")))

    def test_summary_extracts_issue5_failure_and_skip_evidence(self):
        output = ("FAILED dsd_workbench/dsd_tool/tests/test_version_check.py::test_g2_smoke_direct\n"
                  "SKIPPED [76] " + SKIP + "\n"
                  "1 failed, 236 passed, 76 skipped\n"
                  "[AuditDesk] pytest=1, webui build=0\n")
        result = subprocess.CompletedProcess([], 1, output, "")
        summary = results.summarize("scripts/test_auditdesk.py", result)
        self.assertEqual(summary["failures"], [SMOKE])
        self.assertEqual(summary["skipped"], 76)
        self.assertEqual(summary["components"]["webui_build"], 0)


if __name__ == "__main__":
    unittest.main()
