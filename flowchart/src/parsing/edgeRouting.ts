/**
 * 직각(orthogonal) 화살표 경로 계산 — 캔버스(RoutedEdge)와 PPT(pptExport)가
 * 같은 함수를 써서 화면과 PPT 의 화살표 모양을 일치시킨다.
 *
 *   - route 가 없으면 React Flow smoothstep 과 동일한 경로 (getPoints 이식)
 *   - route.corridors 가 있으면 "통로" 선을 차례로 지나는 경로.
 *     배치 엔진이 다른 박스를 피해 가도록 통로를 지정한다
 *     (예: 같은 줄 건너뛰기 → 줄 아래 통로, 줄바꿈 → 바깥쪽 세로 통로).
 *
 *   통로는 절대 좌표, 핸들에서 빠져나오는 길이(srcOffset/tgtOffset)는 상대값이라
 *   사용자가 노드를 옮겨도 경로가 끊기지 않고 직각을 유지한다.
 */

export type Side = "left" | "right" | "top" | "bottom";

export interface Pt {
  x: number;
  y: number;
}

export interface Corridor {
  /** "y" = 가로 통로(y=value 선을 따라 이동), "x" = 세로 통로(x=value 선) */
  axis: "x" | "y";
  value: number;
}

export interface EdgeRoute {
  /** 소스 핸들에서 직진하는 길이 (px). 기본 14 */
  srcOffset?: number;
  /** 타깃 핸들 직전 직진 길이 (px). 기본 14 */
  tgtOffset?: number;
  /** 거쳐갈 통로 (순서대로). 없으면 smoothstep 과 동일 */
  corridors?: Corridor[];
  /** smoothstep fallback 시 offset */
  offset?: number;
}

const DIR: Record<Side, Pt> = {
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
  top: { x: 0, y: -1 },
  bottom: { x: 0, y: 1 },
};

export function sideDir(side: Side): Pt {
  return DIR[side];
}

/* ─────────────────────────────────────────────
 * React Flow v11 getPoints 이식 (@reactflow/core SmoothStepEdge)
 *   캔버스 기본 smoothstep 엣지와 PPT 경로를 동일하게 만들기 위함.
 * ───────────────────────────────────────────── */

function edgeCenter(s: Pt, t: Pt): Pt {
  const xOffset = Math.abs(t.x - s.x) / 2;
  const cx = t.x < s.x ? t.x + xOffset : t.x - xOffset;
  const yOffset = Math.abs(t.y - s.y) / 2;
  const cy = t.y < s.y ? t.y + yOffset : t.y - yOffset;
  return { x: cx, y: cy };
}

export function smoothStepPoints(
  source: Pt,
  sourcePosition: Side,
  target: Pt,
  targetPosition: Side,
  offset = 20,
): Pt[] {
  const sourceDir = DIR[sourcePosition];
  const targetDir = DIR[targetPosition];
  const sourceGapped = {
    x: source.x + sourceDir.x * offset,
    y: source.y + sourceDir.y * offset,
  };
  const targetGapped = {
    x: target.x + targetDir.x * offset,
    y: target.y + targetDir.y * offset,
  };
  const horizontalSrc =
    sourcePosition === "left" || sourcePosition === "right";
  const dir = horizontalSrc
    ? sourceGapped.x < targetGapped.x
      ? { x: 1, y: 0 }
      : { x: -1, y: 0 }
    : sourceGapped.y < targetGapped.y
      ? { x: 0, y: 1 }
      : { x: 0, y: -1 };
  const acc: "x" | "y" = dir.x !== 0 ? "x" : "y";
  const currDir = dir[acc];
  let points: Pt[] = [];
  const sourceGapOffset = { x: 0, y: 0 };
  const targetGapOffset = { x: 0, y: 0 };
  const center = edgeCenter(source, target);

  if (sourceDir[acc] * targetDir[acc] === -1) {
    const verticalSplit = [
      { x: center.x, y: sourceGapped.y },
      { x: center.x, y: targetGapped.y },
    ];
    const horizontalSplit = [
      { x: sourceGapped.x, y: center.y },
      { x: targetGapped.x, y: center.y },
    ];
    if (sourceDir[acc] === currDir) {
      points = acc === "x" ? verticalSplit : horizontalSplit;
    } else {
      points = acc === "x" ? horizontalSplit : verticalSplit;
    }
  } else {
    const sourceTarget = [{ x: sourceGapped.x, y: targetGapped.y }];
    const targetSource = [{ x: targetGapped.x, y: sourceGapped.y }];
    if (acc === "x") {
      points = sourceDir.x === currDir ? targetSource : sourceTarget;
    } else {
      points = sourceDir.y === currDir ? sourceTarget : targetSource;
    }
    if (sourcePosition === targetPosition) {
      const diff = Math.abs(source[acc] - target[acc]);
      if (diff <= offset) {
        const gapOffset = Math.min(offset - 1, offset - diff);
        if (sourceDir[acc] === currDir) {
          sourceGapOffset[acc] =
            (sourceGapped[acc] > source[acc] ? -1 : 1) * gapOffset;
        } else {
          targetGapOffset[acc] =
            (targetGapped[acc] > target[acc] ? -1 : 1) * gapOffset;
        }
      }
    }
    if (sourcePosition !== targetPosition) {
      const opp: "x" | "y" = acc === "x" ? "y" : "x";
      const isSameDir = sourceDir[acc] === targetDir[opp];
      const sourceGtTargetOppo = sourceGapped[opp] > targetGapped[opp];
      const sourceLtTargetOppo = sourceGapped[opp] < targetGapped[opp];
      const flip =
        (sourceDir[acc] === 1 &&
          ((!isSameDir && sourceGtTargetOppo) ||
            (isSameDir && sourceLtTargetOppo))) ||
        (sourceDir[acc] !== 1 &&
          ((!isSameDir && sourceLtTargetOppo) ||
            (isSameDir && sourceGtTargetOppo)));
      if (flip) {
        points = acc === "x" ? sourceTarget : targetSource;
      }
    }
  }

  return simplify([
    source,
    {
      x: sourceGapped.x + sourceGapOffset.x,
      y: sourceGapped.y + sourceGapOffset.y,
    },
    ...points,
    {
      x: targetGapped.x + targetGapOffset.x,
      y: targetGapped.y + targetGapOffset.y,
    },
    target,
  ]);
}

/* ─────────────────────────────────────────────
 * 통로 기반 경로
 * ───────────────────────────────────────────── */

export function routePoints(
  source: Pt,
  sourceSide: Side,
  target: Pt,
  targetSide: Side,
  route?: EdgeRoute | null,
): Pt[] {
  const corridors = route?.corridors ?? [];
  if (corridors.length === 0) {
    return smoothStepPoints(
      source,
      sourceSide,
      target,
      targetSide,
      route?.offset ?? 20,
    );
  }
  const so = route?.srcOffset ?? 14;
  const to = route?.tgtOffset ?? 14;
  const sd = DIR[sourceSide];
  const td = DIR[targetSide];
  const s1 = { x: source.x + sd.x * so, y: source.y + sd.y * so };
  const t1 = { x: target.x + td.x * to, y: target.y + td.y * to };

  const pts: Pt[] = [source, s1];
  let cur = s1;
  for (const c of corridors) {
    const p = c.axis === "y" ? { x: cur.x, y: c.value } : { x: c.value, y: cur.y };
    pts.push(p);
    cur = p;
  }
  const last = corridors[corridors.length - 1];
  // 마지막 통로를 따라 타깃 직전 지점까지 이동
  pts.push(last.axis === "y" ? { x: t1.x, y: cur.y } : { x: cur.x, y: t1.y });
  pts.push(t1, target);
  return simplify(pts);
}

/** 연속 중복점·일직선 중간점 제거 (직각 경로 정리) */
export function simplify(points: Pt[]): Pt[] {
  const EPS = 0.01;
  const out: Pt[] = [];
  for (const p of points) {
    const prev = out[out.length - 1];
    if (prev && Math.abs(prev.x - p.x) < EPS && Math.abs(prev.y - p.y) < EPS) {
      continue;
    }
    out.push({ x: p.x, y: p.y });
    while (out.length >= 3) {
      const a = out[out.length - 3];
      const b = out[out.length - 2];
      const c = out[out.length - 1];
      const collinearX = Math.abs(a.x - b.x) < EPS && Math.abs(b.x - c.x) < EPS;
      const collinearY = Math.abs(a.y - b.y) < EPS && Math.abs(b.y - c.y) < EPS;
      if (collinearX || collinearY) {
        out.splice(out.length - 2, 1);
      } else {
        break;
      }
    }
  }
  return out;
}

/** 꺾이는 지점을 둥글린 SVG path (React Flow getBend 와 동일한 모양) */
export function pointsToSvgPath(points: Pt[], radius = 5): string {
  if (points.length === 0) return "";
  const dist = (a: Pt, b: Pt) => Math.hypot(b.x - a.x, b.y - a.y);
  let d = `M${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const p = points[i];
    if (i === points.length - 1) {
      d += `L${p.x} ${p.y}`;
      continue;
    }
    const a = points[i - 1];
    const c = points[i + 1];
    const r = Math.min(dist(a, p) / 2, dist(p, c) / 2, radius);
    if ((a.x === p.x && p.x === c.x) || (a.y === p.y && p.y === c.y)) {
      d += `L${p.x} ${p.y}`;
    } else if (a.y === p.y) {
      const xDir = a.x < c.x ? -1 : 1;
      const yDir = a.y < c.y ? 1 : -1;
      d += `L ${p.x + r * xDir},${p.y}Q ${p.x},${p.y} ${p.x},${p.y + r * yDir}`;
    } else {
      const xDir = a.x < c.x ? 1 : -1;
      const yDir = a.y < c.y ? -1 : 1;
      d += `L ${p.x},${p.y + r * yDir}Q ${p.x},${p.y} ${p.x + r * xDir},${p.y}`;
    }
  }
  return d;
}

/**
 * 분기 라벨(Y/N) 위치 — 소스 핸들에서 빠져나온 첫 구간 옆.
 *   반환값은 라벨 박스 중심.
 */
export function branchLabelAnchor(points: Pt[], sourceSide: Side, gap = 14): Pt {
  const s = points[0];
  const d = DIR[sourceSide];
  // 진행 방향으로 gap 만큼, 수직 방향으로 9px 비켜 둔다 (선과 겹치지 않게)
  const along = { x: s.x + d.x * gap, y: s.y + d.y * gap };
  return d.x !== 0 ? { x: along.x, y: along.y - 9 } : { x: along.x + 10, y: along.y };
}
