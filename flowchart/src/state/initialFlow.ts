import { Edge, MarkerType, Node } from "reactflow";

import {
  activityNodeDesign,
  canvasDesign as C,
  shapeNodeDesign,
} from "../design";
import type { Activity, RcmRow } from "../types";
import type { ActivityNodeData } from "../components/ActivityNode";
import type { ShapeNodeData } from "../components/ShapeNode";

/**
 * 초기(부트스트랩) 더미 데이터 — 회사 산출물 예시 톤으로 격자 정렬.
 *
 *    [START] → [A1] → [A2] → [A3(R/C/M)] → [A4] → [END]
 *                                  ↓
 *                              [Document]
 *                ↑ (점선)
 *              [DB]
 *
 * 추후 엑셀 파싱이 붙으면 이 함수 대신 그 결과가 FlowProvider 의
 * initialNodes/initialEdges 로 들어간다.
 */

function rcm(partial: Partial<RcmRow> & { rowNum: number }): RcmRow {
  return {
    process: "",
    processName: "",
    subProcessNo: "",
    subProcessName: "",
    narrative: "",
    riskNo: "",
    riskDesc: "",
    controlNo: "",
    controlName: "",
    controlDesc: "",
    itSystem: "",
    controlOwner: "",
    controlOrg: "",
    keyCa: "",
    controlType: "",
    ...partial,
  };
}

const DUMMY_ACTIVITIES: Activity[] = [
  {
    actNo: 1,
    rcmRow: 4,
    actName: "구매요청 기안",
    teamOverride: "",
    subSteps: "",
    docNames: "",
    branchInfo: "",
    note: "",
    rcm: rcm({ rowNum: 4, controlOrg: "각 현업부서", itSystem: "전사 ERP" }),
  },
  {
    actNo: 2,
    rcmRow: 5,
    actName: "팀장 1차 승인",
    teamOverride: "",
    subSteps: "",
    docNames: "",
    branchInfo: "",
    note: "",
    rcm: rcm({ rowNum: 5, controlOrg: "각 현업부서 팀장", itSystem: "전사 ERP" }),
  },
  {
    actNo: 3,
    rcmRow: 6,
    actName: "재무팀 최종 승인",
    teamOverride: "재무팀",
    subSteps: "",
    docNames: "승인내역",
    branchInfo: "",
    note: "",
    rcm: rcm({
      rowNum: 6,
      controlOrg: "재무팀",
      itSystem: "전사 ERP",
      controlNo: "FA21-C02",
      controlName: "구매요청 최종 승인 (한도 통제)",
      controlType: "Automated",
      keyCa: "Y",
    }),
  },
  {
    actNo: 4,
    rcmRow: 7,
    actName: "발주 / 입고 처리",
    teamOverride: "",
    subSteps: "",
    docNames: "",
    branchInfo: "",
    note: "",
    rcm: rcm({ rowNum: 7, controlOrg: "구매팀", itSystem: "전사 ERP" }),
  },
];

const GRID = {
  X0: 60,
  COL_GAP: 40,
  ACT_TOP: 140,
  LABEL_TOP: 108,
  ATTACH_TOP: 290,
};

/**
 * 부트스트랩 시 단일 flowchart "DEFAULT" 로 초기화.
 * 엑셀 업로드 후 FlowProvider.loadFlowcharts 로 실제 데이터로 교체된다.
 */
export function buildInitialFlow(): {
  nodes: Node[];
  edges: Edge[];
} {
  const aW = activityNodeDesign.width;
  const seW = shapeNodeDesign.startEnd.width;
  const seH = shapeNodeDesign.startEnd.height;
  const riskW = shapeNodeDesign.risk.width;
  const ctrlW = shapeNodeDesign.keyControl.width;
  const ctW = shapeNodeDesign.controlType.width;
  const docW = shapeNodeDesign.document.width;
  const dbW = shapeNodeDesign.db.width;

  const aH = 88;
  const colX = (i: number) =>
    GRID.X0 + seW + GRID.COL_GAP + i * (aW + GRID.COL_GAP);
  const seY = GRID.ACT_TOP + aH / 2 - seH / 2;

  const activities = DUMMY_ACTIVITIES;
  const nodes: Node[] = [];

  nodes.push({
    id: "start",
    type: "shape",
    position: { x: GRID.X0, y: seY },
    data: { shapeKey: "startEnd", label: "START" } satisfies ShapeNodeData,
  });

  activities.forEach((a, idx) => {
    nodes.push({
      id: `act-${a.actNo}`,
      type: "activity",
      position: { x: colX(idx), y: GRID.ACT_TOP },
      data: { activity: a } satisfies ActivityNodeData,
    });
  });

  const endX = colX(activities.length);
  nodes.push({
    id: "end",
    type: "shape",
    position: { x: endX, y: seY },
    data: { shapeKey: "startEnd", label: "END" } satisfies ShapeNodeData,
  });

  // A3 위 [R][C][M] 라벨 띠
  const a3X = colX(2);
  const labelGap = 2;
  const labelTotalW = riskW + labelGap + ctrlW + labelGap + ctW;
  const labelStartX = a3X + (aW - labelTotalW) / 2;
  nodes.push({
    id: "lbl-risk-a3",
    type: "shape",
    position: { x: labelStartX, y: GRID.LABEL_TOP },
    data: { shapeKey: "risk", label: "R.FA21-1" } satisfies ShapeNodeData,
  });
  nodes.push({
    id: "lbl-ctrl-a3",
    type: "shape",
    position: { x: labelStartX + riskW + labelGap, y: GRID.LABEL_TOP },
    data: {
      shapeKey: "keyControl",
      label: "C.FA21-2",
    } satisfies ShapeNodeData,
  });
  nodes.push({
    id: "lbl-ct-a3",
    type: "shape",
    position: {
      x: labelStartX + riskW + labelGap + ctrlW + labelGap,
      y: GRID.LABEL_TOP,
    },
    data: { shapeKey: "controlType", label: "A" } satisfies ShapeNodeData,
  });

  // A3 아래 Document
  nodes.push({
    id: "doc-a3",
    type: "shape",
    position: { x: a3X + (aW - docW) / 2, y: GRID.ATTACH_TOP },
    data: { shapeKey: "document", label: "승인내역" } satisfies ShapeNodeData,
  });

  // A1 아래 DB
  const a1X = colX(0);
  nodes.push({
    id: "db-a1",
    type: "shape",
    position: { x: a1X + (aW - dbW) / 2, y: GRID.ATTACH_TOP - 10 },
    data: {
      shapeKey: "db",
      label: "전사 ERP",
      sublabel: "구매원장",
    } satisfies ShapeNodeData,
  });

  // 엣지
  const baseType = C.edgeType;
  const solid = (id: string, source: string, target: string): Edge => ({
    id,
    source,
    target,
    type: baseType,
    markerEnd: { type: MarkerType.ArrowClosed, color: C.edgeStroke },
    style: { stroke: C.edgeStroke, strokeWidth: C.edgeStrokeWidth },
  });
  const dashed = (id: string, source: string, target: string): Edge => ({
    id,
    source,
    target,
    type: baseType,
    markerEnd: { type: MarkerType.ArrowClosed, color: C.edgeStroke },
    style: {
      stroke: C.edgeStroke,
      strokeWidth: C.edgeStrokeWidth,
      strokeDasharray: C.edgeDashedPattern,
    },
  });

  const edges: Edge[] = [
    solid("e-start-a1", "start", `act-${activities[0].actNo}`),
    ...activities.slice(0, -1).map((a, i) =>
      solid(
        `e-a${a.actNo}-a${activities[i + 1].actNo}`,
        `act-${a.actNo}`,
        `act-${activities[i + 1].actNo}`,
      ),
    ),
    solid(
      "e-aLast-end",
      `act-${activities[activities.length - 1].actNo}`,
      "end",
    ),
    dashed("e-a3-doc", `act-${activities[2].actNo}`, "doc-a3"),
    dashed("e-db-a1", "db-a1", `act-${activities[0].actNo}`),
  ];

  return { nodes, edges };
}
