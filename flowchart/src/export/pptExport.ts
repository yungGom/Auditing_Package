import JSZip from "jszip";
import PptxGenJS from "pptxgenjs";
import type { Edge, Node } from "reactflow";

import {
  activityNodeDesign,
  CHIP_GAP,
  icfrColors,
  PX_PER_PT,
  shapeNodeDesign,
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
 *   페이지 1     : Flowchart 구성정보 (도형 범례, 정적)
 *   페이지 2~    : 각 flowchart (헤더 표 + 테두리 + 본문 도형) [+ Narrative 표]
 *
 * 모양은 회사 양식 예시 PPT 의 실제 값(XML)을 그대로 따른다:
 *   헤더 표 위치·칸 폭, 본문 테두리, 0.25pt 밝은 회색 선, 작은 화살촉,
 *   굵지 않은 7pt 글자, 활동 85.9×42pt.
 *
 * 좌표 매핑:
 *   캔버스 px → PPT inch 균일 스케일. 양식 크기(PX_PER_PT)보다 크게 키우지는 않고,
 *   본문이 테두리 안에 다 들어가지 않을 때만 줄인다.
 *
 * 한글 폰트: "맑은 고딕". 폰트 임베드는 불가 — 받는 사람 PC 폰트에 따라 다르게 표시될 수 있음.
 */

/* ─────────────────────────────────────────────
 * 상수 / 유틸
 * ───────────────────────────────────────────── */

const FONT = "맑은 고딕";
// 기준 양식: 4:3 (720×540pt = 10×7.5인치)
const SLIDE_WIDTH_IN = 10;
const SLIDE_HEIGHT_IN = 7.5;

/** pt → inch */
function pt(v: number): number {
  return v / 72;
}
function hex(c: string): string {
  return c.startsWith("#") ? c.slice(1) : c;
}

/** 회사 양식 예시에서 잰 값 (pt) */
const HEADER = {
  x: 9.27,
  y: 10.55,
  h: 33.6,
  // 회사명|값|대분류|값|중·소분류|값|Flowchart Code|값|Last Change Date|값
  cols: [42.2, 87.1, 45.3, 98.1, 54.9, 116.9, 54.6, 67.2, 63.0, 72.2],
};
const FRAME = { x: 9.35, y: 51.7, w: 701.3, h: 457.7 };
const FRAME_PAD = 16; // 테두리 안쪽 여백 (pt)
const LINE_PT = 0.25; // 도형 테두리·연결선
const GRID_PT = 0.5; // 헤더 표 칸선
const FRAME_PT = 0.75; // 본문 테두리
const TEXT = "000000";
const BORDER = hex(icfrColors.border);
const CONTENT_TOP = pt(HEADER.y + HEADER.h) + 0.12; // Narrative 표 등 헤더 아래 시작점

/** 양식 크기 — 캔버스 1px 이 PPT 에서 차지하는 인치 */
const NATIVE_SCALE = 1 / (PX_PER_PT * 72);

/**
 * WYSIWYG 좌표계 — buildFlowchartSlide 가 슬라이드마다 갱신한다.
 *   캔버스 전체 bounding box 를 테두리 안에 비율 유지로 넣되 양식 크기 이상으로 키우지 않음.
 */
let activeScaleInPerPx = NATIVE_SCALE;
let activeOffsetX = pt(FRAME.x + FRAME_PAD);
let activeOffsetY = pt(FRAME.y + FRAME_PAD);

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

/** 문자 폭 단위 (한글 ≈ 1em, 영문·숫자 ≈ 0.58em) */
function textUnits(text: string): number {
  return [...(text || "")].reduce((s, ch) => s + (/[ -~]/.test(ch) ? 0.58 : 1), 0);
}

/**
 * 한 줄에 들어가도록 글자 크기 계산 (배지·칸처럼 높이가 한 줄뿐인 곳).
 *   marginPt: 좌우 안쪽 여백 합.
 */
function fitFontPt(text: string, wIn: number, maxPt: number, minPt = 3.5, marginPt = 2): number {
  const units = textUnits(text);
  if (units === 0) return maxPt;
  const usablePt = Math.max(4, wIn * 72 - marginPt);
  const size = usablePt / units;
  return Math.max(minPt, Math.min(maxPt, Math.floor(size * 10) / 10));
}

/** 여러 줄로 줄바꿈해서 상자에 들어가는 가장 큰 글자 크기 */
function fitBoxFontPt(text: string, wIn: number, hIn: number, maxPt: number, minPt = 4): number {
  const paras = (text || "").split("\n");
  const usableW = Math.max(4, wIn * 72 - 3);
  const usableH = Math.max(4, hIn * 72 - 2);
  for (let size = maxPt; size > minPt; size -= 0.25) {
    const lines = paras.reduce(
      (n, p) => n + Math.max(1, Math.ceil((textUnits(p) * size) / usableW)),
      0,
    );
    if (lines * size * 1.2 <= usableH) return Math.round(size * 10) / 10;
  }
  return minPt;
}

/** 캔버스 px 폰트 → PPT pt (도형과 같은 비율로 줄어듦). 양식 크기에서 px/2.1 = pt */
function fpt(canvasPx: number): number {
  const v = canvasPx * activeScaleInPerPx * 72;
  return Math.max(3.5, Math.round(v * 10) / 10);
}

/** 얇은 회색 선 (도형 테두리) */
function thin(color = BORDER, width = LINE_PT) {
  return { color, width };
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

const PPTX_MIME =
  "application/vnd.openxmlformats-officedocument.presentationml.presentation";

/** 파일 저장 방식 — 기본은 브라우저 다운로드 (검증 스크립트는 파일로 직접 저장) */
export type PptSaver = (data: ArrayBuffer, fileName: string) => void | Promise<void>;

export async function exportToPpt(
  headerInfo: HeaderInfo,
  flowcharts: PptFlowchart[],
  filename?: string,
  save: PptSaver = downloadInBrowser,
): Promise<void> {
  const pptx = new PptxGenJS();
  // 기준 표준 4:3 — 720×540pt = 10×7.5인치
  pptx.defineLayout({ name: "CT_4x3", width: SLIDE_WIDTH_IN, height: SLIDE_HEIGHT_IN });
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
  const raw = (await pptx.write({ outputType: "arraybuffer" })) as ArrayBuffer;
  await save(await refineXml(raw), fname);
}

/**
 * pptxgenjs 가 지원하지 않는 세부 값을 XML 에 직접 반영.
 *   - 화살촉 크기: 양식처럼 작게 (w/len = sm). pptxgenjs 는 크기 옵션이 없다.
 *   - 글꼴: 양식처럼 영문·숫자는 Arial, 한글은 맑은 고딕.
 *     (pptxgenjs 는 영문·한글 글꼴을 하나로만 지정할 수 있다)
 */
async function refineXml(raw: ArrayBuffer): Promise<ArrayBuffer> {
  const zip = await JSZip.loadAsync(raw);
  const slideNames = Object.keys(zip.files).filter((n) =>
    /^ppt\/slides\/slide\d+\.xml$/.test(n),
  );
  for (const name of slideNames) {
    const xml = await zip.file(name)!.async("string");
    zip.file(
      name,
      xml
        .replace(
          /<a:(tailEnd|headEnd) type="(triangle|arrow)"\/>/g,
          '<a:$1 type="$2" w="sm" len="sm"/>',
        )
        .replace(/<a:latin typeface="맑은 고딕"/g, '<a:latin typeface="Arial"'),
    );
  }
  return zip.generateAsync({ type: "arraybuffer", compression: "DEFLATE", mimeType: PPTX_MIME });
}

function downloadInBrowser(data: ArrayBuffer, fileName: string) {
  const blob = new Blob([data], { type: PPTX_MIME });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
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
 * 공통 틀 — 본문 테두리
 * ───────────────────────────────────────────── */

function drawFrame(slide: PptxGenJS.Slide) {
  slide.addShape("rect", {
    x: pt(FRAME.x), y: pt(FRAME.y), w: pt(FRAME.w), h: pt(FRAME.h),
    line: thin(BORDER, FRAME_PT),
  });
}

/* ─────────────────────────────────────────────
 * 슬라이드 1 — Flowchart 구성정보 가이드 (양식 예시와 같은 위치)
 * ───────────────────────────────────────────── */

function buildGuideSlide(pptx: PptxGenJS) {
  const slide = pptx.addSlide();
  drawFrame(slide);

  // 제목 띠 — 오른쪽 위 모서리가 잘린 사각형 + 그림자
  slide.addShape("snip1Rect" as PptxGenJS.ShapeType, {
    x: pt(13.9), y: pt(62.0), w: pt(683.5), h: pt(38.4),
    fill: { color: hex(icfrColors.headerBg) },
    line: { color: hex(icfrColors.headerBg), width: 0.25 },
    shadow: { type: "outer", blur: 3, offset: 2, angle: 45, color: "000000", opacity: 0.35 },
  });
  slide.addText("Flowchart 구성정보", {
    x: pt(18.3), y: pt(66.0), w: pt(447.4), h: pt(32.2),
    fontFace: FONT, fontSize: 22, bold: true, color: "FFFFFF",
    valign: "middle", margin: 7,
  });

  const desc = (text: string, x: number, y: number, h = 17, w = 193.7) =>
    slide.addText(text, {
      x: pt(x), y: pt(y), w: pt(w), h: pt(h),
      fontFace: FONT, fontSize: 8, color: TEXT, valign: "middle", margin: 3,
    });
  const iconLine = thin(BORDER, 0.5);

  // ── 왼쪽 열: 아이콘 x=89.7pt (85.9×42), 설명 x=183.9pt ──
  const L = 89.7;
  const IW = 85.9;
  const IH = 42;

  // Link
  slide.addShape("rect", { x: pt(L), y: pt(119.5), w: pt(IW), h: pt(IH), fill: { color: "FFFFFF" }, line: iconLine });
  for (const f of [0.12, 0.88]) {
    slide.addShape("line", { x: pt(L + IW * f), y: pt(119.5), w: 0, h: pt(IH), line: iconLine });
  }
  desc("Link : 소분류 이상의 타 프로세스를 연결", 183.9, 132.3);

  // Start / End
  slide.addShape("rect", { x: pt(L), y: pt(182.8), w: pt(IW), h: pt(IH), fill: { color: "FFFFFF" }, line: iconLine });
  desc("Start/End : 프로세스의 시작과 끝", 183.9, 190.8);

  // Activity (A|B / C / D)
  const ay = 246.2;
  const rowH = 8.9;
  const aW = 26;
  slide.addShape("rect", { x: pt(L), y: pt(ay), w: pt(IW), h: pt(IH), fill: { color: "FFFFFF" }, line: iconLine });
  slide.addShape("line", { x: pt(L), y: pt(ay + rowH), w: pt(IW), h: 0, line: iconLine });
  slide.addShape("line", { x: pt(L), y: pt(ay + IH - rowH), w: pt(IW), h: 0, line: iconLine });
  slide.addShape("line", { x: pt(L + aW), y: pt(ay), w: 0, h: pt(rowH), line: iconLine });
  const cell = (t: string, x: number, y: number, w: number, h: number) =>
    slide.addText(t, {
      x: pt(x), y: pt(y), w: pt(w), h: pt(h),
      fontFace: FONT, fontSize: 7, color: TEXT, align: "center", valign: "middle", margin: 0,
    });
  cell("A", L, ay, aW, rowH);
  cell("B", L + aW, ay, IW - aW, rowH);
  cell("C", L, ay + rowH, IW, IH - 2 * rowH);
  cell("D", L, ay + IH - rowH, IW, rowH);
  desc(
    "소분류 이하의 Activity\n*A-Activity No\n*B-Activity 수행 팀\n*C-Activity Name\n*D-Activity 발생 위치(시스템/Manual)",
    183.9, 239.7, 55.7,
  );

  // DB
  slide.addShape("can", {
    x: pt(L), y: pt(313.6), w: pt(86), h: pt(IH),
    fill: { color: hex(icfrColors.dbFill) }, line: iconLine,
  });
  slide.addText("SAP\nFI 전표", {
    x: pt(L), y: pt(313.6 + 6), w: pt(86), h: pt(IH - 6),
    fontFace: FONT, fontSize: 7, color: "FFFFFF", align: "center", valign: "middle", margin: 0,
  });
  desc("DB : 시스템 Data Base 에 저장된 데이터/정보/회계전표 등", 183.9, 321.0, 36.4);

  // 분기점
  slide.addShape("diamond", {
    x: pt(89.2), y: pt(377.1), w: pt(85.5), h: pt(IH),
    fill: { color: "FFFFFF" }, line: iconLine,
  });
  desc("분기점 : 의사결정/유형구분 등", 183.9, 389.6, 17, 148.7);

  // ── 오른쪽 열: 아이콘 x≈392~418pt, 설명 x=484.7pt ──
  const R = 484.7;

  // I/F
  slide.addShape("ellipse", {
    x: pt(423.7), y: pt(129.7), w: pt(23.1), h: pt(22.1),
    fill: { color: "D9D9D9" }, line: iconLine,
  });
  slide.addText("I/F", {
    x: pt(423.7), y: pt(129.7), w: pt(23.1), h: pt(22.1),
    fontFace: FONT, fontSize: 7, color: TEXT, align: "center", valign: "middle", margin: 0,
  });
  desc("시스템 간 Data 인터페이스", R, 135.3);

  // 프로세스 흐름 (실선) / 데이터·정보 흐름 (점선)
  slide.addShape("line", {
    x: pt(392.3), y: pt(203.5), w: pt(85.7), h: 0,
    line: { color: BORDER, width: 0.5, endArrowType: "triangle" },
  });
  desc("프로세스 흐름 표시", R, 198.0);
  slide.addShape("line", {
    x: pt(392.3), y: pt(266.7), w: pt(85.7), h: 0,
    line: { color: BORDER, width: 0.5, dashType: "dash", endArrowType: "triangle" },
  });
  desc("데이터/정보의 흐름 표시", R, 261.8);

  // Document
  slide.addShape("flowChartDocument", {
    x: pt(393.1), y: pt(309.2), w: pt(85), h: pt(42.5),
    fill: { color: BORDER }, line: iconLine,
  });
  desc("Document : 생성되는 문서정보 등", R, 322.2);

  // Risk / Key / Non-Key 색 견본
  const swatches: Array<{ y: number; color: string; label: string }> = [
    { y: 380.5, color: icfrColors.risk, label: "Risk Number" },
    { y: 398.9, color: icfrColors.keyCtrl, label: "Key Control Number" },
    { y: 417.3, color: icfrColors.nonkeyCtrl, label: "Non-Key Control Number" },
  ];
  for (const s of swatches) {
    slide.addShape("roundRect" as PptxGenJS.ShapeType, {
      x: pt(418.0), y: pt(s.y), w: pt(34.3), h: pt(10.6),
      fill: { color: hex(s.color) }, line: iconLine, rectRadius: pt(1.8),
    });
    desc(s.label, R, s.y + 5.3 - 8.5);
  }

  // 통제구분 A/M/I
  ["A", "M", "I"].forEach((k, i) => {
    const x = 418.7 + i * 12;
    slide.addShape("roundRect" as PptxGenJS.ShapeType, {
      x: pt(x), y: pt(439.8), w: pt(8.5), h: pt(10.5),
      fill: { color: hex(icfrColors.ctrlM) }, line: thin(hex(icfrColors.ctrlM)), rectRadius: pt(1.5),
    });
    slide.addText(k, {
      x: pt(x), y: pt(439.8), w: pt(8.5), h: pt(10.5),
      fontFace: FONT, fontSize: 7, color: TEXT, align: "center", valign: "middle", margin: 0,
    });
  });
  slide.addText("통제구분 :", {
    x: pt(R), y: pt(436.5), w: pt(50), h: pt(36.4),
    fontFace: FONT, fontSize: 8, color: TEXT, valign: "top", margin: 3,
  });
  slide.addText("A(Auto)\nM(Manual)\nI(ITDM)", {
    x: pt(R + 42), y: pt(436.5), w: pt(120), h: pt(36.4),
    fontFace: FONT, fontSize: 8, color: TEXT, valign: "top", margin: 3,
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

  drawHeaderRow(slide, headerInfo);
  drawFrame(slide);

  // 캔버스 bounding box 를 테두리 안쪽에 비율 유지로 배치.
  //   양식 크기(NATIVE_SCALE)보다 크게 키우지 않는다 — 활동이 몇 개든 글자 크기가 일정.
  //   넘칠 때만 줄이고, 가로는 가운데·세로는 가운데보다 약간 위.
  const bbox = computeBoundingBox(nodes, edges);

  const areaX = pt(FRAME.x + FRAME_PAD);
  const areaY = pt(FRAME.y + FRAME_PAD);
  const areaW = pt(FRAME.w - 2 * FRAME_PAD);
  const areaH = pt(FRAME.h - 2 * FRAME_PAD);

  const scale = Math.max(
    0.0005,
    Math.min(NATIVE_SCALE, areaW / bbox.width, areaH / bbox.height),
  );
  const contentW = bbox.width * scale;
  const contentH = bbox.height * scale;
  const contentLeft = areaX + (areaW - contentW) / 2;
  const contentTop = areaY + (areaH - contentH) * 0.4;

  activeScaleInPerPx = scale;
  activeOffsetX = contentLeft - bbox.minX * scale;
  activeOffsetY = contentTop - bbox.minY * scale;

  // 노드 인덱스
  const nodeById = new Map<string, Node>();
  for (const n of nodes) nodeById.set(n.id, n);

  // 레인 → 엣지 → 나머지 도형 순서로 그려, 화살표가 박스 위를 덮지 않게 한다
  const lanes = nodes.filter(
    (n) => n.type === "shape" && (n.data as ShapeNodeData).shapeKey === "lane",
  );
  for (const n of lanes) drawShapeNode(slide, n);

  for (const e of edges) {
    drawEdge(slide, e, nodeById);
  }

  for (const n of nodes) {
    if (n.type === "activity") {
      drawActivity(slide, n);
    } else if (n.type === "shape" && !lanes.includes(n)) {
      drawShapeNode(slide, n);
    }
  }
}

/* ─── 헤더 표 (양식 예시와 같은 위치·칸 폭) ─── */

function drawHeaderRow(slide: PptxGenJS.Slide, h: HeaderInfo) {
  const y = HEADER.y;
  const H = HEADER.h;
  const half = H / 2;
  const xs: number[] = [];
  let acc = HEADER.x;
  for (const w of HEADER.cols) {
    xs.push(acc);
    acc += w;
  }
  const W = HEADER.cols;

  const label = (text: string, i: number, top: number, hh: number) => {
    slide.addShape("rect", {
      x: pt(xs[i]), y: pt(top), w: pt(W[i]), h: pt(hh),
      fill: { color: hex(icfrColors.headerBg) }, line: thin(BORDER, GRID_PT),
    });
    slide.addText(text, {
      x: pt(xs[i]), y: pt(top), w: pt(W[i]), h: pt(hh),
      fontFace: FONT, fontSize: 8, bold: true, color: "FFFFFF",
      align: "center", valign: "middle", margin: 1,
    });
  };
  const value = (text: string, i: number, top: number, hh: number) => {
    slide.addShape("rect", {
      x: pt(xs[i]), y: pt(top), w: pt(W[i]), h: pt(hh),
      fill: { color: "FFFFFF" }, line: thin(BORDER, GRID_PT),
    });
    const t = text || "";
    slide.addText(t || " ", {
      x: pt(xs[i]), y: pt(top), w: pt(W[i]), h: pt(hh),
      fontFace: FONT, fontSize: fitFontPt(t, pt(W[i]), 9, 5, 6), color: TEXT,
      align: "center", valign: "middle", margin: 2,
    });
  };

  label("회사명", 0, y, H);
  value(h.company, 1, y, H);
  label("대분류", 2, y, H);
  value(h.processName, 3, y, H);
  label("중분류", 4, y, half);
  label("소분류", 4, y + half, half);
  value(h.middleCategory, 5, y, half);
  value(h.subProcessName, 5, y + half, half);
  label("Flowchart\nCode", 6, y, H);
  value(h.flowchartCode, 7, y, H);
  label("Last Change\nDate", 8, y, H);
  value(h.lastChangeDate, 9, y, H);
}

/* ─── 활동 박스 4분할 ─── */

function drawActivity(slide: PptxGenJS.Slide, node: Node) {
  const data = node.data as ActivityNodeData;
  const a = data.activity;
  const W = pxX(nodeWidthPx(node));
  const H = pxY(nodeHeightPx(node));
  const N = activityNodeDesign;
  // 활동번호 칸 — 좁은 활동에서도 비례 유지
  const aCellW = Math.min(pxX(N.actNoColWidth), W * 0.3);
  // 위·아래 칸은 고정 픽셀 — 활동이 길어져도 일정, 본문만 늘어남
  const hdrH = pxY(N.headerHeight);
  const footH = pxY(N.footerHeight);
  const x = nx(node.position.x);
  const y = ny(node.position.y);

  // v5: SUB_STEPS 한 셀에 줄바꿈으로 여러 단계 입력 → ①②③ 자동 번호 + 동적 폰트
  const steps = parseSubSteps(a.subSteps);
  const stepCount = steps.length;
  const stepFontSize = subStepsFontSize(stepCount);

  const line = thin();
  slide.addShape("rect", { x, y, w: W, h: H, fill: { color: "FFFFFF" }, line });
  slide.addShape("line", { x, y: y + hdrH, w: W, h: 0, line });
  slide.addShape("line", { x: x + aCellW, y, w: 0, h: hdrH, line });
  slide.addShape("line", { x, y: y + H - footH, w: W, h: 0, line });

  slide.addText(a.displayNo ?? String(a.actNo), {
    x, y, w: aCellW, h: hdrH,
    fontFace: FONT, fontSize: fpt(N.actNoFontSize), color: TEXT,
    align: "center", valign: "middle", margin: 0,
  });
  const team = activityTeam(a);
  slide.addText(team || " ", {
    x: x + aCellW, y, w: W - aCellW, h: hdrH,
    fontFace: FONT,
    fontSize: fitFontPt(team, W - aCellW, fpt(N.teamFontSize), 3.5, 2),
    color: TEXT, align: "center", valign: "middle", margin: 0,
  });

  // 본문 — 활동명 + (있다면) 번호 매긴 단계 리스트
  const bodyY = y + hdrH;
  const bodyH = H - hdrH - footH;
  if (stepCount === 0) {
    slide.addText(a.actName, {
      x, y: bodyY, w: W, h: bodyH,
      fontFace: FONT,
      fontSize: fitBoxFontPt(a.actName, W, bodyH, fpt(N.bodyTitleFontSize)),
      color: TEXT, align: "center", valign: "middle", margin: 2,
    });
  } else {
    const runs: Array<{
      text: string;
      options: {
        fontSize?: number;
        align?: "left" | "center" | "right";
        breakLine?: boolean;
      };
    }> = [
      {
        text: a.actName,
        options: {
          fontSize: fpt(N.bodyTitleFontSize),
          align: "center",
          breakLine: true,
        },
      },
    ];
    steps.forEach((s, i) => {
      runs.push({
        text: numberedStep(i, s),
        options: {
          fontSize: fpt(stepFontSize),
          align: "left",
          breakLine: i < steps.length - 1,
        },
      });
    });
    slide.addText(runs, {
      x, y: bodyY, w: W, h: bodyH,
      fontFace: FONT, color: TEXT,
      valign: "top",
      margin: 3,
      wrap: true,
      shrinkText: true,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);
  }

  const loc = activityLocation(a);
  slide.addText(loc, {
    x, y: y + H - footH, w: W, h: footH,
    fontFace: FONT, fontSize: fitFontPt(loc, W, fpt(N.locationFontSize)), color: TEXT,
    align: "center", valign: "middle", margin: 0,
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
  const S = shapeNodeDesign;

  const centerText = (text: string, opts: {
    x?: number; y?: number; w?: number; h?: number;
    maxPt: number; color?: string; bold?: boolean; margin?: number;
  }) => {
    const bw = opts.w ?? W;
    const bh = opts.h ?? H;
    slide.addText(text, {
      x: opts.x ?? x, y: opts.y ?? y, w: bw, h: bh,
      fontFace: FONT,
      fontSize: fitBoxFontPt(text, bw, bh, opts.maxPt),
      bold: !!opts.bold,
      color: opts.color ?? TEXT,
      align: "center", valign: "middle", margin: opts.margin ?? 1,
    });
  };

  switch (key) {
    case "startEnd": {
      slide.addShape("rect", { x, y, w: W, h: H, fill: { color: "FFFFFF" }, line: thin() });
      if (data.label) centerText(data.label, { maxPt: fpt(S.startEnd.fontSize) });
      return;
    }
    case "link": {
      slide.addShape("rect", { x, y, w: W, h: H, fill: { color: "FFFFFF" }, line: thin() });
      for (const f of [0.1, 0.9]) {
        slide.addShape("line", { x: x + W * f, y, w: 0, h: H, line: thin() });
      }
      // 글자는 양쪽 세로선 안쪽(가운데 80%)에만
      if (data.label) {
        centerText(data.label, { x: x + W * 0.1, w: W * 0.8, maxPt: fpt(S.link.fontSize) });
      }
      return;
    }
    case "diamond": {
      slide.addShape("diamond", { x, y, w: W, h: H, fill: { color: "FFFFFF" }, line: thin() });
      // 마름모 안쪽 사각형(가로·세로 절반)에 글자
      if (data.label) {
        centerText(data.label, {
          x: x + W * 0.2, y: y + H * 0.2, w: W * 0.6, h: H * 0.6,
          maxPt: fpt(S.diamond.fontSize), margin: 0,
        });
      }
      return;
    }
    case "risk":
    case "keyControl":
    case "nonkeyControl": {
      const isNeutral = key === "nonkeyControl" && !!data.neutralControl;
      const fill =
        key === "risk"
          ? icfrColors.risk
          : key === "keyControl"
            ? icfrColors.keyCtrl
            : isNeutral
              ? icfrColors.neutralCtrl
              : icfrColors.nonkeyCtrl;
      // 흰 글씨는 진한 Key 배지만
      const fg = key === "keyControl" ? "FFFFFF" : TEXT;

      const showChip =
        (key === "keyControl" || key === "nonkeyControl") && !!data.controlType;
      const chipW = showChip ? pxX(S.controlType.width) : 0;
      const chipGap = showChip ? pxX(CHIP_GAP) : 0;
      const mainW = W - chipW - chipGap;
      const radius = Math.min(H, mainW) * 0.17;

      slide.addShape("roundRect" as PptxGenJS.ShapeType, {
        x, y, w: mainW, h: H,
        fill: { color: hex(fill) }, line: thin(hex(fill)), rectRadius: radius,
      });
      slide.addText(data.label, {
        x, y, w: mainW, h: H,
        fontFace: FONT, fontSize: fitFontPt(data.label, mainW, fpt(S.risk.fontSize), 3.5, 2),
        color: fg, align: "center", valign: "middle", margin: 0,
      });

      if (showChip && data.controlType) {
        const letter = ["A", "M", "I"].includes(data.controlType) ? data.controlType : "M";
        const cx = x + mainW + chipGap;
        slide.addShape("roundRect" as PptxGenJS.ShapeType, {
          x: cx, y, w: chipW, h: H,
          fill: { color: hex(icfrColors.ctrlM) }, line: thin(hex(icfrColors.ctrlM)),
          rectRadius: Math.min(H, chipW) * 0.17,
        });
        slide.addText(letter, {
          x: cx, y, w: chipW, h: H,
          fontFace: FONT, fontSize: fpt(S.controlType.fontSize), color: TEXT,
          align: "center", valign: "middle", margin: 0,
        });
      }
      return;
    }
    case "controlType": {
      const letter = (data.label || "M").toUpperCase().charAt(0);
      const safe = letter === "A" || letter === "M" || letter === "I" ? letter : "M";
      slide.addShape("roundRect" as PptxGenJS.ShapeType, {
        x, y, w: W, h: H,
        fill: { color: hex(icfrColors.ctrlM) }, line: thin(hex(icfrColors.ctrlM)),
        rectRadius: Math.min(W, H) * 0.17,
      });
      slide.addText(safe, {
        x, y, w: W, h: H,
        fontFace: FONT, fontSize: fpt(S.controlType.fontSize), color: TEXT,
        align: "center", valign: "middle", margin: 0,
      });
      return;
    }
    case "document": {
      slide.addShape("flowChartDocument", {
        x, y, w: W, h: H,
        fill: { color: hex(icfrColors.docFill) }, line: thin(hex(icfrColors.docBorder)),
      });
      const label = (data.label || "").trim();
      // 아래 물결 부분을 빼고 글자
      if (label) centerText(label, { h: H * 0.8, maxPt: fpt(S.document.fontSize) });
      return;
    }
    case "db": {
      slide.addShape("can", {
        x, y, w: W, h: H,
        fill: { color: hex(icfrColors.dbFill) }, line: thin(hex(icfrColors.dbBorder)),
      });
      const text = (data.label || "DB") + (data.sublabel ? "\n" + data.sublabel : "");
      // 위 타원(뚜껑) 아래 몸통에 글자
      centerText(text, {
        y: y + H * 0.18, h: H * 0.78, maxPt: fpt(S.db.fontSize), color: "FFFFFF",
      });
      return;
    }
    case "interface": {
      slide.addShape("ellipse", {
        x, y, w: W, h: H,
        fill: { color: "D9D9D9" }, line: thin(),
      });
      centerText(data.label || "I/F", { maxPt: fpt(S.interface.fontSize), margin: 0 });
      return;
    }
    case "textBox": {
      // 테두리·배경 없는 순수 텍스트 — PPT 에서도 텍스트 상자로 출력
      if (data.label) centerText(data.label, { maxPt: fpt(S.textBox.fontSize) });
      return;
    }
    case "phase": {
      // 단계(구분) 라벨 — 흰 상자 + 얇은 회색 테두리, 한 줄 글자 (양식 9pt)
      slide.addShape("rect", { x, y, w: W, h: H, fill: { color: "FFFFFF" }, line: thin() });
      if (data.label) {
        slide.addText(data.label, {
          x, y, w: W, h: H,
          fontFace: FONT, fontSize: fitFontPt(data.label, W, fpt(S.phase.fontSize), 3.5, 6),
          color: TEXT, align: "center", valign: "middle", margin: 2,
        });
      }
      return;
    }
    case "lane": {
      // 스윔레인 배경 — 연한 본문 + 왼쪽 레인명 칸
      const labelW = pxX(data.laneLabelWidth ?? 70);
      slide.addShape("rect", {
        x, y, w: W, h: H,
        fill: { color: hex(icfrColors.laneBg) }, line: thin(BORDER, GRID_PT),
      });
      slide.addShape("rect", {
        x, y, w: labelW, h: H,
        fill: { color: hex(icfrColors.headerBg) }, line: thin(BORDER, GRID_PT),
      });
      // 부서명은 한 줄로 (짧은 이름이 중간에서 줄바꿈되지 않게)
      slide.addText(data.label, {
        x, y, w: labelW, h: H,
        fontFace: FONT, fontSize: fitFontPt(data.label, labelW, fpt(S.lane.fontSize), 3.5, 4),
        bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 1,
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
    width: LINE_PT,
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

/** 화살표 라벨(Y/N 등) — 캔버스 좌표 기준 중심점에 작은 흰 배경 텍스트 */
function drawEdgeLabelAt(slide: PptxGenJS.Slide, at: Pt, label: string) {
  const fs = fpt(12);
  const em = fs / 72;
  const w = Math.max(em * 1.2, textUnits(label) * em + pt(2));
  const h = em * 1.4;
  slide.addText(label, {
    x: nx(at.x) - w / 2, y: ny(at.y) - h / 2, w, h,
    fontFace: FONT, fontSize: fs, color: TEXT,
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
  const colW = [0.42, 1.15, 2.85, 0.8, 0.72, 1.38, 1.7, 0.35, 0.37]; // 합 9.74" (헤더 표 폭)
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

  const border = { type: "solid" as const, pt: GRID_PT, color: BORDER };
  pages.forEach((page, pi) => {
    const slide = pptx.addSlide();
    drawHeaderRow(slide, headerInfo);
    slide.addText(
      `업무 기술 (Narrative)${pages.length > 1 ? `  ${pi + 1}/${pages.length}` : ""}`,
      {
        x: pt(HEADER.x), y: CONTENT_TOP, w: 6, h: 0.26,
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
      x: pt(HEADER.x), y: tableTop, w: colW.reduce((s, v) => s + v, 0), colW,
      fontFace: FONT, fontSize: FS, color: TEXT,
      border, margin: 3,
    });
  });
}
