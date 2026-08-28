// hit.js — 좌표 변환 + 히트 판정. U-4의 유일한 좌표 코드다.
//
// ★ 링 그리기와 클릭 판정이 같은 변환 함수(pdfRectToViewport)를 쓴다. 그래서 링이
//   눈에 맞는 자리에 그려졌다면 히트영역도 반드시 같은 자리다 — 둘이 어긋날 구조적
//   여지를 없앤 것이다.
//
// ★ 글리프 오프셋을 여기에 하드코딩하지 않는다. ui/glyph_offsets.json이 유일한
//   출처이고, glyph_gate.py가 그 값을 render.py의 실제 드로잉에 묶어 둔다
//   (설계안_UI셸_U4.md §2, CLAUDE.md 결정 18).
//
// 좌표 경로 (설계안 §1):
//   pdfplumber(좌상단, PDF pt) → y뒤집기 → PDF 사용자공간(좌하단)
//     → viewport.convertToViewportPoint → 뷰포트(CSS px, 좌상단) → client
//   어느 단계에서도 반올림하지 않는다. 비교 시점에만 EPS를 쓴다.

const EPS = 0.01; // pt — 부동소수 왕복 오차만 흡수한다(히트영역을 넓히는 용도 아님)

export function pageHeightOf(viewport) {
  return viewport.viewBox[3] - viewport.viewBox[1];
}

/** pdfplumber 사각형 {x0, top, x1, bottom} → 뷰포트 사각형 {left, top, right, bottom}.
 *  회전은 convertToViewportPoint가 이미 처리하므로 직접 다루지 않는다. */
export function pdfRectToViewport(rect, viewport) {
  const H = pageHeightOf(viewport);
  const a = viewport.convertToViewportPoint(rect.x0, H - rect.bottom);
  const b = viewport.convertToViewportPoint(rect.x1, H - rect.top);
  return {
    left: Math.min(a[0], b[0]), right: Math.max(a[0], b[0]),
    top: Math.min(a[1], b[1]), bottom: Math.max(a[1], b[1]),
  };
}

function glyphKey(mark) {
  if (mark.kind === "cross" && (mark.source || {}).check === "C") return "cross_C";
  if (mark.kind === "cross" || mark.kind === "question") return mark.kind;
  return null;
}

/** 실제로 그려진 글리프(✗ / ?)의 사각형 — pdfplumber 규약. */
export function glyphRect(mark, offsets) {
  const key = glyphKey(mark);
  const off = offsets.glyph[key];
  if (!off) return null;
  const b = mark.box;
  const x0 = b.x1 + off.dx;
  const bottom = b.bottom - off.dy;
  return { x0, x1: x0 + off.w, top: bottom - off.h, bottom };
}

/** 최소 히트영역 확보 — PDF pt 기준으로 넓힌다.
 *  ⚠ 화면 px 기준이 아니라 pt 기준인 이유: 표 행 피치가 14pt고 글리프 충돌
 *  최근접이 14.00pt라 여유가 2pt뿐이다. 화면 px로 잡으면 75% 축소 시 12px =
 *  16pt가 되어 위아래 행이 충돌한다. 100% 배율에서는 1pt = 1px라 스펙의
 *  "12×12px"와 정확히 일치한다(CLAUDE.md 결정 19). */
function atLeast(rect, minPt) {
  const w = rect.x1 - rect.x0, h = rect.bottom - rect.top;
  const dx = Math.max(0, (minPt - w) / 2), dy = Math.max(0, (minPt - h) / 2);
  return { x0: rect.x0 - dx, x1: rect.x1 + dx, top: rect.top - dy, bottom: rect.bottom + dy };
}

function contains(vrect, vx, vy) {
  return vx >= vrect.left - EPS && vx <= vrect.right + EPS
      && vy >= vrect.top - EPS && vy <= vrect.bottom + EPS;
}

/** 뷰포트 좌표 (vx, vy)에 걸리는 마크들. 2단 우선순위(설계안 §2):
 *    tier 1 = 실제로 보이는 글리프(최소 min_hit_pt)  → 여기서 잡히면 끝
 *    tier 2 = 셀 box(anchor_bbox)                    → tier 1이 비었을 때만
 *  평평하게 합치면 인접 열 글리프가 옆 칸 box를 침범해 겹침이 4→54쌍으로 늘고
 *  후보 목록이 상시로 뜬다(5축 실측). 우선순위를 두면 그 경쟁 자체가 없어진다.
 *  → 반환: 걸린 마크 배열(0·1·2건 이상). 2건 이상이면 호출부가 후보 목록을 띄운다. */
export function hitTest(vx, vy, marks, viewport, offsets) {
  const minPt = offsets.min_hit_pt;
  const tier1 = [], tier2 = [];
  for (const m of marks) {
    const g = glyphRect(m, offsets);
    if (g && contains(pdfRectToViewport(atLeast(g, minPt), viewport), vx, vy)) tier1.push(m);
    if (contains(pdfRectToViewport(m.box, viewport), vx, vy)) tier2.push(m);
  }
  return tier1.length ? tier1 : tier2;
}
