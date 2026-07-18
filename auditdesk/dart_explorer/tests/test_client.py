"""OpenDART 클라이언트 게이트 (패치 B-1).

게이트: 실제 상장사 1곳 검색 → rcept_no 목록 정확 반환,
오프라인 재실행 시 캐시 히트 (라이브 테스트는 API 키 있을 때만).
오프라인 단위 테스트는 가짜 응답으로 캐시 TTL·페이징·키 제외를 검증.
"""
import io
import json
import os
import time
import zipfile

import pytest

from dart_explorer.client.cache import Cache, TTL_CORP, TTL_SEARCH
from dart_explorer.client.opendart import OpenDartClient, OpenDartError

try:
    from dart_explorer.client.config import load_api_key
    _HAS_KEY = bool(load_api_key())
except RuntimeError:
    _HAS_KEY = False


# ---------------------------------------------------------------------------
# 가짜 응답 헬퍼
# ---------------------------------------------------------------------------

def _corp_zip():
    xml = ("<result>"
           "<list><corp_code>00126380</corp_code>"
           "<corp_name>삼성전자</corp_name><stock_code>005930</stock_code>"
           "<modify_date>20250101</modify_date></list>"
           "<list><corp_code>99999999</corp_code>"
           "<corp_name>삼성전자서비스</corp_name><stock_code></stock_code>"
           "<modify_date>20250101</modify_date></list>"
           "</result>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("CORPCODE.xml", xml.encode("utf-8"))
    return buf.getvalue()


class _Resp:
    def __init__(self, content=b"", json_obj=None):
        self.content = content
        self._json = json_obj
        self.headers = ({"content-type": "application/json"}
                        if json_obj is not None
                        else {"content-type": "application/zip"})

    def json(self):
        return self._json


@pytest.fixture()
def client(tmp_path, monkeypatch):
    return OpenDartClient(api_key="TESTKEY", cache_dir=str(tmp_path), sleep=0)


def test_corp_codes_parse_and_cache(client, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return _Resp(content=_corp_zip())
    monkeypatch.setattr("dart_explorer.client.opendart.requests.get",
                        fake_get)
    codes = client.corp_codes()
    assert {c["corp_name"] for c in codes} == {"삼성전자", "삼성전자서비스"}
    # 캐시 히트: 네트워크 재호출 없음
    codes2 = client.corp_codes()
    assert codes2 == codes and len(calls) == 1
    # 상장사 우선 매칭
    assert client.resolve_corp_code("삼성전자") == "00126380"


def test_search_paging_and_cache(client, monkeypatch):
    pages = {1: {"status": "000", "total_page": 2,
                 "list": [{"rcept_no": "20250101000001"}]},
             2: {"status": "000", "total_page": 2,
                 "list": [{"rcept_no": "20250101000002"}]}}
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        assert "crtfc_key" in params
        return _Resp(json_obj=pages[params["page_no"]])
    monkeypatch.setattr("dart_explorer.client.opendart.requests.get",
                        fake_get)
    docs = client.search(corp_code="00126380", bgn_de="20250101",
                         end_de="20251231", pblntf_ty="A")
    assert [d["rcept_no"] for d in docs] == ["20250101000001",
                                             "20250101000002"]
    assert len(calls) == 2                     # 페이징 2회

    # 오프라인 재실행(네트워크 차단) → 캐시 히트
    def offline(*a, **k):
        raise ConnectionError("offline")
    monkeypatch.setattr("dart_explorer.client.opendart.requests.get", offline)
    docs2 = client.search(corp_code="00126380", bgn_de="20250101",
                          end_de="20251231", pblntf_ty="A")
    assert docs2 == docs


def test_search_error_status(client, monkeypatch):
    monkeypatch.setattr(
        "dart_explorer.client.opendart.requests.get",
        lambda *a, **k: _Resp(json_obj={"status": "020",
                                        "message": "요청 제한 초과"}))
    with pytest.raises(OpenDartError, match="020"):
        client.search(corp_code="00126380", bgn_de="20250101",
                      end_de="20251231")


def test_search_no_data_returns_empty(client, monkeypatch):
    monkeypatch.setattr(
        "dart_explorer.client.opendart.requests.get",
        lambda *a, **k: _Resp(json_obj={"status": "013",
                                        "message": "조회된 데이타가 없습니다."}))
    assert client.search(corp_code="00126380", bgn_de="20250101",
                         end_de="20250102") == []


def test_cache_key_excludes_api_key_and_ttl(tmp_path):
    c = Cache(str(tmp_path))
    k1 = c.key_for({"crtfc_key": "AAA", "corp_code": "1", "bgn_de": "2"})
    k2 = c.key_for({"crtfc_key": "BBB", "corp_code": "1", "bgn_de": "2"})
    assert k1 == k2                            # 인증키는 캐시 키에서 제외
    c.put_json("search", k1, [1, 2])
    assert c.get_json("search", k1, TTL_SEARCH) == [1, 2]
    # TTL 만료 시뮬레이션
    path = os.path.join(str(tmp_path), "search", f"{k1}.json")
    old = time.time() - TTL_SEARCH - 10
    os.utime(path, (old, old))
    assert c.get_json("search", k1, TTL_SEARCH) is None
    assert c.get_json("search", k1, None) == [1, 2]   # 영구 TTL은 유지


def test_fetch_binary_permanent_cache(client, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return _Resp(content=b"ZIPDATA")
    monkeypatch.setattr("dart_explorer.client.opendart.requests.get",
                        fake_get)
    data, path = client.fetch_binary("document.xml", {"rcept_no": "X"},
                                     "files/X/doc.zip")
    assert data == b"ZIPDATA" and os.path.exists(path)
    data2, _ = client.fetch_binary("document.xml", {"rcept_no": "X"},
                                   "files/X/doc.zip")
    assert data2 == b"ZIPDATA" and len(calls) == 1    # 영구 캐시 히트


# ---------------------------------------------------------------------------
# 라이브 게이트 (API 키 있을 때만): 실제 상장사 검색 + 오프라인 캐시 히트
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HAS_KEY, reason="OPENDART_API_KEY 없음")
def test_gate_live_search_and_offline_cache(tmp_path, monkeypatch):
    cli = OpenDartClient(cache_dir=str(tmp_path))
    docs = cli.search(corp_name="삼성전자", bgn_de="20250101",
                      end_de="20251231", pblntf_ty="A")
    rcepts = [d["rcept_no"] for d in docs]
    assert rcepts, "정기공시 검색 결과 없음"
    assert all(len(r) == 14 and r.isdigit() for r in rcepts)
    assert all(d["corp_name"] == "삼성전자" for d in docs)

    # 오프라인 재실행 → 캐시 히트 (네트워크 차단)
    def offline(*a, **k):
        raise ConnectionError("offline")
    monkeypatch.setattr("dart_explorer.client.opendart.requests.get", offline)
    docs2 = cli.search(corp_name="삼성전자", bgn_de="20250101",
                       end_de="20251231", pblntf_ty="A")
    assert [d["rcept_no"] for d in docs2] == rcepts
