"""D-3a: 계정과목 매핑 코퍼스 구축 (전업종, 주기 실행).

상장사 전체 목록(corpCode) → 사업보고서 XBRL 일괄 수신(B-3 재사용, 영구 캐시)
→ 인스턴스별 element 사용 실태를 mapping_corpus.sqlite에 적재.

- usages: (corp_code, element_id, 회사 라벨(lab-ko), Role 코드들, 차원 문맥,
  팩트 수, 확장 여부) — 사용 회사수는 조회 시 집계
- extensions: 확장 element 별도 테이블 (신규 계정과목 정의 참고자료)
- standard_labels: 금감원 택사노미 xlsm에서 표준 한/영 라벨 적재
- companies: 처리 상태(ok/no_annual/no_xbrl/error) — 재개(resume) 지원
- 요청 한도 보호: 캐시 히트 시 재다운로드 없음 (일 20,000건)

LLM/외부 AI 불사용 — 실증 빈도 기반 (보안·재현성·감사조서 근거).
"""
import datetime
import os
import sqlite3

from lxml import etree

from ..client.opendart import OpenDartClient, OpenDartError
from .pipeline import (REPRT, XbrlNotAvailable, download_xbrl,
                       find_periodic_rcept, unpack_xbrl)
from .taxonomy import LB, XL, TaxonomyPackage, _pkg_glob
from .dimension_table import XbrlInstance

DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "corpus", "mapping_corpus.sqlite")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies(
  corp_code TEXT PRIMARY KEY, corp_name TEXT, stock_code TEXT,
  induty_code TEXT, year INTEGER, rcept_no TEXT, report_nm TEXT,
  status TEXT NOT NULL, error TEXT, fetched_at TEXT);
CREATE TABLE IF NOT EXISTS usages(
  corp_code TEXT NOT NULL, element_id TEXT NOT NULL, is_ext INTEGER,
  label_ko TEXT, roles TEXT, dims TEXT, n_facts INTEGER,
  PRIMARY KEY(corp_code, element_id));
CREATE TABLE IF NOT EXISTS extensions(
  corp_code TEXT NOT NULL, element_id TEXT NOT NULL,
  label_ko TEXT, roles TEXT, dims TEXT, n_facts INTEGER,
  PRIMARY KEY(corp_code, element_id));
CREATE TABLE IF NOT EXISTS standard_labels(
  element_id TEXT PRIMARY KEY, label_ko TEXT, label_en TEXT);
CREATE INDEX IF NOT EXISTS idx_usages_element ON usages(element_id);
CREATE INDEX IF NOT EXISTS idx_usages_label ON usages(label_ko);
"""


def connect(db_path=None):
    path = db_path or DEFAULT_DB
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(_SCHEMA)
    return con


# ---------------------------------------------------------------------------
# 패키지 1개 → 사용 실태 추출
# ---------------------------------------------------------------------------

def _element_roles(folder):
    """pre.xml에서 element → {role 코드} (loc 기반, 트리 순회 없이)."""
    out = {}
    for path in _pkg_glob(folder, "*_pre.xml"):
        root = etree.parse(path).getroot()
        for pl in root.findall(f"{{{LB}}}presentationLink"):
            role = pl.get(f"{{{XL}}}role") or ""
            code = role.rsplit("role-", 1)[-1]
            for loc in pl.findall(f"{{{LB}}}loc"):
                concept = (loc.get(f"{{{XL}}}href") or "").split("#")[-1]
                out.setdefault(concept, set()).add(code)
    return out


def extract_package(folder):
    """XBRL 패키지 → [usage dict]. (표준+확장, 팩트가 있는 element만)"""
    pkg = TaxonomyPackage(folder)
    inst = XbrlInstance(folder)
    roles = _element_roles(folder)
    rows = []
    for element_id, facts in inst.facts.items():
        dims = sorted({"|".join(sorted(f["ctx"]["dims"])) or "(없음)"
                       for f in facts})
        rows.append({
            "element_id": element_id,
            "is_ext": int(element_id in pkg.extensions),
            "label_ko": pkg._label(pkg.labels_ko, element_id),
            "roles": ",".join(sorted(roles.get(element_id, set()))),
            "dims": ";".join(dims),
            "n_facts": len(facts),
        })
    return rows


# ---------------------------------------------------------------------------
# 배치 빌드 (재개 가능)
# ---------------------------------------------------------------------------

def build(year, limit=None, db_path=None, cli=None, listed_only=True,
          progress=print):
    """상장사 전체(또는 limit)를 순회하며 코퍼스 적재. 요약 dict 반환."""
    cli = cli or OpenDartClient()
    con = connect(db_path)
    corps = [c for c in cli.corp_codes()
             if (c["stock_code"] if listed_only else True)]
    corps.sort(key=lambda c: c["corp_code"])
    done = {r[0] for r in con.execute(
        "SELECT corp_code FROM companies WHERE year = ?", (year,))}
    todo = [c for c in corps if c["corp_code"] not in done]
    if limit is not None:
        # limit = 목표 총 회사 수 (기존 처리분 포함) — 재개 시 잔여분만
        todo = todo[:max(0, limit - len(done))]
    counts = {"ok": 0, "no_annual": 0, "no_xbrl": 0, "error": 0}

    for i, corp in enumerate(todo, 1):
        code = corp["corp_code"]
        status, err, rcept, report_nm, induty = "ok", None, None, None, None
        try:
            doc = find_periodic_rcept(cli, code, year)
            if doc is None:
                status = "no_annual"
            else:
                rcept, report_nm = doc["rcept_no"], doc.get("report_nm")
                _, zpath = download_xbrl(cli, code, rcept, REPRT["annual"])
                folder = unpack_xbrl(zpath)
                rows = extract_package(folder)
                try:
                    induty = cli.company(code).get("induty_code")
                except OpenDartError:
                    induty = None
                con.execute("DELETE FROM usages WHERE corp_code = ?", (code,))
                con.execute("DELETE FROM extensions WHERE corp_code = ?",
                            (code,))
                for r in rows:
                    con.execute(
                        "INSERT OR REPLACE INTO usages VALUES(?,?,?,?,?,?,?)",
                        (code, r["element_id"], r["is_ext"], r["label_ko"],
                         r["roles"], r["dims"], r["n_facts"]))
                    if r["is_ext"]:
                        con.execute(
                            "INSERT OR REPLACE INTO extensions "
                            "VALUES(?,?,?,?,?,?)",
                            (code, r["element_id"], r["label_ko"],
                             r["roles"], r["dims"], r["n_facts"]))
        except XbrlNotAvailable:
            status = "no_xbrl"
        except OpenDartError as e:
            if "020" in str(e):                    # 일 한도 초과 → 중단
                progress(f"요청 한도 도달 — 중단 (재실행 시 이어서 진행): {e}")
                break
            status, err = "error", str(e)[:300]
        except Exception as e:                     # 손상 패키지 등
            status, err = "error", f"{type(e).__name__}: {e}"[:300]
        counts[status] += 1
        con.execute(
            "INSERT OR REPLACE INTO companies "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (code, corp["corp_name"], corp["stock_code"], induty, year,
             rcept, report_nm, status, err,
             datetime.datetime.now().isoformat(timespec="seconds")))
        con.commit()
        if i % 10 == 0 or i == len(todo):
            progress(f"  [{i}/{len(todo)}] {corp['corp_name']} → {status} "
                     f"(누적 ok {counts['ok']})")
    con.close()
    return counts


# ---------------------------------------------------------------------------
# 표준 라벨 적재 (금감원 xlsm)
# ---------------------------------------------------------------------------

def load_standard_labels(xlsm_path, db_path=None):
    from .taxonomy import fss_xlsm_role_rows
    con = connect(db_path)
    for _, rows in fss_xlsm_role_rows(xlsm_path):
        for r in rows:
            eid = f"{r['prefix']}_{r['id']}" if r["prefix"] else r["id"]
            con.execute(
                "INSERT OR IGNORE INTO standard_labels VALUES(?,?,?)",
                (eid, r["ko_std"], r["en_std"]))
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM standard_labels").fetchone()[0]
    con.close()
    return n


# ---------------------------------------------------------------------------
# 통계
# ---------------------------------------------------------------------------

def stats(db_path=None):
    con = connect(db_path)
    out = {}
    out["companies"] = dict(con.execute(
        "SELECT status, COUNT(*) FROM companies GROUP BY status"))
    out["usages"] = con.execute("SELECT COUNT(*) FROM usages").fetchone()[0]
    out["distinct_elements"] = con.execute(
        "SELECT COUNT(DISTINCT element_id) FROM usages").fetchone()[0]
    out["extensions"] = con.execute(
        "SELECT COUNT(*) FROM extensions").fetchone()[0]
    out["standard_labels"] = con.execute(
        "SELECT COUNT(*) FROM standard_labels").fetchone()[0]
    out["top_elements"] = con.execute(
        "SELECT element_id, COUNT(DISTINCT corp_code) AS n, MAX(label_ko) "
        "FROM usages WHERE is_ext = 0 GROUP BY element_id "
        "ORDER BY n DESC LIMIT 10").fetchall()
    con.close()
    return out
