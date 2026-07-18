"""OpenDART API 클라이언트 (패치 B-1).

dart_benchmark_finder.py의 호출 코드(list.json 검색, 페이징)를 모듈로 분리하고
corpCode.xml 다운로드·캐시와 회사명→corp_code 변환을 추가했다.

수신 전용: 이 모듈은 OpenDART에서 공개 데이터를 내려받기만 한다.
"""
import io
import time
import xml.etree.ElementTree as ET
import zipfile

import requests

from .cache import Cache, TTL_CORP, TTL_SEARCH
from .config import CACHE_DIR, load_api_key

BASE = "https://opendart.fss.or.kr/api"

# 정기공시 주요 상세유형 (pblntf_detail_ty)
DETAIL_TYPES = {
    "사업보고서": "A001", "반기보고서": "A002", "분기보고서": "A003",
    "감사보고서": "F001", "연결감사보고서": "F002",
}


class OpenDartError(Exception):
    pass


class OpenDartClient:
    def __init__(self, api_key=None, cache_dir=None, sleep=0.2):
        self.api_key = api_key or load_api_key()
        self.cache = Cache(cache_dir or CACHE_DIR)
        self.sleep = sleep

    # ------------------------------------------------------------------
    # corpCode.xml — 전체 회사 고유번호 (7일 캐시)
    # ------------------------------------------------------------------
    def corp_codes(self, force=False):
        """[{corp_code, corp_name, stock_code, modify_date}] 전체 목록."""
        if not force:
            cached = self.cache.get_json("corp", "corp_codes", TTL_CORP)
            if cached is not None:
                return cached
        r = requests.get(f"{BASE}/corpCode.xml",
                         params={"crtfc_key": self.api_key}, timeout=60)
        if r.headers.get("content-type", "").startswith("application/json"):
            j = r.json()
            raise OpenDartError(f"corpCode {j.get('status')}: "
                                f"{j.get('message')}")
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            name = next(n for n in z.namelist()
                        if n.lower().endswith(".xml"))
            root = ET.fromstring(z.read(name))
        out = []
        for el in root.iter("list"):
            def _t(tag):
                node = el.find(tag)
                return (node.text or "").strip() if node is not None else ""
            out.append({"corp_code": _t("corp_code"),
                        "corp_name": _t("corp_name"),
                        "stock_code": _t("stock_code"),
                        "modify_date": _t("modify_date")})
        if not out:
            raise OpenDartError("corpCode.xml 파싱 결과가 비어 있습니다.")
        self.cache.put_json("corp", "corp_codes", out)
        return out

    def find_corp(self, name, listed_only=True):
        """회사명 → 후보 목록. 정확 일치 우선, 다음 부분 일치.

        listed_only: 상장사(stock_code 있음)만. 동명 비상장 법인 잡음 제거.
        """
        name = name.strip()
        codes = self.corp_codes()
        pool = [c for c in codes if c["stock_code"]] if listed_only else codes
        exact = [c for c in pool if c["corp_name"] == name]
        if exact:
            return exact
        partial = [c for c in pool if name in c["corp_name"]]
        if partial or listed_only is False:
            return partial
        return self.find_corp(name, listed_only=False)

    def resolve_corp_code(self, name) -> str:
        cands = self.find_corp(name)
        if not cands:
            raise OpenDartError(f"회사를 찾을 수 없습니다: {name}")
        if len(cands) > 1:
            names = ", ".join(f"{c['corp_name']}({c['corp_code']})"
                              for c in cands[:5])
            raise OpenDartError(
                f"'{name}' 후보가 여럿입니다 — 정확한 회사명을 지정하세요: "
                f"{names}{' …' if len(cands) > 5 else ''}")
        return cands[0]["corp_code"]

    # ------------------------------------------------------------------
    # list.json — 공시검색 (1일 캐시, 페이징)
    # ------------------------------------------------------------------
    def search(self, corp_name=None, corp_code=None, bgn_de=None, end_de=None,
               pblntf_ty=None, pblntf_detail_ty=None, last_reprt_at="Y",
               induty_code=None, max_pages=100, force=False):
        """공시 목록 검색. induty_code 지정 시 회사개황으로 클라이언트측 필터.

        반환: [{rcept_no, corp_code, corp_name, report_nm, rcept_dt, ...}]
        """
        if corp_code is None and corp_name:
            corp_code = self.resolve_corp_code(corp_name)
        if pblntf_detail_ty:
            pblntf_ty = None      # 동시 지정 시 상세유형이 무시됨 — 상세 우선
        params = {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de,
                  "pblntf_ty": pblntf_ty, "pblntf_detail_ty": pblntf_detail_ty,
                  "last_reprt_at": last_reprt_at, "page_count": 100}
        key = self.cache.key_for(params)
        if not force:
            cached = self.cache.get_json("search", key, TTL_SEARCH)
            if cached is not None:
                return cached

        out, page = [], 1
        while page <= max_pages:
            q = {k: v for k, v in params.items() if v is not None}
            q.update(crtfc_key=self.api_key, page_no=page)
            r = requests.get(f"{BASE}/list.json", params=q, timeout=30)
            j = r.json()
            status = j.get("status")
            if status == "013":            # 조회된 데이터 없음
                break
            if status != "000":
                raise OpenDartError(f"list {status}: {j.get('message')}")
            out += j.get("list", [])
            if page >= int(j.get("total_page", 1)):
                break
            page += 1
            time.sleep(self.sleep)

        if induty_code is not None:
            out = [d for d in out
                   if self.company(d["corp_code"]).get("induty_code")
                   == str(induty_code)]
        self.cache.put_json("search", key, out)
        return out

    # ------------------------------------------------------------------
    # company.json — 회사개황 (업종코드 등, 7일 캐시)
    # ------------------------------------------------------------------
    def company(self, corp_code):
        cached = self.cache.get_json("company", corp_code, TTL_CORP)
        if cached is not None:
            return cached
        r = requests.get(f"{BASE}/company.json",
                         params={"crtfc_key": self.api_key,
                                 "corp_code": corp_code}, timeout=30)
        j = r.json()
        if j.get("status") != "000":
            raise OpenDartError(f"company {j.get('status')}: "
                                f"{j.get('message')}")
        self.cache.put_json("company", corp_code, j)
        return j

    # ------------------------------------------------------------------
    # 원본 파일 수신 (영구 캐시) — B-2/B-3에서 사용
    # ------------------------------------------------------------------
    def fetch_binary(self, endpoint, params, cache_relpath):
        """바이너리 API(document.xml, fnlttXbrl.xml 등) 수신 + 영구 캐시.

        오류(JSON) 응답이면 OpenDartError.
        """
        cached = self.cache.get_file(cache_relpath)
        if cached is not None:
            return cached, self.cache.file_path(cache_relpath)
        q = dict(params)
        q["crtfc_key"] = self.api_key
        r = requests.get(f"{BASE}/{endpoint}", params=q, timeout=120)
        if r.headers.get("content-type", "").startswith("application/json"):
            j = r.json()
            raise OpenDartError(f"{endpoint} {j.get('status')}: "
                                f"{j.get('message')}")
        path = self.cache.put_file(cache_relpath, r.content)
        return r.content, path
