"""OpenDART document.xml 원본 처리 헬퍼 (패치 B-2 잠정 — 구조대조 리포트 참조).

OpenDART 원본은 ZIP{ {rcept_no}_00760.xml } 단일 파일이며 meta.xml이 없다.
본문 스키마(dart4.xsd DOCUMENT)는 dartdb DSD의 contents.xml과 동일하므로,
분석·엑셀 추출용으로 contents.xml 래핑을 제공한다.

주의: 래핑 결과는 DART 편집기용 DSD가 아니다 (meta.xml 없음 — 읽기 전용
수신물 취급). 왕복(repack) 대상은 dartdb/편집기 파일만.

import 방향: explorer → workbench 단방향만 허용 (dsd_tool 파서 재사용).
"""
import io
import os
import sys
import zipfile

# dsd_workbench의 dsd_tool 재사용 (단방향 import)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_WORKBENCH = os.path.join(_REPO_ROOT, "dsd_workbench")
if _WORKBENCH not in sys.path:
    sys.path.insert(0, _WORKBENCH)


def unwrap_document(zip_bytes: bytes) -> bytes:
    """document.xml 응답 ZIP에서 본문 XML 바이트를 꺼낸다."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        xmls = [n for n in z.namelist() if n.lower().endswith(".xml")]
        if not xmls:
            raise ValueError("ZIP 안에 XML이 없습니다: " + str(z.namelist()))
        # _00760(감사보고서) 우선, 없으면 첫 XML
        name = next((n for n in xmls if "_00760" in n), xmls[0])
        return z.read(name)


def wrap_as_contents(xml_bytes: bytes, out_path: str) -> str:
    """본문 XML을 contents.xml 단일 엔트리 ZIP으로 래핑 (분석·추출용)."""
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("contents.xml", xml_bytes)
    return out_path


def extract_to_excel(document_zip_path: str, xlsx_path: str,
                     work_dir: str = None) -> dict:
    """OpenDART 원본 ZIP → (래핑) → dsd_tool extract 엑셀 산출.

    주석 분할은 마크업 차이로 부정확할 수 있다 (구조대조 리포트 §2).
    """
    from dsd_tool.excel_out import extract  # 지연 import (단방향)
    with open(document_zip_path, "rb") as f:
        inner = unwrap_document(f.read())
    wrapped = os.path.join(work_dir or os.path.dirname(xlsx_path),
                           "_wrapped_contents.zip")
    wrap_as_contents(inner, wrapped)
    return extract(wrapped, xlsx_path)


def fetch_and_wrap(cli, corp_code: str, rcept_no: str) -> str:
    """document.xml 수신(영구 캐시 경유) + DSD 형식 래핑. wrapped 경로 반환.

    UI-5 동선 통합용 — [DSD 저장]·[엑셀로 변환] 공용 (원본이 곧 DSD:
    래핑 결과는 contents.xml 단일 ZIP이라 dsd_tool extract가 그대로
    읽는다. 단, meta.xml이 없어 편집기 왕복 대상은 아니다 — 클래스
    docstring의 '읽기 전용 수신물' 원칙 그대로).
    """
    data, _zpath = cli.fetch_binary(
        "document.xml", {"rcept_no": rcept_no},
        f"document/{corp_code}/{rcept_no}.zip")
    out_dir = os.path.join(cli.cache.root, "document", corp_code)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{rcept_no}.dsd")
    wrap_as_contents(unwrap_document(data), out_path)
    return out_path
