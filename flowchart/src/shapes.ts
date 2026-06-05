/**
 * 회사 표준 Flowchart 구성 도형 — 우측 사이드바 툴바·단축키·디자인 프리뷰의 단일 소스.
 *
 * 출처: references/구성정보 가이드 + flowchart_generator.py.
 * 가이드의 11개 항목을 그대로 옮긴다 (Link, Start/End, Activity, DB, 분기점,
 * Document, I/F, Risk, Key Control, Non-Key Control, 통제구분 A/M/I).
 */
import { icfrColors } from "./design";

export type ShapeKey =
  | "activity"
  | "link"
  | "startEnd"
  | "diamond"
  | "risk"
  | "keyControl"
  | "nonkeyControl"
  | "controlType" // 작은 M/A/I 색 블록
  | "document"
  | "db"
  | "interface"
  | "textBox";

export interface ShapeDef {
  key: ShapeKey;
  label: string; // 사이드바 버튼에 표시되는 한국어 이름
  shortcut?: string; // 단축키 한 글자 (대문자). 일부 도형은 단축키 없음.
  description: string; // tooltip / aria-label
  fill: string; // 미리보기 아이콘 채움색
  stroke: string; // 미리보기 아이콘 테두리색
}

/**
 * 사이드바 노출 순서 — 회사 가이드 그림 순서를 그대로 따른다.
 * (Link · Start/End · Activity · DB · 분기점 · Document · I/F · Risk
 *  · Key Control · Non-Key Control · 통제구분)
 *
 * Activity 는 메인 도형이므로 사이드바에는 같은 자리에 같이 둔다.
 */
export const SHAPES: ShapeDef[] = [
  {
    key: "link",
    label: "Link",
    shortcut: "L",
    description: "Link — 소분류 이상의 타 프로세스 연결 (3분할 사각형).",
    fill: "#FFFFFF",
    stroke: icfrColors.border,
  },
  {
    key: "startEnd",
    label: "Start / End",
    shortcut: "S",
    description: "프로세스의 시작/끝 — 빈 사각형.",
    fill: "#FFFFFF",
    stroke: icfrColors.border,
  },
  {
    key: "activity",
    label: "활동",
    shortcut: "A",
    description: "활동(Activity) — 4분할 박스. 소분류 이하의 한 행동.",
    fill: icfrColors.actBody,
    stroke: icfrColors.border,
  },
  {
    key: "db",
    label: "DB",
    shortcut: "B",
    description: "Database — 시스템 DB·전표 (원통).",
    fill: icfrColors.dbFill,
    stroke: icfrColors.dbBorder,
  },
  {
    key: "diamond",
    label: "분기점",
    shortcut: "D",
    description: "분기점(Decision) — 의사결정·유형구분.",
    fill: "#FFFFFF",
    stroke: icfrColors.border,
  },
  {
    key: "document",
    label: "문서",
    shortcut: "M",
    description: "Document — 생성되는 문서정보 (물결 사각형).",
    fill: icfrColors.docFill,
    stroke: icfrColors.docBorder,
  },
  {
    key: "interface",
    label: "I/F",
    shortcut: "I",
    description: "Interface — 시스템 간 데이터 인터페이스 (작은 회색 원).",
    fill: "#E0E0E0",
    stroke: icfrColors.border,
  },
  {
    key: "risk",
    label: "Risk",
    shortcut: "R",
    description: "Risk — Risk Number 가 들어가는 노란 작은 박스.",
    fill: icfrColors.risk,
    stroke: icfrColors.risk,
  },
  {
    key: "keyControl",
    label: "Key 통제",
    shortcut: "K",
    description: "Key Control — 진분홍 작은 박스.",
    fill: icfrColors.keyCtrl,
    stroke: icfrColors.keyCtrl,
  },
  {
    key: "nonkeyControl",
    label: "Non-Key 통제",
    shortcut: "N",
    description: "Non-Key Control — 연분홍 작은 박스.",
    fill: icfrColors.nonkeyCtrl,
    stroke: icfrColors.nonkeyCtrl,
  },
  {
    key: "controlType",
    label: "통제구분 (M/A/I)",
    // 단축키는 우선 비워둠 — 우측 툴바 클릭 또는 통제와 함께 자동 생성.
    description: "통제구분 — A(Auto)/M(Manual)/I(ITDM) 색 블록.",
    fill: icfrColors.ctrlM,
    stroke: icfrColors.ctrlM,
  },
  {
    key: "textBox",
    label: "텍스트",
    shortcut: "T",
    description: "텍스트 박스 — 테두리·배경 없는 자유 텍스트 메모.",
    fill: "transparent",
    stroke: "transparent",
  },
];

/** 단축키 → ShapeKey 역인덱스. 키보드 핸들러에서 사용 예정. */
export const SHORTCUT_TO_SHAPE: Record<string, ShapeKey> = Object.fromEntries(
  SHAPES.filter((s) => !!s.shortcut).map((s) => [s.shortcut!, s.key]),
);
