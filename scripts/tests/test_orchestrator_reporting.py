"""Owner-facing report layer preserves the existing technical result."""

import sys
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator_reporting import QUESTIONS, human_owner_summary  # noqa: E402
import orchestrator as orch  # noqa: E402


class OwnerReportTests(unittest.TestCase):
    def test_all_six_questions_and_plain_status(self):
        for state, status in (("READY", "준비 중"), ("DONE", "완료 후보"),
                              ("HUMAN_APPROVAL", "사람 확인 필요"),
                              ("TASK_PASS_WITH_KNOWN_GAPS", "완료 후보"),
                              ("FAILED", "추가 작업 필요")):
            with self.subTest(state=state):
                text = human_owner_summary({"state": state, "attempts": 1,
                                            "evidence": []})
                self.assertTrue(text.startswith("## 한눈에 보기\n"))
                for index, question in enumerate(QUESTIONS, 1):
                    self.assertEqual(text.count(f"### {index}. {question}"), 1)
                self.assertTrue(text.endswith(status))
                self.assertNotIn("Technical PASS", text)
                self.assertNotIn("baseline", text)

    def test_known_gap_is_not_described_as_full_completion(self):
        text = human_owner_summary({"state": "TASK_PASS_WITH_KNOWN_GAPS",
                                    "attempts": 1, "task_result": "PASS",
                                    "known_gaps": ["existing missing input"],
                                    "new_regressions": [], "evidence": []})
        self.assertIn("이전부터 있던 일부 검사는 여전히 통과하지 못했습니다", text)
        self.assertIn("이전부터 확인된 검사 공백이 남아 있습니다", text)
        self.assertIn("최종 승인", text)

    def test_declared_gate_that_now_passes_is_not_a_remaining_gap(self):
        text = human_owner_summary({"state": "DONE", "attempts": 1,
                                    "known_unavailable_gates": ["old declaration"],
                                    "known_gaps": [], "evidence": []})
        self.assertIn("현재 확인된 남은 문제는 없습니다", text)
        self.assertNotIn("검사 공백이 남아", text)

    def test_ready_does_not_claim_no_remaining_problems(self):
        text = human_owner_summary({"state": "READY", "attempts": 0,
                                    "evidence": []})
        self.assertIn("남은 문제를 판단할 수 없습니다", text)

    def test_new_problem_is_visible(self):
        text = human_owner_summary({"state": "FAILED", "attempts": 1,
                                    "new_regressions": ["new failure"], "evidence": []})
        self.assertIn("이번 변경으로 생긴 문제 1건", text)
        self.assertTrue(text.endswith("문제 발견"))

    def test_untrusted_issue_text_is_not_copied_to_owner_summary(self):
        report = {"state": "HUMAN_APPROVAL", "attempts": 1,
                  "reason": "client-secret@example.com — branch fixture", "evidence": []}
        text = human_owner_summary(report)
        self.assertNotIn("client-secret", text)
        self.assertNotIn("branch", text)
        self.assertIn("이 자동 요약만으로 승인하지 마세요", text)

    def test_issue_status_comment_puts_summary_before_technical_evidence(self):
        report = {"state": "TASK_PASS_WITH_KNOWN_GAPS",
                  "reason": "client-secret@example.com",
                  "attempts": 1, "known_gaps": ["old failure"],
                  "evidence": [{"step": "required checks", "status": "PASS"}]}
        captured = []

        def fake_command(argv, **_kwargs):
            captured.append(Path(argv[argv.index("--body-file") + 1]).read_text(
                encoding="utf-8"))
            return subprocess.CompletedProcess(argv, 0, "", "")

        with patch.object(orch, "command", side_effect=fake_command):
            self.assertIsNone(orch.comment("example/repo", 5, report))
        self.assertTrue(captured[0].startswith("## 한눈에 보기\n"))
        self.assertLess(captured[0].index("### 6. 지금 상태는?"),
                        captured[0].index("## Developer Details"))
        self.assertIn("required checks: PASS", captured[0])
        self.assertNotIn("client-secret", captured[0])


if __name__ == "__main__":
    unittest.main()
