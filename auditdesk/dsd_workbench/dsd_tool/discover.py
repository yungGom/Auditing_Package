"""N-2: DSD 입력 경로 해석 — 폴더 스캔 + 파일 직접, 이중 수용.

재현 확정(사용자 실측): 폴더 경로 입력은 종전에 스캔 단계 없이
파일 존재 검사에서 즉시 거부되었다("DSD 파일 없음") — 나열이 비거나
필터에서 떨어진 게 아니라 나열 자체가 부재. 이 모듈이 그 단계를
신설한다.

규약:
- 파일 경로면 그대로 채택 (직접 입력 경로 현행 유지)
- 폴더면 나열(listdir — glob 미사용: 대괄호 등 특수문자 함정 원천
  회피) 후 확장자 필터: .dsd/.xml, 대소문자 무시, 유니코드 NFC
  정규화(OneDrive 동기화 자모 분해 대비)
- 후보 1건 = 자동 채택 / .dsd가 정확히 1건이면 .xml보다 우선
- 0건·다건 = 오류 대신 **파일별 제외 사유 보고** ("N개 발견: xxx는
  확장자 불일치…") — 침묵 실패 금지
- .ixd는 편집기 프로젝트 파일 사유 명시 (UI-7 가드와 동일 안내)
- 클라우드 전용(OneDrive) 안내 병기
"""
import os
import unicodedata

_EXTS = (".dsd", ".xml")


def _reason(name, full):
    if os.path.isdir(full):
        return "폴더"
    ext = os.path.splitext(unicodedata.normalize("NFC", name))[1].lower()
    if ext == ".ixd":
        return "제외 — 편집기 프로젝트 파일(IXD)"
    if ext not in _EXTS:
        return f"확장자 불일치({ext or '없음'})"
    return "후보"


def resolve_dsd_path(path):
    """입력 경로(폴더 또는 파일) → 채택 파일 확정.

    반환 dict:
      file: 채택된 파일 경로 (실패 시 None)
      report: [(이름, 사유)] — 폴더 스캔 시 파일별 판정 전수
      error: 사용자 안내문 (성공 시 None)
    """
    p = str(path or "").strip().strip('"').rstrip("\\/") or ""
    if not p:
        return {"file": None, "report": [],
                "error": "경로가 비었습니다 — 폴더 또는 파일 경로를 "
                         "입력하세요"}
    if os.path.isfile(p):
        return {"file": p, "report": [], "error": None}
    if not os.path.isdir(p):
        return {"file": None, "report": [],
                "error": f"경로가 존재하지 않습니다: {p}"}

    report, cands = [], []
    try:
        names = sorted(os.listdir(p))
    except OSError as e:
        return {"file": None, "report": [],
                "error": f"폴더를 읽을 수 없습니다: {e}"}
    for name in names:
        full = os.path.join(p, name)
        r = _reason(name, full)
        report.append((name, r))
        if r == "후보":
            cands.append(full)

    dsd_only = [c for c in cands
                if os.path.splitext(unicodedata.normalize(
                    "NFC", c))[1].lower() == ".dsd"]
    if len(cands) == 1 or len(dsd_only) == 1:
        return {"file": dsd_only[0] if len(dsd_only) == 1 else cands[0],
                "report": report, "error": None}
    if not cands:
        detail = " · ".join(f"{n}: {r}" for n, r in report[:8])
        more = f" 외 {len(report) - 8}건" if len(report) > 8 else ""
        return {"file": None, "report": report, "error": (
            f"이 폴더에서 DSD 파일을 찾지 못했습니다 — {len(report)}개 "
            f"항목 검토: {detail or '(빈 폴더)'}{more}. OneDrive 클라우드"
            " 전용 파일은 '항상 이 장치에 유지' 후 다시 시도하세요")}
    names = ", ".join(os.path.basename(c) for c in cands[:8])
    return {"file": None, "report": report, "error": (
        f"이 폴더에서 DSD 후보 {len(cands)}개 발견 — 파일 경로로 "
        f"지정하세요: {names}")}
