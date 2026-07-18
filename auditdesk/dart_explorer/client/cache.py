"""다운로드 캐시 (지시서 B-1-3).

- corpCode: 7일
- 검색결과(list.json): 1일
- 다운로드 파일(공시원본·XBRL): 영구
캐시 히트 시 재다운로드 금지 (요청 한도 일 20,000건 보호).
"""
import hashlib
import json
import os
import time

TTL_CORP = 7 * 86400
TTL_SEARCH = 1 * 86400
TTL_FOREVER = None


class Cache:
    def __init__(self, root):
        self.root = root

    def _path(self, *parts):
        p = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    @staticmethod
    def key_for(params: dict) -> str:
        """검색 파라미터 → 캐시 키. 인증키는 키 재발급과 무관하도록 제외."""
        clean = {k: v for k, v in sorted(params.items())
                 if k not in ("crtfc_key",) and v is not None}
        blob = json.dumps(clean, ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()

    def _fresh(self, path, ttl) -> bool:
        if not os.path.exists(path):
            return False
        if ttl is None:
            return True
        return (time.time() - os.path.getmtime(path)) < ttl

    # --- JSON 캐시 -------------------------------------------------------
    def get_json(self, category, key, ttl):
        path = self._path(category, f"{key}.json")
        if self._fresh(path, ttl):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def put_json(self, category, key, obj):
        path = self._path(category, f"{key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        return path

    # --- 바이너리 캐시 ---------------------------------------------------
    def get_file(self, relpath, ttl=TTL_FOREVER):
        path = self._path(relpath)
        if self._fresh(path, ttl):
            with open(path, "rb") as f:
                return f.read()
        return None

    def put_file(self, relpath, data: bytes):
        path = self._path(relpath)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def file_path(self, relpath):
        return self._path(relpath)
