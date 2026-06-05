import { Edge, MarkerType, Node } from "reactflow";

import {
  activityNodeDesign,
  canvasDesign as C,
  shapeNodeDesign,
} from "../design";
import type { Activity, HeaderInfo } from "../types";
import {
  hasRisk,
  activityDocs,
  activityLocation,
  activityAutoHeight,
  parseSubSteps,
  isControlActivity,
  resolvedControl,
} from "../types";
import type { ActivityNodeData } from "../components/ActivityNode";
import type { ShapeNodeData } from "../components/ShapeNode";
import type { ParsedXlsx } from "./xlsxParser";

/**
 * 파싱 결과(ParsedXlsx) → N개의 flowchart 노드/엣지 세트로 변환.
 *
 * v4 매핑 시트 구조:
 *  - 모든 활동이 같은 시트, FLOWCHART_CODE 컬럼으로 어떤 flowchart 인지 구분
 *  - 같은 flowchart 의 모든 활동은 같은 RCM_ROW 를 참조 (1 통제 = N 활동)
 *  - 통제 라벨 띠 [R][C][M] 는 NOTE 가 "KC:" 로 시작하는 활동에만 부착
 *
 * 출력은 BuildResult.flowcharts 배열. 한 항목 = 한 sub-process flowchart.
 * UI 는 이 중 하나를 active 로 두고 캔버스에 그린다.
 */

export interface FlowchartBuilt {
  /** sub-process 코드 (예: "FA21"). 화면 드롭다운·PPT 파일명에 사용. */
  code: string;
  /** sub-process 이름 (예: "유지보수"). 헤더 표 소분류·드롭다운 라벨에 사용. */
  name: string;
  nodes: Node[];
  edges: Edge[];
}

export interface BuildResult {
  flowcharts: FlowchartBuilt[];
  headerInfo: HeaderInfo;
  warnings: string[];
}

const GRID = {
  X0: 60,
  COL_GAP: 40,
  PER_ROW: 4,
  // 첫 활동 행의 y. 활동 위에 라벨 세트(22px) 와 DB(-120) 가 들어가므로
  // 캔버스 헤더 표 / PPT 헤더 표 와 겹치지 않도록 충분히 내림.
  FIRST_ROW_ACT_Y: 280,
  // 행 간 거리 — 활동 높이가 텍스트 분량에 따라 88~220+ 로 늘어남을 감안.
  //   worst case 한 행 span: DB 위 120 + label 26 + activity 220 + 32 gap + doc 52 ≈ 450
  //   ROW_HEIGHT 가 그보다 충분히 커야 다음 행과 안 겹침. 520 으로 잡음.
  ROW_HEIGHT: 520,
  LABEL_TOP_OFFSET: -24,
  DB_TOP_OFFSET: -120,
  // doc 은 활동 하단에서 32px 띄움 (활동 height 가변이라 activity_bottom + GAP 으로 계산)
  DOC_TOP_GAP: 32,
};

const NON_DB_LOCATIONS = new Set([
  "manual",
  "수기",
  "수작업",
  "n/a",
  "na",
  "none",
  "-",
  "",
]);

function isDbLocation(location: string): boolean {
  const v = (location || "").trim().toLowerCase();
  return !NON_DB_LOCATIONS.has(v);
}

export function buildFlowFromExcel(parsed: ParsedXlsx): BuildResult {
  const warnings = [...parsed.warnings];

  // 활동을 flowchart 코드 별로 그룹핑
  //  - v4 정상: FLOWCHART_CODE 사용
  //  - v3 호환: flowchartCode 가 비면 RCM.subProcessNo 로 폴백
  const groups = new Map<string, Activity[]>();
  for (const a of parsed.activities) {
    const code = (a.flowchartCode || a.rcm?.subProcessNo || "DEFAULT").trim();
    const list = groups.get(code) ?? [];
    list.push(a);
    groups.set(code, list);
  }

  if (groups.size === 0) {
    return {
      flowcharts: [],
      headerInfo: parsed.headerInfo,
      warnings: [...warnings, "표시할 활동이 없습니다."],
    };
  }

  // 등장 순으로 정렬
  const codeOrder = parsed.flowchartCodes.length > 0
    ? parsed.flowchartCodes
    : [...groups.keys()];

  const flowcharts: FlowchartBuilt[] = [];
  for (const code of codeOrder) {
    const activities = groups.get(code);
    if (!activities || activities.length === 0) continue;
    const firstRcm = activities.find((a) => a.rcm)?.rcm;
    const name = firstRcm?.subProcessName || code;
    const { nodes, edges } = layoutSingleFlowchart(activities);
    flowcharts.push({ code, name, nodes, edges });
  }

  // 누락된 매칭이 있는 그룹도 fallback 으로 추가 (예외 케이스)
  for (const [code, activities] of groups) {
    if (flowcharts.some((f) => f.code === code)) continue;
    const firstRcm = activities.find((a) => a.rcm)?.rcm;
    const name = firstRcm?.subProcessName || code;
    const { nodes, edges } = layoutSingleFlowchart(activities);
    flowcharts.push({ code, name, nodes, edges });
  }

  return {
    flowcharts,
    headerInfo: parsed.headerInfo,
    warnings,
  };
}

/* ─────────────────────────────────────────────
 * 한 flowchart 의 활동 배열 → 격자(wrap) 배치
 *
 * v4 규약:
 *  - 같은 RCM_ROW 를 가진 여러 활동 중, NOTE 에 "KC:" 가 있는 활동에만 라벨 띠 부착
 *  - 활동의 LOCATION (or RCM.itSystem) 이 Manual/수기 가 아니면 DB 자동
 *  - DOC_NAMES 가 있으면 활동 아래 Document(들)
 *  - START / END 자동 추가
 *  - 가로 PER_ROW 마다 wrap
 * ───────────────────────────────────────────── */

function layoutSingleFlowchart(activities: Activity[]): {
  nodes: Node[];
  edges: Edge[];
} {
  // ACT_NO 별 정렬 (이미 parser 에서 정렬되어 있지만 안전하게)
  const sorted = [...activities].sort((a, b) => a.actNo - b.actNo);

  // ACT_NO 별 그룹핑 (한 활동 박스 = 한 ACT_NO. 통제는 KC 가 붙은 항목만)
  const byActNo = new Map<number, Activity[]>();
  for (const a of sorted) {
    const list = byActNo.get(a.actNo) ?? [];
    list.push(a);
    byActNo.set(a.actNo, list);
  }
  const actNos = [...byActNo.keys()].sort((a, b) => a - b);

  const aW = activityNodeDesign.width;
  const seW = shapeNodeDesign.startEnd.width;
  const seH = shapeNodeDesign.startEnd.height;
  const dbW = shapeNodeDesign.db.width;

  const aH = 96;

  function colXof(col: number): number {
    if (col < 0) return GRID.X0;
    return GRID.X0 + seW + GRID.COL_GAP + col * (aW + GRID.COL_GAP);
  }
  function rowActY(row: number): number {
    return GRID.FIRST_ROW_ACT_Y + row * GRID.ROW_HEIGHT;
  }
  function gridPos(idx: number) {
    return {
      row: Math.floor(idx / GRID.PER_ROW),
      col: idx % GRID.PER_ROW,
    };
  }

  const nodes: Node[] = [];

  // START
  const startActY = rowActY(0);
  const seY = startActY + aH / 2 - seH / 2;
  nodes.push({
    id: "start",
    type: "shape",
    position: { x: colXof(-1), y: seY },
    data: { shapeKey: "startEnd", label: "START" } satisfies ShapeNodeData,
  });

  actNos.forEach((actNo, idx) => {
    const group = byActNo.get(actNo)!;
    // 본체 활동: 첫 행을 기본으로 (보통 KC 가 붙은 게 단일이지만, 없으면 첫 행)
    const primary = group.find((a) => isControlActivity(a)) ?? group[0];
    const { row, col } = gridPos(idx);
    const x = colXof(col);
    const yAct = rowActY(row);
    // 단계 텍스트 줄바꿈을 감안한 자동 높이 (기준 박스에서 본문이 하단 띠를 침범하지 않도록)
    const actSteps = parseSubSteps(primary.subSteps);
    const actHeight = activityAutoHeight(actSteps.length, actSteps);

    nodes.push({
      id: `act-${actNo}`,
      type: "activity",
      position: { x, y: yAct },
      data: {
        activity: primary,
        customHeight: actHeight,
      } satisfies ActivityNodeData,
    });

    // 라벨 띠 — v8: 매핑 시트 CONTROL_NO 우선, 없으면 RCM JOIN
    //   같은 actNo 에 여러 활동(KC 표시) 가 있던 v4 케이스도 호환 — 모두 처리.
    const tripletRows = group
      .filter((a) => isControlActivity(a) || !!(a.riskNoRaw || "").trim())
      .map((a) => makeLabelTriplet(a))
      .filter((t): t is LabelTriplet => t !== null);

    tripletRows.forEach((triplet, rowIdx) => {
      addLabelRow(nodes, actNo, rowIdx, x, aW, yAct, triplet);
    });

    // 활동 위 DB — primary activity 의 location 기준
    const loc = activityLocation(primary);
    if (isDbLocation(loc)) {
      nodes.push({
        id: `db-a${actNo}`,
        type: "shape",
        position: {
          x: x + (aW - dbW) / 2,
          y: yAct + GRID.DB_TOP_OFFSET,
        },
        data: { shapeKey: "db", label: loc } satisfies ShapeNodeData,
      });
    }

    // 활동 아래 Document — DOC_NAMES 가 쉼표로 여러 개면 N개의 별도 박스를
    //   활동 폭에 맞춰 가로로 나란히 배치 (v7 — 한 박스에 몰아넣지 않음).
    //   "인사·조직 변경 통보서" 처럼 중점(·) 은 분리 대상 X (한 문서명).
    const docs = activityDocs(primary);
    if (docs.length > 0) {
      const docY = yAct + actHeight + GRID.DOC_TOP_GAP;
      const gap = 6;
      // 활동 폭과 동일하게 펼침. 한 개면 활동 폭 그대로, N개면 (aW - gap*(N-1)) / N.
      const perW = (aW - gap * (docs.length - 1)) / docs.length;
      const docH = shapeNodeDesign.document.height;
      docs.forEach((label, i) => {
        nodes.push({
          id: `doc-a${actNo}-${i}`,
          type: "shape",
          position: {
            x: x + i * (perW + gap),
            y: docY,
          },
          data: {
            shapeKey: "document",
            label,
            customWidth: perW,
            customHeight: docH,
          } satisfies ShapeNodeData,
        });
      });
    }

    // BRANCH_INFO → 활동 오른쪽에 마름모(diamond) 도형 자동 생성
    const branchText = primary.branchInfo.trim();
    if (branchText) {
      const diaW = 80;
      const diaH = 60;
      nodes.push({
        id: `branch-a${actNo}`,
        type: "shape",
        position: {
          x: x + aW + 10,
          y: yAct + (actHeight - diaH) / 2,
        },
        data: {
          shapeKey: "diamond",
          label: branchText,
          customWidth: diaW,
          customHeight: diaH,
        } satisfies ShapeNodeData,
      });
    }
  });

  // END — 마지막 활동 다음 칸.
  //   주의: 마지막 활동이 한 행을 정확히 가득 채운 경우 (PER_ROW와 일치) 단순 모듈러로
  //   계산하면 END 가 "다음 행 첫 칸" 으로 wrap 되어 어색한 긴 화살표가 생긴다.
  //   그래서 마지막 활동의 (row, col) 을 기준으로 한 칸 옆을 우선 시도하고,
  //   col 이 한계를 넘은 다음 행이라면 그때만 wrap.
  const lastIdx = actNos.length - 1;
  const lastGrid = gridPos(lastIdx);
  let endCol = lastGrid.col + 1;
  let endRow = lastGrid.row;
  // 너무 멀리 가서 슬라이드 폭을 벗어날 정도(>= PER_ROW + 1) 가 되면 다음 행으로 wrap.
  if (endCol > GRID.PER_ROW) {
    endCol = 0;
    endRow += 1;
  }
  const endX = colXof(endCol);
  const endActY = rowActY(endRow);
  const endY = endActY + aH / 2 - seH / 2;
  nodes.push({
    id: "end",
    type: "shape",
    position: { x: endX, y: endY },
    data: { shapeKey: "startEnd", label: "END" } satisfies ShapeNodeData,
  });

  // 엣지
  const solid = (
    id: string,
    source: string,
    target: string,
    sourceHandle = "right",
    targetHandle = "left",
  ): Edge => ({
    id,
    source,
    target,
    sourceHandle,
    targetHandle,
    type: C.edgeType,
    markerEnd: { type: MarkerType.ArrowClosed, color: C.edgeStroke },
    style: { stroke: C.edgeStroke, strokeWidth: C.edgeStrokeWidth },
  });
  const dashed = (
    id: string,
    source: string,
    target: string,
    sourceHandle = "bottom",
    targetHandle = "top",
  ): Edge => ({
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
  });

  const edges: Edge[] = [];
  if (actNos.length > 0) {
    edges.push(solid("e-start-first", "start", `act-${actNos[0]}`));
    for (let i = 0; i < actNos.length - 1; i++) {
      // 활동 간 연결 — 같은 행이면 right→left, 다음 행으로 wrap 되면 bottom→top
      // (회사 양식: 활동 4 → 활동 5 가 행 줄바꿈일 때 "오른쪽 끝 → 아래 → 왼쪽 처음" 흐름)
      // PPT 는 wrap 감지하여 수동 4-segment polyline 으로 그림 (pptExport.drawWrapEdge).
      const fromGrid = gridPos(i);
      const toGrid = gridPos(i + 1);
      const isWrap = toGrid.row > fromGrid.row;
      edges.push(
        solid(
          `e-a${actNos[i]}-a${actNos[i + 1]}`,
          `act-${actNos[i]}`,
          `act-${actNos[i + 1]}`,
          isWrap ? "bottom" : "right",
          isWrap ? "top" : "left",
        ),
      );
    }
    // 마지막 활동 → END. END 가 다른 행에 있으면 wrap 처리.
    {
      const lastActIdx = actNos.length - 1;
      const lastGrid2 = gridPos(lastActIdx);
      const isWrap = endRow > lastGrid2.row;
      edges.push(
        solid(
          "e-last-end",
          `act-${actNos[lastActIdx]}`,
          "end",
          isWrap ? "bottom" : "right",
          isWrap ? "top" : "left",
        ),
      );
    }

    for (const actNo of actNos) {
      const primary =
        byActNo.get(actNo)!.find((a) => isControlActivity(a)) ??
        byActNo.get(actNo)![0];
      const loc = activityLocation(primary);
      if (isDbLocation(loc)) {
        edges.push(
          dashed(`e-db-a${actNo}`, `db-a${actNo}`, `act-${actNo}`),
        );
      }
      const docs = activityDocs(primary);
      if (docs.length > 0) {
        // v7: N개 doc → N개 점선 화살표. 모두 활동 bottom 에서 출발.
        docs.forEach((_label, i) => {
          edges.push(
            dashed(
              `e-a${actNo}-doc-${i}`,
              `act-${actNo}`,
              `doc-a${actNo}-${i}`,
            ),
          );
        });
      }
      // BRANCH_INFO → 활동 right 에서 마름모 left 로 실선 연결
      if (primary.branchInfo.trim()) {
        edges.push(
          solid(
            `e-a${actNo}-branch`,
            `act-${actNo}`,
            `branch-a${actNo}`,
            "right",
            "left",
          ),
        );
      }
    }
  }

  return { nodes, edges };
}

/* ─────────────────────────────────────────────
 * 라벨 띠 헬퍼
 * ───────────────────────────────────────────── */

interface LabelTriplet {
  risk?: { no: string };
  /** isKey: true=Key(진분홍) / false=Non-Key(연분홍) / null=미지정(회색) */
  control?: { no: string; isKey: boolean | null };
  ctrlType?: "A" | "M" | "I";
}

function makeLabelTriplet(a: Activity): LabelTriplet | null {
  const resolved = resolvedControl(a);
  // v9: 위험번호 우선순위 — 매핑 시트 RISK_NO > RCM riskNo
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

/**
 * 활동 위에 [위험] [통제+배지] 를 **가로 한 줄** 로 배치.
 *
 *   v9 회사 양식:
 *     [R.FA.X.X-N] [C.FA.X.X-N | M]
 *          ↑              ↑       ↑
 *       위험 박스    통제 박스   배지(칩)
 *     ├────── 세트 전체 폭 ──────┤
 *              ← 활동 중앙 정렬 →
 *     ┌──────────────────────────┐
 *     │  활동 박스 (4분할)        │
 *     └──────────────────────────┘
 *
 *   - 세 요소가 딱 붙어서 한 세트 (사이 간격 2px)
 *   - 통제구분(M/A/I) 칩은 통제 박스 우측에 내장 (data.controlType)
 *   - 세트의 좌우 중심이 활동 박스 좌우 중심과 정렬
 *   - rowIdx > 0 인 경우 위로 더 쌓아 올림
 */
function addLabelRow(
  nodes: Node[],
  actNo: number,
  rowIdx: number,
  actX: number,
  actW: number,
  yAct: number,
  triplet: LabelTriplet,
) {
  const labelH = shapeNodeDesign.risk.height; // 22
  const riskW = shapeNodeDesign.risk.width; // 70
  const ctrlW = triplet.control?.isKey === true
    ? shapeNodeDesign.keyControl.width
    : shapeNodeDesign.nonkeyControl.width; // 80
  const gap = 2;

  // 총 세트 폭
  let totalW = 0;
  if (triplet.risk) totalW += riskW;
  if (triplet.risk && triplet.control) totalW += gap;
  if (triplet.control) totalW += ctrlW;

  // 세트 시작 X — 활동 중앙 정렬
  const startX = actX + (actW - totalW) / 2;

  // Y — 활동 바로 위(여백 4px), rowIdx 만큼 위로 쌓기
  const badgeGap = 4;
  const rowY = yAct - labelH - badgeGap - rowIdx * (labelH + gap);

  let curX = startX;

  // R (위험) — 왼쪽
  if (triplet.risk) {
    nodes.push({
      id: `lbl-r-a${actNo}-${rowIdx}`,
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

  // C (통제 + 배지) — 오른쪽
  if (triplet.control) {
    const shapeKey =
      triplet.control.isKey === true ? "keyControl" : "nonkeyControl";
    const neutralControl =
      triplet.control.isKey === null ? true : undefined;
    nodes.push({
      id: `lbl-c-a${actNo}-${rowIdx}`,
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
