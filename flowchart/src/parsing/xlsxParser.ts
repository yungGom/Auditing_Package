import * as XLSX from "xlsx";
import type { Activity, HeaderInfo, RcmRow } from "../types";

/**
 * xlsx 파서 — references/flowchart_generator.py 의 read_header_info / read_rcm /
 * read_mapping / load_all 을 TypeScript 로 포팅.
 *
 * 핵심 책임:
 *  1. 시트별 헤더 행 자동 탐색 (RCM 양식이 60여 컬럼이고 행이 합쳐져 2단인 경우도 처리)
 *  2. 정규화된 컬럼명 (공백·괄호·점·줄바꿈·하이픈 제거 후 소문자) 으로 별칭 매핑
 *  3. 매핑 시트의 ACT_NO/RCM_ROW → RCM 행 JOIN, 헤더 자동 채움
 *  4. 어떤 sub-process 가 발견됐는지 수집 (multi-flowchart 분리용)
 *
 * 외부 통신 없음 — 모든 처리가 브라우저 안에서.
 */

export interface ParsedXlsx {
  headerInfo: HeaderInfo;
  rcmByRow: Map<number, RcmRow>;
  activities: Activity[];
  /** RCM 안에서 발견된 sub-process 번호들 (유니크, 등장 순). */
  subProcessNos: string[];
  /**
   * v4: 매핑 시트 FLOWCHART_CODE 컬럼에서 발견된 코드들 (유니크, 등장 순).
   * v3 호환 파일이면 빈 배열.
   */
  flowchartCodes: string[];
  /** 파싱 중 발생한 경고 (감사 데이터 무결성 점검용). */
  warnings: string[];
}

/* ─────────────────────────────────────────────
 * 컬럼명 정규화 + 별칭
 *   - 정확히 "Process Narrative" 인지, "process narrative" 인지,
 *     "Process_Narrative" 인지 등 변형을 모두 흡수.
 * ───────────────────────────────────────────── */

function normalizeHeader(s: unknown): string {
  if (s == null) return "";
  let v = String(s);
  for (const ch of [" ", "\n", "\t", "\r", "(", ")", ".", "/", "-", "_"]) {
    v = v.split(ch).join("");
  }
  return v.toLowerCase();
}

// RCM 컬럼 별칭 — 정규화 키 → 별칭들
const RCM_COL_ALIASES: Record<string, string[]> = {
  process: ["프로세스", "process"],
  processName: ["프로세스이름", "processname"],
  subProcessNo: ["하위프로세스번호", "subprocessno", "subprocesscode"],
  subProcessName: ["하위프로세스이름", "subprocessname"],
  narrative: ["processnarrative", "narrative", "프로세스내러티브"],
  riskNo: ["리스크no", "risk번호", "위험번호", "riskno", "리스크번호"],
  riskDesc: ["리스크", "위험내용", "risk", "위험"],
  controlNo: ["통제활동번호", "통제번호", "controlno", "controlid", "ca번호"],
  controlName: ["통제활동이름", "통제이름", "controlname"],
  controlDesc: ["통제활동설명", "통제설명", "controldesc", "controldescription"],
  itSystem: ["it시스템", "itsystem", "system"],
  controlOwner: ["controlowner", "통제수행자", "통제소유자"],
  controlOrg: [
    "controlorganization",
    "controlorg",
    "통제조직",
    "통제organization",
  ],
  keyCa: ["keyca", "keycontrol", "핵심통제", "keyyn"],
  controlType: ["통제유형8가지", "통제유형", "controltype", "통제유형8"],
};

interface CellAccessor {
  /** 1-base 행/열 (Python python-pptx 와 동일하게) */
  cell(row: number, col: number): string;
  /** 1-base 마지막 행 */
  maxRow: number;
  /** 1-base 마지막 열 */
  maxCol: number;
}

function makeAccessor(ws: XLSX.WorkSheet): CellAccessor {
  const ref = ws["!ref"];
  if (!ref) return { cell: () => "", maxRow: 0, maxCol: 0 };
  const range = XLSX.utils.decode_range(ref);
  return {
    cell(row: number, col: number) {
      const addr = XLSX.utils.encode_cell({ r: row - 1, c: col - 1 });
      const c = ws[addr];
      if (c == null) return "";
      const v = c.v;
      return v == null ? "" : String(v).trim();
    },
    maxRow: range.e.r + 1,
    maxCol: range.e.c + 1,
  };
}

/**
 * v6 — RCM 시트의 한 컬럼 정보. group(상위 그룹 헤더, 보통 헤더 위 1행) 과
 * name(헤더 자체) 을 함께 들고 다닌다. 같은 이름이 두 그룹에 동시에 등장하는
 * 케이스 (메인 "통제활동" vs "(비교) 기존 RCM") 를 그룹으로 분리할 수 있도록.
 */
interface ColumnInfo {
  /** 1-base 컬럼 번호 */
  index: number;
  /** 헤더 위 1행에서 끌어온 그룹 헤더 (병합 셀이면 가장 가까운 좌측 비어있지 않은 셀). 없으면 "" */
  group: string;
  /** 헤더 셀 원문 (디버그·로그용) */
  rawName: string;
  /** 정규화된 헤더 이름 (alias 매칭에 사용) */
  name: string;
}

/**
 * v6 부터 등장한 무시 대상 그룹 — 명시적 블랙리스트.
 *
 *   "(비교) 기존 RCM" 그룹 안의 "통제활동 번호" / "통제활동 이름" / "맵핑 안되는 경우"
 *   는 같은 이름으로 메인 그룹에도 있을 수 있으므로 그룹 단위로 차단해야 안전.
 *
 *   매치 판정: 그룹명 또는 컬럼명을 정규화 후 부분 문자열로 비교.
 */
const IGNORED_GROUP_KEYWORDS = ["비교", "맵핑안되는경우"];

function shouldIgnoreColumn(col: ColumnInfo): boolean {
  const g = normalizeHeader(col.group);
  if (IGNORED_GROUP_KEYWORDS.some((kw) => g.includes(kw))) return true;
  if (IGNORED_GROUP_KEYWORDS.some((kw) => col.name.includes(kw))) return true;
  return false;
}

/**
 * 헤더 행 자동 탐색.
 *
 *   1~maxScanRows 안에서 requiredKeys 가 가장 많이 매칭되는 행을 헤더로 본다.
 *   매칭 카운트는 *무시 그룹을 제외* 한 컬럼들에 대해서만 센다 — 즉
 *   "(비교) 통제활동 번호" 는 매칭 카운트에 포함되지 않음.
 *
 *   그룹 헤더 (헤더 위 1행) 는 병합 셀 처리를 위해 좌측 비어있지 않은 셀이
 *   계속 이어진다고 본다. "통제활동" 그룹이 col 11~15 에 걸쳐 있고 12-15 가
 *   빈 셀이면 12-15 의 group 도 "통제활동" 으로 추론.
 *
 * 반환: { headerRow, columns } — columns 는 무시 대상도 포함한 전체 (개별 col 의
 *   shouldIgnoreColumn 으로 필터링).
 */
function findHeaderRow(
  acc: CellAccessor,
  requiredKeys: string[],
  maxScanRows = 10,
): { headerRow: number; columns: ColumnInfo[] } {
  let bestRow = -1;
  let bestMatches = 0;
  let bestColumns: ColumnInfo[] = [];

  const limit = Math.min(maxScanRows, acc.maxRow);
  for (let r = 1; r <= limit; r++) {
    const columns: ColumnInfo[] = [];
    // 그룹 헤더 carry-forward: 빈 셀은 가장 가까운 좌측 그룹을 상속
    let currentGroup = "";
    for (let c = 1; c <= acc.maxCol; c++) {
      if (r > 1) {
        const groupCell = acc.cell(r - 1, c);
        if (groupCell) currentGroup = groupCell;
        // groupCell 이 비어있으면 currentGroup 유지 (병합 셀)
      }
      const rawName = acc.cell(r, c);
      if (!rawName) continue;
      columns.push({
        index: c,
        group: currentGroup,
        rawName,
        name: normalizeHeader(rawName),
      });
    }
    // 무시 대상 제외한 컬럼 중에서 requiredKeys 매칭 카운트
    const usable = columns.filter((c) => !shouldIgnoreColumn(c));
    const matchCount = requiredKeys.filter((k) =>
      usable.some((c) => c.name === k),
    ).length;
    if (matchCount > bestMatches) {
      bestMatches = matchCount;
      bestRow = r;
      bestColumns = columns;
    }
  }

  if (bestMatches === 0) {
    throw new Error(`헤더 행을 찾을 수 없습니다. 필수 키: ${requiredKeys.join(", ")}`);
  }
  return { headerRow: bestRow, columns: bestColumns };
}

/**
 * alias 목록(=동일 의미의 컬럼 후보 이름들) 중 첫 매칭되는 컬럼을 반환.
 *
 *   - 무시 그룹은 자동 제외.
 *   - 같은 alias 에 매치되는 컬럼이 여러 개면 preferredGroup 과 그룹명이
 *     일치하는(또는 포함하는) 컬럼을 우선. 없으면 가장 왼쪽(첫 매칭).
 *
 *   v6 의 "통제활동 번호" 가 메인 그룹과 (비교) 그룹에 둘 다 있을 때
 *   preferredGroup="통제활동" 으로 호출 → 메인 그룹의 컬럼 선택.
 */
function findColumnByAliases(
  columns: ColumnInfo[],
  aliases: string[],
  preferredGroup?: string,
): ColumnInfo | null {
  const candidates = columns.filter((c) => !shouldIgnoreColumn(c));
  for (const alias of aliases) {
    const norm = normalizeHeader(alias);
    const matches = candidates.filter((c) => c.name === norm);
    if (matches.length === 0) continue;
    if (matches.length === 1) return matches[0];
    if (preferredGroup) {
      const m = matches.find(
        (c) =>
          c.group === preferredGroup ||
          normalizeHeader(c.group).includes(normalizeHeader(preferredGroup)),
      );
      if (m) return m;
    }
    return matches[0]; // 첫 매칭 = 가장 왼쪽 = 보통 메인 그룹
  }
  return null;
}

/* ─────────────────────────────────────────────
 * 헤더정보 시트
 * ───────────────────────────────────────────── */

/**
 * 엑셀 날짜 처리 — SheetJS 가 날짜 셀을 raw 숫자(직렬값, 예: 45793) 로 읽어
 * 헤더에 "45793" 처럼 표시되는 문제를 보정.
 *
 *   - Date 객체  → 로컬 연/월/일로 YYYY-MM-DD (cellDates 사용 시 대비)
 *   - 숫자/숫자형 문자열 직렬값(40000~60000) → 엑셀 기준일(1899-12-30) 보정 후
 *     UTC 기준 변환 (타임존 off-by-one 회피)
 *   - 그 외(이미 "2025-05-16" 같은 텍스트) → 그대로
 */
function formatHeaderDate(value: unknown): string {
  if (value instanceof Date) {
    const y = value.getFullYear();
    const m = String(value.getMonth() + 1).padStart(2, "0");
    const d = String(value.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }
  const s = String(value ?? "").trim();
  if (/^\d+(\.\d+)?$/.test(s)) {
    const serial = Number(s);
    if (Number.isFinite(serial) && serial > 40000 && serial < 60000) {
      // 엑셀 직렬값 → 1970-01-01 기준 일수 (25569 = 1899-12-30 ~ 1970-01-01)
      const utcDays = Math.floor(serial) - 25569;
      const date = new Date(utcDays * 86400 * 1000);
      const y = date.getUTCFullYear();
      const m = String(date.getUTCMonth() + 1).padStart(2, "0");
      const d = String(date.getUTCDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    }
  }
  return s;
}

function readHeaderInfo(wb: XLSX.WorkBook): HeaderInfo {
  const info: HeaderInfo = {
    company: "",
    processName: "",
    middleCategory: "",
    subProcessName: "",
    flowchartCode: "",
    lastChangeDate: "",
    author: "",
  };
  if (!wb.Sheets["헤더정보"]) return info;

  const acc = makeAccessor(wb.Sheets["헤더정보"]);
  const keyMap: Record<string, keyof HeaderInfo> = {
    회사명: "company",
    대분류: "processName",
    중분류: "middleCategory",
    소분류: "subProcessName",
    flowchartcode: "flowchartCode",
    lastchangedate: "lastChangeDate",
    작성자: "author",
  };

  for (let r = 1; r <= acc.maxRow; r++) {
    const k = normalizeHeader(acc.cell(r, 1));
    const v = acc.cell(r, 2);
    if (k in keyMap && v) {
      const field = keyMap[k];
      // 날짜 필드는 엑셀 직렬값(45793) → YYYY-MM-DD 로 보정
      info[field] = field === "lastChangeDate" ? formatHeaderDate(v) : v;
    }
  }
  return info;
}

/* ─────────────────────────────────────────────
 * RCM 시트
 *   - 한 행이 RcmRow 1개. row_num 은 엑셀 1-base 행 번호.
 *   - narrative 비어있는 행은 스킵.
 * ───────────────────────────────────────────── */

function readRcm(wb: XLSX.WorkBook): {
  rows: Map<number, RcmRow>;
  columns: ColumnInfo[];
  ignoredColumns: ColumnInfo[];
  headerRow: number;
} {
  const ws = wb.Sheets["RCM"];
  if (!ws) throw new Error("RCM 시트가 없습니다.");
  const acc = makeAccessor(ws);

  const { headerRow, columns } = findHeaderRow(
    acc,
    [
      normalizeHeader("Process Narrative"),
      normalizeHeader("하위 프로세스 번호"),
      normalizeHeader("리스크 No."),
      normalizeHeader("통제활동 번호"),
      normalizeHeader("IT시스템"),
    ],
    10,
  );

  // v6: 메인 "통제활동" 그룹과 "(비교) 기존 RCM" 그룹이 같은 컬럼명을 공유.
  //   preferredGroup 으로 정확한 그룹의 컬럼만 선택. 무시 그룹은
  //   findColumnByAliases 안에서 자동 제외.
  const colMap = {
    process: findColumnByAliases(columns, RCM_COL_ALIASES.process),
    processName: findColumnByAliases(columns, RCM_COL_ALIASES.processName),
    subProcessNo: findColumnByAliases(columns, RCM_COL_ALIASES.subProcessNo),
    subProcessName: findColumnByAliases(columns, RCM_COL_ALIASES.subProcessName),
    narrative: findColumnByAliases(columns, RCM_COL_ALIASES.narrative),
    riskNo: findColumnByAliases(columns, RCM_COL_ALIASES.riskNo, "리스크"),
    riskDesc: findColumnByAliases(columns, RCM_COL_ALIASES.riskDesc, "리스크"),
    controlNo: findColumnByAliases(columns, RCM_COL_ALIASES.controlNo, "통제활동"),
    controlName: findColumnByAliases(columns, RCM_COL_ALIASES.controlName, "통제활동"),
    controlDesc: findColumnByAliases(columns, RCM_COL_ALIASES.controlDesc, "통제활동"),
    itSystem: findColumnByAliases(columns, RCM_COL_ALIASES.itSystem, "통제활동"),
    controlOwner: findColumnByAliases(columns, RCM_COL_ALIASES.controlOwner),
    controlOrg: findColumnByAliases(columns, RCM_COL_ALIASES.controlOrg),
    keyCa: findColumnByAliases(columns, RCM_COL_ALIASES.keyCa),
    controlType: findColumnByAliases(columns, RCM_COL_ALIASES.controlType),
  };

  // ── 진단 로그 — 콘솔에서 그룹 + 컬럼 매핑이 정확한지 확인 ──
  console.log(`[xlsx parser] RCM 헤더 행: ${headerRow}, 컬럼 ${columns.length}개`);
  console.table(
    columns.map((c) => ({
      idx: c.index,
      group: c.group,
      name: c.rawName,
      ignored: shouldIgnoreColumn(c) ? "✗" : "",
    })),
  );
  console.log("[xlsx parser] 선택된 컬럼 매핑:");
  console.table(
    Object.fromEntries(
      Object.entries(colMap).map(([k, v]) => [
        k,
        v ? `col ${v.index} · group="${v.group}" · name="${v.rawName}"` : "(없음)",
      ]),
    ),
  );

  const ignoredColumns = columns.filter(shouldIgnoreColumn);

  if (colMap.narrative == null) {
    throw new Error("RCM 시트에서 'Process Narrative' 컬럼을 찾지 못했습니다.");
  }

  const rows = new Map<number, RcmRow>();
  const getCell = (r: number, c: ColumnInfo | null): string =>
    c ? acc.cell(r, c.index) : "";

  for (let r = headerRow + 1; r <= acc.maxRow; r++) {
    const narrative = getCell(r, colMap.narrative);
    if (!narrative) continue;
    const row: RcmRow = {
      rowNum: r,
      process: getCell(r, colMap.process),
      processName: getCell(r, colMap.processName),
      subProcessNo: getCell(r, colMap.subProcessNo),
      subProcessName: getCell(r, colMap.subProcessName),
      narrative,
      riskNo: getCell(r, colMap.riskNo),
      riskDesc: getCell(r, colMap.riskDesc),
      controlNo: getCell(r, colMap.controlNo),
      controlName: getCell(r, colMap.controlName),
      controlDesc: getCell(r, colMap.controlDesc),
      itSystem: getCell(r, colMap.itSystem),
      controlOwner: getCell(r, colMap.controlOwner),
      controlOrg: getCell(r, colMap.controlOrg),
      keyCa: getCell(r, colMap.keyCa),
      controlType: getCell(r, colMap.controlType),
    };
    rows.set(r, row);
  }

  // 데이터 검증 로그 — 첫 데이터 행에서 통제번호가 비어있으면 경고
  const firstRow = [...rows.values()][0];
  if (firstRow && colMap.controlNo) {
    console.log(
      `[xlsx parser] 첫 데이터 행(${firstRow.rowNum}) 통제 정보:`,
      {
        controlNo: firstRow.controlNo || "(빈값 ⚠)",
        controlName: firstRow.controlName,
        controlNoColIndex: colMap.controlNo.index,
        controlNoColGroup: colMap.controlNo.group,
      },
    );
    if (!firstRow.controlNo) {
      console.warn(
        `[xlsx parser] ⚠ 통제번호가 비어있습니다. 잘못된 그룹 컬럼(${colMap.controlNo.index})을 ` +
          `잡았을 가능성 있음. 위 컬럼 테이블에서 col ${colMap.controlNo.index} 의 group 확인.`,
      );
    }
  }

  return { rows, columns, ignoredColumns, headerRow };
}

/* ─────────────────────────────────────────────
 * 매핑 시트
 *   - ACT_NO / RCM_ROW / ACT_NAME 필수.
 *   - 헤더 행은 자동 탐색.
 * ───────────────────────────────────────────── */

function readMapping(wb: XLSX.WorkBook): Activity[] {
  const ws = wb.Sheets["매핑"];
  if (!ws) throw new Error("매핑 시트가 없습니다.");
  const acc = makeAccessor(ws);

  const { headerRow, columns } = findHeaderRow(
    acc,
    [normalizeHeader("ACT_NO"), normalizeHeader("RCM_ROW")],
    10,
  );
  // 매핑 시트는 그룹 충돌이 없는 단일 헤더 구조 — preferredGroup 불필요.

  function getCol(...aliases: string[]): number | null {
    const c = findColumnByAliases(columns, aliases);
    return c ? c.index : null;
  }

  const cFlowchartCode = getCol("FLOWCHART_CODE", "flowchartcode", "플로우차트코드");
  const cActNo = getCol("ACT_NO", "활동번호");
  const cRcmRow = getCol("RCM_ROW", "RCMROW", "RCM행");
  const cActName = getCol("ACT_NAME", "활동명");
  const cTeam = getCol("TEAM_OVERRIDE", "TEAM", "수행팀");
  const cLocation = getCol("LOCATION", "발생위치", "위치");
  // v9: 매핑 시트에서 위험 번호 직접 입력
  const cRiskNo = getCol("RISK_NO", "riskno", "위험번호", "리스크번호");
  // v8: 매핑 시트에서 통제 정보 직접 입력
  const cControlNo = getCol("CONTROL_NO", "controlno", "통제번호");
  const cControlType = getCol("CONTROL_TYPE", "controltype", "통제유형", "통제구분");
  const cKeyCa = getCol("KEY_CA", "keyca", "key", "핵심통제");
  const cSub = getCol("SUB_STEPS", "서브스텝");
  const cDocs = getCol("DOC_NAMES", "문서");
  const cBranch = getCol("BRANCH_INFO", "분기");
  const cNote = getCol("NOTE", "비고");

  if (cActNo == null || cRcmRow == null || cActName == null) {
    throw new Error(
      "매핑 시트에 ACT_NO, RCM_ROW, ACT_NAME 컬럼이 모두 필요합니다.",
    );
  }

  const activities: Activity[] = [];
  for (let r = headerRow + 1; r <= acc.maxRow; r++) {
    const actNoStr = acc.cell(r, cActNo);
    if (!actNoStr) continue;

    const actNo = Number(actNoStr);
    const rcmRow = Number(acc.cell(r, cRcmRow));
    if (!Number.isFinite(actNo) || !Number.isFinite(rcmRow)) {
      // 헤더 설명 행 등은 스킵
      continue;
    }

    // ACT_NAME 공란 → 행 자체를 스킵.
    //   사용자 의도: 활동 박스를 만들지 않고 다음 단계로 자연스럽게 연결되도록.
    //   (buildFlowFromExcel 가 actNo 순서대로 엣지를 잇기 때문에 자동으로 다음 활동과 연결됨.)
    const actNameRaw = acc.cell(r, cActName);
    if (!actNameRaw || !actNameRaw.trim()) {
      console.warn(
        `[매핑 파싱] 행 ${r}: ACT_NAME 공란 → 활동번호 ${actNo} 스킵 (다음 단계로 자동 연결)`,
      );
      continue;
    }

    activities.push({
      flowchartCode: cFlowchartCode
        ? acc.cell(r, cFlowchartCode) || undefined
        : undefined,
      actNo: Math.trunc(actNo),
      rcmRow: Math.trunc(rcmRow),
      actName: acc.cell(r, cActName),
      teamOverride: cTeam ? acc.cell(r, cTeam) : "",
      locationOverride: cLocation
        ? acc.cell(r, cLocation) || undefined
        : undefined,
      riskNoRaw: cRiskNo ? acc.cell(r, cRiskNo) || undefined : undefined,
      controlNo: cControlNo ? acc.cell(r, cControlNo) || undefined : undefined,
      controlTypeRaw: cControlType
        ? acc.cell(r, cControlType) || undefined
        : undefined,
      keyCaRaw: cKeyCa ? acc.cell(r, cKeyCa) || undefined : undefined,
      subSteps: cSub ? acc.cell(r, cSub) : "",
      docNames: cDocs ? acc.cell(r, cDocs) : "",
      branchInfo: cBranch ? acc.cell(r, cBranch) : "",
      note: cNote ? acc.cell(r, cNote) : "",
    });
  }

  // 정렬: flowchartCode 그룹 내에서 actNo 순. flowchartCode 자체의 등장 순서는 보존.
  // 그룹 안에서만 안정 정렬되도록 (flowchartCode, actNo) 키 sort.
  const codeOrder = new Map<string, number>();
  for (const a of activities) {
    const k = a.flowchartCode ?? "";
    if (!codeOrder.has(k)) codeOrder.set(k, codeOrder.size);
  }
  activities.sort((a, b) => {
    const ca = codeOrder.get(a.flowchartCode ?? "") ?? 0;
    const cb = codeOrder.get(b.flowchartCode ?? "") ?? 0;
    if (ca !== cb) return ca - cb;
    return a.actNo - b.actNo;
  });
  return activities;
}

/* ─────────────────────────────────────────────
 * 전체 파싱 — 시트 3개를 읽고 JOIN.
 * ───────────────────────────────────────────── */

export function parseXlsx(wb: XLSX.WorkBook): ParsedXlsx {
  const warnings: string[] = [];

  const headerInfo = readHeaderInfo(wb);
  const { rows: rcmByRow, ignoredColumns, headerRow: rcmHeaderRow } = readRcm(wb);
  const activitiesRaw = readMapping(wb);

  if (ignoredColumns.length > 0) {
    const list = ignoredColumns
      .map((c) => `${c.index}[${c.rawName}|group="${c.group}"]`)
      .join(", ");
    warnings.push(
      `RCM 시트 ${rcmHeaderRow}행 헤더에서 (비교)/맵핑안되는경우 그룹 컬럼 ` +
        `${ignoredColumns.length}개 무시: ${list}. v6+ 양식에서 메인 통제활동 그룹만 사용.`,
    );
  }

  // JOIN — 매핑.rcmRow → RCM 행
  const activities: Activity[] = activitiesRaw.map((a) => {
    const rcm = rcmByRow.get(a.rcmRow);
    if (!rcm) {
      warnings.push(
        `⚠ 활동 ${a.actNo} (${a.actName}): RCM_ROW=${a.rcmRow} 에 해당하는 RCM 행이 없습니다.`,
      );
    }
    return { ...a, rcm };
  });

  // 헤더 자동 보강 — 비어있는 항목을 첫 활동의 RCM 행에서 가져옴
  const firstWithRcm = activities.find((a) => a.rcm);
  if (firstWithRcm?.rcm) {
    const r = firstWithRcm.rcm;
    if (!headerInfo.processName) headerInfo.processName = r.processName;
    if (!headerInfo.subProcessName)
      headerInfo.subProcessName = r.subProcessName;
    if (!headerInfo.flowchartCode) headerInfo.flowchartCode = r.subProcessNo;
  }

  // sub-process 수집 (등장 순, 유니크)
  const seen = new Set<string>();
  const subProcessNos: string[] = [];
  for (const r of rcmByRow.values()) {
    if (r.subProcessNo && !seen.has(r.subProcessNo)) {
      seen.add(r.subProcessNo);
      subProcessNos.push(r.subProcessNo);
    }
  }

  // v4: 매핑 시트의 FLOWCHART_CODE 컬럼에서 등장한 코드 수집 (유니크, 등장 순)
  const seenCodes = new Set<string>();
  const flowchartCodes: string[] = [];
  for (const a of activities) {
    const code = a.flowchartCode;
    if (code && !seenCodes.has(code)) {
      seenCodes.add(code);
      flowchartCodes.push(code);
    }
  }
  if (flowchartCodes.length === 0) {
    warnings.push(
      "매핑 시트에 FLOWCHART_CODE 컬럼이 비어있거나 없습니다. " +
        "v3 호환 모드로 단일 flowchart 처리. " +
        "여러 flowchart 를 한 파일에 담으려면 FLOWCHART_CODE 를 채워주세요.",
    );
  }

  return {
    headerInfo,
    rcmByRow,
    activities,
    subProcessNos,
    flowchartCodes,
    warnings,
  };
}
