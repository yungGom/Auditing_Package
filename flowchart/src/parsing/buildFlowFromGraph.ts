import { Edge, Node } from "reactflow";

import { activityNodeDesign, shapeNodeDesign } from "../design";
import type { Activity, HeaderInfo, RcmRow } from "../types";
import { activityAutoHeight, parseSubSteps } from "../types";
import type { ActivityNodeData } from "../components/ActivityNode";
import type { ShapeNodeData } from "../components/ShapeNode";
import type { RoutedEdgeData } from "../components/RoutedEdge";
import type { FlowchartBuilt } from "./buildFlowFromExcel";
import {
  addLabelRow,
  dashedEdge,
  LABEL_GAP,
  LABEL_ROW_H,
  makeLabelTriplet,
  solidEdge,
  type HandleSide,
} from "./flowShared";
import type { EdgeRoute } from "./edgeRouting";
import {
  idKey,
  type GraphFlowchart,
  type GraphNodeKind,
  type GraphRow,
  type ParsedGraph,
} from "./graphSheet";

/**
 * 그래프형 시트(ParsedGraph) → flowchart 노드/엣지.
 *
 *   스네이크 배치: 한 줄에 PER_ROW 칸, 줄마다 진행 방향을 바꿔(→ ← →) 줄바꿈 화살표를
 *   짧은 U턴으로 만든다. 행 높이는 그 줄에 있는 배지·DB·문서에 맞춰 자동 계산.
 *
 *   배치 순서 = 엑셀 행 순서. 화살표 = Next ID (비우면 다음 행).
 *   분기에서 갈라져 끝나는 Link 는 줄에 넣지 않고 분기 아래에 붙인다.
 *
 *   인접하지 않은 화살표(분기 건너뛰기·되돌아가기·다른 줄로 점프)는
 *   박스를 관통하지 않도록 통로(corridor)를 지정 — RoutedEdge / PPT 가 같은 경로로 그림.
 */

export type GraphLayout = "snake" | "swimlane";

export interface GraphBuildResult {
  flowcharts: FlowchartBuilt[];
  headerInfo: HeaderInfo;
  /** 좌측 통제·위험 카탈로그용 */
  activities: Activity[];
  warnings: string[];
}

/* ── 치수 ── */
const PER_ROW = 4;
const SLOT_W = activityNodeDesign.width; // 180
const COL_GAP = 80;
const X0 = 60;
const Y0 = 160;
const ROW_GAP = 90;

const DIAMOND = { w: shapeNodeDesign.diamond.width, h: shapeNodeDesign.diamond.height };
const LINK = { w: 170, h: 44 };
const SE = { w: shapeNodeDesign.startEnd.width, h: shapeNodeDesign.startEnd.height };
const DB = { w: 84, h: 60 };
const DOC_H = shapeNodeDesign.document.height;
const BELOW_GAP = 30; // 활동 하단 ~ DB/문서
const SIDE_LINK_GAP = 44; // 분기 하단 ~ Link

/* ─────────────────────────────────────────────
 * 내부 모델
 * ───────────────────────────────────────────── */

type GKind = "start" | "end" | GraphNodeKind;

interface GNode {
  key: string; // idKey
  nodeId: string; // React Flow node id
  kind: GKind;
  row?: GraphRow;
  activity?: Activity;
  w: number;
  h: number;
  /** 위·아래로 붙는 장식(배지·DB·문서·Link) 높이 */
  above: number;
  below: number;
  /** 위치 (중심) — 배치 후 채움 */
  cx: number;
  cy: number;
  /** 줄 정보 */
  gridRow: number;
  dir: 1 | -1;
  seqIdx: number; // -1 = 줄 밖 (분기 아래 Link)
  hostKey?: string; // 분기 아래 Link 의 호스트
}

interface GEdge {
  from: string;
  to: string;
  label?: string;
}

const START = "__START__";
const END = "__END__";

/* ─────────────────────────────────────────────
 * 행 → Activity (캔버스 활동 박스·카탈로그·Narrative 공용)
 * ───────────────────────────────────────────── */

function rowToActivity(fc: GraphFlowchart, row: GraphRow, idx: number): Activity {
  const numeric = /^\d+$/.test(row.id.trim());
  const rcm: RcmRow = {
    rowNum: row.excelRow,
    process: fc.cycleCode,
    processName: fc.cycleName,
    subProcessNo: fc.code,
    subProcessName: fc.subName || fc.processName || fc.code,
    narrative: row.narrative,
    riskNo: row.riskNo,
    riskDesc: row.riskDesc,
    controlNo: row.controlNo,
    controlName: row.controlTitle,
    controlDesc: row.controlDesc,
    itSystem: row.system,
    controlOwner: "",
    controlOrg: row.dept,
    keyCa: row.keyCa,
    controlType: row.controlType,
  };
  return {
    flowchartCode: fc.code,
    actNo: numeric ? Number(row.id.trim()) : idx + 1,
    displayNo: numeric ? undefined : row.id.trim(),
    rcmRow: row.excelRow,
    actName: row.name,
    teamOverride: row.dept,
    locationOverride: row.system,
    riskNoRaw: row.riskNo || undefined,
    controlNo: row.controlNo || undefined,
    controlTypeRaw: row.controlNo ? row.controlType || undefined : undefined,
    keyCaRaw: row.controlNo ? row.keyCa : undefined,
    subSteps: row.subSteps,
    docNames: row.docs.join(", "),
    branchInfo: "",
    note: "",
    rcm,
  };
}

function labelRowCount(a: Activity): number {
  return makeLabelTriplet(a) ? 1 : 0;
}

/* ─────────────────────────────────────────────
 * 메인
 * ───────────────────────────────────────────── */

export function buildFlowFromGraph(
  parsed: ParsedGraph,
  layout: GraphLayout = "snake",
): GraphBuildResult {
  const warnings = [...parsed.warnings];
  const flowcharts: FlowchartBuilt[] = [];
  const activities: Activity[] = [];

  for (const fc of parsed.flowcharts) {
    const built =
      layout === "swimlane"
        ? layoutSwimlane(fc, warnings, activities)
        : layoutSnake(fc, warnings, activities);
    flowcharts.push({
      code: fc.code,
      name: fc.subName || fc.processName || fc.code,
      nodes: built.nodes,
      edges: built.edges,
      header: {
        processName: fc.cycleName,
        middleCategory: fc.processName,
        subProcessName: fc.subName || fc.processName || fc.code,
        flowchartCode: fc.code,
      },
    });
  }

  return {
    flowcharts,
    headerInfo: parsed.headerInfo,
    activities,
    warnings,
  };
}

/* ─────────────────────────────────────────────
 * 공통: 노드·엣지 그래프 구성 + 검증
 * ───────────────────────────────────────────── */

interface Graph {
  nodes: Map<string, GNode>;
  order: string[]; // 엑셀 행 순서 (key)
  edges: GEdge[];
  sideLinks: Set<string>;
  hasEnd: boolean;
}

function buildGraph(
  fc: GraphFlowchart,
  warnings: string[],
  activities: Activity[],
): Graph {
  const nodes = new Map<string, GNode>();
  const order: string[] = [];
  const base = (key: string, nodeId: string, kind: GKind): GNode => ({
    key, nodeId, kind, w: 0, h: 0, above: 0, below: 0,
    cx: 0, cy: 0, gridRow: 0, dir: 1, seqIdx: -1,
  });

  nodes.set(START, { ...base(START, `start-${fc.code}`, "start"), w: SE.w, h: SE.h });

  fc.rows.forEach((row, idx) => {
    const key = idKey(row.id);
    const safe = key.replace(/[^A-Z0-9가-힣_-]/gi, "_");
    if (row.kind === "activity") {
      const a = rowToActivity(fc, row, idx);
      activities.push(a);
      const steps = parseSubSteps(a.subSteps);
      const labels = labelRowCount(a);
      const hasBelow = !!row.db || row.docs.length > 0;
      nodes.set(key, {
        ...base(key, `act-${fc.code}-${safe}`, "activity"),
        row,
        activity: a,
        w: SLOT_W,
        h: activityAutoHeight(steps.length, steps),
        above: labels ? LABEL_GAP + labels * LABEL_ROW_H : 0,
        below: hasBelow ? BELOW_GAP + Math.max(row.db ? DB.h : 0, row.docs.length ? DOC_H : 0) : 0,
      });
    } else if (row.kind === "decision") {
      nodes.set(key, {
        ...base(key, `dec-${fc.code}-${safe}`, "decision"),
        row,
        w: DIAMOND.w,
        h: DIAMOND.h,
      });
    } else {
      nodes.set(key, {
        ...base(key, `link-${fc.code}-${safe}`, "link"),
        row,
        w: LINK.w,
        h: LINK.h,
      });
    }
    order.push(key);
  });

  // 1) Next ID 명시 엣지
  const edges: GEdge[] = [];
  let hasEnd = false;
  for (const key of order) {
    const n = nodes.get(key)!;
    const row = n.row!;
    for (const nx of row.next) {
      const tk = idKey(nx.to);
      if (tk === "END") {
        edges.push({ from: key, to: END, label: nx.label });
        hasEnd = true;
      } else if (nodes.has(tk) && tk !== START) {
        edges.push({ from: key, to: tk, label: nx.label });
      } else {
        warnings.push(
          `${fc.code} ${row.excelRow}행: Next ID '${nx.to}' 를 찾을 수 없어 연결하지 않습니다.`,
        );
      }
    }
  }

  // 분기에서 갈라져 끝나는 Link (Next 없음 + 분기로부터만 들어옴) → 줄 밖에 배치
  const incoming = new Map<string, string[]>();
  for (const e of edges) {
    incoming.set(e.to, [...(incoming.get(e.to) ?? []), e.from]);
  }
  const sideLinks = new Set<string>();
  for (const key of order) {
    const n = nodes.get(key)!;
    if (n.kind !== "link" || n.row!.next.length > 0) continue;
    const preds = incoming.get(key) ?? [];
    if (preds.length > 0 && preds.every((p) => nodes.get(p)?.kind === "decision")) {
      sideLinks.add(key);
      n.hostKey = preds[0];
    }
  }

  // 2) Next ID 가 빈 행 → 다음 행(분기 아래 Link 제외)으로, 마지막이면 END
  order.forEach((key, i) => {
    const n = nodes.get(key)!;
    const row = n.row!;
    if (row.next.length > 0 || n.kind === "link") return;
    const nextKey = order.slice(i + 1).find((k) => !sideLinks.has(k));
    if (n.kind === "decision") {
      warnings.push(
        `${fc.code} ${row.excelRow}행: 분기 '${row.name}' 에 Next ID 가 없어 다음 행으로 연결합니다.`,
      );
    }
    if (nextKey) {
      edges.push({ from: key, to: nextKey });
    } else {
      edges.push({ from: key, to: END });
      hasEnd = true;
    }
  });

  // 분기 갈래 수 점검
  for (const key of order) {
    const n = nodes.get(key)!;
    if (n.kind === "decision" && n.row!.next.length === 1) {
      warnings.push(
        `${fc.code} ${n.row!.excelRow}행: 분기 '${n.row!.name}' 의 갈래가 1개입니다. 보통 2개 이상입니다 (예: 3(Y), L1(N)).`,
      );
    }
  }

  // START → 첫 행 (분기 아래 Link 제외)
  const firstKey = order.find((k) => !sideLinks.has(k));
  if (firstKey) edges.unshift({ from: START, to: firstKey });

  if (hasEnd) {
    nodes.set(END, { ...base(END, `end-${fc.code}`, "end"), w: SE.w, h: SE.h });
  }

  // 도달 불가 점검
  const reach = new Set<string>([START]);
  const queue = [START];
  while (queue.length) {
    const cur = queue.shift()!;
    for (const e of edges) {
      if (e.from === cur && !reach.has(e.to)) {
        reach.add(e.to);
        queue.push(e.to);
      }
    }
  }
  for (const key of order) {
    if (!reach.has(key)) {
      const r = nodes.get(key)!.row!;
      warnings.push(
        `${fc.code} ${r.excelRow}행: '${r.name}' 은 START 에서 이어지는 화살표가 없습니다. Next ID 를 확인하세요.`,
      );
    }
  }

  // 분기 아래 Link 가 있으면 분기의 아래 여백 확보
  for (const key of sideLinks) {
    const host = nodes.get(nodes.get(key)!.hostKey!)!;
    host.below = SIDE_LINK_GAP + LINK.h;
  }

  return { nodes, order, edges, sideLinks, hasEnd };
}

/* ─────────────────────────────────────────────
 * 스네이크 배치
 * ───────────────────────────────────────────── */

function layoutSnake(
  fc: GraphFlowchart,
  warnings: string[],
  activities: Activity[],
): { nodes: Node[]; edges: Edge[] } {
  const g = buildGraph(fc, warnings, activities);
  const seq = [START, ...g.order.filter((k) => !g.sideLinks.has(k))];
  if (g.hasEnd) seq.push(END);

  const nRows = Math.ceil(seq.length / PER_ROW);
  const slotCx = (col: number) => X0 + col * (SLOT_W + COL_GAP) + SLOT_W / 2;

  // 줄·칸 배정
  seq.forEach((key, i) => {
    const n = g.nodes.get(key)!;
    const gridRow = Math.floor(i / PER_ROW);
    const pos = i % PER_ROW;
    const dir: 1 | -1 = gridRow % 2 === 0 ? 1 : -1;
    const col = dir === 1 ? pos : PER_ROW - 1 - pos;
    n.seqIdx = i;
    n.gridRow = gridRow;
    n.dir = dir;
    n.cx = slotCx(col);
  });

  // 줄별 위/아래 범위 → 줄 중심선(cy) 쌓기
  const relTop: number[] = Array(nRows).fill(0);
  const relBottom: number[] = Array(nRows).fill(0);
  for (const key of seq) {
    const n = g.nodes.get(key)!;
    relTop[n.gridRow] = Math.min(relTop[n.gridRow], -n.h / 2 - n.above);
    relBottom[n.gridRow] = Math.max(relBottom[n.gridRow], n.h / 2 + n.below);
  }
  const rowCy: number[] = [];
  for (let r = 0; r < nRows; r++) {
    rowCy[r] =
      r === 0
        ? Y0 - relTop[0]
        : rowCy[r - 1] + relBottom[r - 1] + ROW_GAP - relTop[r];
  }
  for (const key of seq) {
    const n = g.nodes.get(key)!;
    n.cy = rowCy[n.gridRow];
  }

  // 분기 아래 Link 위치
  const linksByHost = new Map<string, string[]>();
  for (const key of g.sideLinks) {
    const host = g.nodes.get(key)!.hostKey!;
    linksByHost.set(host, [...(linksByHost.get(host) ?? []), key]);
  }
  for (const [hostKey, keys] of linksByHost) {
    const host = g.nodes.get(hostKey)!;
    const total = keys.length * LINK.w + (keys.length - 1) * 16;
    keys.forEach((k, i) => {
      const n = g.nodes.get(k)!;
      n.gridRow = host.gridRow;
      n.dir = host.dir;
      n.cx = host.cx - total / 2 + LINK.w / 2 + i * (LINK.w + 16);
      n.cy = host.cy + host.h / 2 + SIDE_LINK_GAP + LINK.h / 2;
    });
  }

  const bandTop = (r: number) => rowCy[r] + relTop[r];
  const bandBottom = (r: number) => rowCy[r] + relBottom[r];
  const gridLeft = X0;
  const gridRight = X0 + PER_ROW * SLOT_W + (PER_ROW - 1) * COL_GAP;

  const rfNodes: Node[] = [];
  const rfEdges: Edge[] = [];
  emitNodes(g, rfNodes, rfEdges);

  // 화살표
  const skipLane = new Map<number, number>(); // 줄별 건너뛰기 통로 번호
  const nextLane = (r: number) => {
    const k = skipLane.get(r) ?? 0;
    skipLane.set(r, k + 1);
    return k;
  };
  const outSide = (n: GNode): HandleSide => (n.dir === 1 ? "right" : "left");
  const inSide = (n: GNode): HandleSide => (n.dir === 1 ? "left" : "right");
  const bottomFree = (n: GNode) =>
    n.kind === "decision" && !linksByHost.has(n.key);

  g.edges.forEach((e, i) => {
    const u = g.nodes.get(e.from)!;
    const v = g.nodes.get(e.to)!;
    const id = `e-${fc.code}-${i}`;
    let sh: HandleSide;
    let th: HandleSide;
    let route: EdgeRoute | undefined;

    if (g.sideLinks.has(v.key) && v.hostKey === u.key) {
      // 분기 → 바로 아래 Link
      sh = "bottom";
      th = "top";
    } else if (v.seqIdx === u.seqIdx + 1 && u.seqIdx >= 0) {
      if (v.gridRow === u.gridRow) {
        sh = outSide(u);
        th = inSide(v);
      } else {
        // 줄바꿈: 바깥쪽으로 U턴
        sh = outSide(u);
        th = sh;
        const x =
          u.dir === 1
            ? Math.max(u.cx + u.w / 2, v.cx + v.w / 2) + 32
            : Math.min(u.cx - u.w / 2, v.cx - v.w / 2) - 32;
        route = { srcOffset: 12, tgtOffset: 12, corridors: [{ axis: "x", value: x }] };
      }
    } else {
      // 인접하지 않은 화살표
      sh = bottomFree(u) ? "bottom" : outSide(u);
      th = inSide(v);
      const srcOffset = sh === "bottom" ? 12 : 20;
      if (v.gridRow > u.gridRow) {
        // 아래 줄로 점프: 출발 줄 아래 통로 → 도착 박스 옆 칸 사이로 내려감
        const y = bandBottom(u.gridRow) + 22 + nextLane(u.gridRow) * 10;
        route = { srcOffset, tgtOffset: 22, corridors: [{ axis: "y", value: y }] };
      } else if (v.gridRow === u.gridRow) {
        // 같은 줄 건너뛰기/되돌아가기: 줄 아래 통로
        const y = bandBottom(u.gridRow) + 22 + nextLane(u.gridRow) * 10;
        route = { srcOffset, tgtOffset: 22, corridors: [{ axis: "y", value: y }] };
      } else {
        // 위 줄로 되돌아가기: 출발 줄 아래 → 바깥 세로 통로 → 도착 줄 위
        const y1 = bandBottom(u.gridRow) + 22 + nextLane(u.gridRow) * 10;
        const goLeft = (u.cx + v.cx) / 2 <= (gridLeft + gridRight) / 2;
        const x = goLeft ? gridLeft - 56 : gridRight + 56;
        const y2 = bandTop(v.gridRow) - 22 - nextLane(v.gridRow - 1 + 1000) * 10;
        route = {
          srcOffset,
          tgtOffset: 22,
          corridors: [
            { axis: "y", value: y1 },
            { axis: "x", value: x },
            { axis: "y", value: y2 },
          ],
        };
      }
    }

    rfEdges.push(routedEdge(id, u.nodeId, v.nodeId, sh, th, e.label, route));
  });

  return { nodes: rfNodes, edges: rfEdges };
}

/* ─────────────────────────────────────────────
 * 스윔레인 배치 — 담당부서별 가로 레인, 왼쪽→오른쪽 진행
 * ───────────────────────────────────────────── */

const LANE_LABEL_W = 70;
const LANE_PAD = 34;
const SW_COL_GAP = 44;

function layoutSwimlane(
  fc: GraphFlowchart,
  warnings: string[],
  activities: Activity[],
): { nodes: Node[]; edges: Edge[] } {
  const g = buildGraph(fc, warnings, activities);
  const main = g.order.filter((k) => !g.sideLinks.has(k));

  // 레인 = 담당부서 (레인 순서 → 첫 등장 순)
  const laneOf = (key: string): string => {
    const r = g.nodes.get(key)?.row;
    return (r?.dept || "").trim() || "(부서 미지정)";
  };
  const laneOrderVal = new Map<string, number>();
  const firstSeen = new Map<string, number>();
  g.order.forEach((k, i) => {
    const lane = laneOf(k);
    const lo = g.nodes.get(k)!.row!.laneOrder;
    if (!firstSeen.has(lane)) firstSeen.set(lane, i);
    if (lo != null && !laneOrderVal.has(lane)) laneOrderVal.set(lane, lo);
  });
  const lanes = [...firstSeen.keys()].sort((a, b) => {
    const la = laneOrderVal.get(a);
    const lb = laneOrderVal.get(b);
    if (la != null && lb != null && la !== lb) return la - lb;
    if (la != null && lb == null) return -1;
    if (la == null && lb != null) return 1;
    return firstSeen.get(a)! - firstSeen.get(b)!;
  });

  // 칸 = 진행 순서 (START, 각 행, END)
  const endN = g.hasEnd ? g.nodes.get(END)! : null;
  // 분기 아래 Link 묶음 (호스트별)
  const linksByHost = new Map<string, string[]>();
  for (const k of g.sideLinks) {
    const host = g.nodes.get(k)!.hostKey!;
    linksByHost.set(host, [...(linksByHost.get(host) ?? []), k]);
  }
  const linkSpan = (n: number) => n * LINK.w + (n - 1) * 16;

  // 칸 폭 = 그 칸 박스 폭 (START·END·마름모는 좁게) — 가로 길이를 줄여 글씨를 키움
  const seqCols = [START, ...main, ...(endN ? [END] : [])];
  let cursor = X0 + LANE_LABEL_W + 30;
  seqCols.forEach((k, i) => {
    const n = g.nodes.get(k)!;
    const hosted = linksByHost.get(k);
    const w = Math.max(n.w, hosted ? linkSpan(hosted.length) : 0);
    n.seqIdx = i;
    n.cx = cursor + w / 2;
    n.dir = 1;
    cursor += w + SW_COL_GAP;
  });

  // START/END 는 첫 노드/마지막 노드의 레인에 둔다
  const laneIdx = new Map<string, number>(lanes.map((l, i) => [l, i]));
  const nodeLane = new Map<string, number>();
  for (const k of main) nodeLane.set(k, laneIdx.get(laneOf(k))!);
  nodeLane.set(START, main.length ? nodeLane.get(main[0])! : 0);
  if (endN) {
    const preds = g.edges.filter((e) => e.to === END).map((e) => e.from);
    nodeLane.set(END, preds.length ? nodeLane.get(preds[0]) ?? 0 : 0);
  }
  for (const k of g.sideLinks) {
    const host = g.nodes.get(k)!.hostKey!;
    nodeLane.set(k, nodeLane.get(host) ?? 0);
  }

  // 레인별 높이 (그 레인 노드의 위/아래 장식 포함)
  const laneTop: number[] = [];
  const laneH: number[] = [];
  const laneCy: number[] = [];
  let y = Y0;
  lanes.forEach((_l, li) => {
    let up = 0;
    let down = 0;
    for (const [k, idx] of nodeLane) {
      if (idx !== li || g.sideLinks.has(k)) continue;
      const n = g.nodes.get(k)!;
      up = Math.max(up, n.h / 2 + n.above);
      down = Math.max(down, n.h / 2 + n.below);
    }
    // 분기 아래 Link 가 있는 레인은 아래 여백 확보
    for (const k of g.sideLinks) {
      if (nodeLane.get(k) === li) {
        const host = g.nodes.get(g.nodes.get(k)!.hostKey!)!;
        down = Math.max(down, host.h / 2 + SIDE_LINK_GAP + LINK.h);
      }
    }
    if (up === 0 && down === 0) {
      up = 44;
      down = 44;
    }
    laneTop[li] = y;
    laneCy[li] = y + LANE_PAD + up;
    laneH[li] = LANE_PAD * 2 + up + down;
    y += laneH[li];
  });

  for (const [k, li] of nodeLane) {
    if (g.sideLinks.has(k)) continue;
    const n = g.nodes.get(k)!;
    n.gridRow = li;
    n.cy = laneCy[li];
  }
  for (const [hostKey, keys] of linksByHost) {
    const host = g.nodes.get(hostKey)!;
    const span = linkSpan(keys.length);
    keys.forEach((k, i) => {
      const n = g.nodes.get(k)!;
      n.gridRow = host.gridRow;
      n.cx = host.cx - span / 2 + LINK.w / 2 + i * (LINK.w + 16);
      n.cy = host.cy + host.h / 2 + SIDE_LINK_GAP + LINK.h / 2;
    });
  }

  const rfNodes: Node[] = [];
  const rfEdges: Edge[] = [];

  // 레인 배경 (가장 먼저 → 맨 아래 레이어)
  const totalW = cursor - SW_COL_GAP + 30 - X0;
  lanes.forEach((lane, li) => {
    rfNodes.push({
      id: `lane-${fc.code}-${li}`,
      type: "shape",
      position: { x: X0, y: laneTop[li] },
      draggable: false,
      selectable: false,
      zIndex: -1,
      // 레인 위를 클릭해도 캔버스(빈 곳) 클릭으로 처리 — 도형 추가·패닝 방해 안 함
      style: { pointerEvents: "none" },
      data: {
        shapeKey: "lane",
        label: lane,
        customWidth: totalW,
        customHeight: laneH[li],
        laneLabelWidth: LANE_LABEL_W,
        locked: true,
      } satisfies ShapeNodeData,
    });
  });

  emitNodes(g, rfNodes, rfEdges);

  const inSide: HandleSide = "left";
  const lanesBottom = y;
  let laneCounter = 0;

  g.edges.forEach((e, i) => {
    const u = g.nodes.get(e.from)!;
    const v = g.nodes.get(e.to)!;
    const id = `e-${fc.code}-${i}`;
    let sh: HandleSide;
    let th: HandleSide;
    let route: EdgeRoute | undefined;

    if (g.sideLinks.has(v.key) && v.hostKey === u.key) {
      sh = "bottom";
      th = "top";
    } else if (v.seqIdx === u.seqIdx + 1) {
      // 바로 다음 칸 — 레인이 달라도 칸 사이 세로선으로 연결
      sh = "right";
      th = inSide;
    } else if (v.seqIdx > u.seqIdx) {
      // 앞으로 건너뛰기: 레인 아래쪽 통로 대신, 전체 레인 아래로 우회
      sh = u.kind === "decision" && !g.sideLinks.has(v.key) ? "bottom" : "right";
      const yy = lanesBottom + 18 + laneCounter++ * 10;
      route = {
        srcOffset: sh === "bottom" ? 12 : 20,
        tgtOffset: 20,
        corridors: [{ axis: "y", value: yy }],
      };
      th = inSide;
    } else {
      // 되돌아가기: 전체 레인 위로 우회
      sh = u.kind === "decision" ? "top" : "right";
      const yy = Y0 - 18 - laneCounter++ * 10;
      route = {
        srcOffset: sh === "top" ? 12 : 20,
        tgtOffset: 20,
        corridors: [{ axis: "y", value: yy }],
      };
      th = inSide;
    }
    rfEdges.push(routedEdge(id, u.nodeId, v.nodeId, sh, th, e.label, route));
  });

  return { nodes: rfNodes, edges: rfEdges };
}

/* ─────────────────────────────────────────────
 * 노드 출력 (배치 방식 공통)
 * ───────────────────────────────────────────── */

function emitNodes(g: Graph, rfNodes: Node[], rfEdges: Edge[]) {
  let seq = 0;
  const all = [START, ...g.order, ...(g.hasEnd ? [END] : [])];
  for (const key of all) {
    const n = g.nodes.get(key);
    if (!n) continue;
    const x = n.cx - n.w / 2;
    const yTop = n.cy - n.h / 2;
    seq += 1;

    if (n.kind === "start" || n.kind === "end") {
      rfNodes.push({
        id: n.nodeId,
        type: "shape",
        position: { x, y: yTop },
        data: {
          shapeKey: "startEnd",
          label: n.kind === "start" ? "START" : "END",
        } satisfies ShapeNodeData,
      });
      continue;
    }

    const row = n.row!;
    if (n.kind === "decision" || n.kind === "link") {
      rfNodes.push({
        id: n.nodeId,
        type: "shape",
        position: { x, y: yTop },
        data: {
          shapeKey: n.kind === "decision" ? "diamond" : "link",
          label: row.name,
          customWidth: n.kind === "link" ? LINK.w : undefined,
          customHeight: n.kind === "link" ? LINK.h : undefined,
          refId: row.id,
          narrative: row.narrative,
          dept: row.dept,
          seq,
        } satisfies ShapeNodeData,
      });
      continue;
    }

    // 활동 + 배지 + 아래 DB/문서
    const a = n.activity!;
    rfNodes.push({
      id: n.nodeId,
      type: "activity",
      position: { x, y: yTop },
      data: {
        activity: a,
        customHeight: n.h,
        seq,
      } satisfies ActivityNodeData,
    });

    const triplet = makeLabelTriplet(a);
    if (triplet) addLabelRow(rfNodes, n.nodeId, 0, x, n.w, yTop, triplet);

    const belowY = yTop + n.h + BELOW_GAP;
    const docs = row.docs;
    let docLeft = x;
    let docWidth = n.w;
    if (row.db) {
      const dbId = `db-${n.nodeId}`;
      const dbX = docs.length ? x : n.cx - DB.w / 2;
      const sys = row.system.trim();
      const isManual = !sys || /^(manual|수기|수작업)$/i.test(sys);
      rfNodes.push({
        id: dbId,
        type: "shape",
        position: { x: dbX, y: belowY },
        data: {
          shapeKey: "db",
          label: isManual ? row.db : sys,
          sublabel: isManual ? undefined : row.db,
          customWidth: DB.w,
          customHeight: DB.h,
        } satisfies ShapeNodeData,
      });
      rfEdges.push(dashedEdge(`e-${n.nodeId}-db`, n.nodeId, dbId, "bottom", "top"));
      docLeft = x + DB.w + 8;
      docWidth = n.w - DB.w - 8;
    }
    if (docs.length) {
      const gap = 6;
      const perW = (docWidth - gap * (docs.length - 1)) / docs.length;
      docs.forEach((label, i) => {
        const docId = `doc-${n.nodeId}-${i}`;
        rfNodes.push({
          id: docId,
          type: "shape",
          position: { x: docLeft + i * (perW + gap), y: belowY },
          data: {
            shapeKey: "document",
            label,
            customWidth: perW,
            customHeight: DOC_H,
          } satisfies ShapeNodeData,
        });
        rfEdges.push(
          dashedEdge(`e-${n.nodeId}-doc-${i}`, n.nodeId, docId, "bottom", "top"),
        );
      });
    }
  }
}

function routedEdge(
  id: string,
  source: string,
  target: string,
  sh: HandleSide,
  th: HandleSide,
  label: string | undefined,
  route: EdgeRoute | undefined,
): Edge {
  const e = solidEdge(id, source, target, sh, th, { label });
  e.type = "routed";
  e.data = { route } satisfies RoutedEdgeData;
  return e;
}
