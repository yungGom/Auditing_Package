"""Bounded orchestration behavior without network or agent calls."""

from pathlib import Path
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orchestrator as orch  # noqa: E402


def issue(decision: str = "none") -> dict:
    return {"number": 5, "state": "OPEN", "title": "Pilot",
            "url": "https://github.com/example/repo/issues/5",
            "body": ("## Problem\nExample\n\n## Required tests\n"
                     "`python scripts/test_auditdesk.py`\n"
                     "`python scripts/test_all.py`\n\n"
                     "## Human decision required\n" + decision)}


def args(dry_run: bool = False):
    from argparse import Namespace
    return Namespace(repo="example/repo", issue=5, issue_json=None,
                     dry_run=dry_run, max_attempts=2, agent_timeout=30,
                     test_timeout=30, no_comment=True, report=None)


class OrchestratorTests(unittest.TestCase):
    def test_template_none_allows_ready_intake(self):
        item = issue("Accounting judgment or protected-artifact decision (or `none`): none\n"
                     "Definition of done: implementation and review")
        self.assertIsNone(orch.approval_pending(item))

    def test_roles_use_separate_sandboxes_and_structured_output(self):
        calls = []

        def fake_command(argv, **kwargs):
            calls.append((argv, kwargs))
            output = Path(argv[argv.index("--output-last-message") + 1])
            output.write_text(json.dumps({"decision": "PASS", "summary": "ok", "findings": []}),
                              encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with patch.object(orch, "command", side_effect=fake_command):
            orch.agent("implementer", issue(), "", 30)
            orch.agent("reviewer", issue(), "test evidence", 30)
        self.assertEqual(calls[0][0][calls[0][0].index("--sandbox") + 1], "workspace-write")
        self.assertEqual(calls[1][0][calls[1][0].index("--sandbox") + 1], "read-only")
        self.assertIn("test evidence", calls[1][1]["input_text"])

    def test_pilot_stops_before_agent_or_tests(self):
        pilot = issue("Approve public fixture source and handling. Protected fixture edits require owner action.")
        with patch.object(orch, "get_issue", return_value=pilot), patch.object(orch, "agent") as agent:
            result = orch.run(args(dry_run=True))
        self.assertEqual(result["state"], "HUMAN_APPROVAL")
        self.assertEqual(result["attempts"], 0)
        agent.assert_not_called()

    def test_dry_run_ready_without_execution(self):
        with patch.object(orch, "get_issue", return_value=issue()), patch.object(orch, "agent") as agent:
            result = orch.run(args(dry_run=True))
        self.assertEqual(result["state"], "READY")
        agent.assert_not_called()

    def test_protected_failure_stops_before_tests_or_reviewer(self):
        with patch.object(orch, "get_issue", return_value=issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "agent", return_value={"decision": "PASS", "summary": "done", "findings": []}) as agent, \
             patch.object(orch, "protected_check", return_value=(False, "protected artifact changed")), \
             patch.object(orch, "command") as command:
            result = orch.run(args())
        self.assertEqual(result["state"], "HUMAN_APPROVAL")
        self.assertEqual(agent.call_count, 1)
        command.assert_not_called()

    def test_review_blocker_reworks_then_passes(self):
        replies = iter([{"decision": "PASS", "summary": "implemented", "findings": []},
                        {"decision": "BLOCKER", "summary": "missing edge case", "findings": ["edge"]},
                        {"decision": "PASS", "summary": "fixed", "findings": []},
                        {"decision": "PASS", "summary": "review clean", "findings": []}])
        with patch.object(orch, "get_issue", return_value=issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "agent", side_effect=lambda *a: next(replies)) as agent, \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "command", return_value=subprocess.CompletedProcess([], 0, "2 passed", "")):
            result = orch.run(args())
        self.assertEqual(result["state"], "DONE")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(agent.call_count, 4)

    def test_failed_required_test_never_passes(self):
        with patch.object(orch, "get_issue", return_value=issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "agent", return_value={"decision": "PASS", "summary": "done", "findings": []}) as agent, \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "command", return_value=subprocess.CompletedProcess([], 1, "1 failed, 1 skipped", "")):
            result = orch.run(args())
        self.assertEqual(result["state"], "FAILED")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(agent.call_count, 2)  # no reviewer
        self.assertTrue(any(step["status"] == "FAIL" for step in result["evidence"]))


if __name__ == "__main__":
    unittest.main()
