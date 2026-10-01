"""Conservative, structured task-versus-repository check classification."""
from __future__ import annotations

import re
import json

TASK_PATH = re.compile(r"(?:auditdesk/(?:dsd_workbench/dsd_tool|dart_explorer|backend)/tests|scripts/tests)/test_[A-Za-z0-9_]+\.py$")
FAILURE = re.compile(r"(?m)^(?:FAILED|ERROR)\s+(\S+)")
SUMMARY = re.compile(r"(\d+)\s+(passed|failed|skipped|errors|error)\b")
SKIP_SITE = re.compile(r"(?m)^SKIPPED\s+\[\d+\]\s+(.+?\.py:\d+)(?::|\s|$)")
AUDITDESK = re.compile(r"\[AuditDesk\] pytest=(\d+), webui build=(\d+)")
HARNESS = re.compile(r"Harness result:\s*([^\r\n]+)")
EXPECTED_COMPONENTS = {
    "scripts/test_auditdesk.py": {"auditdesk_pytest", "webui_build"},
    "scripts/test_all.py": {"auditdesk", "dsd_footing", "auditdesk_pytest", "webui_build"},
}


def section(body: str, title: str) -> str:
    match = re.search(rf"(?im)^##\s+{re.escape(title)}\s*$", body)
    if not match:
        return ""
    tail = body[match.end():]
    next_heading = re.search(r"(?m)^##\s+", tail)
    return tail[:next_heading.start() if next_heading else None].strip()


def task_paths(body: str) -> list[str]:
    """Issue-declared pytest files only; never execute Issue-provided commands."""
    value = section(body, "Task required checks")
    if not value:
        # Pilot #1's approved contract names its two new files in the
        # acceptance criterion beginning "Add only". Keep this fallback narrow:
        # other mentioned tests are not silently promoted to task checks.
        value = "\n".join(line for line in section(body, "Acceptance criteria").splitlines()
                          if re.match(r"^\s*-\s+Add only\s+", line, re.I))
        if not value:
            return []
    paths = re.findall(r"`([^`]+)`", value)
    if section(body, "Task required checks"):
        if not paths or any(not TASK_PATH.fullmatch(path) for path in paths):
            raise ValueError("Task required checks must list repository test_*.py paths in backticks")
        return list(dict.fromkeys(paths))
    return list(dict.fromkeys(path for path in paths if TASK_PATH.fullmatch(path)))


def known_gate_ids(body: str) -> set[str]:
    value = section(body, "Known unavailable gates")
    if not value:
        value = section(body, "Reproduction")
    return set(re.findall(r"`([^\r\n`]+::[^\r\n`]+)`", value))


def normalize_node(node: str) -> str:
    return node.replace("\\", "/").removeprefix("auditdesk/")


def declared_node(node: str, known: set[str]) -> bool:
    return any(node == item or node.endswith("/" + item) for item in known)


def summarize(script: str, result) -> dict:
    output = result.stdout + result.stderr
    marker = "HARNESS_REPORT_JSON:"
    if marker in output:
        try:
            report = json.loads(output.rsplit(marker, 1)[1].splitlines()[0])
            checks = report["technical_checks"]
            counts = checks["auditdesk_python"].get("counts", {})
            component = lambda key: 0 if checks[key]["status"] == "PASS" else 1
            components = {"auditdesk_pytest": component("auditdesk_python"),
                          "webui_build": component("webui_build"),
                          "auditdesk": max(component("auditdesk_python"), component("webui_build")),
                          "dsd_footing": component("dsd_footing")}
            return {"step": script, "status": "PASS" if result.returncode == 0 and report["technical_gate"] == "PASS" else "FAIL",
                    "exit_code": result.returncode, "passed": counts.get("PASS", 0),
                    "failed": counts.get("FAIL", 0), "skipped": counts.get("SKIP", 0), "errors": 0,
                    "failures": [n for n,r in checks["auditdesk_python"].get("checks", {}).items() if r["status"] == "FAIL"],
                    "skip_sites": [n for n,r in checks["auditdesk_python"].get("checks", {}).items() if r["status"] == "SKIP"],
                    "components": components, "real_material_compatibility": report["real_material_compatibility"],
                    "human_business_acceptance": "PENDING"}
        except (ValueError, KeyError, TypeError):
            return {"step":script,"status":"FAIL","exit_code":result.returncode,"passed":0,"failed":0,"skipped":0,"errors":1,"failures":[],"skip_sites":[],"components":{}}
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    for number, kind in SUMMARY.findall(output):
        key = "errors" if kind in {"error", "errors"} else kind
        counts[key] = max(counts[key], int(number))
    components = {}
    match = AUDITDESK.search(output)
    if match:
        components["auditdesk_pytest"] = int(match.group(1))
        components["webui_build"] = int(match.group(2))
    match = HARNESS.search(output)
    if match:
        components.update({name: 0 if status == "PASS" else 1
                           for name, status in re.findall(
                               r"(auditdesk|dsd_footing)=(PASS|FAIL)", match.group(1))})
    return {"step": script, "status": "PASS" if result.returncode == 0 else "FAIL",
            "exit_code": result.returncode, **counts,
            "failures": sorted({normalize_node(x) for x in FAILURE.findall(output)}),
            "skip_sites": sorted({normalize_node(x) for x in SKIP_SITE.findall(output)}),
            "components": components}


def compare(before: list[dict], after: list[dict], declared: set[str]) -> tuple[list[dict], list[str], list[str]]:
    """Recognize only declared, observed baseline failures with unchanged skip evidence."""
    gaps = []
    regressions = []
    unclassified = []
    known = {normalize_node(x) for x in declared}
    for prior, current in zip(before, after, strict=True):
        name = current["step"]
        if prior["step"] != name:
            raise ValueError("Regression script order changed")
        for component in EXPECTED_COMPONENTS.get(name, set()):
            if component not in prior["components"]:
                unclassified.append(f"{name}: baseline {component} result unavailable")
            elif component not in current["components"]:
                regressions.append(f"{name}: {component} result unavailable after implementation")
        compatibility = current.get("real_material_compatibility")
        if compatibility and compatibility["status"] != "PASS":
            gaps.append({"script": name, "status": compatibility["status"],
                         "real_material_compatibility": compatibility})
        old_compat = prior.get("real_material_compatibility", {}).get("checks", {})
        for node, row in (compatibility or {}).get("checks", {}).items():
            if row["status"] == "FAIL" and old_compat.get(node, {}).get("status") != "FAIL":
                regressions.append(f"{name}: new compatibility failure {node}")
            if old_compat.get(node, {}).get("status") == "PASS" and row["status"] != "PASS":
                regressions.append(f"{name}: compatibility PASS lost {node}")
        old_failed = set(prior["failures"])
        new_failed = set(current["failures"])
        new_ids = new_failed - old_failed
        undeclared = {node for node in new_failed if not declared_node(node, known)}
        if prior["status"] == "PASS" and current["status"] == "FAIL":
            regressions.append(f"{name}: PASS became FAIL")
        if new_ids:
            regressions.append(f"{name}: new failing tests {sorted(new_ids)}")
        if current["failed"] > prior["failed"] or current["errors"] > prior["errors"]:
            regressions.append(f"{name}: failure or error count increased")
        if current["passed"] < prior["passed"]:
            regressions.append(f"{name}: passed test count decreased")
        if undeclared:
            unclassified.append(f"{name}: baseline failures not declared known {sorted(undeclared)}")
        if current["skipped"] > prior["skipped"]:
            regressions.append(f"{name}: skipped count increased")
        old_sites, new_sites = set(prior["skip_sites"]), set(current["skip_sites"])
        if current["skipped"] and (not old_sites or not new_sites):
            unclassified.append(f"{name}: skip identities unavailable for comparison")
        elif new_sites - old_sites:
            regressions.append(f"{name}: new skipped sites {sorted(new_sites - old_sites)}")
        for component, code in current["components"].items():
            if prior["components"].get(component) == 0 and code != 0:
                regressions.append(f"{name}: {component} PASS became FAIL")
        if current["status"] == "FAIL" and not new_failed and not current["components"]:
            unclassified.append(f"{name}: baseline failure identity unavailable")
        for component, code in current["components"].items():
            if (code and prior["components"].get(component)
                    and f"{name}#{component}" not in known
                    and not (component in {"auditdesk_pytest", "auditdesk"}
                             and new_failed and
                             all(declared_node(node, known) for node in new_failed))):
                unclassified.append(f"{name}: baseline component {component} not declared known")
        if current["status"] == "FAIL" or current["skipped"]:
            gaps.append({"script": name, "status": current["status"],
                         "failed_tests": sorted(node for node in new_failed
                                                if declared_node(node, known)),
                         "skipped": current["skipped"],
                         "skip_sites": current["skip_sites"],
                         "components": current["components"]})
    return gaps, list(dict.fromkeys(regressions)), list(dict.fromkeys(unclassified))
