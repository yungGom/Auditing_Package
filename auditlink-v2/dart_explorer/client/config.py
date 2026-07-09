"""API 키·경로 설정. 키는 로컬 .env에만 저장한다 (레포 커밋 금지)."""
import os

_EXPLORER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(_EXPLORER_DIR, "cache")


def _parse_env_file(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_api_key() -> str:
    """OPENDART_API_KEY 탐색: 환경변수 → dart_explorer/.env → client/.env"""
    key = os.environ.get("OPENDART_API_KEY")
    if key:
        return key
    for env_path in (os.path.join(_EXPLORER_DIR, ".env"),
                     os.path.join(_EXPLORER_DIR, "client", ".env")):
        key = _parse_env_file(env_path).get("OPENDART_API_KEY")
        if key:
            return key
    raise RuntimeError(
        "OPENDART_API_KEY가 없습니다. dart_explorer/.env에 저장하세요 "
        "(무료 발급: https://opendart.fss.or.kr)")
