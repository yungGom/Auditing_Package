"""A-7: 공용 단위 리졸버 — 시트/표 단위 마커 감지 (단일 소스).

발원: 실전 검토 — 본문(원)↔주석(천원) 크로스 미발견의 실체가 표시
단위 차이. 규약:
- 마커("(단위: 원/천원/백만원)" 변형 표기 포함)를 감지해 배율 확정
- 표별 상이 지원 — 마커가 표 상단(직전 행들)에 오는 구조
- 미감지 = 환산 보류 + "단위 미상" (자릿수 추정 금지)
- V-1(태깅 검증)의 시트 단위 정규화와 같은 개념 — 정규식·배율 표를
  이 모듈로 단일화 (xbrl_recon은 재사용)
"""
import re

UNIT_RE = re.compile(r"단\s*위\s*[:：]\s*([^\)\s]+)")
UNIT_SCALE = {"원": 1, "천원": 1_000, "천 원": 1_000,
              "백만원": 1_000_000, "백만 원": 1_000_000,
              "십억원": 1_000_000_000, "억원": 100_000_000}


def parse_unit(text):
    """텍스트에서 단위 마커 → (배율, 표기) 또는 None."""
    m = UNIT_RE.search(str(text or ""))
    if not m:
        return None
    unit = m.group(1).strip()
    compact = unit.replace(" ", "")
    for k, s in UNIT_SCALE.items():
        kk = k.replace(" ", "")
        if compact.startswith(kk[0]) and kk in compact:
            return s, unit
    return None                                 # 미인식 표기 = 단위 미상


def detect_sheet_unit(ws, max_scan=8, max_col=4):
    """시트 상단의 단위 행 → (배율, 표기) 또는 None (V-1 개념 승계)."""
    for r in range(1, max_scan + 1):
        for c in range(1, max_col + 1):
            hit = parse_unit(ws.cell(r, c).value)
            if hit:
                return hit
    return None


def region_scales(ctx, sheet, lookback=6, max_col=4):
    """표(region)별 배율 지도: {데이터 행: 배율 or None}.

    각 region 직전 행들(마커가 표 상단에 오는 구조)에서 단위 마커를
    찾고, 없으면 시트 상단 마커로 폴백. 그래도 없으면 None(단위 미상
    — 환산 보류). 반환 배율은 region의 모든 행에 동일 적용.
    """
    from .foot import _regions
    ws = ctx.wb[sheet]
    rowmap = ctx.rowmaps[sheet]
    regions = _regions(rowmap)
    default = detect_sheet_unit(ws)
    out = {}
    prev_end = 0
    for region in regions:
        scale = None
        lo = max(prev_end + 1, region[0] - lookback)
        for r in range(region[0] - 1, lo - 1, -1):
            for c in range(1, max_col + 1):
                hit = parse_unit(ws.cell(r, c).value)
                if hit:
                    scale = hit[0]
                    break
            if scale is not None:
                break
        if scale is None and default is not None:
            scale = default[0]
        for r in region:
            out[r] = scale
        prev_end = region[-1]
    return out


def sheet_scale(ctx, sheet):
    """시트 단위 배율 (FS류 — 시트 상단 마커). 미감지 None."""
    hit = detect_sheet_unit(ctx.wb[sheet])
    return hit[0] if hit else None
