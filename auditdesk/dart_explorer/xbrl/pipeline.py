"""XBRL 원클릭 파이프라인 (패치 B-3).

fnlttXbrl.xml API로 재무제표원본(XBRL) ZIP 수신 → 압축해제(인스턴스 +
lab-ko.xml 동일 폴더) → xbrl_extract.py 무수정 입력 → 엑셀 산출.
--diff 지정 시 당기·전기 수신 후 xbrl_diff 버전대사까지 자동.

주의 (지시서 B-3):
- XBRL은 정기보고서(사업/반기/분기) 첨부 — 사업보고서 rcept_no로 요청
  (감사보고서 접수번호 아님)
- 비상장 소규모는 XBRL 미제출 → "결과 없음" 명확 처리 (XbrlNotAvailable)
- 캐시 히트 시 재다운로드 금지 (요청 한도 일 20,000건)
"""
import glob
import os
import re
import zipfile

from ..client.opendart import OpenDartClient, OpenDartError

# 보고서 코드 (fnlttXbrl reprt_code)
REPRT = {"annual": "11011", "half": "11012", "q1": "11013", "q3": "11014"}
# 사업연도 → 정기공시 상세유형
DETAIL = {"annual": "A001", "half": "A002", "q1": "A003", "q3": "A003"}


class XbrlNotAvailable(Exception):
    """XBRL 미제출 (비상장 소규모 등) — 결과 없음의 명확한 신호."""


def find_periodic_rcept(cli: OpenDartClient, corp_code: str, year: int,
                        report: str = "annual"):
    """사업연도 year의 정기보고서 접수번호 탐색.

    사업보고서(YYYY.12)는 이듬해 봄에 접수되므로 year+1 범위를 검색하고
    report_nm의 "(YYYY." 표기로 대상 연도를 확정한다.
    """
    docs = cli.search(corp_code=corp_code, bgn_de=f"{year + 1}0101",
                      end_de=f"{year + 1}1231",
                      pblntf_detail_ty=DETAIL[report])
    for d in docs:
        if f"({year}." in d.get("report_nm", ""):
            return d
    # 12월 결산이 아닌 회사 등: 같은 연도 내 접수 검색 폴백
    docs = cli.search(corp_code=corp_code, bgn_de=f"{year}0101",
                      end_de=f"{year}1231", pblntf_detail_ty=DETAIL[report])
    for d in docs:
        if f"({year}" in d.get("report_nm", ""):
            return d
    return None


def download_xbrl(cli: OpenDartClient, corp_code: str, rcept_no: str,
                  reprt_code: str = REPRT["annual"]):
    """fnlttXbrl ZIP 수신 (영구 캐시). 미제출이면 XbrlNotAvailable.

    오류 페이로드(XML/JSON)는 캐시에 남기지 않는다.
    """
    rel = f"xbrl/{corp_code}/{rcept_no}_{reprt_code}.zip"
    data, path = cli.fetch_binary(
        "fnlttXbrl.xml", {"rcept_no": rcept_no, "reprt_code": reprt_code},
        rel)
    if data[:2] != b"PK":                      # ZIP 아님 → 오류 페이로드
        os.remove(path)
        text = data[:500].decode("utf-8", "replace")
        m = re.search(r"<status>(\d+)</status>", text)
        status = m.group(1) if m else "?"
        msg = re.search(r"<message>([^<]*)</message>", text)
        msg = msg.group(1) if msg else text
        if status in ("013", "014"):   # 013=조회 없음, 014=파일 없음
            raise XbrlNotAvailable(
                f"XBRL 미제출 (rcept_no={rcept_no}, status={status}): {msg} — "
                "XBRL 재무제표를 제출하지 않은 보고서입니다.")
        raise OpenDartError(f"fnlttXbrl {status}: {msg}")
    return data, path


def unpack_xbrl(zip_path: str) -> str:
    """ZIP 해제 → 인스턴스(.xbrl)와 lab-ko.xml이 같은 폴더에 위치."""
    folder = zip_path.rsplit(".", 1)[0]
    os.makedirs(folder, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(folder)
    instances = glob.glob(os.path.join(folder, "*.xbrl"))
    if not instances:
        raise OpenDartError(f"압축 안에 .xbrl 인스턴스가 없습니다: {folder}")
    return folder


def instance_path(folder: str) -> str:
    return sorted(glob.glob(os.path.join(folder, "*.xbrl")))[0]


def has_ko_labels(folder: str) -> bool:
    return bool(glob.glob(os.path.join(folder, "*_lab-ko.xml"))
                or glob.glob(os.path.join(folder, "*lab*ko*.xml")))


def extract_to_excel(folder: str, out_xlsx: str) -> int:
    """xbrl_extract.py 무수정 호출 (폴더 내 lab-ko 자동 탐색). 행 수 반환."""
    from .xbrl_extract import build_excel, extract
    rows = extract(instance_path(folder))
    build_excel(rows, out_xlsx)
    return len(rows)


def run(corp: str, year: int, diff_year: int = None, report: str = "annual",
        out_dir: str = None, cli: OpenDartClient = None) -> dict:
    """원클릭: 수신 → 해제 → extract [→ diff]. 결과 경로 dict 반환."""
    cli = cli or OpenDartClient()
    corp_code = corp if (corp.isdigit() and len(corp) == 8) \
        else cli.resolve_corp_code(corp)
    out_dir = out_dir or os.path.join(cli.cache.root, "xbrl", corp_code)
    os.makedirs(out_dir, exist_ok=True)
    result = {"corp_code": corp_code}

    def _one(y):
        doc = find_periodic_rcept(cli, corp_code, y, report)
        if doc is None:
            raise XbrlNotAvailable(
                f"{y}년 {report} 정기보고서를 찾을 수 없습니다 "
                f"(corp_code={corp_code}).")
        _, zpath = download_xbrl(cli, corp_code, doc["rcept_no"],
                                 REPRT[report])
        return doc, unpack_xbrl(zpath)

    doc, folder = _one(year)
    result.update(rcept_no=doc["rcept_no"], report_nm=doc["report_nm"],
                  folder=folder, has_ko_labels=has_ko_labels(folder))
    xlsx = os.path.join(out_dir, f"{corp_code}_{year}_{report}_추출.xlsx")
    result["rows"] = extract_to_excel(folder, xlsx)
    result["xlsx"] = xlsx

    if diff_year is not None:
        doc2, folder2 = _one(diff_year)
        result.update(diff_rcept_no=doc2["rcept_no"], diff_folder=folder2)
        from .xbrl_diff import version_compare, write_excel
        from .xbrl_extract import extract as x_extract
        rows_old = x_extract(instance_path(folder2))
        rows_new = x_extract(instance_path(folder))
        diff_rows = version_compare(rows_old, rows_new)
        diff_xlsx = os.path.join(
            out_dir, f"{corp_code}_{diff_year}vs{year}_버전비교.xlsx")
        write_excel(diff_rows, diff_xlsx, None)
        result.update(diff_rows=len(diff_rows), diff_xlsx=diff_xlsx)
    return result
