"""F-4b-lite: [가이드 체크] 시트 — 산출물 부착 (UI 변경 없음).

활성 규칙 = F-4a 검수 반영본(guide_rules_2026.json, approved=true만).
검증형 4종은 기계 판정, 나머지는 "판단필요" 나열 — 자동은 추천,
확정은 회계사. 미승인 조항은 사용하지 않는다.

검증형 4종 (판정 입력은 조립층이 dict로 전달 — 입력이 없으면 해당
규칙은 '판단필요(입력 없음)'로 정직 노출):
- 5.Ⅱ.4(1)나  member 중복: axis_members {축: [member...]} — 같은 축
  하위 중복 구성 검사
- 5.Ⅱ.4(1)라  도메인 합계열: table_headers {표: [열 라벨...]} —
  '합계' 열 별도 구성 검사 (5.Ⅰ.2(2)가 동일 취지)
- 5.Ⅱ.3(1)아  유동·비유동 축: axes_used [(축, 사용처 element/role)] —
  변동(Changes/Movement/변동) 외 사용 검사
- 5.Ⅱ.5(2)   기초·기말 행: open_close [(표, 기초 element, 기말
  element)] — 동일 행 사용 검사
"""
import io
import json
import os
import re

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from .cellsafe import put as _safe_put

_BOLD = Font(bold=True)
_HDR_FILL = PatternFill("solid", start_color="D9E1F2")
_FALSE_FILL = PatternFill("solid", start_color="FFC7CE")
_WARN_FILL = PatternFill("solid", start_color="FFEB9C")

_ASSET = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "assets", "guide",
    "guide_rules_2026.json")

MACHINE_RULES = ("5.Ⅱ.4(1)나", "5.Ⅱ.4(1)라", "5.Ⅱ.3(1)아", "5.Ⅱ.5(2)")
_CNC_RE = re.compile(r"CurrentAndNoncurrent|CurrentNoncurrent", re.I)
_CHANGE_RE = re.compile(r"Changes?|Movement|변동", re.I)
# 5.Ⅱ.3(1)아 예외 화이트리스트 — 회계사 조건부 승인(2026-08-03):
# 2026 배포용 전수 실측상 유동/비유동 계열 '변동 전용' 표준 축은 이 1개뿐.
# 화이트리스트 외 변동성 이름 축(표준 신규·확장)은 자동 면제 금지 —
# '판단필요(오탐 후보)' 정지 (통제 4호). 선별·예외는 축(dimension)에만
# 적용 — axes_used 입력은 컨텍스트 explicitMember의 dimension 속성에서만
# 수집되므로 비축 요소(Table 등)는 구조적으로 배제된다.
CNC_CHANGE_AXIS_WHITELIST = frozenset({
    "dart_ClassesOfCurrentAndNoncurrentValuesUsedForChangesIn"
    "AssetAndLiabilityAxis",
})


def load_active_rules(path=None):
    """승인(approved) 규칙만 — 미승인 조항 비활성 원칙."""
    data = json.load(io.open(path or _ASSET, encoding="utf-8"))
    return [r for r in data["rules"] if r.get("approved")]


def machine_check(rule_id, inputs):
    """검증형 4종 판정. 반환: [(적용 지점, 판정, 비고)] — 입력 없으면
    [('', '판단필요', '입력 없음 — 산출물에서 판정 대상 미제공')]."""
    out = []
    if rule_id == "5.Ⅱ.4(1)나":
        am = inputs.get("axis_members")
        if am is None:
            return [("", "판단필요", "입력 없음")]
        for axis, members in sorted(am.items()):
            dup = sorted({m for m in members if members.count(m) > 1})
            if dup:
                out.append((axis, "위반",
                            f"member 중복: {', '.join(dup[:3])}"))
            else:
                out.append((axis, "통과", ""))
    elif rule_id == "5.Ⅱ.4(1)라":
        th = inputs.get("table_headers")
        dim = inputs.get("domain_in_members")
        if th is None and dim is None:
            return [("", "판단필요", "입력 없음")]
        # 제출파일 단독 판정(F-4b-lite+): 도메인이 member로도 구성
        # = 합계열 별도 구성 (도메인이 이미 합계열 역할)
        for spot, is_dup in sorted((dim or {}).items()):
            if is_dup:
                out.append((spot, "위반",
                            "도메인이 member로 재등장 — 합계열 별도 구성"))
            else:
                out.append((spot, "통과", ""))
        for table, headers in sorted((th or {}).items()):
            bad = [h for h in headers
                   if str(h or "").replace(" ", "") in ("합계", "총계")]
            if bad:
                out.append((table, "위반",
                            "합계열 별도 구성 — 도메인이 합계열 역할"))
            else:
                out.append((table, "통과", ""))
    elif rule_id == "5.Ⅱ.3(1)아":
        au = inputs.get("axes_used")
        if au is None:
            return [("", "판단필요", "입력 없음")]
        for axis, where in sorted(au):
            if not _CNC_RE.search(axis):
                continue
            # 조건부 승인(2026-08-03): 예외 = 표준 축 화이트리스트 1개뿐
            if axis in CNC_CHANGE_AXIS_WHITELIST:
                out.append((f"{axis} @ {where}", "통과",
                            "변동 전용 표준 축 — 예외 허용(승인)"))
                continue
            if _CHANGE_RE.search(where or ""):
                # 경로 ii(element명 기반 예외) — 현행 유지 (승인 4호)
                out.append((f"{axis} @ {where}", "통과",
                            "변동 공시 — 예외 허용"))
            elif _CHANGE_RE.search(axis):
                # 화이트리스트 외 변동성 이름 축 — 자동 면제 금지
                out.append((f"{axis} @ {where}", "판단필요",
                            "오탐 후보 — 변동성 이름이나 화이트리스트 외"
                            " (회계사 확인)"))
            else:
                out.append((f"{axis} @ {where}", "위반",
                            "유동/비유동 구분은 행으로 — 축 사용 불가"))
        if not out:
            out.append(("(유동·비유동 축 미사용)", "통과", ""))
    elif rule_id == "5.Ⅱ.5(2)":
        oc = inputs.get("open_close")
        if oc is None:
            return [("", "판단필요", "입력 없음")]
        for table, open_e, close_e in oc:
            if open_e == close_e:
                out.append((table, "통과", ""))
            else:
                out.append((table, "위반",
                            f"기초({open_e}) ≠ 기말({close_e}) 행"))
    return out or [("", "판단필요", "입력 없음")]


def _scope_hit(rule, scope):
    """규칙의 대상 매칭 키가 산출물 범위(scope)에 해당하는가."""
    tgt = rule["target"]
    if tgt.startswith("주석:"):
        key = tgt.split(":", 1)[1]
        return any(key.replace(" ", "") in str(t).replace(" ", "")
                   for t in scope.get("note_titles", []))
    return True                                 # role/표/축/행/Fact 일반 규칙


def attach_guide_check(xlsx_path, inputs=None, scope=None, rules=None):
    """산출물 엑셀에 [가이드 체크] 시트 부착 (후처리 — 기존 함수 무수정).

    inputs: 검증형 4종 판정 입력 (없으면 전부 '판단필요')
    scope: {"note_titles": [...]} — Ⅲ절 규칙의 해당/비해당 판별
    반환: 요약 dict {rows, machine, violations, need_judge, na, fill_rate}
    """
    inputs = inputs or {}
    scope = scope or {}
    write_failures = []                         # H-2: 기입 불가 축적
    rules = rules if rules is not None else load_active_rules()
    wb = load_workbook(xlsx_path)
    name = "가이드 체크"
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)
    ws.append(["2026 XBRL 작성가이드 체크 — 활성(승인) 규칙 "
               f"{len(rules)}조항 기준"])
    _safe_put(ws, 1, 1, font=Font(bold=True, size=12),
              failures=write_failures, what="제목 서식")
    ws.append(["검증형 4종은 기계 판정, 나머지는 '판단필요' — 자동은 "
               "추천, 확정은 회계사. 근거 페이지는 2026 작성가이드 기준"])
    _safe_put(ws, 2, 1, fill=_WARN_FILL,
              failures=write_failures, what="안내 서식")
    ws.append([])
    ws.append(["조항ID", "유형", "요지", "p.", "적용 지점", "판정", "비고"])
    hr = ws.max_row
    for c in ws[hr]:
        c.font = _BOLD
        c.fill = _HDR_FILL

    stats = {"rows": 0, "machine": 0, "violations": 0,
             "need_judge": 0, "na": 0, "write_failures": write_failures}
    for r in rules:
        if r["id"] in MACHINE_RULES:
            for spot, verdict, note in machine_check(r["id"], inputs):
                ws.append([r["id"], r["type"], r["summary"], r["page"],
                           spot, verdict, note])
                stats["rows"] += 1
                if verdict in ("통과", "위반"):
                    stats["machine"] += 1
                if verdict == "위반":
                    stats["violations"] += 1
                    for c in ws[ws.max_row]:
                        c.fill = _FALSE_FILL
                elif verdict == "판단필요":
                    stats["need_judge"] += 1
                    _safe_put(ws, ws.max_row, 6, fill=_WARN_FILL,
                              failures=write_failures, what="판정 서식")
        else:
            if _scope_hit(r, scope):
                verdict = "판단필요"
                stats["need_judge"] += 1
            else:
                verdict = "해당없음"
                stats["na"] += 1
            ws.append([r["id"], r["type"], r["summary"], r["page"],
                       r["target"], verdict, ""])
            stats["rows"] += 1
            if verdict == "판단필요":
                _safe_put(ws, ws.max_row, 6, fill=_WARN_FILL,
                          failures=write_failures, what="판정 서식")
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    covered = stats["machine"] + stats["need_judge"]
    stats["fill_rate"] = round(covered / stats["rows"], 4) \
        if stats["rows"] else None
    ws.append([])
    ws.append([f"충전율(기계 판정+판단필요 노출): {covered}/"
               f"{stats['rows']} ({stats['fill_rate']:.1%}) · 위반 "
               f"{stats['violations']} · 해당없음 {stats['na']}"])
    ws.cell(ws.max_row, 1).font = _BOLD
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 9
    ws.column_dimensions["C"].width = 60
    ws.column_dimensions["D"].width = 6
    ws.column_dimensions["E"].width = 34
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 34
    ws.freeze_panes = f"A{hr + 1}"
    wb.save(xlsx_path)
    return stats
