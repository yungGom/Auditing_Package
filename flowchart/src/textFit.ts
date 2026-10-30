/**
 * 칸 크기에 맞춘 글자 크기 추정 (캔버스 px).
 *   PPT 와 같은 규칙 — 한글 ≈ 1em, 영문·숫자 ≈ 0.58em — 으로 폭을 어림한다.
 *   양식처럼 글자는 기본 7pt 이고, 칸보다 길 때만 줄인다.
 */

export function textUnits(text: string): number {
  return [...(text || "")].reduce((s, ch) => s + (/[ -~]/.test(ch) ? 0.58 : 1), 0);
}

/** 한 줄에 들어가는 글자 크기 */
export function fitOneLinePx(text: string, widthPx: number, maxPx: number, minPx = 7): number {
  const units = textUnits(text);
  if (units === 0) return maxPx;
  return Math.max(minPx, Math.min(maxPx, Math.floor((widthPx / units) * 10) / 10));
}

/** 줄바꿈해서 상자(폭×높이)에 들어가는 가장 큰 글자 크기 */
export function fitBoxPx(
  text: string,
  widthPx: number,
  heightPx: number,
  maxPx: number,
  minPx = 8,
  lineHeight = 1.2,
): number {
  const paras = (text || "").split("\n");
  for (let size = maxPx; size > minPx; size -= 0.5) {
    const lines = paras.reduce(
      (n, p) => n + Math.max(1, Math.ceil((textUnits(p) * size) / Math.max(1, widthPx))),
      0,
    );
    if (lines * size * lineHeight <= heightPx) return size;
  }
  return minPx;
}
