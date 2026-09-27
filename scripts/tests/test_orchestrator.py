"""Bounded orchestration behavior without network or agent calls."""

from pathlib import Path
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import orchestrator as orch  # noqa: E402
import orchestrator_preflight as probe  # noqa: E402


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


def ready_runtime() -> dict:
    return {"ready": True, "error_code": "NONE",
            "selected_executable": "C:/sandbox/python.exe",
            "version": "3.12.14",
            "dependencies": {"pytest": True, "openpyxl": True},
            "temp_write": True, "commands": {"git": True, "npm": True},
            "diagnostic": {"command_class": "codex exec preflight",
                           "exit_code": 0, "stderr_tail": "NONE"}}


def probe_reply(prompt: str, **changes) -> dict:
    nonce = re.search(r"--nonce ([0-9a-f]+)", prompt).group(1)
    data = {"nonce": nonce, "candidate": orch.runtime_candidates()[-1],
            "executable": "C:/sandbox/python.exe", "version": "3.12.14",
            "pytest": True, "openpyxl": True, "temp_write": True,
            "git": True, "npm": True, "error_code": "NONE"}
    data.update(changes)
    return data


def preflight_command(**changes):
    def fake(argv, **kwargs):
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(json.dumps(probe_reply(kwargs["input_text"], **changes)),
                          encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")
    return fake


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
             patch.object(orch, "runtime_preflight", return_value=ready_runtime()), \
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
             patch.object(orch, "runtime_preflight", return_value=ready_runtime()), \
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
             patch.object(orch, "runtime_preflight", return_value=ready_runtime()), \
             patch.object(orch, "agent", return_value={"decision": "PASS", "summary": "done", "findings": []}) as agent, \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "command", return_value=subprocess.CompletedProcess([], 1, "1 failed, 1 skipped", "")):
            result = orch.run(args())
        self.assertEqual(result["state"], "FAILED")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(agent.call_count, 2)  # no reviewer
        self.assertTrue(any(step["status"] == "FAIL" for step in result["evidence"]))


class PreflightTests(unittest.TestCase):
    def test_parent_python_does_not_prove_child_is_usable(self):
        with patch.object(orch, "command", side_effect=preflight_command(
                candidate="", executable="", version="", pytest=False,
                openpyxl=False, temp_write=False, git=False, npm=False,
                error_code="NOT_FOUND")) as command:
            result = orch.runtime_preflight(30, ["scripts/test_auditdesk.py"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["error_code"], "NOT_FOUND")
        self.assertIn("--sandbox", command.call_args.args[0])
        self.assertEqual(command.call_args.args[0][command.call_args.args[0].index("--sandbox") + 1],
                         "workspace-write")

    def test_access_denied_candidate(self):
        with patch.object(orch, "command", side_effect=preflight_command(
                candidate="", executable="", version="", pytest=False,
                openpyxl=False, temp_write=False, git=False, npm=False,
                error_code="ACCESS_DENIED")):
            result = orch.runtime_preflight(30, [])
        self.assertEqual(result["error_code"], "ACCESS_DENIED")

    def test_executable_with_missing_pytest_is_blocked(self):
        with patch.object(orch, "command", side_effect=preflight_command(pytest=False)):
            result = orch.runtime_preflight(30, [])
        self.assertFalse(result["ready"])
        self.assertEqual(result["error_code"], "MISSING_DEPENDENCY")

    def test_temp_write_failure_is_blocked(self):
        with patch.object(orch, "command", side_effect=preflight_command(temp_write=False)):
            result = orch.runtime_preflight(30, [])
        self.assertFalse(result["ready"])
        self.assertEqual(result["error_code"], "TEMP_NOT_WRITABLE")

    def test_partial_python_identity_is_retained_on_dependency_failure(self):
        with patch.object(orch, "command", side_effect=preflight_command(pytest=False)):
            result = orch.runtime_preflight(30, [])
        self.assertFalse(result["ready"])
        self.assertIsNone(result["selected_executable"])
        self.assertEqual(result["probe_executable"], "C:/sandbox/python.exe")
        self.assertEqual(result["version"], "3.12.14")
        self.assertFalse(result["dependencies"]["pytest"])

    def test_usable_runtime_selection_and_prompt(self):
        with patch.object(orch, "command", side_effect=preflight_command()) as command:
            result = orch.runtime_preflight(30, ["scripts/test_all.py"])
        self.assertTrue(result["ready"])
        self.assertEqual(result["selected_executable"], "C:/sandbox/python.exe")
        self.assertIn("--require-npm", command.call_args.kwargs["input_text"])
        self.assertNotIn("token", json.dumps(result).lower())
        self.assertEqual(result["diagnostic"]["command_class"], "codex exec preflight")

    def test_forged_nonce_does_not_pass(self):
        with patch.object(orch, "command", side_effect=preflight_command(nonce="wrong")):
            result = orch.runtime_preflight(30, [])
        self.assertFalse(result["ready"])
        self.assertEqual(result["error_code"], "INVALID_PROBE")

    def test_environment_failure_stops_before_implementer_and_is_not_approval(self):
        failed = {"ready": False, "error_code": "ACCESS_DENIED"}
        with patch.object(orch, "get_issue", return_value=issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=failed), \
             patch.object(orch, "agent") as agent:
            report = orch.run(args())
        self.assertEqual(report["state"], "FAILED")
        self.assertIn("ENVIRONMENT_BLOCKER", report["reason"])
        self.assertEqual(report["attempts"], 0)
        agent.assert_not_called()

    def test_probe_helper_checks_actual_modules_and_commands(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(probe, "_module_available", side_effect=lambda name: name == "openpyxl"), \
             patch.object(probe, "_command_available", return_value=True):
            result = probe.probe("nonce", Path(tmp), require_npm=True)
        self.assertFalse(result["pytest"])
        self.assertTrue(result["openpyxl"])
        self.assertTrue(result["temp_write"])
        self.assertTrue(result["git"])
        self.assertTrue(result["npm"])

    def test_probe_helper_reports_temp_permission_failure(self):
        with patch.object(probe.tempfile, "TemporaryDirectory", side_effect=PermissionError()), \
             patch.object(probe, "_module_available", return_value=True), \
             patch.object(probe, "_command_available", return_value=True):
            result = probe.probe("nonce", Path("C:/blocked"), require_npm=False)
        self.assertFalse(result["temp_write"])

    def test_cli_failure_diagnostic_is_classified_without_raw_secret(self):
        def failed_command(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, "",
                                               "Access denied: token=example-secret C:/client.dsd")
        with patch.object(orch, "command", side_effect=failed_command):
            with self.assertRaises(orch.AgentExecutionError) as caught:
                orch.agent("implementer", issue(), "", 30, ready_runtime())
        self.assertEqual(caught.exception.diagnostic["stderr_tail"], "ACCESS_DENIED")
        self.assertNotIn("example-secret", json.dumps(caught.exception.diagnostic))
        self.assertNotIn("client.dsd", json.dumps(caught.exception.diagnostic))

    def test_failed_implementer_keeps_sanitized_diagnostic_in_report(self):
        diagnostic = {"command_class": "codex exec implementer", "exit_code": 1,
                      "selected_runtime": "C:/sandbox/python.exe",
                      "stderr_tail": "ACCESS_DENIED"}
        with patch.object(orch, "get_issue", return_value=issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=ready_runtime()), \
             patch.object(orch, "agent", side_effect=orch.AgentExecutionError(diagnostic)), \
             patch.object(orch, "protected_check") as protected:
            report = orch.run(args())
        self.assertEqual(report["state"], "FAILED")
        self.assertEqual(report["attempts"], 1)
        self.assertEqual(report["evidence"][-1]["diagnostic"], diagnostic)
        protected.assert_not_called()

    def test_implementer_receives_verified_runtime(self):
        def fake(argv, **kwargs):
            self.assertIn("C:/sandbox/python.exe", kwargs["input_text"])
            output = Path(argv[argv.index("--output-last-message") + 1])
            output.write_text(json.dumps({"decision": "PASS", "summary": "ok", "findings": []}),
                              encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")
        with patch.object(orch, "command", side_effect=fake):
            result = orch.agent("implementer", issue(), "", 30, ready_runtime())
        self.assertEqual(result["_diagnostic"]["selected_runtime"], "C:/sandbox/python.exe")

    def test_cp949_console_roundtrip_and_exit_states(self):
        for state, expected_code in (("HUMAN_APPROVAL", 0), ("FAILED", 1),
                                     ("DONE", 0)):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as tmp:
                report = {"issue": 5, "state": state, "reason": "승인 — 검토",
                          "attempts": 0, "evidence": []}
                output = Path(tmp) / "report.json"
                buffer = io.BytesIO()
                stream = io.TextIOWrapper(buffer, encoding="cp949")
                with patch.object(orch, "run", return_value=report), \
                     patch.object(sys, "stdout", stream), \
                     patch.object(sys, "argv", ["orchestrator", "5", "--dry-run",
                                                "--no-comment", "--report", str(output)]):
                    code = orch.main()
                stream.flush()
                printed = json.loads(buffer.getvalue().decode("cp949"))
                saved = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(printed, saved)
                self.assertEqual(saved, report)
                self.assertEqual(code, expected_code)

    def test_happy_path_keeps_preflight_diagnostic_and_reviewer(self):
        replies = iter([{"decision": "PASS", "summary": "implemented", "findings": [],
                         "_diagnostic": {"command_class": "codex exec implementer",
                                         "exit_code": 0, "stderr_tail": "NONE"}},
                        {"decision": "PASS", "summary": "review clean", "findings": [],
                         "_diagnostic": {"command_class": "codex exec reviewer",
                                         "exit_code": 0, "stderr_tail": "NONE"}}])
        with patch.object(orch, "get_issue", return_value=issue()), \
             patch.object(orch, "changed_files", return_value=[]), \
             patch.object(orch, "runtime_preflight", return_value=ready_runtime()), \
             patch.object(orch, "agent", side_effect=lambda *a: next(replies)), \
             patch.object(orch, "protected_check", return_value=(True, "PASS")), \
             patch.object(orch, "command", return_value=subprocess.CompletedProcess([], 0, "2 passed", "")):
            report = orch.run(args())
        self.assertEqual(report["state"], "DONE")
        self.assertEqual(report["attempts"], 1)
        self.assertEqual([x["step"] for x in report["evidence"] if x["step"].endswith("preflight")],
                         ["runtime preflight"])
        self.assertEqual([x["diagnostic"]["exit_code"] for x in report["evidence"]
                          if x["step"].startswith(("implementer", "reviewer"))], [0, 0])


if __name__ == "__main__":
    unittest.main()
