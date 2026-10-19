/**
 * 디자인 토큰 — 색상·치수·폰트·엣지 스타일의 단일 소스.
 *
 * 여기서 값 하나를 바꾸면:
 *   - 캔버스(FlowCanvas) 에 그려진 노드/엣지
 *   - 디자인 프리뷰 페이지에 깔린 변종들
 *   - Tailwind 가 생성하는 `bg-icfr-*` 류 색상 유틸리티
 * 가 모두 동시에 갱신된다 (Vite HMR + Tailwind JIT).
 *
 * 색상의 출처는 references/flowchart_generator.py 의 RGB 상수.
 */

/* ─────────────────────────────────────────────
 * 색상
 * ───────────────────────────────────────────── */
/*
 * 색상 출처 — 회사 표준 Flowchart 양식 (예시 PPT 의 실제 XML 값).
 *   헤더 라벨 #AA0041, 박스 테두리/연결선 #BFBFBF (밝은 회색),
 *   DB(can) #D20050, Document #E2E2E2,
 *   Risk #FFC000, Key Control #D20050, Non-Key Control #FF69A2,
 *   통제구분 칩(A/M/I) #FFC0CB.
 */
export const icfrColors = {
  headerBg: "#AA0041", // 상단 헤더 표 라벨 (진한 크림슨)
  headerCellBg: "#FCE3EE", // (UI 액센트) 사이드바 활성 하이라이트 연핑크 — 실제 헤더 값 칸은 흰색
  titleBg: "#1F3A5F", // (legacy) START/END 은 이제 흰 박스 + 회색 테두리
  border: "#BFBFBF", // 도형/박스 테두리 (밝은 회색)

  actHdr: "#FFFFFF", // 활동 박스 헤더/푸터 — 기준은 전부 흰색, 회색 칸선으로만 구분
  actBody: "#FFFFFF", // 활동 박스 본문 흰색

  risk: "#FFC000", // Risk 뱃지 골드 (검정 글씨)
  keyCtrl: "#D20050", // Key Control 뱃지 크림슨 (흰 글씨)
  nonkeyCtrl: "#FF69A2", // Non-Key Control 뱃지 핑크 (검정 글씨)
  neutralCtrl: "#D9D9D9", // Key/Non-Key 미지정 (KEY_CA 공란) — 연회색

  // 통제구분(A/M/I) 작은 칩 — 양식은 세 가지 모두 연핑크 + 검정 글씨
  ctrlA: "#FFC0CB",
  ctrlM: "#FFC0CB",
  ctrlI: "#FFC0CB",

  docFill: "#E2E2E2", // Document 도형 연회색
  docBorder: "#E2E2E2", // Document 테두리 (동일 연회색)
  dbFill: "#D20050", // DB(can) 진한 로즈/마젠타
  dbBorder: "#E2E2E2", // DB 테두리 연회색
  arrow: "#BFBFBF", // 연결선 밝은 회색
  laneBg: "#FAFAFA", // 스윔레인 본문 배경
} as const;

/* ─────────────────────────────────────────────
 * 활동 노드 (4분할 박스) 치수·폰트
 *   - px 단위. inline style 로 적용되어 HMR 즉시 반영.
 * ───────────────────────────────────────────── */
export const activityNodeDesign = {
  // 회사 양식 예시의 활동 박스 85.9×42pt 를 캔버스 180×88px 로 (PX_PER_PT 배).
  //   위 칸(번호|수행팀)·아래 칸(시스템) 은 각 8.8pt, 글자는 굵지 않은 7pt.
  width: 180,
  borderWidth: 1,

  // 위·아래 칸 높이 (px) — 활동이 길어져도 일정
  headerHeight: 19,
  footerHeight: 19,

  // 좌상단 활동번호 칸
  actNoColWidth: 50,
  actNoFontSize: 14.7, // 7pt
  actNoFontWeight: 400,

  // 상단 우측 수행팀 칸 (양식은 5~7pt — 길면 줄여서 한 줄)
  teamFontSize: 14.7, // 최대 7pt — 길면 줄임

  // 중앙 본문
  bodyPaddingX: 8,
  bodyPaddingY: 7,
  bodyTitleFontSize: 14.7, // 7pt
  bodyTitleFontWeight: 400,
  bodySubFontSize: 10,
  bodySubColor: "#475569", // slate-600 톤
  bodyLineHeight: 1.3,

  // 헤더/푸터 공통
  headerPaddingY: 3,
  footerPaddingY: 3,
  locationFontSize: 14.7, // 7pt
} as const;

/** 캔버스 px ↔ PPT pt 기준 비율. 활동 180px = 양식 85.9pt → 약 2.1 */
export const PX_PER_PT = 2.1;

/* ─────────────────────────────────────────────
 * 통제유형 원형 배지 (활동 노드 우상단)
 * ───────────────────────────────────────────── */
export const controlBadgeDesign = {
  size: 28, // 지름 px
  offsetTop: -12, // 노드 우상단에서 얼마나 튀어나오는지
  offsetRight: -12,
  fontSize: 12,
  fontWeight: 700,
  keyRingWidth: 2, // Key Control 일 때만 흰 링
  keyRingColor: "#FFFFFF",
  shadow: "0 1px 2px rgba(0,0,0,0.15)",
} as const;

/* ─────────────────────────────────────────────
 * 캔버스 (React Flow) 전역
 * ───────────────────────────────────────────── */
export const canvasDesign = {
  bgDotGap: 20,
  bgDotSize: 1,

  // 화살표 — 기본 모양·색. 사용자가 캔버스 좌상단 셀렉터로 직선/꺾은선/곡선 변경.
  edgeType: "smoothstep" as const,
  edgeStroke: icfrColors.arrow,
  edgeStrokeWidth: 1,
  edgeDashedPattern: "5 4", // 데이터/정보 흐름 (점선)

  // 자동 배치 시 노드 간 간격
  autoLayoutGapX: 280,
  autoLayoutBaseY: 200,

  // 스냅·정렬 (레고처럼 붙는 느낌)
  snapGridSize: 10, // 노드 이동을 10px 격자에 스냅
  connectionRadius: 36, // 화살표 드래그 시 핸들이 잡히는 반경 (기본 20)
  nodeSnapDistance: 36, // 다른 노드 핸들과 정렬되는 거리 (드롭 시점 자동 정렬)
  axisSnapDistance: 80, // 다른 노드 중심선(X 또는 Y)과 가까우면 자동 정렬되는 임계 (px)
} as const;

/** React Flow 의 edge type 으로 그대로 들어갈 수 있는 값 */
export type EdgeShape = "straight" | "smoothstep" | "default"; // default = bezier(곡선)
export const EDGE_SHAPE_LABELS: Record<EdgeShape, string> = {
  straight: "직선",
  smoothstep: "꺾은선",
  default: "곡선",
};

/* ─────────────────────────────────────────────
 * UI 셸 (Topbar / Sidebar) 치수
 * ───────────────────────────────────────────── */
export const shellDesign = {
  topbarHeight: 56, // px — 액션 버튼 + 토글이 들어가는 높이
  sidebarWidth: 280, // px — 우측 사이드바 폭
  leftSidebarWidth: 280, // px — 좌측 사이드바 폭 (헤더 정보 + 통제·위험 목록)
  sidebarShapeBtnHeight: 44,
  sidebarSectionGap: 12,
} as const;

/* ─────────────────────────────────────────────
 * 비-Activity 도형 노드 치수
 *   - 회사 표준 양식의 각 도형이 캔버스에 그려질 때의 기본 크기.
 *   - 사용자가 추후 노드별 크기를 자유 조정하더라도 "새로 추가" 시의 초기값.
 *   - 크기 비율은 references/구성정보 가이드 + 실제 산출물 예시 기준.
 *
 * Risk/Key/NonKey/ControlType 은 활동 위에 한 줄로 묶인 작은 라벨 띠이므로
 * 폭을 좁게 잡고 한 줄에 자연스럽게 들어가도록 한다.
 * ───────────────────────────────────────────── */
export const shapeNodeDesign = {
  // 글자는 모두 양식의 7pt (= 14.7px). 칸보다 길면 자동으로 줄인다.
  // 회사 양식: START/END·분기점은 활동과 같은 크기의 빈 사각형/마름모
  startEnd: { width: 180, height: 88, fontSize: 14.7, fontWeight: 400 },

  // Link — 양쪽 끝에 세로선이 있는 사각형
  link: { width: 170, height: 52, fontSize: 14.7 },

  diamond: { width: 180, height: 88, fontSize: 14.7 },

  // 활동 위 한 줄(왼쪽 정렬)에 묶이는 라벨 — 양식 42×10.5pt, 칩 8.5×10.5pt
  risk: { width: 84, height: 22, fontSize: 14.7, fontWeight: 400 },
  keyControl: { width: 84, height: 22, fontSize: 14.7, fontWeight: 400 },
  nonkeyControl: { width: 84, height: 22, fontSize: 14.7, fontWeight: 400 },
  controlType: { width: 18, height: 22, fontSize: 14.7, fontWeight: 400 },

  // 활동 아래 모서리에 걸쳐 붙는 문서·DB (양식 68×34pt / 62.6×28pt)
  document: { width: 126, height: 62, fontSize: 14.7 },
  db: { width: 116, height: 54, fontSize: 14.7, fontWeight: 400 },
  interface: { width: 48, height: 48, fontSize: 14.7, fontWeight: 400 },
  textBox: { width: 120, height: 36, fontSize: 14.7, fontWeight: 400 },
  lane: { width: 1200, height: 200, fontSize: 13, fontWeight: 700 },

  borderWidth: 1,
} as const;

/** 통제 배지 오른쪽 A/M/I 칩 — 배지와의 간격 (px) */
export const CHIP_GAP = 4;

/* ─────────────────────────────────────────────
 * 폰트 패밀리 — Tailwind fontFamily.sans 로도 동시에 적용됨
 * ───────────────────────────────────────────── */
export const fontStack = {
  sans: [
    "Pretendard",
    "Pretendard Variable",
    '"Apple SD Gothic Neo"',
    '"Noto Sans KR"',
    '"Malgun Gothic"',
    '"맑은 고딕"',
    "system-ui",
    "-apple-system",
    "Segoe UI",
    "Roboto",
    "sans-serif",
  ],
} as const;

/* ─────────────────────────────────────────────
 * Tailwind 가 그대로 흡수할 형식의 테마 단편.
 * tailwind.config.ts 에서 `theme.extend` 에 spread.
 * ───────────────────────────────────────────── */
export const tailwindTheme = {
  colors: {
    icfr: { ...icfrColors },
  },
  fontFamily: {
    sans: [...fontStack.sans],
  },
} as const;
