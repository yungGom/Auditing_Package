import PptxGenJS from "pptxgenjs";
import type { Edge, Node } from "reactflow";

import {
  icfrColors,
  shapeNodeDesign,
  activityNodeDesign,
} from "../design";
import type { HeaderInfo } from "../types";
import {
  activityLocation,
  activityTeam,
  numberedStep,
  parseSubSteps,
  subStepsFontSize,
} from "../types";
import type { ActivityNodeData } from "../components/ActivityNode";
import type { NonActivityShape, ShapeNodeData } from "../components/ShapeNode";

/**
 * PPT 다운로드 — pptxgenjs 로 모든 flowchart 를 하나의 .pptx 로 출력.
 *
 *   페이지 1     : Flowchart 구성정보 (도형 11종 범례, 정적)
 *   페이지 2~N+1 : 각 flowchart (헤더 표 + 본문 캔버스 도형)
 *
 * 입력은 headerInfo + flowcharts[] (BuildResult.flowcharts 형태). 활성 여부와 무관하게
 * 모든 flowchart 가 한 파일에 들어간다.
 *
 * 좌표 매핑:
 *   캔버스 px → PPT inch 균일 스케일.
 *   각 flowchart 페이지마다 헤더 표(고정 영역) 아래에 본문.
 *
 * 한글 폰트: "맑은 고딕". 폰트 임베드는 불가 — 받는 사람 PC 폰트에 따라 다르게 표시될 수 있음.
 */

/* ─────────────────────────────────────────────
 * 상수 / 유틸
 * ───────────────────────────────────────────── */

const FONT = "맑은 고딕";
// 기준 양식: 4:3 (720×540pt = 10×7.5인치)
const MARGIN_X = 0.2;
const MARGIN_BOTTOM = 0.2;
const SLIDE_WIDTH_IN = 10;
const SLIDE_HEIGHT_IN = 7.5;
const HEADER_TOP_IN = 0.15;
const HEADER_HEIGHT_IN = 0.7;
const CONTENT_TOP = HEADER_TOP_IN + HEADER_HEIGHT_IN + 0.1; // 헤더 표 바로 아래

// 콘텐츠 둘레 안전 margin (slide 가장자리에서 5%)
const FIT_MARGIN_FRACTION = 0.05;

/**
 * v7 — WYSIWYG 좌표계.
 *
 *   더 이상 X·Y 를 따로 stretch 하지 않는다. 캔버스의 모든 노드를 둘러싸는
 *   bounding box 를 계산해 슬라이드의 가용 영역(헤더 표 아래)에 비율 유지로
 *   맞춰 넣는다 — 가로·세로 중 작은 쪽이 가용 영역의 (1 - 2·5%) 를 채우고
 *   나머지 방향은 가운데 정렬.
 *
 *   결과: 사용자가 캔버스에서 본 배치(상대 위치·간격) 가 PPT 에 그대로 옮겨짐.
 *   2-활동 flowchart 가 짧으면 짧은 대로, 5-활동이면 채우는 대로.
 *
 *   buildFlowchartSlide 가 슬라이드마다 이 세 값을 갱신한다.
 */
let activeScaleInPerPx = 0.009; // 1 캔버스 px = N 인치
let activeOffsetX = MARGIN_X;
let activeOffsetY = CONTENT_TOP;

/** 캔버스 px → PPT 인치 (스칼라 — 폭·높이에 동일하게 적용) */
function pxX(p: number): number {
  return p * activeScaleInPerPx;
}
function pxY(p: number): number {
  return p * activeScaleInPerPx;
}
function nx(canvasX: number): number {
  return activeOffsetX + canvasX * activeScaleInPerPx;
}
function ny(canvasY: number): number {
  return activeOffsetY + canvasY * activeScaleInPerPx;
}
function hex(c: string): string {
  return c.startsWith("#") ? c.slice(1) : c;
}

/**
 * 캔버스 px 폰트 → PPT 포인트 변환.
 *
 *   도형 크기는 WYSIWYG fit 으로 activeScaleInPerPx 만큼 줄어드는데, 폰트를 고정 pt
 *   로 두면 박스가 작아질 때 텍스트가 넘친다. 그래서 폰트도 동일 비율로 스케일해
 *   "박스 대비 글자 비율" 을 캔버스와 동일하게 유지한다 (= 진짜 WYSIWYG).
 *
 *   1 px ≈ 0.75pt (96dpi) 기준이 아니라, 인치 변환(scale) × 72 로 직접 포인트 산출.
 *   가독성을 위해 최소 5pt 보장 (기준 부서명 라벨이 5pt).
 */
function fpt(canvasPx: number): number {
  const pt = canvasPx * activeScaleInPerPx * 72;
  return Math.max(4, Math.round(pt * 10) / 10);
}

/* ─────────────────────────────────────────────
 * 메인 엔트리
 *   exportToPpt 가 받는 flowcharts 는 BuildResult.flowcharts 와 동일 구조.
 *   filename 지정 안 하면 Flowchart_<prefix>_<year>.pptx
 * ───────────────────────────────────────────── */

export interface PptFlowchart {
  code: string;
  name: string;
  nodes: Node[];
  edges: Edge[];
}

export async function exportToPpt(
  headerInfo: HeaderInfo,
  flowcharts: PptFlowchart[],
  filename?: string,
): Promise<void> {
  const pptx = new PptxGenJS();
  // 기준 표준 4:3 — 720×540pt = 10×7.5인치
  pptx.defineLayout({ name: "CT_4x3", width: 10, height: 7.5 });
  pptx.layout = "CT_4x3";
  pptx.title = headerInfo.processName || "ICFR Flowchart";
  pptx.author = headerInfo.author || "ICFR Flowchart Generator";

  // 페이지 1 — 가이드
  buildGuideSlide(pptx);

  // 페이지 2~ — 각 flowchart
  for (const fc of flowcharts) {
    const localHeader: HeaderInfo = {
      ...headerInfo,
      flowchartCode: fc.code,
      subProcessName: fc.name,
    };
    buildFlowchartSlide(pptx, localHeader, fc.nodes, fc.edges);
  }

  const fname =
    filename ?? defaultFilename(headerInfo, flowcharts.map((f) => f.code));
  await pptx.writeFile({ fileName: fname });
}

function defaultFilename(h: HeaderInfo, codes: string[]): string {
  const first = codes[0] ?? "";
  const match = first.match(/^[A-Z]+/i);
  const prefix = match ? match[0].toUpperCase() : "Flowchart";
  // lastChangeDate (YYYY-MM-DD) 에서 연도 추출, 없으면 올해
  const year = h.lastChangeDate?.match(/\d{4}/)?.[0] ?? String(new Date().getFullYear());
  return `Flowchart_${prefix}_${year}.pptx`;
}

/* ─────────────────────────────────────────────
 * 슬라이드 1 — Flowchart 구성정보 가이드
 * ───────────────────────────────────────────── */

function buildGuideSlide(pptx: PptxGenJS) {
  const slide = pptx.addSlide();

  // 상단 진분홍 타이틀 띠 (4:3 폭 10")
  slide.addShape("rect", {
    x: 0, y: 0, w: SLIDE_WIDTH_IN, h: 0.6,
    fill: { color: hex(icfrColors.headerBg) },
    line: { color: hex(icfrColors.headerBg) },
  });
  slide.addText("Flowchart 구성정보", {
    x: 0.3, y: 0.05, w: 7, h: 0.5,
    fontFace: FONT, fontSize: 20, bold: true, color: "FFFFFF",
    valign: "middle",
  });

  // 본문 박스 (외곽선만)
  slide.addShape("rect", {
    x: 0.3, y: 0.8, w: SLIDE_WIDTH_IN - 0.6, h: 6.5,
    fill: { color: "FFFFFF" },
    line: { color: hex(icfrColors.border), width: 0.75 },
  });

  // ── 왼쪽 컬럼 (아이콘 x=0.7, 라벨 x=2.05) ──
  const lIcon = 0.7;
  const lLabel = 2.05;
  const lLabelW = 2.7;
  drawLink(slide, lIcon, 1.2);
  drawStartEnd(slide, lIcon, 2.2);
  drawActivityIcon(slide, lIcon, 3.2);
  drawDB(slide, lIcon, 4.4);
  drawDiamondIcon(slide, lIcon, 5.6);

  const leftLabels = [
    "Link : 소분류 이상의 타 프로세스를 연결",
    "Start/End : 프로세스의 시작과 끝",
    "소분류 이하의 Activity\n*A-Activity No\n*B-Activity 수행 팀\n*C-Activity Name\n*D-Activity 발생 위치(시스템/Manual)",
    "DB : 시스템 Data Base 에 저장된 데이터/정보/회계전표 등",
    "분기점 : 의사결정/유형구분 등",
  ];
  const leftYs = [1.2, 2.2, 3.2, 4.4, 5.6];
  leftLabels.forEach((label, i) => {
    slide.addText(label, {
      x: lLabel, y: leftYs[i] - 0.1, w: lLabelW, h: 1.0,
      fontFace: FONT, fontSize: 9, color: "0F172A",
      valign: "top",
    });
  });

  // ── 오른쪽 컬럼 (아이콘 x=5.3, 라벨 x=6.5) ──
  const rIcon = 5.3;
  const rLabel = 6.5;
  const rLabelW = 3.2;
  drawInterfaceIcon(slide, rIcon, 1.2);
  slide.addText("시스템 간 Data 인터페이스", {
    x: rLabel, y: 1.15, w: rLabelW, h: 0.3,
    fontFace: FONT, fontSize: 9, color: "0F172A",
  });

  // 화살표 실선
  slide.addShape("line", {
    x: rIcon, y: 2.35, w: 0.7, h: 0,
    line: { color: hex(icfrColors.arrow), width: 1.25, endArrowType: "triangle" },
  });
  slide.addText("프로세스 흐름 표시", {
    x: rLabel, y: 2.2, w: rLabelW, h: 0.3,
    fontFace: FONT, fontSize: 9, color: "0F172A",
  });

  // 화살표 점선
  slide.addShape("line", {
    x: rIcon, y: 3.35, w: 0.7, h: 0,
    line: {
      color: hex(icfrColors.arrow), width: 1.25,
      dashType: "dash", endArrowType: "triangle",
    },
  });
  slide.addText("데이터/정보의 흐름 표시", {
    x: rLabel, y: 3.2, w: rLabelW, h: 0.3,
    fontFace: FONT, fontSize: 9, color: "0F172A",
  });

  // Document
  drawDocumentIcon(slide, rIcon, 4.0);
  slide.addText("Document : 생성되는 문서정보 등", {
    x: rLabel + 0.4, y: 4.2, w: rLabelW - 0.4, h: 0.3,
    fontFace: FONT, fontSize: 9, color: "0F172A",
  });

  // Risk / KC / NKC 색 범례
  const swatches: Array<{ y: number; color: string; label: string }> = [
    { y: 5.4, color: icfrColors.risk, label: "Risk Number" },
    { y: 5.75, color: icfrColors.keyCtrl, label: "Key Control Number" },
    { y: 6.1, color: icfrColors.nonkeyCtrl, label: "Non-Key Control Number" },
  ];
  for (const s of swatches) {
    slide.addShape("rect", {
      x: rIcon, y: s.y, w: 0.6, h: 0.25,
      fill: { color: hex(s.color) },
      line: { color: hex(s.color) },
    });
    slide.addText(s.label, {
      x: rLabel - 0.4, y: s.y - 0.02, w: rLabelW + 0.4, h: 0.3,
      fontFace: FONT, fontSize: 9, color: "0F172A",
    });
  }

  // 통제구분 A/M/I — 기준: A 핑크/흰, M 연핑크/검정, I 골드/검정
  const ctSize = 0.22;
  const ctY = 6.55;
  const ctColors: Array<{ k: "A" | "M" | "I"; color: string; fg: string }> = [
    { k: "A", color: icfrColors.ctrlA, fg: "FFFFFF" },
    { k: "M", color: icfrColors.ctrlM, fg: "0F172A" },
    { k: "I", color: icfrColors.ctrlI, fg: "0F172A" },
  ];
  ctColors.forEach((c, i) => {
    const xPos = rIcon + i * (ctSize + 0.05);
    slide.addShape("roundRect" as unknown as "rect", {
      x: xPos, y: ctY, w: ctSize, h: ctSize,
      fill: { color: hex(c.color) },
      line: { color: hex(c.color) },
      rectRadius: 0.03,
    });
    slide.addText(c.k, {
      x: xPos, y: ctY, w: ctSize, h: ctSize,
      fontFace: FONT, fontSize: 9, bold: true, color: c.fg,
      align: "center", valign: "middle",
    });
  });
  slide.addText("통제구분 : A(Auto)  M(Manual)  I(ITDM)", {
    x: rLabel - 0.4, y: ctY - 0.02, w: rLabelW + 0.4, h: 0.3,
    fontFace: FONT, fontSize: 9, color: "0F172A",
  });
}

/* ─── 가이드용 아이콘 헬퍼 ─── */

function drawLink(slide: PptxGenJS.Slide, x: number, y: number) {
  const w = 1.2, h = 0.55;
  slide.addShape("rect", {
    x, y, w, h,
    fill: { color: "FFFFFF" },
    line: { color: hex(icfrColors.border), width: 1 },
  });
  slide.addShape("line", {
    x: x + w / 3, y, w: 0, h,
    line: { color: hex(icfrColors.border), width: 0.75 },
  });
  slide.addShape("line", {
    x: x + 2 * w / 3, y, w: 0, h,
    line: { color: hex(icfrColors.border), width: 0.75 },
  });
}
function drawStartEnd(slide: PptxGenJS.Slide, x: number, y: number) {
  slide.addShape("rect", {
    x, y, w: 1.2, h: 0.55,
    fill: { color: "FFFFFF" },
    line: { color: hex(icfrColors.border), width: 1 },
  });
}
function drawActivityIcon(slide: PptxGenJS.Slide, x: number, y: number) {
  const W = 1.2, H = 0.9;
  const aCellW = 0.35, hdrH = 0.25, footH = 0.22;
  slide.addShape("rect", {
    x, y, w: W, h: H,
    fill: { color: "FFFFFF" },
    line: { color: hex(icfrColors.border), width: 1 },
  });
  slide.addShape("rect", {
    x, y, w: W, h: hdrH,
    fill: { color: hex(icfrColors.actHdr) },
    line: { color: hex(icfrColors.border), width: 0.5 },
  });
  slide.addShape("line", {
    x: x + aCellW, y, w: 0, h: hdrH,
    line: { color: hex(icfrColors.border), width: 0.5 },
  });
  slide.addShape("rect", {
    x, y: y + H - footH, w: W, h: footH,
    fill: { color: hex(icfrColors.actHdr) },
    line: { color: hex(icfrColors.border), width: 0.5 },
  });
  slide.addText("A", {
    x, y, w: aCellW, h: hdrH,
    fontFace: FONT, fontSize: 8, align: "center", valign: "middle", color: "0F172A",
  });
  slide.addText("B", {
    x: x + aCellW, y, w: W - aCellW, h: hdrH,
    fontFace: FONT, fontSize: 8, align: "center", valign: "middle", color: "0F172A",
  });
  slide.addText("C", {
    x, y: y + hdrH, w: W, h: H - hdrH - footH,
    fontFace: FONT, fontSize: 9, align: "center", valign: "middle", color: "0F172A",
  });
  slide.addText("D", {
    x, y: y + H - footH, w: W, h: footH,
    fontFace: FONT, fontSize: 8, align: "center", valign: "middle", color: "0F172A",
  });
}
function drawDB(slide: PptxGenJS.Slide, x: number, y: number) {
  slide.addShape("can", {
    x, y, w: 1.0, h: 0.75,
    fill: { color: hex(icfrColors.dbFill) },
    line: { color: hex(icfrColors.dbBorder), width: 1 },
  });
  slide.addText("SAP\nFI 전표", {
    x, y, w: 1.0, h: 0.75,
    fontFace: FONT, fontSize: 8, bold: true, color: "FFFFFF",
    align: "center", valign: "middle",
  });
}
function drawDiamondIcon(slide: PptxGenJS.Slide, x: number, y: number) {
  slide.addShape("diamond", {
    x, y, w: 1.3, h: 0.7,
    fill: { color: "FFFFFF" },
    line: { color: hex(icfrColors.border), width: 1 },
  });
}
function drawInterfaceIcon(slide: PptxGenJS.Slide, x: number, y: number) {
  slide.addShape("ellipse", {
    x, y, w: 0.45, h: 0.45,
    fill: { color: "E0E0E0" },
    line: { color: hex(icfrColors.border), width: 1 },
  });
  slide.addText("I/F", {
    x, y, w: 0.45, h: 0.45,
    fontFace: FONT, fontSize: 8, bold: true, color: "0F172A",
    align: "center", valign: "middle",
  });
}
function drawDocumentIcon(slide: PptxGenJS.Slide, x: number, y: number) {
  slide.addShape("flowChartDocument", {
    x, y, w: 1.2, h: 0.6,
    fill: { color: hex(icfrColors.docFill) },
    line: { color: hex(icfrColors.docBorder), width: 0.75 },
  });
}

/* ─────────────────────────────────────────────
 * 슬라이드 2~ — flowchart 본문
 * ───────────────────────────────────────────── */

function buildFlowchartSlide(
  pptx: PptxGenJS,
  headerInfo: HeaderInfo,
  nodes: Node[],
  edges: Edge[],
) {
  const slide = pptx.addSlide();

  // 상단 헤더 표
  drawHeaderRow(slide, headerInfo);

  // ── v7 WYSIWYG: 캔버스 bounding box 를 슬라이드 가용 영역에 비율 유지 fit ──
  //   사용자가 본 배치 그대로(상대 위치·간격) 옮겨오기 위해 X·Y 동일 스칼라.
  //   여기서 X_STRETCH 같은 가로 늘리기를 하지 않으므로, 2-활동 짧은 flowchart 는
  //   짧은 그대로 가운데 정렬, 8-활동 wrap 은 슬라이드 폭을 가득 채우는 식.
  const bbox = computeBoundingBox(nodes);

  const usableW = SLIDE_WIDTH_IN - 2 * MARGIN_X;
  const usableTop = CONTENT_TOP;
  const usableH = SLIDE_HEIGHT_IN - usableTop - MARGIN_BOTTOM;

  // 가용 영역 안쪽으로 5% margin 확보 → 실제로 콘텐츠가 차지할 영역
  const targetW = usableW * (1 - 2 * FIT_MARGIN_FRACTION);
  const targetH = usableH * (1 - 2 * FIT_MARGIN_FRACTION);

  const scaleByW = targetW / bbox.width;
  const scaleByH = targetH / bbox.height;
  // letterbox: 양쪽 다 안 넘기는 최대 스케일
  const scale = Math.max(0.001, Math.min(scaleByW, scaleByH));

  const contentW = bbox.width * scale;
  const contentH = bbox.height * scale;
  // 콘텐츠 좌상단이 들어갈 위치 — 가용 영역 안에서 가운데
  const contentLeft = MARGIN_X + (usableW - contentW) / 2;
  const contentTop = usableTop + (usableH - contentH) / 2;

  activeScaleInPerPx = scale;
  activeOffsetX = contentLeft - bbox.minX * scale;
  activeOffsetY = contentTop - bbox.minY * scale;

  // 노드 인덱스
  const nodeById = new Map<string, Node>();
  for (const n of nodes) nodeById.set(n.id, n);

  // 노드 (활동/도형)
  for (const n of nodes) {
    if (n.type === "activity") {
      drawActivity(slide, n);
    } else if (n.type === "shape") {
      drawShapeNode(slide, n);
    }
  }

  // 엣지
  for (const e of edges) {
    drawEdge(slide, e, nodeById);
  }
}

/* ─── 헤더 표 (재설계: 셀 폭↑ + 중/소분류 2서브행 스택) ─── */

function drawHeaderRow(slide: PptxGenJS.Slide, h: HeaderInfo) {
  const y = HEADER_TOP_IN;
  const rowH = HEADER_HEIGHT_IN;
  const subH = rowH / 2;

  // 헤더 표 가용 폭 — 슬라이드 폭에서 좌우 마진을 뺀 영역 전체를 채움
  const totalW = SLIDE_WIDTH_IN - MARGIN_X * 2;

  // 라벨 칸 폭 — pptxgenjs 기본 inset(0.1in) 감안하여 충분한 여유 확보.
  // "회사명"·"대분류"·"중분류"·"소분류" 같은 짧은 라벨도 한 줄에 들어가도록.
  const labelLwShort = 0.8;
  const labelLwLong = 1.1; // "Flowchart Code", "Last Change Date"

  // 5개 컬럼이 가용 폭 균등 분할
  const totalLabelW = labelLwShort * 3 + labelLwLong * 2;
  const totalValueW = totalW - totalLabelW;
  const valueVw = totalValueW / 5;

  let x = MARGIN_X;

  // 회사명
  drawCellPair(slide, {
    x, y, lw: labelLwShort, vw: valueVw, h: rowH,
    label: "회사명", value: h.company,
  });
  x += labelLwShort + valueVw;

  // 대분류
  drawCellPair(slide, {
    x, y, lw: labelLwShort, vw: valueVw, h: rowH,
    label: "대분류", value: h.processName,
  });
  x += labelLwShort + valueVw;

  // 중/소분류 — 2 서브행 스택. 대분류와 동일한 (lw + vw) 폭, 전체 높이 동일.
  drawCellPair(slide, {
    x, y, lw: labelLwShort, vw: valueVw, h: subH,
    label: "중분류", value: h.middleCategory,
  });
  drawCellPair(slide, {
    x, y: y + subH, lw: labelLwShort, vw: valueVw, h: subH,
    label: "소분류", value: h.subProcessName,
  });
  x += labelLwShort + valueVw;

  // Flowchart Code
  drawCellPair(slide, {
    x, y, lw: labelLwLong, vw: valueVw, h: rowH,
    label: "Flowchart Code", value: h.flowchartCode,
  });
  x += labelLwLong + valueVw;

  // Last Change Date
  drawCellPair(slide, {
    x, y, lw: labelLwLong, vw: valueVw, h: rowH,
    label: "Last Change Date", value: h.lastChangeDate,
  });
}

interface CellPairSpec {
  x: number;
  y: number;
  lw: number;
  vw: number;
  h: number;
  label: string;
  value: string;
}

function drawCellPair(slide: PptxGenJS.Slide, c: CellPairSpec) {
  const { x, y, lw, vw, h, label, value } = c;
  // 라벨 (진분홍) — 내부 inset 작게(0.03) 하여 텍스트가 한 줄에 들어가도록
  slide.addShape("rect", {
    x, y, w: lw, h,
    fill: { color: hex(icfrColors.headerBg) },
    line: { color: hex(icfrColors.headerBg) },
  });
  slide.addText(label, {
    x, y, w: lw, h,
    fontFace: FONT, fontSize: 9, bold: true, color: "FFFFFF",
    align: "center", valign: "middle",
    margin: 0.02,
    autoFit: true,
  });
  // 값 (흰 배경)
  slide.addShape("rect", {
    x: x + lw, y, w: vw, h,
    fill: { color: "FFFFFF" },
    line: { color: hex(icfrColors.border), width: 0.5 },
  });
  slide.addText(value || "—", {
    x: x + lw, y, w: vw, h,
    fontFace: FONT, fontSize: 9, color: "0F172A",
    align: "center", valign: "middle",
    margin: 0.04,
    autoFit: true,
  });
}

/* ─── 활동 박스 4분할 ─── */

function drawActivity(slide: PptxGenJS.Slide, node: Node) {
  const data = node.data as ActivityNodeData;
  const a = data.activity;
  const W = pxX(nodeWidthPx(node));
  const H = pxY(nodeHeightPx(node));
  // 활동번호 칸은 본문 폭의 일정 비율 — 좁은 활동에서도 비례 유지
  const aCellW = Math.min(
    pxX(activityNodeDesign.actNoColWidth),
    W * 0.2,
  );
  // 헤더/푸터는 캔버스와 동일하게 고정 픽셀 (HDR_PX=24, FOOT_PX=20)
  // 활동 박스가 단계 수에 따라 커져도 헤더·푸터 높이는 일정하게 두고 본문만 늘어남.
  const hdrH = pxY(24);
  const footH = pxY(20);
  const x = nx(node.position.x);
  const y = ny(node.position.y);

  // v5: SUB_STEPS 한 셀에 줄바꿈으로 여러 단계 입력 → ①②③ 자동 번호 + 동적 폰트
  const steps = parseSubSteps(a.subSteps);
  const stepCount = steps.length;
  const stepFontSize = subStepsFontSize(stepCount);

  slide.addShape("rect", {
    x, y, w: W, h: H,
    fill: { color: "FFFFFF" },
    line: { color: hex(icfrColors.border), width: 1 },
  });
  slide.addShape("rect", {
    x, y, w: W, h: hdrH,
    fill: { color: hex(icfrColors.actHdr) },
    line: { color: hex(icfrColors.border), width: 0.5 },
  });
  slide.addShape("line", {
    x: x + aCellW, y, w: 0, h: hdrH,
    line: { color: hex(icfrColors.border), width: 0.5 },
  });
  slide.addShape("rect", {
    x, y: y + H - footH, w: W, h: footH,
    fill: { color: hex(icfrColors.actHdr) },
    line: { color: hex(icfrColors.border), width: 0.5 },
  });

  slide.addText(String(a.actNo), {
    x, y, w: aCellW, h: hdrH,
    fontFace: FONT, fontSize: fpt(activityNodeDesign.actNoFontSize), bold: true, color: "0F172A",
    align: "center", valign: "middle",
    margin: 0.01,
  });
  slide.addText(activityTeam(a) || " ", {
    x: x + aCellW, y, w: W - aCellW, h: hdrH,
    fontFace: FONT, fontSize: fpt(activityNodeDesign.teamFontSize), color: "0F172A",
    align: "center", valign: "middle",
    margin: 0.02,
    shrinkText: true,
  });

  // 본문 — 활동명 + (있다면) 번호 매긴 단계 리스트
  //   단계 0개: 활동명을 가운데 정렬 (기존 동작 유지)
  //   단계 1개+: 활동명(가운데/굵게) → 줄바꿈 → ①② 번호 매긴 단계(왼쪽/작은 폰트)
  const bodyY = y + hdrH;
  const bodyH = H - hdrH - footH;
  if (stepCount === 0) {
    slide.addText(a.actName, {
      x, y: bodyY, w: W, h: bodyH,
      fontFace: FONT, fontSize: fpt(activityNodeDesign.bodyTitleFontSize), bold: true, color: "0F172A",
      align: "center", valign: "middle",
      margin: 0.02,
      shrinkText: true,
    });
  } else {
    const runs: Array<{
      text: string;
      options: {
        bold?: boolean;
        fontSize?: number;
        align?: "left" | "center" | "right";
        breakLine?: boolean;
      };
    }> = [
      {
        text: a.actName,
        options: {
          bold: true,
          fontSize: fpt(activityNodeDesign.bodyTitleFontSize),
          align: "center",
          breakLine: true,
        },
      },
    ];
    steps.forEach((s, i) => {
      runs.push({
        text: numberedStep(i, s),
        options: {
          bold: false,
          fontSize: fpt(stepFontSize),
          align: "left",
          breakLine: i < steps.length - 1,
        },
      });
    });
    slide.addText(runs, {
      x, y: bodyY, w: W, h: bodyH,
      fontFace: FONT, color: "0F172A",
      valign: "top",
      margin: 0.04,
      wrap: true,
      shrinkText: true,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
  }

  slide.addText(activityLocation(a), {
    x, y: y + H - footH, w: W, h: footH,
    fontFace: FONT, fontSize: fpt(activityNodeDesign.locationFontSize), color: "0F172A",
    align: "center", valign: "middle",
    margin: 0.02,
    shrinkText: true,
  });
}

/* ─── 도형 노드 (Shape) ─── */

function drawShapeNode(slide: PptxGenJS.Slide, node: Node) {
  const data = node.data as ShapeNodeData;
  const key = data.shapeKey as NonActivityShape;
  // 모든 도형 공통 — customWidth/Height 우선, 없으면 design.ts 기본
  const W = pxX(nodeWidthPx(node));
  const H = pxY(nodeHeightPx(node));
  const x = nx(node.position.x);
  const y = ny(node.position.y);

  switch (key) {
    case "startEnd": {
      slide.addShape("rect", {
        x, y, w: W, h: H,
        fill: { color: "FFFFFF" },
        line: { color: hex(icfrColors.border), width: 1 },
      });
      slide.addText(data.label, {
        x, y, w: W, h: H,
        fontFace: FONT, fontSize: fpt(shapeNodeDesign.startEnd.fontSize), bold: true, color: "0F172A",
        align: "center", valign: "middle",
        shrinkText: true,
      });
      return;
    }
    case "link": {
      slide.addShape("rect", {
        x, y, w: W, h: H,
        fill: { color: "FFFFFF" },
        line: { color: hex(icfrColors.border), width: 1 },
      });
      slide.addShape("line", {
        x: x + W / 3, y, w: 0, h: H,
        line: { color: hex(icfrColors.border), width: 0.75 },
      });
      slide.addShape("line", {
        x: x + 2 * W / 3, y, w: 0, h: H,
        line: { color: hex(icfrColors.border), width: 0.75 },
      });
      if (data.label) {
        slide.addText(data.label, {
          x, y, w: W, h: H,
          fontFace: FONT, fontSize: fpt(shapeNodeDesign.link.fontSize), color: "0F172A",
          align: "center", valign: "middle",
          shrinkText: true,
        });
      }
      return;
    }
    case "diamond": {
      slide.addShape("diamond", {
        x, y, w: W, h: H,
        fill: { color: "FFFFFF" },
        line: { color: hex(icfrColors.border), width: 1 },
      });
      slide.addText(data.label, {
        x: x + 0.05, y, w: W - 0.1, h: H,
        fontFace: FONT, fontSize: fpt(shapeNodeDesign.diamond.fontSize), color: "0F172A",
        align: "center", valign: "middle",
        shrinkText: true,
      });
      return;
    }
    case "risk":
    case "keyControl":
    case "nonkeyControl": {
      const isNeutral =
        (key === "nonkeyControl") && !!(data as ShapeNodeData).neutralControl;
      const fill =
        key === "risk"
          ? icfrColors.risk
          : key === "keyControl"
            ? icfrColors.keyCtrl
            : isNeutral
              ? icfrColors.neutralCtrl
              : icfrColors.nonkeyCtrl;
      const fg = key === "risk" || isNeutral ? "0F172A" : "FFFFFF";

      const showChip =
        (key === "keyControl" || key === "nonkeyControl") &&
        !!data.controlType;
      const chipW = showChip ? H : 0;
      const mainW = W - chipW;

      // 본체 (라벨) — 모서리 둥근 사각형 (기준 양식 형태)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      slide.addShape("roundRect" as any, {
        x, y, w: mainW, h: H,
        fill: { color: hex(fill) },
        line: { color: hex(fill) },
        rectRadius: 0.4,
      });
      slide.addText(data.label, {
        x, y, w: mainW, h: H,
        fontFace: FONT, fontSize: fpt(shapeNodeDesign.risk.fontSize), bold: true, color: fg,
        align: "center", valign: "middle",
        margin: 0.01,
        shrinkText: true,
      });

      // M/A/I 칩 — 통제구분별 색상 (기준 구성정보 가이드)
      if (showChip && data.controlType) {
        const letter = data.controlType as "A" | "M" | "I";
        const CHIP_COLORS: Record<"A" | "M" | "I", { bg: string; fg: string }> = {
          A: { bg: icfrColors.ctrlA, fg: "FFFFFF" },
          M: { bg: icfrColors.ctrlM, fg: "FFFFFF" },
          I: { bg: icfrColors.ctrlI, fg: "0F172A" },
        };
        const safeLetter = (letter === "A" || letter === "M" || letter === "I") ? letter : "M";
        const chipColor = CHIP_COLORS[safeLetter];
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        slide.addShape("roundRect" as any, {
          x: x + mainW, y, w: chipW, h: H,
          fill: { color: hex(chipColor.bg) },
          line: { color: hex(chipColor.bg) },
          rectRadius: 0.4,
        });
        slide.addText(safeLetter, {
          x: x + mainW, y, w: chipW, h: H,
          fontFace: FONT, fontSize: fpt(shapeNodeDesign.controlType.fontSize), bold: true, color: chipColor.fg,
          align: "center", valign: "middle",
          margin: 0.01,
        });
      }
      return;
    }
    case "controlType": {
      const letter = (data.label || "M").toUpperCase().charAt(0) as
        | "A" | "M" | "I";
      const safe = letter === "A" || letter === "M" || letter === "I"
        ? letter : "M";
      const fill =
        safe === "A" ? icfrColors.ctrlA
          : safe === "M" ? icfrColors.ctrlM
            : icfrColors.ctrlI;
      const fg = safe === "I" ? "0F172A" : "FFFFFF";
      slide.addShape("rect", {
        x, y, w: W, h: H,
        fill: { color: hex(fill) },
        line: { color: hex(fill) },
      });
      slide.addText(safe, {
        x, y, w: W, h: H,
        fontFace: FONT, fontSize: fpt(shapeNodeDesign.controlType.fontSize), bold: true, color: fg,
        align: "center", valign: "middle",
        margin: 0.01,
      });
      return;
    }
    case "document": {
      // v7: doc 박스 = 한 문서 = 한 노드.
      //   텍스트가 박스 경계를 넘지 않도록 shrinkText + 작은 폰트 적용.
      slide.addShape("flowChartDocument", {
        x, y, w: W, h: H,
        fill: { color: hex(icfrColors.docFill) },
        line: { color: hex(icfrColors.docBorder), width: 0.75 },
      });
      const label = (data.label || "").trim();
      if (label) {
        slide.addText(label, {
          x, y, w: W, h: H * 0.82,
          fontFace: FONT, fontSize: fpt(shapeNodeDesign.document.fontSize), color: "0F172A",
          align: "center", valign: "middle",
          margin: 0.02,
          shrinkText: true,
        });
      }
      return;
    }
    case "db": {
      slide.addShape("can", {
        x, y, w: W, h: H,
        fill: { color: hex(icfrColors.dbFill) },
        line: { color: hex(icfrColors.dbBorder), width: 1 },
      });
      const sublabel = data.sublabel ? "\n" + data.sublabel : "";
      slide.addText((data.label || "DB") + sublabel, {
        x, y, w: W, h: H,
        fontFace: FONT, fontSize: fpt(shapeNodeDesign.db.fontSize), bold: true, color: "FFFFFF",
        align: "center", valign: "middle",
        margin: 0.03,
        shrinkText: true,
      });
      return;
    }
    case "interface": {
      slide.addShape("ellipse", {
        x, y, w: W, h: H,
        fill: { color: "E0E0E0" },
        line: { color: hex(icfrColors.border), width: 0.75 },
      });
      slide.addText(data.label || "I/F", {
        x, y, w: W, h: H,
        fontFace: FONT, fontSize: fpt(shapeNodeDesign.interface.fontSize), bold: true, color: "0F172A",
        align: "center", valign: "middle",
        margin: 0.02,
        shrinkText: true,
      });
      return;
    }
    case "textBox": {
      // 테두리·배경 없는 순수 텍스트 — PPT 에서도 텍스트 상자로 출력
      if (data.label) {
        slide.addText(data.label, {
          x, y, w: W, h: H,
          fontFace: FONT, fontSize: fpt(shapeNodeDesign.textBox.fontSize), color: "0F172A",
          align: "center", valign: "middle",
          margin: 0.02,
          shrinkText: true,
        });
      }
      return;
    }
  }
}

/* ─── 엣지 ─── */

type HandleKey = "left" | "right" | "top" | "bottom";

function handlePoint(node: Node, handle?: string | null): { x: number; y: number } {
  const w = nodeWidthPx(node);
  const h = nodeHeightPx(node);
  const { x, y } = node.position;
  const key = (handle as HandleKey) ?? "right";
  switch (key) {
    case "left": return { x, y: y + h / 2 };
    case "right": return { x: x + w, y: y + h / 2 };
    case "top": return { x: x + w / 2, y };
    case "bottom": return { x: x + w / 2, y: y + h };
  }
}

/**
 * 모든 노드를 둘러싸는 bounding box (캔버스 px). 빈 입력은 작은 더미 box.
 * width/height 는 customWidth/customHeight 또는 디자인 기본값에서 가져옴.
 */
function computeBoundingBox(nodes: Node[]): {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
} {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const n of nodes) {
    const w = nodeWidthPx(n);
    const h = nodeHeightPx(n);
    if (n.position.x < minX) minX = n.position.x;
    if (n.position.y < minY) minY = n.position.y;
    if (n.position.x + w > maxX) maxX = n.position.x + w;
    if (n.position.y + h > maxY) maxY = n.position.y + h;
  }
  if (!Number.isFinite(minX)) {
    minX = 0;
    minY = 0;
    maxX = 100;
    maxY = 100;
  }
  return {
    minX,
    minY,
    maxX,
    maxY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}

function nodeWidthPx(node: Node): number {
  // 우선 순위: data.customWidth (사용자 명시 또는 buildFlowFromExcel 설정) > design.ts 기본.
  //   node.width (React Flow DOM 측정값) 는 사용하지 않는다 — 브라우저 렌더링·border 에 따라
  //   디자인 토큰과 미세하게 달라질 수 있어 PPT 좌표 계산의 불일치를 유발.
  //   사용자 리사이즈는 onResize 콜백이 customWidth 로 기록하므로 누락 없음.
  const dataCustom = (node.data as { customWidth?: number } | undefined)
    ?.customWidth;
  if (dataCustom != null) return dataCustom;
  if (node.type === "activity") return activityNodeDesign.width;
  const d = (node.data as ShapeNodeData).shapeKey;
  return shapeNodeDesign[d as NonActivityShape].width;
}
function nodeHeightPx(node: Node): number {
  const dataCustom = (node.data as { customHeight?: number } | undefined)
    ?.customHeight;
  if (dataCustom != null) return dataCustom;
  if (node.type === "activity") return 88;
  const d = (node.data as ShapeNodeData).shapeKey;
  return shapeNodeDesign[d as NonActivityShape].height;
}

function drawEdge(
  slide: PptxGenJS.Slide,
  edge: Edge,
  nodeById: Map<string, Node>,
) {
  const source = nodeById.get(edge.source);
  const target = nodeById.get(edge.target);
  if (!source || !target) {
    console.warn(
      `[PPT] 유령 엣지 스킵: ${edge.id} (source=${edge.source} ${source ? "✓" : "✗"}, target=${edge.target} ${target ? "✓" : "✗"})`,
    );
    return;
  }

  const isDashed = !!(edge.style as Record<string, unknown> | undefined)
    ?.strokeDasharray;

  const a = handlePoint(source, edge.sourceHandle ?? null);
  const b = handlePoint(target, edge.targetHandle ?? null);

  // wrap 엣지 감지: 활동→활동 실선에만 적용.
  //   점선 엣지(DB→활동, 활동→문서) 는 수직 직선이므로 wrap 4-segment 를 쓰면
  //   엉뚱한 방향으로 그려진다 → 점선은 항상 handlePoint 기반 직선으로 처리.
  const sBottom = source.position.y + nodeHeightPx(source);
  const isWrap = !isDashed && sBottom < target.position.y - 10;
  if (isWrap) {
    drawWrapEdge(slide, source, target, isDashed);
    if (typeof edge.label === "string" && edge.label) {
      drawEdgeLabel(slide, source, target, edge.label);
    }
    return;
  }

  const lineOpts: LineOpts = {
    color: hex(icfrColors.arrow),
    width: 1,
    endArrowType: "triangle",
    dashType: isDashed ? "dash" : "solid",
  };

  // 점선 엣지(활동→문서, DB→활동) 는 PowerPoint "복구(R) 대화상자" 의 직접적
  // 원인이었던 `bentConnector3 + dashType:"dash"` 조합을 피해 항상 단순 직선으로 출력.
  //   - 시각적으로도 자연스러움 (점선 엣지는 대부분 수직/수평 직선)
  //   - addLine → addSafeLine 으로 좌표 정규화 + 슬라이드 범위 클램핑
  //
  // 추가 보정: 거의 수직(Δx 매우 작음) 이면 완벽 수직으로, 거의 수평이면 완벽 수평으로 보정.
  //   캔버스에서 top↔bottom 핸들 연결은 X 가 같아야 하지만, 도형 폭 차이 때문에
  //   소수점 단위 오차가 생길 수 있음 → snap.
  if (isDashed) {
    const dx = Math.abs(a.x - b.x);
    const dy = Math.abs(a.y - b.y);
    // 수직 스냅: X 오차가 전체 거리의 10% 이하면 수직으로 간주
    if (dx < dy * 0.1 && dy > 1) {
      const midX = (a.x + b.x) / 2;
      a.x = midX;
      b.x = midX;
    }
    // 수평 스냅: Y 오차가 전체 거리의 10% 이하면 수평으로 간주
    if (dy < dx * 0.1 && dx > 1) {
      const midY = (a.y + b.y) / 2;
      a.y = midY;
      b.y = midY;
    }
    addLine(slide, a, b, lineOpts);
  } else if (edge.type === "straight") {
    addLine(slide, a, b, lineOpts);
  } else if (edge.type === "smoothstep" || edge.type === "step") {
    addBentConnector(slide, a, b, lineOpts);
  } else {
    addCurvedConnector(slide, a, b, lineOpts);
  }

  if (typeof edge.label === "string" && edge.label) {
    const cx = (a.x + b.x) / 2;
    const cy = (a.y + b.y) / 2;
    slide.addText(edge.label, {
      x: nx(cx) - 0.4, y: ny(cy) - 0.12, w: 0.8, h: 0.24,
      fontFace: FONT, fontSize: 9, color: "0F172A",
      align: "center", valign: "middle",
      fill: { color: "FFFFFF" },
    });
  }
}

/**
 * 다음 행으로 wrap 되는 엣지 — 3-segment 직각 꺾임 (기준 양식 매칭).
 *
 *   캔버스 핸들: source bottom → target top (세로 흐름)
 *
 *   source
 *     │ (1: 아래로 — source bottom center)
 *     └──────────┐ (2: 가로로 — target X 로 이동)
 *                │ (3: 아래로 → target top center, 화살촉)
 *                ▼
 *              target
 */
function drawWrapEdge(
  slide: PptxGenJS.Slide,
  source: Node,
  target: Node,
  isDashed: boolean,
) {
  const sW = nodeWidthPx(source);
  const sH = nodeHeightPx(source);
  const tW = nodeWidthPx(target);
  const sx = source.position.x;
  const sy = source.position.y;
  const tx = target.position.x;
  const ty = target.position.y;

  // source bottom center → target top center
  const startX = sx + sW / 2;
  const startY = sy + sH;
  const endX = tx + tW / 2;
  const endY = ty;

  // midY: source bottom 과 target top 사이의 40% 지점
  const midY = startY + 0.4 * (endY - startY);

  const color = hex(icfrColors.arrow);
  const width = 1;
  const dashType: "solid" | "dash" = isDashed ? "dash" : "solid";
  const stroke: LineOpts = { color, width, dashType };
  const strokeArrow: LineOpts = { color, width, dashType, endArrowType: "triangle" };

  // 3-segment 직각 꺾임: ↓ → ←/→ → ↓
  // 1: 아래로 (source bottom center → midY)
  addSafeLine(slide, nx(startX), ny(startY), nx(startX), ny(midY), stroke);
  // 2: 가로로 (source X → target X)
  addSafeLine(slide, nx(startX), ny(midY), nx(endX), ny(midY), stroke);
  // 3: 아래로 target top center (화살촉)
  addSafeLine(slide, nx(endX), ny(midY), nx(endX), ny(endY), strokeArrow);
}

function drawEdgeLabel(
  slide: PptxGenJS.Slide,
  source: Node,
  target: Node,
  label: string,
) {
  const sH = nodeHeightPx(source);
  const cx = (source.position.x + nodeWidthPx(source) + target.position.x) / 2;
  const cy = (source.position.y + sH + target.position.y) / 2;
  slide.addText(label, {
    x: nx(cx) - 0.4, y: ny(cy) - 0.12, w: 0.8, h: 0.24,
    fontFace: FONT, fontSize: 9, color: "0F172A",
    align: "center", valign: "middle",
    fill: { color: "FFFFFF" },
  });
}

interface LineOpts {
  color: string;
  width: number;
  endArrowType?: "arrow" | "triangle"; // 중간 segment 는 화살표 없음 → optional. 기준: triangle
  dashType: "solid" | "dash";
}

/* ─────────────────────────────────────────────
 * 좌표 안전 헬퍼 — PowerPoint XML 호환
 *
 *   목적: "복구(R) 대화상자" 가 뜨지 않도록 invalid XML 을 사전 차단.
 *   원인:
 *     1) addShape({ w: 음수 }) → <a:ext cx="음수"/> → invalid (unsigned int)
 *     2) addShape({ w: 0, h: 0 }) → degenerate shape
 *     3) 슬라이드 범위 밖 좌표 → 일부 PPT 버전이 거부
 *   해법:
 *     - 항상 양수 w/h + flipH/flipV 로 표현 → 화살표는 flip 변환 후에도 (x2,y2) 끝점에
 *     - 슬라이드 안쪽으로 0.02in 여유 두고 클램핑
 * ───────────────────────────────────────────── */

const CLAMP_PAD_IN = 0.02;

function clampN(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}
function clampX(x: number): number {
  return clampN(x, CLAMP_PAD_IN, SLIDE_WIDTH_IN - CLAMP_PAD_IN);
}
function clampY(y: number): number {
  return clampN(y, CLAMP_PAD_IN, SLIDE_HEIGHT_IN - CLAMP_PAD_IN);
}

/**
 * PowerPoint XML 표준에 맞는 안전한 직선.
 *   - 인치 좌표 (x1,y1) → (x2,y2) 사이의 line 도형
 *   - 양수 w/h + flipH/flipV — 음수 dimension 회피
 *   - 슬라이드 범위 클램핑
 *   - opts.endArrowType 가 있으면 (x2,y2) 에 화살촉
 */
function addSafeLine(
  slide: PptxGenJS.Slide,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  opts: LineOpts,
) {
  const a = { x: clampX(x1), y: clampY(y1) };
  const b = { x: clampX(x2), y: clampY(y2) };
  const minX = Math.min(a.x, b.x);
  const minY = Math.min(a.y, b.y);
  const w = Math.abs(b.x - a.x);
  const h = Math.abs(b.y - a.y);
  // 완전 degenerate (w=h=0) 는 점이라 PowerPoint 가 무시 — 그려도 의미 없음
  if (w < 0.001 && h < 0.001) return;
  const flipH = a.x > b.x;
  const flipV = a.y > b.y;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  slide.addShape("line", {
    x: minX, y: minY, w, h,
    flipH, flipV,
    line: opts,
  } as any);
}

function addLine(
  slide: PptxGenJS.Slide,
  a: { x: number; y: number },
  b: { x: number; y: number },
  opts: LineOpts,
) {
  addSafeLine(slide, nx(a.x), ny(a.y), nx(b.x), ny(b.y), opts);
}

function addBentConnector(
  slide: PptxGenJS.Slide,
  a: { x: number; y: number },
  b: { x: number; y: number },
  opts: LineOpts,
) {
  const x1 = clampX(nx(a.x)), y1 = clampY(ny(a.y));
  const x2 = clampX(nx(b.x)), y2 = clampY(ny(b.y));
  const minX = Math.min(x1, x2);
  const minY = Math.min(y1, y2);
  const w = Math.abs(x2 - x1);
  const h = Math.abs(y2 - y1);
  // bentConnector3 는 최소한 한쪽 방향으로 폭이 있어야 라우팅 가능 — degenerate fallback
  if (w < 0.01 && h < 0.01) return;
  if (w < 0.01 || h < 0.01) {
    // 직선과 동일 → 단순 line 으로 대체 (bentConnector 가 degenerate XML 생성하는 케이스 회피)
    addSafeLine(slide, x1, y1, x2, y2, opts);
    return;
  }
  const flipH = x1 > x2;
  const flipV = y1 > y2;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  slide.addShape("bentConnector3" as any, {
    x: minX, y: minY, w, h,
    flipH, flipV,
    line: opts,
  });
}

function addCurvedConnector(
  slide: PptxGenJS.Slide,
  a: { x: number; y: number },
  b: { x: number; y: number },
  opts: LineOpts,
) {
  const x1 = clampX(nx(a.x)), y1 = clampY(ny(a.y));
  const x2 = clampX(nx(b.x)), y2 = clampY(ny(b.y));
  const minX = Math.min(x1, x2);
  const minY = Math.min(y1, y2);
  const w = Math.abs(x2 - x1);
  const h = Math.abs(y2 - y1);
  if (w < 0.01 && h < 0.01) return;
  if (w < 0.01 || h < 0.01) {
    addSafeLine(slide, x1, y1, x2, y2, opts);
    return;
  }
  const flipH = x1 > x2;
  const flipV = y1 > y2;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  slide.addShape("curvedConnector3" as any, {
    x: minX, y: minY, w, h,
    flipH, flipV,
    line: opts,
  });
}
