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
  resolvedControl,
  subStepsFontSize,
} from "../types";
import type { ActivityNodeData } from "../components/ActivityNode";
import type { NonActivityShape, ShapeNodeData } from "../components/ShapeNode";
import type { RoutedEdgeData } from "../components/RoutedEdge";
import { headerFor } from "../state/flowState";
import {
  branchLabelAnchor,
  routePoints,
  smoothStepPoints,
  type Pt,
  type Side,
} from "../parsing/edgeRouting";

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
/**
 * 한 줄에 들어가도록 글자 크기 계산 (배지처럼 높이가 한 줄뿐인 도형용).
 *   한글 ≈ 1em, 영문·숫자 ≈ 0.58em 으로 폭을 추정해 maxPt 이하로 줄인다.
 */
function fitFontPt(text: string, wIn: number, maxPt: number, minPt = 3.5): number {
  const units = [...(text || '')].reduce((s, ch) => s + (/[ -~]/.test(ch) ? 0.58 : 1), 0);
  if (units === 0) return maxPt;
  const usable = Math.max(0.05, wIn - 0.04);
  const pt = (usable / units) * 72;
  return Math.max(minPt, Math.min(maxPt, Math.floor(pt * 10) / 10));
}

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
  /** flowchart 별 대분류·중분류 (그래프 시트) */
  header?: Partial<HeaderInfo>;
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

  // 페이지 2~ — 각 flowchart (+ 업무기술이 있으면 Narrative 표)
  for (const fc of flowcharts) {
    const localHeader = headerFor(headerInfo, fc);
    buildFlowchartSlide(pptx, localHeader, fc.nodes, fc.edges);
    buildNarrativeSlides(pptx, localHeader, fc.nodes);
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
    x: x + w * 0.1, y, w: 0, h,
    line: { color: hex(icfrColors.border), width: 0.75 },
  });
  slide.addShape("line", {
    x: x + w * 0.9, y, w: 0, h,
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
  const bbox = computeBoundingBox(nodes, edges);

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

  slide.addText(a.displayNo ?? String(a.actNo), {
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
        x: x + W * 0.1, y, w: 0, h: H,
        line: { color: hex(icfrColors.border), width: 0.75 },
      });
      slide.addShape("line", {
        x: x + W * 0.9, y, w: 0, h: H,
        line: { color: hex(icfrColors.border), width: 0.75 },
      });
      if (data.label) {
        // 글자는 양쪽 세로선 안쪽(가운데 80%)에만
        slide.addText(data.label, {
          x: x + W * 0.1, y, w: W * 0.8, h: H,
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
      // 흰 글씨는 진한 Key 배지만 (연분홍 Non-Key 는 흰 글씨가 안 보임)
      const fg = key === "keyControl" && !isNeutral ? "FFFFFF" : "0F172A";

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
        fontFace: FONT, fontSize: fitFontPt(data.label, mainW, fpt(shapeNodeDesign.risk.fontSize)), bold: true, color: fg,
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
    case "lane": {
      // 스윔레인 배경 — 연한 본문 + 왼쪽 레인명 칸
      const labelW = pxX(data.laneLabelWidth ?? 70);
      slide.addShape("rect", {
        x, y, w: W, h: H,
        fill: { color: hex(icfrColors.laneBg) },
        line: { color: hex(icfrColors.border), width: 0.75 },
      });
      slide.addShape("rect", {
        x, y, w: labelW, h: H,
        fill: { color: hex(icfrColors.headerBg) },
        line: { color: hex(icfrColors.border), width: 0.75 },
      });
      slide.addText(data.label, {
        x, y, w: labelW, h: H,
        fontFace: FONT, fontSize: fpt(shapeNodeDesign.lane.fontSize), bold: true,
        color: "FFFFFF", align: "center", valign: "middle",
        margin: 0.03,
        shrinkText: true,
      });
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
function computeBoundingBox(nodes: Node[], edges: Edge[] = []): {
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
  // 박스 바깥으로 돌아가는 화살표 통로도 슬라이드 안에 들어오게 포함 (+여유 8px)
  for (const e of edges) {
    const corridors = (e.data as RoutedEdgeData | undefined)?.route?.corridors;
    if (!corridors) continue;
    for (const c of corridors) {
      if (c.axis === "x") {
        minX = Math.min(minX, c.value - 8);
        maxX = Math.max(maxX, c.value + 8);
      } else {
        minY = Math.min(minY, c.value - 8);
        maxY = Math.max(maxY, c.value + 8);
      }
    }
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
  const sSide = ((edge.sourceHandle as Side | null) ?? "right") as Side;
  const tSide = ((edge.targetHandle as Side | null) ?? "left") as Side;
  const a = handlePoint(source, sSide);
  const b = handlePoint(target, tSide);
  const label = typeof edge.label === "string" ? edge.label : "";

  const lineOpts: LineOpts = {
    color: hex(icfrColors.arrow),
    width: 1,
    endArrowType: "triangle",
    dashType: isDashed ? "dash" : "solid",
  };

  // 점선(활동→문서·DB) 은 단순 직선. 거의 수직/수평이면 완전 수직/수평으로 보정.
  if (isDashed) {
    const dx = Math.abs(a.x - b.x);
    const dy = Math.abs(a.y - b.y);
    if (dx < dy * 0.1 && dy > 1) {
      const midX = (a.x + b.x) / 2;
      a.x = midX;
      b.x = midX;
    }
    if (dy < dx * 0.1 && dx > 1) {
      const midY = (a.y + b.y) / 2;
      a.y = midY;
      b.y = midY;
    }
    // 수직·수평이 아니면 캔버스 smoothstep 과 같은 꺾은선
    if (a.x === b.x || a.y === b.y) {
      addLine(slide, a, b, lineOpts);
    } else {
      addPolyline(slide, smoothStepPoints(a, sSide, b, tSide, 20), lineOpts);
    }
    return;
  }

  if (edge.type === "straight") {
    addLine(slide, a, b, lineOpts);
    if (label) drawEdgeLabelAt(slide, { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, label);
    return;
  }
  if (edge.type === "default" || edge.type === "simplebezier") {
    addCurvedConnector(slide, a, b, lineOpts);
    if (label) drawEdgeLabelAt(slide, { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, label);
    return;
  }

  // smoothstep / step / routed — 캔버스와 같은 계산식으로 직각 경로
  const offset =
    (edge as Edge & { pathOptions?: { offset?: number } }).pathOptions?.offset ?? 20;
  const pts =
    edge.type === "routed"
      ? routePoints(a, sSide, b, tSide, (edge.data as RoutedEdgeData | undefined)?.route)
      : smoothStepPoints(a, sSide, b, tSide, offset);
  addPolyline(slide, pts, lineOpts);

  if (label) {
    // 분기 라벨(Y/N)은 출발점 옆 — 캔버스 RoutedEdge 와 같은 위치
    const sourceIsDiamond =
      source.type === "shape" &&
      (source.data as ShapeNodeData).shapeKey === "diamond";
    const at =
      edge.type === "routed" || sourceIsDiamond
        ? branchLabelAnchor(pts, sSide)
        : polylineMidpoint(pts);
    drawEdgeLabelAt(slide, at, label);
  }
}

/** 꺾은선 길이의 절반 지점 */
function polylineMidpoint(pts: Pt[]): Pt {
  let total = 0;
  for (let i = 1; i < pts.length; i++) {
    total += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
  }
  let half = total / 2;
  for (let i = 1; i < pts.length; i++) {
    const seg = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    if (half <= seg && seg > 0) {
      const t = half / seg;
      return {
        x: pts[i - 1].x + (pts[i].x - pts[i - 1].x) * t,
        y: pts[i - 1].y + (pts[i].y - pts[i - 1].y) * t,
      };
    }
    half -= seg;
  }
  return pts[pts.length - 1];
}

/** 화살표 라벨 — 캔버스 좌표 기준 중심점에 작은 흰 배경 텍스트 */
function drawEdgeLabelAt(slide: PptxGenJS.Slide, at: Pt, label: string) {
  const fs = fpt(11);
  // 글자 수 기준 대략 폭 (한글 ≈ 1em, 영문 ≈ 0.6em)
  const em = fs / 72;
  const chars = [...label].reduce((s, ch) => s + (/[ -~]/.test(ch) ? 0.62 : 1), 0);
  const w = Math.max(0.16, chars * em + 0.06);
  const h = em * 1.5;
  slide.addText(label, {
    x: nx(at.x) - w / 2, y: ny(at.y) - h / 2, w, h,
    fontFace: FONT, fontSize: fs, bold: true, color: "334155",
    align: "center", valign: "middle",
    margin: 0,
    fill: { color: "FFFFFF" },
  });
}

/**
 * 직각 꺾은선을 도형 1개(자유형)로 출력 — 끝점에 화살촉.
 *   점 2개면 일반 직선으로 대체 (자유형의 폭/높이가 0 이 되는 경우 회피).
 */
function addPolyline(slide: PptxGenJS.Slide, ptsCanvas: Pt[], opts: LineOpts) {
  if (ptsCanvas.length < 2) return;
  if (ptsCanvas.length === 2) {
    addLine(slide, ptsCanvas[0], ptsCanvas[1], opts);
    return;
  }
  const P = ptsCanvas.map((p) => ({ x: clampX(nx(p.x)), y: clampY(ny(p.y)) }));
  const minX = Math.min(...P.map((p) => p.x));
  const minY = Math.min(...P.map((p) => p.y));
  const maxX = Math.max(...P.map((p) => p.x));
  const maxY = Math.max(...P.map((p) => p.y));
  const w = Math.max(maxX - minX, 0.002);
  const h = Math.max(maxY - minY, 0.002);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  slide.addShape("custGeom" as any, {
    x: minX, y: minY, w, h,
    points: P.map((p, i) => ({
      x: p.x - minX,
      y: p.y - minY,
      ...(i === 0 ? { moveTo: true } : {}),
    })),
    line: opts,
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

/* ─────────────────────────────────────────────
 * Narrative 표 — 그래프 시트로 만든 flowchart 의 업무기술·위험·통제를 표로.
 *   행 순서 = 엑셀 행 순서(seq). 수기로 추가한 박스·구 매핑 시트 flowchart 는 제외.
 *   표가 길면 여러 장으로 나누고 각 장에 헤더 표를 다시 그린다.
 * ───────────────────────────────────────────── */

interface NarrativeRow {
  seq: number;
  id: string;
  kind: string;
  name: string;
  narrative: string;
  dept: string;
  system: string;
  risk: string;
  control: string;
  key: string;
  type: string;
}

function collectNarrativeRows(nodes: Node[]): NarrativeRow[] {
  const rows: NarrativeRow[] = [];
  for (const n of nodes) {
    if (n.type === "activity") {
      const d = n.data as ActivityNodeData;
      if (d.seq == null) continue;
      const a = d.activity;
      const rc = resolvedControl(a);
      const riskNo = (a.riskNoRaw || a.rcm?.riskNo || "").trim();
      const riskDesc = (a.rcm?.riskDesc || "").trim();
      rows.push({
        seq: d.seq,
        id: a.displayNo ?? String(a.actNo),
        kind: "활동",
        name: a.actName,
        narrative: (a.rcm?.narrative || "").trim(),
        dept: activityTeam(a),
        system: activityLocation(a),
        risk: [riskNo, riskDesc].filter(Boolean).join("\n"),
        control: rc.controlNo
          ? [`${rc.controlNo}${rc.controlName ? " " + rc.controlName : ""}`, rc.controlDesc]
              .filter(Boolean)
              .join("\n")
          : "",
        key: rc.controlNo
          ? rc.isKeyControl === true ? "Y" : rc.isKeyControl === false ? "N" : "-"
          : "",
        type: rc.controlNo ? rc.controlType : "",
      });
    } else if (n.type === "shape") {
      const d = n.data as ShapeNodeData;
      if (d.seq == null) continue;
      if (d.shapeKey !== "diamond" && d.shapeKey !== "link") continue;
      rows.push({
        seq: d.seq,
        id: d.refId ?? "",
        kind: d.shapeKey === "diamond" ? "분기" : "Link",
        name: d.label,
        narrative: (d.narrative || "").trim(),
        dept: d.dept || "",
        system: "",
        risk: "",
        control: "",
        key: "",
        type: "",
      });
    }
  }
  return rows.sort((p, q) => p.seq - q.seq);
}

function buildNarrativeSlides(
  pptx: PptxGenJS,
  headerInfo: HeaderInfo,
  nodes: Node[],
) {
  const rows = collectNarrativeRows(nodes);
  if (rows.length === 0 || rows.every((r) => !r.narrative && !r.risk && !r.control)) {
    return;
  }

  const FS = 7; // pt
  const colW = [0.42, 1.15, 2.75, 0.8, 0.72, 1.35, 1.66, 0.35, 0.4]; // 합 9.6"
  const heads = ["ID", "활동명", "업무 내용", "담당부서", "시스템", "위험", "통제", "Key", "유형"];
  const cellText = (r: NarrativeRow): string[] => [
    r.id,
    r.kind === "활동" ? r.name : `[${r.kind}] ${r.name}`,
    r.narrative,
    r.dept,
    r.system,
    r.risk,
    r.control,
    r.key,
    r.type,
  ];

  // 행 높이 추정 (한글 글자폭 ≈ 1em, 영문 ≈ 0.6em)
  const em = FS / 72;
  const lineH = em * 1.35;
  const estLines = (text: string, w: number): number => {
    const usable = Math.max(0.2, w - 0.1);
    return text.split("\n").reduce((sum, line) => {
      const units = [...line].reduce((s, ch) => s + (/[ -~]/.test(ch) ? 0.6 : 1), 0);
      return sum + Math.max(1, Math.ceil((units * em) / usable));
    }, 0);
  };
  const rowH = (cells: string[]) =>
    Math.max(...cells.map((t, i) => estLines(t, colW[i]))) * lineH + 0.08;

  const tableTop = CONTENT_TOP + 0.32;
  const avail = SLIDE_HEIGHT_IN - tableTop - 0.25;
  const headH = lineH + 0.08;

  // 장 나누기
  const pages: NarrativeRow[][] = [];
  let cur: NarrativeRow[] = [];
  let used = headH;
  for (const r of rows) {
    const h = rowH(cellText(r));
    if (cur.length > 0 && used + h > avail) {
      pages.push(cur);
      cur = [];
      used = headH;
    }
    cur.push(r);
    used += h;
  }
  if (cur.length) pages.push(cur);

  const border = { type: "solid" as const, pt: 0.5, color: hex(icfrColors.border) };
  pages.forEach((page, pi) => {
    const slide = pptx.addSlide();
    drawHeaderRow(slide, headerInfo);
    slide.addText(
      `업무 기술 (Narrative)${pages.length > 1 ? `  ${pi + 1}/${pages.length}` : ""}`,
      {
        x: MARGIN_X, y: CONTENT_TOP, w: 6, h: 0.26,
        fontFace: FONT, fontSize: 10, bold: true, color: hex(icfrColors.headerBg),
        margin: 0,
      },
    );
    const headRow: PptxGenJS.TableRow = heads.map((t) => ({
      text: t,
      options: {
        bold: true, color: "FFFFFF", fill: { color: hex(icfrColors.headerBg) },
        align: "center", valign: "middle",
      },
    }));
    const bodyRows: PptxGenJS.TableRow[] = page.map((r) =>
      cellText(r).map((t, ci) => ({
        text: t,
        options: {
          align: ci === 0 || ci >= 7 ? "center" : "left",
          valign: "top",
          ...(r.kind !== "활동" ? { fill: { color: "F5F5F5" } } : {}),
        },
      })),
    );
    slide.addTable([headRow, ...bodyRows], {
      x: MARGIN_X, y: tableTop, w: colW.reduce((s, v) => s + v, 0), colW,
      fontFace: FONT, fontSize: FS, color: "0F172A",
      border, margin: 0.04,
    });
  });
}
