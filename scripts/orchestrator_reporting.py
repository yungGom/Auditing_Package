"""Plain-Korean owner layer for the existing machine-readable report."""

from __future__ import annotations

from typing import Any


QUESTIONS = (
    "이번에 무엇을 했나?",
    "실제로 무엇이 달라졌나?",
    "확인 결과는 어땠나?",
    "아직 남은 문제는?",
    "내가 결정해야 할 게 있나?",
    "지금 상태는?",
)

STATUS = {
    "READY": "준비 중",
    "IN_PROGRESS": "개발 중",
    "HUMAN_APPROVAL": "사람 확인 필요",
    "DONE": "완료 후보",
    "TASK_PASS_WITH_KNOWN_GAPS": "완료 후보",
}

def human_owner_summary(report: dict[str, Any]) -> str:
    """Explain known outcomes without promoting missing or failed checks to a pass."""
    state = report.get("state", "FAILED")
    attempts = report.get("attempts", 0)
    if state == "READY":
        done = "요청 내용을 확인했습니다. 아직 실제 작업은 시작하지 않았습니다."
        changed = "아직 달라진 결과는 없습니다."
        checks = "검사는 아직 실행하지 않았습니다."
    elif state == "HUMAN_APPROVAL":
        done = "요청을 검토하다가 사람의 판단이 필요한 단계에서 멈췄습니다."
        changed = "결정 전이라 결과를 확정하지 않았습니다."
        checks = "필요한 확인을 모두 마치지 않았습니다."
    elif state in {"DONE", "TASK_PASS_WITH_KNOWN_GAPS"}:
        done = "요청한 변경과 확인을 마쳤습니다."
        changed = "요청한 변경을 적용했습니다. 실제 업무 결과는 사람의 확인이 필요합니다."
        checks = ("이번 작업에 필요한 검사는 통과했습니다. "
                  "이전부터 있던 일부 검사는 여전히 통과하지 못했습니다."
                  if state == "TASK_PASS_WITH_KNOWN_GAPS" else
                  "필요한 검사와 독립 검토가 통과했습니다.")
    else:
        done = ("요청된 작업을 진행했지만 완료하지 못했습니다." if attempts else
                "요청을 확인했지만 작업을 시작하지 못했습니다.")
        changed = "변경 결과를 확정하지 못했습니다."
        if report.get("new_regressions"):
            checks = "이번 변경으로 새 문제가 발견됐습니다."
        elif report.get("task_result") == "FAIL":
            checks = "이번 작업에 필요한 검사가 실패했습니다."
        elif any(step.get("status") == "NOT_RUN" for step in report.get("evidence", [])):
            checks = "필요한 검사를 실행하지 못했습니다."
        else:
            checks = "필요한 확인을 끝내지 못했습니다."

    if report.get("new_regressions"):
        remaining = f"이번 변경으로 생긴 문제 {len(report['new_regressions'])}건이 남았습니다."
    elif report.get("known_gaps"):
        remaining = "이전부터 확인된 검사 공백이 남아 있습니다."
    elif state in {"READY", "IN_PROGRESS"}:
        remaining = "아직 확인을 마치지 않아 남은 문제를 판단할 수 없습니다."
    elif state == "FAILED":
        remaining = "완료를 막은 문제가 남아 있습니다."
    elif state == "HUMAN_APPROVAL":
        remaining = "사람의 판단 전까지 작업을 마칠 수 없습니다."
    else:
        remaining = "현재 확인된 남은 문제는 없습니다."

    if state == "HUMAN_APPROVAL":
        owner_decision = ("있음. 업무 판단이나 보호된 기준의 변경 여부를 결정해야 합니다. "
                          "선택지와 영향은 별도의 쉬운 한국어 승인 요청서에서 확인해 주세요. "
                          "이 자동 요약만으로 승인하지 마세요.")
    elif state in {"DONE", "TASK_PASS_WITH_KNOWN_GAPS"}:
        owner_decision = "있음. 실제 업무 결과를 최종 승인할지 확인해 주세요."
    else:
        owner_decision = "현재 요청된 최종 승인 결정은 없습니다."

    status = STATUS.get(state, "문제 발견" if report.get("new_regressions")
                        else "추가 작업 필요")
    answers = (done, changed, checks, remaining, owner_decision, status)
    lines = ["## 한눈에 보기", ""]
    for index, (question, answer) in enumerate(zip(QUESTIONS, answers), 1):
        lines.extend((f"### {index}. {question}", "", answer, ""))
    return "\n".join(lines).rstrip()
