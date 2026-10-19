import { Edge, MarkerType, Node } from "reactflow";

import { canvasDesign as C, shapeNodeDesign } from "../design";
import type { Activity } from "../types";
import { hasRisk, resolvedControl } from "../types";
import type { ShapeNodeData } from "../components/ShapeNode";

/**
 * 두 빌더(구 매핑 시트용 buildFlowFromExcel / 새 그래프 시트용 buildFlowFromGraph)
 * 가 함께 쓰는 노드·엣지 헬퍼.
 */

export type HandleSide = "left" | "right" | "top" | "bottom";

/** 프로세스 흐름 화살표 (실선). offset 은 꺾은선이 핸들에서 벗어나는 거리(px). */
export function solidEdge(
  id: string,
  source: string,
  target: string,
  sourceHandle: HandleSide = "right",
  targetHandle: HandleSide = "left",
  opts: { label?: string; offset?: number } = {},
): Edge {
  const edge: Edge = {
    id,
    source,
    target,
    sourceHandle,
    targetHandle,
    type: C.edgeType,
    markerEnd: { type: MarkerType.ArrowClosed, color: C.edgeStroke },
    style: { stroke: C.edgeStroke, strokeWidth: C.edgeStrokeWidth },
  };
  if (opts.label) {
    edge.label = opts.label;
    edge.labelStyle = { fontSize: 11, fontWeight: 700, fill: "#334155" };
    edge.labelBgStyle = { fill: "#FFFFFF" };
  }
  if (opts.offset != null) {
    (edge as Edge & { pathOptions?: { offset: number } }).pathOptions = {
      offset: opts.offset,
    };
  }
  return edge;
}

/** 데이터/정보 흐름 화살표 (점선) — DB↔활동, 활동→문서 */
export function dashedEdge(
  id: string,
  source: string,
  target: string,
  sourceHandle: HandleSide = "bottom",
  targetHandle: HandleSide = "top",
): Edge {
  return {
    id,
    source,
    target,
    sourceHandle,
    targetHandle,
    type: C.edgeType,
    markerEnd: { type: MarkerType.ArrowClosed, color: C.edgeStroke },
    style: {
      stroke: C.edgeStroke,
      strokeWidth: C.edgeStrokeWidth,
      strokeDasharray: C.edgeDashedPattern,
    },
  };
}

/* ─────────────────────────────────────────────
 * 라벨 띠 (위험 / 통제 + M·A·I 칩)
 * ───────────────────────────────────────────── */

export interface LabelTriplet {
  risk?: { no: string };
  /** isKey: true=Key / false=Non-Key / null=미지정(회색) */
  control?: { no: string; isKey: boolean | null };
  ctrlType?: "A" | "M" | "I";
}

export function makeLabelTriplet(a: Activity): LabelTriplet | null {
  const resolved = resolvedControl(a);
  // 위험번호 우선순위 — 매핑 시트 RISK_NO > RCM riskNo
  const mappingRiskNo = (a.riskNoRaw || "").trim();
  const r = mappingRiskNo
    ? { no: mappingRiskNo }
    : a.rcm && hasRisk(a.rcm)
      ? { no: a.rcm.riskNo }
      : undefined;
  const c = resolved.controlNo
    ? { no: resolved.controlNo, isKey: resolved.isKeyControl }
    : undefined;
  const t = resolved.controlNo ? resolved.controlType : undefined;
  if (!r && !c) return null;
  return { risk: r, control: c, ctrlType: t };
}

/** 라벨 띠 한 줄이 차지하는 높이 (줄 간격 포함) */
export const LABEL_ROW_H = shapeNodeDesign.risk.height + 2;
/** 활동 상단과 라벨 띠 사이 여백 */
export const LABEL_GAP = 4;

/**
 * 활동 위에 [위험] [통제+칩] 을 가로 한 줄로, 활동 중앙에 맞춰 배치.
 * rowIdx > 0 이면 위로 한 줄씩 더 쌓는다.
 */
export function addLabelRow(
  nodes: Node[],
  key: string | number,
  rowIdx: number,
  actX: number,
  actW: number,
  yAct: number,
  triplet: LabelTriplet,
) {
  const labelH = shapeNodeDesign.risk.height;
  const riskW = shapeNodeDesign.risk.width;
  const ctrlW =
    triplet.control?.isKey === true
      ? shapeNodeDesign.keyControl.width
      : shapeNodeDesign.nonkeyControl.width;
  const gap = 2;

  let totalW = 0;
  if (triplet.risk) totalW += riskW;
  if (triplet.risk && triplet.control) totalW += gap;
  if (triplet.control) totalW += ctrlW;

  const startX = actX + (actW - totalW) / 2;
  const rowY = yAct - labelH - LABEL_GAP - rowIdx * (labelH + gap);

  let curX = startX;
  if (triplet.risk) {
    nodes.push({
      id: `lbl-r-a${key}-${rowIdx}`,
      type: "shape",
      position: { x: curX, y: rowY },
      data: {
        shapeKey: "risk",
        label: triplet.risk.no,
        customWidth: riskW,
        customHeight: labelH,
      } satisfies ShapeNodeData,
    });
    curX += riskW + gap;
  }

  if (triplet.control) {
    const shapeKey =
      triplet.control.isKey === true ? "keyControl" : "nonkeyControl";
    const neutralControl = triplet.control.isKey === null ? true : undefined;
    nodes.push({
      id: `lbl-c-a${key}-${rowIdx}`,
      type: "shape",
      position: { x: curX, y: rowY },
      data: {
        shapeKey,
        label: triplet.control.no,
        customWidth: ctrlW,
        customHeight: labelH,
        controlType: triplet.ctrlType,
        neutralControl,
      } satisfies ShapeNodeData,
    });
  }
}
