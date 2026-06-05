/**
 * 데이터 모델 — flowchart_generator.py 의 dataclass 들을 TypeScript 로 포팅.
 *
 * 도메인 배경:
 *  - RCM (Risk Control Matrix): 내부회계관리제도 평가 대상이 되는
 *    "프로세스 → 하위 프로세스 → 위험 → 통제" 매트릭스.
 *  - 매핑(Mapping) 시트: RCM 한 행을 flowchart 의 활동(Activity) 한 개로
 *    어떻게 풀어낼지 감사인이 직접 적은 시트.
 *  - 활동(Activity): flowchart 상의 한 사각형 노드. RCM 의 한 행을 참조.
 */

/** PPT 상단 헤더 박스에 들어가는 메타 정보 */
export interface HeaderInfo {
  company: string;
  processName: string; // 대분류
  middleCategory: string; // 중분류
  subProcessName: string; // 소분류
  flowchartCode: string; // 예: FA21
  lastChangeDate: string;
  author: string;
}

/** RCM 시트의 한 행 (Process Narrative 단락 단위) */
export interface RcmRow {
  rowNum: number; // 엑셀 행 번호 (4부터)
  process: string;
  processName: string;
  subProcessNo: string;
  subProcessName: string;
  narrative: string;
  riskNo: string;
  riskDesc: string;
  controlNo: string;
  controlName: string;
  controlDesc: string;
  itSystem: string;
  controlOwner: string;
  controlOrg: string;
  keyCa: string; // "Y" | "N" — 핵심통제 여부
  controlType: string; // Manual / Automated / ITDM 등
}

/** 통제유형 약어 — 활동 박스 우상단 원형 라벨에 사용 */
export type ControlTypeSymbol = "A" | "M" | "I";

export function hasRisk(r: RcmRow): boolean {
  return !!r.riskNo.trim();
}

export function hasControl(r: RcmRow): boolean {
  return !!r.controlNo.trim();
}

export function isKeyControl(r: RcmRow): boolean {
  const v = r.keyCa.trim().toUpperCase();
  return v === "Y" || v === "YES" || v === "KEY";
}

export function controlTypeSymbol(r: RcmRow): ControlTypeSymbol {
  return parseControlType(r.controlType);
}

/**
 * v8 — 자유 텍스트로 들어온 통제구분 값을 "A" / "M" / "I" 단일 문자로 정규화.
 *
 *   - 우선: 단일 한 글자 정확 매치 (사용자가 매핑 시트에 "M" 한 글자 적은 경우)
 *   - 차순: 영문 키워드 부분 매치 (RCM 시트의 "Manual", "Automated", "ITDM 보완통제")
 *   - 기본: "M"
 */
export function parseControlType(raw: string | undefined | null): ControlTypeSymbol {
  const v = (raw ?? "").toString().trim().toUpperCase();
  if (v === "A") return "A";
  if (v === "M") return "M";
  if (v === "I") return "I";
  if (v.includes("ITDM") || v.includes("ITGC") || v.includes("IT D")) return "I";
  if (v.includes("AUTO")) return "A";
  if (v.includes("MANUAL")) return "M";
  return "M";
}

/** v8 — "Y"/"YES"/"TRUE"/"KEY" → true, 그 외 false (비어있으면 false) */
export function parseKeyCA(raw: string | undefined | null): boolean {
  const v = (raw ?? "").toString().trim().toUpperCase();
  return v === "Y" || v === "YES" || v === "TRUE" || v === "KEY";
}

/** 매핑 시트의 한 행 = flowchart 의 활동(Activity) 1개 */
export interface Activity {
  /** v4: 이 활동이 속한 flowchart 코드 (예: "FA11", "FA21"). v3 호환을 위해 옵셔널. */
  flowchartCode?: string;
  actNo: number;
  rcmRow: number; // 참조할 RCM 행 번호
  actName: string;
  teamOverride: string; // 비어있으면 rcm.controlOrg 사용
  /** v4: 발생 위치(D칸)를 매핑 시트에서 직접 override. 비우면 RCM.itSystem 사용. */
  locationOverride?: string;
  /**
   * v9 — 매핑 시트에서 직접 입력하는 위험 번호. RCM JOIN 보다 우선.
   * 비어있으면 기존 RCM riskNo 로 fallback.
   */
  riskNoRaw?: string;
  /**
   * v8 — 매핑 시트에서 직접 입력하는 통제 정보. RCM 헤더 구조 변경에 영향 받지
   * 않게 사용자가 직접 옮겨 적는 방식. 비어있으면 RCM JOIN 으로 fallback.
   *
   *   controlNo  : 통제번호 (예: "C.FA.2.1-1"). 통제 박스 라벨에 사용.
   *   controlTypeRaw : "M" / "A" / "I" — 통제구분 단일 문자. RCM 의 긴 텍스트
   *                    ("Manual", "Automated", "ITDM 보완통제") 도 허용 (parse 단계에서 정규화).
   *   keyCaRaw   : "Y" / "N" — Key Control 여부.
   */
  controlNo?: string;
  controlTypeRaw?: string;
  keyCaRaw?: string;
  subSteps: string;
  docNames: string; // 쉼표 구분
  branchInfo: string;
  note: string;
  // JOIN 후 채워짐
  rcm?: RcmRow;
  // React Flow 캔버스 좌표 (드래그 시 변경)
  position?: { x: number; y: number };
}

/** 활동 박스에 표시할 "수행팀" — TEAM_OVERRIDE 우선, 없으면 RCM 의 controlOrg */
export function activityTeam(a: Activity): string {
  if (a.teamOverride.trim()) return a.teamOverride.trim();
  if (a.rcm?.controlOrg.trim()) return a.rcm.controlOrg.trim();
  return "";
}

/**
 * 활동 박스 하단 D칸 "발생위치".
 *  - v4 우선순위: locationOverride (매핑 시트의 LOCATION 컬럼) > rcm.itSystem > "Manual"
 *  - 자동 도형 도출 (DB 등) 도 이 값을 기준으로 한다.
 */
export function activityLocation(a: Activity): string {
  if (a.locationOverride?.trim()) return a.locationOverride.trim();
  return (a.rcm?.itSystem || "").trim() || "Manual";
}

/**
 * v8 — 활동의 통제 정보 도출 (우선순위 규칙).
 *
 *   1. 매핑 시트(Activity) 의 명시 값 — 있으면 그대로 사용
 *   2. 없으면 RCM JOIN 결과 — v7 이하 양식 호환
 *
 *   controlNo / controlType / isKeyControl 모두 위 우선순위로 결정.
 *   controlName / controlDesc 는 RCM 에서만 (매핑 시트엔 없음).
 */
export interface ResolvedControl {
  controlNo: string;
  controlType: ControlTypeSymbol;
  /**
   * true  = Key Control (진분홍)
   * false = Non-Key Control (연분홍)
   * null  = KEY_CA 공란 (v8 매핑 경로, Key/Non-Key 미지정) → 회색 박스
   */
  isKeyControl: boolean | null;
  controlName: string;
  controlDesc: string;
  /** true 이면 "이 활동은 통제 박스를 부착할 대상" — UI/PPT 의 통제 라벨 띠 표시 여부 */
  hasControlAttachment: boolean;
}

export function resolvedControl(a: Activity): ResolvedControl {
  const mappingNo = (a.controlNo || "").trim();
  const mappingType = (a.controlTypeRaw || "").trim();
  const mappingKey = (a.keyCaRaw || "").trim();

  const rcm = a.rcm;
  const rcmHasCtrl = rcm ? hasControl(rcm) : false;

  // 우선순위: 매핑 시트 값 > RCM 값
  const controlNo = mappingNo || (rcm?.controlNo.trim() ?? "");
  const controlType: ControlTypeSymbol = parseControlType(
    mappingType || rcm?.controlType,
  );
  // KEY_CA 우선순위 규칙:
  //   1. 매핑 시트에 값 있음 → 그대로 사용 (true/false)
  //   2. 매핑 시트에 CONTROL_NO 있는데 KEY_CA 공란 → null (회색: Key/Non-Key 미지정)
  //   3. v7 이하 경로 (CONTROL_NO 매핑 없음) → RCM 으로 fallback
  const isKey: boolean | null =
    mappingKey !== ""
      ? parseKeyCA(mappingKey) // 값 있음 → true/false
      : mappingNo !== ""
        ? null // v8 경로 + KEY_CA 공란 → 회색
        : rcm // v7 경로 → RCM fallback
          ? isKeyControl(rcm)
          : false;

  // 통제 박스 부착 여부:
  //   - 매핑 시트에 controlNo 있으면 무조건 부착 (v8)
  //   - 그렇지 않으면 v7 이하 호환 규칙: RCM 에 통제 있고 (KC: 마커 또는 flowchartCode 없음)
  let attach = false;
  if (mappingNo) {
    attach = true;
  } else if (rcmHasCtrl) {
    const note = (a.note || "").trim();
    if (/^\s*KC\s*:/i.test(note)) attach = true;
    else if (!a.flowchartCode) attach = true;
  }

  return {
    controlNo,
    controlType,
    isKeyControl: isKey,
    controlName: rcm?.controlName.trim() ?? "",
    controlDesc: rcm?.controlDesc.trim() ?? "",
    hasControlAttachment: attach,
  };
}

/**
 * 이 활동이 통제(Key/Non-Key Control) 박스를 부착할 "그 활동" 인지 판단.
 *  - v8: 매핑 시트 CONTROL_NO 있으면 부착
 *  - v7 이하: RCM JOIN + (KC: 마커 OR flowchartCode 없음)
 *
 *   resolvedControl().hasControlAttachment 의 얇은 wrapper.
 */
export function isControlActivity(a: Activity): boolean {
  return resolvedControl(a).hasControlAttachment;
}

/** 활동 박스 본문 — SUB_STEPS 우선, 없으면 narrative */
export function activityBody(a: Activity): string {
  if (a.subSteps.trim()) return a.subSteps.trim();
  if (a.rcm?.narrative.trim()) return a.rcm.narrative.trim();
  return "";
}

export function activityDocs(a: Activity): string[] {
  return a.docNames
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean);
}

/**
 * SUB_STEPS 셀 (한 셀에 줄바꿈으로 여러 단계 입력) 을 단계 배열로 파싱.
 *   - \n, \r\n 모두 처리
 *   - 빈 줄은 제거
 *   - 각 줄의 앞뒤 공백 제거
 *   - 이미 ①②③ 같은 prefix 가 있으면 그대로 둠 (중복 추가 방지)
 */
export function parseSubSteps(raw: string): string[] {
  if (!raw) return [];
  return raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

/** ①②③④⑤... 번호 prefix — 단계 자동 번호 매기기 (10단계까지) */
export const STEP_NUMBERS = [
  "①",
  "②",
  "③",
  "④",
  "⑤",
  "⑥",
  "⑦",
  "⑧",
  "⑨",
  "⑩",
] as const;

/** 단계 1개에 번호를 붙임. 10개 초과 시 "11." 식으로 폴백. */
export function numberedStep(idx: number, text: string): string {
  const prefix = STEP_NUMBERS[idx] ?? `${idx + 1}.`;
  return `${prefix} ${text}`;
}

/**
 * 활동 박스 자동 높이 (px).
 *
 *   단계 텍스트가 박스 폭에서 줄바꿈되는 것을 감안해 "실제 줄 수" 를 추정한다.
 *   - 헤더(번호/팀) 24px + 푸터(위치) 20px 고정
 *   - 제목 1줄 + 각 단계가 줄바꿈으로 차지하는 줄 수
 *   steps 를 주지 않으면(구버전 호출) 단계 수 기반 근사값으로 폴백.
 */
export function activityAutoHeight(stepCount: number, steps?: string[]): number {
  const HDR_FOOT = 44; // 헤더 24 + 푸터 20
  const TITLE_LINE = 16; // 제목 1줄 높이 (굵게)
  const PAD = 12; // 본문 상하 여백

  if (!steps || steps.length === 0) {
    if (stepCount <= 0) return 88;
    // 폴백: 단계 수 기준 근사
    const base = 88;
    if (stepCount <= 3) return base;
    if (stepCount <= 5) return Math.round(base * 1.25);
    if (stepCount <= 7) return Math.round(base * 1.5);
    return Math.round(base * 1.75);
  }

  const fontPx = subStepsFontSize(stepCount); // 9/8/7
  // 본문 가용 폭 ≈ 박스폭 180 - 좌우 패딩(보수적으로 22). 한글 글자폭 ≈ fontPx.
  const charsPerLine = Math.max(8, Math.floor((180 - 22) / fontPx));
  const lineH = fontPx * 1.5; // PowerPoint 실제 줄간격 여유
  // 제목도 길면 2줄까지 줄바꿈될 수 있으므로 2줄분 확보
  const titleH = TITLE_LINE * 2;
  let lines = 0;
  for (let i = 0; i < steps.length; i++) {
    const len = numberedStep(i, steps[i]).length;
    lines += Math.max(1, Math.ceil(len / charsPerLine));
  }
  const bodyNeeded = titleH + lines * lineH + PAD;
  return Math.round(Math.max(88, HDR_FOOT + bodyNeeded));
}

/**
 * 단계 수에 따른 본문(SUB_STEPS) 폰트 크기 (pt).
 *   1~3: 9pt / 4~5: 8pt / 6+: 7pt
 */
export function subStepsFontSize(stepCount: number): number {
  if (stepCount <= 3) return 9;
  if (stepCount <= 5) return 8;
  return 7;
}

/** 활동의 단계 수 (parseSubSteps + length) */
export function activityStepCount(a: Activity): number {
  return parseSubSteps(a.subSteps).length;
}

/* ─────────────────────────────────────────────
 * v6 — 통제/위험 카탈로그 모델
 *
 * 좌측 사이드바·헤더 편집·수기 추가 기능을 위해 엑셀과 수기 데이터를 통일된
 * 모델로 다룬다. RcmRow 는 엑셀의 원형(원본 보존용), ControlData 는 UI 가
 * 다루는 정규화 모델 — 엑셀 RCM 1행 또는 사용자 수기 입력 1개에 대응.
 * ───────────────────────────────────────────── */

export type DataSource = "excel" | "manual";

/** 통제 카드 — 엑셀 RCM 1행 또는 수기 입력 1개. flowchart 와 1:1 대응. */
export interface ControlData {
  /** 고유 ID — 수기 통제는 `manual-<rand>`, 엑셀 통제는 `excel-<rcmRow>` */
  id: string;
  source: DataSource;

  /** flowchart 코드 (예: "FA21", "CM01") — 좌측 카드 클릭 시 이 코드로 캔버스 전환 */
  flowchartCode: string;
  /** 소분류 (flowchart 제목 = 헤더 표 "소분류" + 드롭다운 라벨) */
  subProcessName: string;

  controlNo: string;
  controlName: string;
  controlDesc: string;
  isKeyControl: boolean;
  controlType: ControlTypeSymbol;
  controlOrg: string;
  itSystem: string;

  /** 엑셀 출처일 때만 — 원본 RCM 행 번호 (Activity.rcmRow 와 매칭) */
  rcmRowNum?: number;
}

/** 위험 카드 — 엑셀 RCM 1행 또는 수기 입력 1개. 통제와 연관될 수 있음. */
export interface RiskData {
  id: string;
  source: DataSource;
  riskNo: string;
  riskDesc: string;
  /** 연관된 통제(ControlData.id). 비면 독립 위험 */
  linkedControlId?: string;
}

/** 좌측 사이드바 상단 헤더 정보 — 전역, 좌측 [편집] 모달에서 수정 */
export type GlobalHeaderInfo = HeaderInfo;

/* ─────────────────────────────────────────────
 * 엑셀 RCM 행 → ControlData / RiskData 변환
 *
 * 같은 통제번호가 narrative 가 다른 여러 행에 걸쳐 있을 수 있다.
 * 통제 카탈로그는 controlNo 별 1개로 dedupe (첫 등장 행 사용).
 * 위험은 riskNo 별 1개로 dedupe, 같은 RCM 행의 통제와 연관.
 * ───────────────────────────────────────────── */

export function rcmRowToControl(r: RcmRow): ControlData | null {
  if (!hasControl(r)) return null;
  return {
    id: `excel-${r.rowNum}`,
    source: "excel",
    flowchartCode: r.subProcessNo || "",
    subProcessName: r.subProcessName || "",
    controlNo: r.controlNo,
    controlName: r.controlName,
    controlDesc: r.controlDesc,
    isKeyControl: isKeyControl(r),
    controlType: controlTypeSymbol(r),
    controlOrg: r.controlOrg,
    itSystem: r.itSystem,
    rcmRowNum: r.rowNum,
  };
}

export function rcmRowToRisk(r: RcmRow, linkedControlId?: string): RiskData | null {
  if (!hasRisk(r)) return null;
  return {
    id: `excel-risk-${r.rowNum}`,
    source: "excel",
    riskNo: r.riskNo,
    riskDesc: r.riskDesc,
    linkedControlId,
  };
}

/**
 * RCM 전체 → 통제·위험 카탈로그. (v7 이하 호환 — 매핑 시트에 CONTROL_NO 없는 경우)
 *
 *   - controlNo 가 같은 행이 여러 개면 첫 번째만 사용 (보통 narrative 가 한 통제 안에서
 *     여러 단계로 나뉜 경우. 통제 자체는 동일).
 *   - 같은 controlNo 의 두 번째 이후 행에서 위험만 새로 등장하면 그 위험은 첫 번째
 *     통제와 연관시킨다.
 */
export function buildCatalogFromRcm(rcmByRow: Map<number, RcmRow>): {
  controls: ControlData[];
  risks: RiskData[];
} {
  const controls: ControlData[] = [];
  const risks: RiskData[] = [];
  const seenControlNo = new Map<string, string>(); // controlNo → controlId
  const seenRiskNo = new Set<string>();

  // 행 번호 오름차순 (등장 순)
  const rows = [...rcmByRow.values()].sort((a, b) => a.rowNum - b.rowNum);

  for (const r of rows) {
    let controlId: string | undefined;
    if (hasControl(r) && !seenControlNo.has(r.controlNo)) {
      const c = rcmRowToControl(r);
      if (c) {
        controls.push(c);
        seenControlNo.set(r.controlNo, c.id);
        controlId = c.id;
      }
    } else if (hasControl(r)) {
      controlId = seenControlNo.get(r.controlNo);
    }

    if (hasRisk(r) && !seenRiskNo.has(r.riskNo)) {
      const risk = rcmRowToRisk(r, controlId);
      if (risk) {
        risks.push(risk);
        seenRiskNo.add(r.riskNo);
      }
    }
  }
  return { controls, risks };
}

/**
 * v8 — 매핑 시트(Activity[]) + RCM 시트로 통제·위험 카탈로그 빌드.
 *
 *   매핑 시트의 CONTROL_NO 가 우선. 같은 통제번호가 여러 활동에 반복 입력되어도
 *   카탈로그에는 1개만 (첫 등장 활동의 정보 사용). controlName/controlDesc 는
 *   RCM JOIN 으로 가져옴.
 *
 *   매핑 시트 CONTROL_NO 가 비어있고 RCM 에 통제가 있으면 v7 호환 모드로
 *   RCM 행에서 자동 추출 (buildCatalogFromRcm 와 동일 로직).
 */
export function buildCatalogFromActivities(
  activities: Activity[],
  rcmByRow: Map<number, RcmRow>,
): { controls: ControlData[]; risks: RiskData[] } {
  const controls: ControlData[] = [];
  const risks: RiskData[] = [];
  const seenControlNo = new Map<string, string>(); // controlNo → controlId
  const seenRiskNo = new Set<string>();

  // 1) 매핑 시트에 CONTROL_NO 가 하나라도 있으면 v8 경로 — 활동 순회로 카탈로그 구성.
  //    그렇지 않으면 v7 이하 — RCM 순회.
  const anyMappingControl = activities.some((a) => (a.controlNo || "").trim());

  if (anyMappingControl) {
    for (const a of activities) {
      const rcm = a.rcm ?? rcmByRow.get(a.rcmRow);
      const resolved = resolvedControl({ ...a, rcm });

      if (resolved.controlNo && !seenControlNo.has(resolved.controlNo)) {
        const c: ControlData = {
          id: `excel-${resolved.controlNo}`,
          source: "excel",
          flowchartCode: a.flowchartCode || rcm?.subProcessNo || "",
          subProcessName: rcm?.subProcessName || "",
          controlNo: resolved.controlNo,
          controlName: resolved.controlName,
          controlDesc: resolved.controlDesc,
          isKeyControl: resolved.isKeyControl ?? false,
          controlType: resolved.controlType,
          controlOrg: rcm?.controlOrg || "",
          itSystem: rcm?.itSystem || a.locationOverride || "",
          rcmRowNum: rcm?.rowNum,
        };
        controls.push(c);
        seenControlNo.set(resolved.controlNo, c.id);
      }

      // v9: 위험번호 — 매핑 시트 RISK_NO 우선, 없으면 RCM riskNo
      const riskNo = (a.riskNoRaw || "").trim() || (rcm?.riskNo?.trim() ?? "");
      if (riskNo && !seenRiskNo.has(riskNo)) {
        const linkedControlId = resolved.controlNo
          ? seenControlNo.get(resolved.controlNo)
          : undefined;
        const r: RiskData = {
          id: `excel-risk-${riskNo}`,
          source: "excel",
          riskNo,
          riskDesc: rcm?.riskDesc || "",
          linkedControlId,
        };
        risks.push(r);
        seenRiskNo.add(riskNo);
      }
    }
    return { controls, risks };
  }

  // 2) v7 이하 — RCM 카탈로그를 그대로 사용
  return buildCatalogFromRcm(rcmByRow);
}

/** 새 수기 통제의 기본값 — AddControlModal 초기 상태 */
export function emptyManualControl(): Omit<ControlData, "id"> {
  return {
    source: "manual",
    flowchartCode: "",
    subProcessName: "",
    controlNo: "",
    controlName: "",
    controlDesc: "",
    isKeyControl: true,
    controlType: "M",
    controlOrg: "",
    itSystem: "Manual",
  };
}

/** 새 수기 위험의 기본값 */
export function emptyManualRisk(): Omit<RiskData, "id"> {
  return {
    source: "manual",
    riskNo: "",
    riskDesc: "",
    linkedControlId: undefined,
  };
}

/** 랜덤 ID — 수기 통제·위험·node ID 등에 사용 */
export function genManualId(prefix: string): string {
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${Date.now().toString(36)}-${rand}`;
}
