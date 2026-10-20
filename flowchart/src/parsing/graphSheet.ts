import * as XLSX from "xlsx";

import type { HeaderInfo } from "../types";
import { readHeaderInfo } from "./xlsxParser";

/**
 * 그래프형 시트 파서 — "한 행 = 박스 1개, Next ID 로 연결" 형식.
 *
 *   필수 열 : Flowchart Code · ID · 활동명
 *   연결    : Next ID — "2", "D1", "3(Y), L1(N)", "END". 비우면 다음 행으로 이어짐.
 *             "-" (또는 "없음") 은 화살표 없이 여기서 흐름이 끝남.
 *   유형    : 비움=활동 / 분기 / Link
 *   단계    : 선택. 값이 바뀌는 행부터 새 줄에 단계 라벨과 함께 그린다. 비우면 위 행의 단계를 이어받음.
 *   헤더    : 대분류·중분류·소분류 열 (선택) + 헤더정보 시트 (선택, 회사명·작성일 등)
 *
 * 열 이름은 별칭으로 매칭한다 (한글/영문, 공백·괄호·* 무시).
 * 엑셀 데이터는 브라우저 안에서만 처리되고 외부로 나가지 않는다.
 */

export type GraphNodeKind = "activity" | "decision" | "link";

export interface GraphNext {
  /** 대상 ID (대문자 정규화 전 원문). "END" 는 종료. */
  to: string;
  /** 화살표 라벨 (Y/N, 승인/반려 등) */
  label?: string;
}

export interface GraphRow {
  /** 엑셀 행 번호 (1-base, 경고 메시지용) */
  excelRow: number;
  id: string;
  kind: GraphNodeKind;
  name: string;
  /** 엑셀에 적힌 Next ID 원문 기준 (비었으면 빈 배열 → 빌더가 다음 행으로 이음) */
  next: GraphNext[];
  /** Next ID 가 "-" / "없음" — 다음 행으로 잇지 않고 여기서 흐름이 끝남 */
  stop: boolean;
  /** 단계(구분) 이름 — 비어 있으면 위 행의 값을 이어받은 결과. 단계 열이 없으면 "" */
  phase: string;
  narrative: string;
  dept: string;
  system: string;
  docs: string[];
  db: string;
  riskNo: string;
  riskDesc: string;
  controlNo: string;
  controlTitle: string;
  controlDesc: string;
  keyCa: string;
  controlType: string;
  /** 스윔레인 순서 (선택) */
  laneOrder?: number;
  /** 박스 본문에 표시할 세부 단계 (선택, 줄바꿈 구분) */
  subSteps: string;
}

export interface GraphFlowchart {
  code: string;
  cycleCode: string;
  cycleName: string;
  processCode: string;
  processName: string;
  subCode: string;
  subName: string;
  rows: GraphRow[];
}

export interface ParsedGraph {
  sheetName: string;
  headerInfo: HeaderInfo;
  flowcharts: GraphFlowchart[];
  warnings: string[];
}

/* ─────────────────────────────────────────────
 * 열 별칭
 * ───────────────────────────────────────────── */

function norm(v: unknown): string {
  if (v == null) return "";
  return String(v)
    .replace(/[\s\n\r\t()（）.\/\-_*·:]/g, "")
    .toLowerCase();
}

type Field =
  | "code" | "cycleCode" | "cycleName" | "processCode" | "processName"
  | "subCode" | "subName" | "id" | "type" | "name" | "next" | "narrative"
  | "dept" | "system" | "docs" | "db" | "riskNo" | "riskDesc" | "controlNo"
  | "controlTitle" | "controlDesc" | "keyCa" | "controlType" | "lane"
  | "subSteps" | "phase";

const ALIASES: Record<Field, string[]> = {
  code: ["flowchartcode", "flowchart코드", "플로우차트코드", "fc코드", "fccode"],
  cycleCode: ["cyclecode", "대분류코드"],
  cycleName: ["cycle명", "cyclename", "cycle", "대분류", "대분류명"],
  processCode: ["processcode", "중분류코드"],
  processName: ["process명", "processname", "process", "중분류", "중분류명"],
  subCode: ["subprocesscode", "소분류코드"],
  subName: ["subprocess명", "subprocessname", "subprocess", "소분류", "소분류명"],
  id: ["id", "단계id", "노드id", "번호"],
  type: ["type", "유형", "도형", "도형유형"],
  name: ["iddesc", "활동명", "단계명", "명칭", "activityname", "activity"],
  next: ["nextid", "다음id", "다음단계", "next", "다음"],
  narrative: [
    "processnarrative", "narrative", "업무기술", "업무기술narrative",
    "업무내용", "업무설명",
  ],
  dept: ["담당부서", "수행부서", "수행팀", "부서", "담당팀", "lane명"],
  system: [
    "system명ormanual", "systemormanual", "시스템", "시스템명", "system",
    "발생위치", "시스템manual",
  ],
  docs: ["document", "documents", "문서", "산출문서", "관련문서"],
  db: ["db", "데이터베이스", "db테이블", "저장데이터"],
  riskNo: ["riskcode", "riskno", "위험번호", "리스크번호", "risk번호", "wcgwcode"],
  riskDesc: ["riskdescription", "위험내용", "위험설명", "리스크내용", "wcgw"],
  controlNo: ["controlcode", "controlno", "통제번호", "통제코드"],
  controlTitle: ["controltitle", "controlname", "통제명", "통제제목"],
  controlDesc: ["controldescription", "통제내용", "통제설명", "통제활동"],
  keyCa: [
    "keyynonkeyn", "keyca", "key여부", "key여부yn", "keyyn", "keycontrol", "핵심통제",
    "핵심통제여부", "keynonkey",
  ],
  controlType: [
    "automateditdependentmanualmanual", "통제유형", "통제유형ami", "통제구분", "controltype",
    "자동수동", "통제방식",
  ],
  lane: ["레인순서", "laneorder", "lane", "레인"],
  subSteps: ["세부단계", "substeps", "세부절차", "세부내용"],
  // "단계명" 은 활동명, "통제구분" 은 통제유형 별칭이므로 쓰지 않는다
  phase: ["단계", "업무단계", "프로세스단계", "단계구분", "구분", "phase", "section", "stage"],
};

const NORMALIZED_ALIASES: Record<Field, Set<string>> = Object.fromEntries(
  (Object.keys(ALIASES) as Field[]).map((f) => [
    f,
    new Set(ALIASES[f].map(norm)),
  ]),
) as Record<Field, Set<string>>;

function mapHeaderRow(cells: unknown[]): Partial<Record<Field, number>> {
  const map: Partial<Record<Field, number>> = {};
  cells.forEach((c, idx) => {
    const n = norm(c);
    if (!n) return;
    for (const f of Object.keys(NORMALIZED_ALIASES) as Field[]) {
      if (map[f] == null && NORMALIZED_ALIASES[f].has(n)) {
        map[f] = idx;
        break;
      }
    }
  });
  return map;
}

/* ─────────────────────────────────────────────
 * 형식 판별
 * ───────────────────────────────────────────── */

interface SheetHit {
  sheetName: string;
  headerRowIdx: number; // 0-base
  colMap: Partial<Record<Field, number>>;
}

function findGraphSheet(wb: XLSX.WorkBook): SheetHit | null {
  for (const sheetName of wb.SheetNames) {
    const ws = wb.Sheets[sheetName];
    if (!ws || !ws["!ref"]) continue;
    const rows = XLSX.utils.sheet_to_json<unknown[]>(ws, {
      header: 1,
      defval: "",
      blankrows: true,
    });
    const limit = Math.min(rows.length, 10);
    for (let r = 0; r < limit; r++) {
      const colMap = mapHeaderRow(rows[r] ?? []);
      if (colMap.code != null && colMap.id != null && colMap.next != null) {
        return { sheetName, headerRowIdx: r, colMap };
      }
    }
  }
  return null;
}

/** 이 워크북이 그래프형(Next ID) 시트를 가지고 있는가 */
export function isGraphWorkbook(wb: XLSX.WorkBook): boolean {
  return findGraphSheet(wb) !== null;
}

/* ─────────────────────────────────────────────
 * 값 파싱
 * ───────────────────────────────────────────── */

function cellStr(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : String(v);
  }
  return String(v).trim();
}

function parseKind(raw: string): GraphNodeKind | null {
  const v = norm(raw);
  if (!v || v === "활동" || v === "activity" || v === "작업" || v === "task") {
    return "activity";
  }
  if (["분기", "분기점", "decision", "판단", "d"].includes(v)) return "decision";
  if (["link", "링크", "연결", "타프로세스", "offpage"].includes(v)) return "link";
  return null;
}

/** Next ID 가 "흐름 끝(화살표 없음)" 표시인가 */
export function isStopNext(raw: string): boolean {
  return ["-", "–", "—", "없음", "none", "stop"].includes(raw.trim().toLowerCase());
}

/** "3(Y), L1(N)" / "END" / "2" → GraphNext[] */
export function parseNext(raw: string): GraphNext[] {
  if (!raw.trim() || isStopNext(raw)) return [];
  return raw
    .split(/[,，;\n]/)
    .map((tok) => tok.trim())
    .filter(Boolean)
    .map((tok) => {
      const m = tok.match(/^(.+?)\s*[(（]\s*([^)）]*?)\s*[)）]\s*$/);
      if (m) return { to: m[1].trim(), label: m[2].trim() || undefined };
      return { to: tok };
    });
}

function splitDocs(raw: string): string[] {
  return raw
    .split(/[,，\n]/)
    .map((d) => d.trim())
    .filter(Boolean);
}

/** ID 비교용 키 — 대소문자·공백 무시 */
export function idKey(id: string): string {
  return id.replace(/\s+/g, "").toUpperCase();
}

/* ─────────────────────────────────────────────
 * 메인
 * ───────────────────────────────────────────── */

export function parseGraphWorkbook(wb: XLSX.WorkBook): ParsedGraph {
  const hit = findGraphSheet(wb);
  if (!hit) {
    throw new Error(
      "Flowchart 시트를 찾지 못했습니다. 'Flowchart Code' · 'ID' · 'Next ID' 열이 필요합니다.",
    );
  }
  const { sheetName, headerRowIdx, colMap } = hit;
  const warnings: string[] = [];

  if (colMap.name == null) {
    throw new Error("필수 열 '활동명'(ID Desc.) 이 없습니다.");
  }

  const ws = wb.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json<unknown[]>(ws, {
    header: 1,
    defval: "",
    blankrows: true,
    raw: true,
  });

  const get = (row: unknown[], f: Field): string => {
    const idx = colMap[f];
    return idx == null ? "" : cellStr(row[idx]);
  };

  const byCode = new Map<string, GraphFlowchart>();
  const seenIds = new Map<string, Set<string>>();
  const lastPhase = new Map<string, string>(); // Code 별 직전 단계 (빈 칸은 이어받음)

  for (let r = headerRowIdx + 1; r < rows.length; r++) {
    const row = rows[r] ?? [];
    const excelRow = r + 1;
    if (row.every((c) => cellStr(c) === "")) continue;

    const code = get(row, "code");
    const id = get(row, "id");
    const name = get(row, "name");
    if (!code && !id && !name) continue;

    if (!code) {
      warnings.push(`${excelRow}행: Flowchart Code 가 비어 있어 건너뜁니다.`);
      continue;
    }
    if (!id) {
      warnings.push(`${excelRow}행 (${code}): ID 가 비어 있어 건너뜁니다.`);
      continue;
    }

    let fc = byCode.get(code);
    if (!fc) {
      fc = {
        code,
        cycleCode: get(row, "cycleCode"),
        cycleName: get(row, "cycleName"),
        processCode: get(row, "processCode"),
        processName: get(row, "processName"),
        subCode: get(row, "subCode"),
        subName: get(row, "subName"),
        rows: [],
      };
      byCode.set(code, fc);
      seenIds.set(code, new Set());
    } else {
      // 같은 Code 안에서 분류명이 달라지면 첫 값 유지 + 경고
      const checks: Array<[keyof GraphFlowchart, Field, string]> = [
        ["cycleName", "cycleName", "대분류"],
        ["processName", "processName", "중분류"],
        ["subName", "subName", "소분류"],
      ];
      for (const [key, field, label] of checks) {
        const v = get(row, field);
        if (v && fc[key] && v !== fc[key]) {
          warnings.push(
            `${excelRow}행 (${code}): ${label} '${v}' 가 앞 행의 '${fc[key]}' 와 다릅니다. 첫 값을 사용합니다.`,
          );
        } else if (v && !fc[key]) {
          (fc as unknown as Record<string, string>)[key] = v;
        }
      }
    }

    const ids = seenIds.get(code)!;
    if (ids.has(idKey(id))) {
      warnings.push(`${excelRow}행 (${code}): ID '${id}' 가 중복되어 건너뜁니다.`);
      continue;
    }
    ids.add(idKey(id));

    const typeRaw = get(row, "type");
    let kind = parseKind(typeRaw);
    if (!kind) {
      warnings.push(
        `${excelRow}행 (${code}): 유형 '${typeRaw}' 을 알 수 없어 활동으로 처리합니다. (비움/분기/Link)`,
      );
      kind = "activity";
    }

    const laneRaw = get(row, "lane");
    const laneNum = laneRaw ? Number(laneRaw) : NaN;

    const phase = get(row, "phase") || lastPhase.get(code) || "";
    lastPhase.set(code, phase);
    const nextRaw = get(row, "next");

    fc.rows.push({
      excelRow,
      id,
      kind,
      name: name || id,
      next: parseNext(nextRaw),
      stop: isStopNext(nextRaw),
      phase,
      narrative: get(row, "narrative"),
      dept: get(row, "dept"),
      system: get(row, "system"),
      docs: splitDocs(get(row, "docs")),
      db: get(row, "db"),
      riskNo: get(row, "riskNo"),
      riskDesc: get(row, "riskDesc"),
      controlNo: get(row, "controlNo"),
      controlTitle: get(row, "controlTitle"),
      controlDesc: get(row, "controlDesc"),
      keyCa: get(row, "keyCa"),
      controlType: get(row, "controlType"),
      laneOrder: Number.isFinite(laneNum) ? laneNum : undefined,
      subSteps: get(row, "subSteps"),
    });

    if (!name) {
      warnings.push(`${excelRow}행 (${code}): 활동명이 비어 있어 ID 로 표시합니다.`);
    }
  }

  if (byCode.size === 0) {
    throw new Error("Flowchart 시트에 입력된 행이 없습니다.");
  }

  return {
    sheetName,
    headerInfo: readHeaderInfo(wb),
    flowcharts: [...byCode.values()],
    warnings,
  };
}
