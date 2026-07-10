"""DART 편집기 버전 관리 (패치 A-3).

meta.xml의 GENERATOR editver를 읽고, dsd_workbench/KNOWN_VERSIONS.md의
확인된 버전 목록과 대조한다. 미확인 버전이면 경고를 낸다.
KNOWN_VERSIONS.md의 표는 batch_validate가 자동 갱신한다.
"""
import datetime
import os
import re

from .zipsplice import read_entry

_EDITVER_RE = re.compile(r'editver="([^"]*)"')
_DOCVER_RE = re.compile(r'docver="([^"]*)"')
_SCHEMA_RE = re.compile(r'schema="([^"]*)"')

_AUTO_START = "<!-- AUTO-TABLE-START -->"
_AUTO_END = "<!-- AUTO-TABLE-END -->"

UNKNOWN_WARNING = (
    "⚠ 미확인 DART 편집기 버전(editver={ver})입니다. "
    "이 버전에서 G2(무변경 바이트 동일)가 검증되지 않았습니다 — "
    "batch_validate를 재실행하여 KNOWN_VERSIONS.md를 갱신하세요: "
    "python -m dsd_tool.tests.batch_validate")

# 새 편집기 버전 출시 시 절차 (KNOWN_VERSIONS.md에도 명문화되어 있음).
# 방침(불변): editver/docver는 절대 수정·창작하지 않는다 — 밑바닥 생성 DSD는
# dart4.xsd 스키마 검증에 실패한다(실측). 버전 변환은 DART 편집기 고유 기능이며
# repack 산출물은 항상 뼈대 DSD의 버전을 그대로 상속한다.
NEW_VERSION_PROCEDURE = """\
1. 대표 DSD 1개(한빛정밀 클린본)를 새 편집기에서 열기 → 저장
   → 편집기가 변환한 파일 확보 (예: *_6_1변환.dsd)
2. 변환본을 fixtures/real/에 세대 추가
3. batch_validate: 변환본 extract → 무변경 repack → G2(내용 동일) 확인
4. 통과 → KNOWN_VERSIONS.md에 행 추가 (editver, 확인일, G2 결과)
   실패 → 직렬화 차이 리포트 후 진행 중단 (기획 세션 회신)
5. 이후 신버전 뼈대 사용 가능 (구버전 DSD는 편집기 하위호환으로 계속 열림)"""


def known_versions_path() -> str:
    workbench = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(workbench, "KNOWN_VERSIONS.md")


def read_version_info(data: bytes) -> dict:
    """DSD 바이트에서 meta.xml의 버전 정보 추출."""
    meta = read_entry(data, "meta.xml")
    if meta is None:
        return {"editver": None, "docver": None, "schema": None}
    text = meta.decode("utf-8", "replace")
    return {
        "editver": (_EDITVER_RE.search(text) or [None, None])[1],
        "docver": (_DOCVER_RE.search(text) or [None, None])[1],
        "schema": (_SCHEMA_RE.search(text) or [None, None])[1],
    }


def known_versions() -> set:
    """KNOWN_VERSIONS.md 표에서 확인된 editver 집합."""
    path = known_versions_path()
    if not os.path.exists(path):
        return set()
    versions = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\|\s*(\d+(?:\.\d+)+)\s*\|", line)
            if m:
                versions.add(m.group(1))
    return versions


def is_known(editver) -> bool:
    return editver is not None and editver in known_versions()


def known_versions_table() -> list:
    """KNOWN_VERSIONS.md 표를 [{editver, files, g2, date}] 목록으로 파싱.

    E-0 대시보드의 "확인된 편집기 버전" 카드가 이 함수로 읽어서 보여준다
    (신규 비즈니스 로직 없음 — 기존 파일을 파싱해 보여주기만).
    """
    path = known_versions_path()
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(
                r"^\|\s*(\d+(?:\.\d+)+)\s*\|\s*(\d+)\s*\|\s*(\S+)\s*\|"
                r"\s*(\S+)\s*\|", line)
            if m:
                rows.append({"editver": m.group(1), "files": int(m.group(2)),
                            "g2": m.group(3), "date": m.group(4)})
    return rows


def g2_smoke(dsd_path, work_dir=None) -> dict:
    """즉석 G2 스모크: extract(무변경) → repack(keep-cr) → 바이트 비교.

    version-check가 "이 파일 자체"에서 즉시 검증하는 용도 — batch_validate
    처럼 KNOWN_VERSIONS.md를 갱신하지는 않는다(그건 배치 검증의 몫).
    """
    import shutil
    import tempfile

    from .excel_out import extract
    from .repack import repack

    tmp = work_dir or tempfile.mkdtemp(prefix="version_check_")
    try:
        xlsx = os.path.join(tmp, "_g2_smoke.xlsx")
        out = os.path.join(tmp, "_g2_smoke_out.dsd")
        extract(dsd_path, xlsx, keep_note_numbers=True)
        res = repack(xlsx, dsd_path, out, clean_cr=False,
                     record_history=False)
        with open(dsd_path, "rb") as f1, open(out, "rb") as f2:
            identical = f1.read() == f2.read()
        return {"changes": len(res["changes"]), "byte_identical": identical}
    finally:
        if work_dir is None:
            shutil.rmtree(tmp, ignore_errors=True)


def update_known_versions(results: dict):
    """batch_validate 결과로 KNOWN_VERSIONS.md 표 갱신.

    results: {editver: {"files": int, "g2_pass": bool}}
    기존 표의 다른 버전 행은 유지하고 새 결과를 병합한다.
    """
    path = known_versions_path()
    merged = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(
                    r"^\|\s*(\d+(?:\.\d+)+)\s*\|\s*(\d+)\s*\|\s*(\S+)\s*\|"
                    r"\s*(\S+)\s*\|", line)
                if m:
                    merged[m.group(1)] = {
                        "files": int(m.group(2)),
                        "g2": m.group(3),
                        "date": m.group(4),
                    }
    today = datetime.date.today().isoformat()
    for ver, r in results.items():
        if not ver:
            continue
        merged[ver] = {
            "files": r["files"],
            "g2": "PASS" if r["g2_pass"] else "FAIL",
            "date": today,
        }

    table = [
        _AUTO_START,
        "| editver | 확인 파일 수 | G2(무변경 바이트 동일) | 최근 확인 |",
        "|---------|-------------|------------------------|-----------|",
    ]
    for ver in sorted(merged):
        r = merged[ver]
        table.append(f"| {ver} | {r['files']} | {r['g2']} | {r['date']} |")
    table.append(_AUTO_END)
    table_text = "\n".join(table)

    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            doc = f.read()
        if _AUTO_START in doc and _AUTO_END in doc:
            pre = doc.split(_AUTO_START)[0]
            post = doc.split(_AUTO_END)[1]
            doc = pre + table_text + post
        else:
            doc = doc.rstrip() + "\n\n" + table_text + "\n"
    else:
        doc = (
            "# DART 편집기 버전 관리 (KNOWN_VERSIONS)\n\n"
            "dsd_tool이 G2(무변경 바이트 동일)를 검증한 DART 편집기 버전 목록.\n"
            "아래 표는 `python -m dsd_tool.tests.batch_validate` 실행 시 자동 "
            "갱신된다.\n"
            "extract 시 이 목록에 없는 editver를 만나면 경고가 출력된다.\n\n"
            + table_text + "\n\n"
            "## 수동 메모\n\n"
            "- 지시서에 언급된 5.106 / 5.107은 아직 픽스처 미확보 — 해당 버전 "
            "DSD 확보 시 fixtures/real에 넣고 batch_validate 재실행.\n"
            "- docver는 문서 버전(4.1=구형, 3.5=DART 6.0 변환본에서 관찰)으로 "
            "editver와 별개.\n")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    return path
