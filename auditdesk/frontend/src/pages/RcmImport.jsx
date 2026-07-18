import { useState, useRef } from "react";
import { api } from "../api.js";
import { Icon } from "../components/Tokens.jsx";

// xlsx는 모달을 실제로 사용할 때만 동적 로드 (메인 번들 경량화)
let XLSX = null;
async function ensureXlsx() {
  if (!XLSX) XLSX = await import("xlsx");
  return XLSX;
}

// 매핑 대상 표준 필드 (ICFR 모델에 맞춤)
export const RCM_FIELDS = [
  { key: "ignore",        label: "(무시)" },
  { key: "code",          label: "번호" },
  { key: "process",       label: "프로세스" },
  { key: "description",   label: "통제활동(설명/이름)" },
  { key: "ctrl_type",     label: "통제유형(설계/운영)" },
  { key: "risk",          label: "위험(Risk)" },
  { key: "objective",     label: "통제목적" },
  { key: "org",           label: "수행조직" },
  { key: "owner",         label: "통제책임자" },
  { key: "nature",        label: "예방/적발(nature)" },
  { key: "frequency",     label: "통제주기" },
  { key: "residual_risk", label: "잔여위험" },
  { key: "mrc",           label: "핵심통제(MRC/Key)" },
  { key: "ipe",           label: "IPE" },
  { key: "accounts",      label: "계정과목" },
  { key: "assertions",    label: "경영자주장" },
  { key: "test_types",    label: "테스트(절차/증빙)" },
  { key: "sample_size",   label: "샘플수/모집단" },
  { key: "eval_result",   label: "평가결과" },
  { key: "status",        label: "테스트상태" },
  { key: "due",           label: "완료일" },
  { key: "exception_note",label: "이슈내용" },
];

// 헤더 문자열 → 표준 필드 추정 (구체적인 것 우선)
const GUESS = [
  ["exception_note", ["이슈", "미비", "exception", "예외내용", "결함"]],
  ["status",         ["테스트상태", "test status", "수행상태", "진행상태"]],
  ["residual_risk",  ["잔여", "residual"]],
  ["mrc",            ["mrc", "key ca", "핵심통제", "키통제", "key control"]],
  ["ipe",            ["ipe"]],
  ["sample_size",    ["샘플", "sample", "모집단", "표본"]],
  ["test_types",     ["테스트", "절차", "증빙", "재수행", "질문", "관찰", "검증", "test", "procedure"]],
  ["assertions",     ["주장", "assertion", "경영자"]],
  ["accounts",       ["계정", "account", "주석"]],
  ["frequency",      ["주기", "빈도", "frequency"]],
  ["nature",         ["예방", "적발", "nature", "통제속성", "통제 성격"]],
  ["objective",      ["목적", "objective", "재무보고", "자산보호", "부정방지"]],
  ["org",            ["조직", "organization", "부서", "수행"]],
  ["owner",          ["책임자", "owner", "담당"]],
  ["ctrl_type",      ["통제유형", "설계", "운영", "control type"]],
  ["eval_result",    ["평가결과", "결과", "result", "효과"]],
  ["due",            ["완료일", "완료", "due", "일자", "date"]],
  ["risk",           ["리스크", "위험", "risk point", "risk"]],
  ["process",        ["프로세스", "process", "업무"]],
  ["description",    ["통제활동", "통제명", "통제내용", "통제 설명", "control", "설명", "activity"]],
  ["code",           ["번호", "no.", "no", "code", "id"]],
];

function guessToken(token) {
  const h = String(token || "").toLowerCase().replace(/\s+/g, "");
  if (!h) return "ignore";
  for (const [field, kws] of GUESS) {
    if (kws.some((kw) => h.includes(kw.toLowerCase().replace(/\s+/g, "")))) return field;
  }
  return "ignore";
}

// 다단 헤더 라벨(예: "프로세스 번호")은 말단 토큰을 우선 매칭
function guessField(header) {
  const tokens = String(header || "").split(/\s+/).filter(Boolean);
  for (let i = tokens.length - 1; i >= 0; i--) {
    const f = guessToken(tokens[i]);
    if (f !== "ignore") return f;
  }
  return guessToken(header);
}

const truthy = (v) => /^(y|yes|예|o|true|1|해당|key|핵심)/i.test(String(v || "").trim());
const splitList = (v) => String(v || "").split(/[,;·\n/]+/).map((s) => s.trim()).filter(Boolean);
function mapStatus(v) {
  const s = String(v || "").trim();
  if (/완료|done|complete/i.test(s)) return "done";
  if (/이슈|예외|결함|exception|fail/i.test(s)) return "exception";
  if (/진행|in.?progress|수행중/i.test(s)) return "in_progress";
  return "todo";
}

// 워크시트 → {headers:[{col,label}], dataRows:[[...]]}
function parseSheet(ws) {
  const aoa = XLSX.utils.sheet_to_json(ws, { header: 1, raw: false, defval: "" });
  // 병합 셀: top-left 값을 병합 범위 전체에 채움
  (ws["!merges"] || []).forEach((m) => {
    const val = aoa[m.s.r]?.[m.s.c] ?? "";
    for (let r = m.s.r; r <= m.e.r; r++) {
      for (let c = m.s.c; c <= m.e.c; c++) {
        if (!aoa[r]) aoa[r] = [];
        if (aoa[r][c] === undefined || aoa[r][c] === "") aoa[r][c] = val;
      }
    }
  });

  const scan = aoa.slice(0, 5); // 1~5행만 헤더 후보로 검사
  const colCount = Math.max(0, ...scan.map((row) => row.length));
  // 각 행의 "헤더성" 판정: RCM 키워드에 매칭되는 셀이 충분히 많은가
  const headerish = scan.map((row) => {
    const filled = row.filter((c) => String(c).trim()).length;
    if (!filled) return false;
    const kw = row.filter((c) => guessToken(String(c).trim()) !== "ignore").length;
    return kw >= Math.max(2, Math.ceil(filled * 0.4));
  });
  // 헤더 밴드: 첫 헤더성 행부터 연속된 헤더성 행까지 (다단 헤더 대응)
  let firstHeader = headerish.findIndex(Boolean);
  if (firstHeader < 0) firstHeader = 0;
  let bandEnd = firstHeader;
  while (bandEnd + 1 < scan.length && headerish[bandEnd + 1]) bandEnd++;

  const headers = [];
  for (let c = 0; c < colCount; c++) {
    const parts = [];
    for (let r = firstHeader; r <= bandEnd; r++) {
      const v = String(aoa[r]?.[c] ?? "").trim();
      if (v && !parts.includes(v)) parts.push(v);
    }
    headers.push({ col: c, label: parts.join(" ") || `열 ${c + 1}` });
  }
  const dataRows = aoa.slice(bandEnd + 1).filter((row) => row.some((c) => String(c).trim()));
  return { headers, dataRows };
}

export function RcmImportModal({ open, clients, onClose, onImported }) {
  const [step, setStep] = useState("upload"); // upload | map
  const [sheetNames, setSheetNames] = useState([]);
  const [wb, setWb] = useState(null);
  const [sheetName, setSheetName] = useState("");
  const [parsed, setParsed] = useState(null); // {headers, dataRows}
  const [mapping, setMapping] = useState({}); // col -> field
  const [clientId, setClientId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  if (!open) return null;

  const loadSheet = (workbook, name) => {
    const ws = workbook.Sheets[name];
    const p = parseSheet(ws);
    setParsed(p);
    const m = {};
    p.headers.forEach((h) => { m[h.col] = guessField(h.label); });
    setMapping(m);
  };

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      await ensureXlsx();
      const buf = await file.arrayBuffer();
      const workbook = XLSX.read(buf, { type: "array" });
      setWb(workbook);
      setSheetNames(workbook.SheetNames);
      // 시트명에 'RCM' 포함된 시트 자동 선택, 없으면 첫 시트
      const rcm = workbook.SheetNames.find((n) => /rcm/i.test(n)) || workbook.SheetNames[0];
      setSheetName(rcm);
      loadSheet(workbook, rcm);
      setStep("map");
    } catch (err) {
      setError("엑셀 파일을 읽지 못했습니다: " + err.message);
    }
  };

  const changeSheet = (name) => { setSheetName(name); loadSheet(wb, name); };

  const colFor = (field) => parsed?.headers.find((h) => mapping[h.col] === field)?.col;
  const cell = (row, field) => { const c = colFor(field); return c == null ? "" : String(row[c] ?? "").trim(); };

  const buildPayload = (row) => {
    const code = cell(row, "code");
    const description = cell(row, "description");
    if (!code && !description) return null;
    const ctrlRaw = cell(row, "ctrl_type");
    return {
      client_id: Number(clientId),
      code: code || "(미지정)",
      process: cell(row, "process"),
      description,
      ctrl_type: /설계|design/i.test(ctrlRaw) ? "design" : "operating",
      owner: cell(row, "owner"),
      due: cell(row, "due"),
      status: mapStatus(cell(row, "status")),
      rcm: {
        risk: cell(row, "risk"),
        objective: cell(row, "objective"),
        org: cell(row, "org"),
        nature: cell(row, "nature"),
        frequency: cell(row, "frequency"),
        residual_risk: cell(row, "residual_risk"),
        mrc: truthy(cell(row, "mrc")),
        ipe: truthy(cell(row, "ipe")),
        accounts: splitList(cell(row, "accounts")),
        assertions: splitList(cell(row, "assertions")),
        test_types: splitList(cell(row, "test_types")),
        sample_size: cell(row, "sample_size"),
        eval_result: cell(row, "eval_result"),
        exception_note: cell(row, "exception_note"),
      },
    };
  };

  const validRows = parsed ? parsed.dataRows.map(buildPayload).filter(Boolean) : [];

  const doImport = async () => {
    if (!clientId || validRows.length === 0) return;
    setBusy(true);
    setError("");
    try {
      const created = [];
      for (const payload of validRows) {
        created.push(await api.createIcfr(payload));
      }
      onImported(created);
      reset();
      onClose();
    } catch (err) {
      setError("등록 중 오류: " + err.message);
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setStep("upload"); setWb(null); setSheetNames([]); setSheetName("");
    setParsed(null); setMapping({}); setClientId(""); setError("");
    if (fileRef.current) fileRef.current.value = "";
  };

  const close = () => { reset(); onClose(); };

  const previewRows = parsed ? parsed.dataRows.slice(0, 4) : [];
  const mappedFields = Object.values(mapping).filter((f) => f && f !== "ignore");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/20" onClick={close} />
      <div className="relative bg-white rounded-xl border border-line shadow-xl w-full max-w-3xl max-h-[88vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 pt-6 pb-3">
          <div>
            <h3 className="text-base font-semibold text-ink">RCM 엑셀 업로드</h3>
            <p className="mt-0.5 text-xs text-faint">시트명에 'RCM'이 포함된 시트를 자동 선택하고, 1~5행에서 헤더를 인식합니다 (병합 셀 고려)</p>
          </div>
          <button onClick={close} className="w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
            <Icon name="close" className="text-[18px]" />
          </button>
        </div>

        {error && <div className="mx-6 mb-2 px-3 py-2 rounded-lg bg-[#ef4444]/10 text-[#ef4444] text-xs">{error}</div>}

        {step === "upload" ? (
          <div className="px-6 py-10 flex flex-col items-center gap-4">
            <Icon name="upload_file" className="text-[40px] text-line2" />
            <p className="text-sm text-sub">RCM 엑셀 파일(.xlsx, .xls)을 선택하세요</p>
            <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={onFile}
              className="text-xs text-sub file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:text-white file:text-xs file:font-medium file:cursor-pointer"
              style={{ }} />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-6 pb-2">
            <div className="grid grid-cols-2 gap-3 mb-4">
              <label className="block">
                <span className="text-xs text-sub mb-1.5 block">시트 선택</span>
                <select value={sheetName} onChange={(e) => changeSheet(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink border border-line2">
                  {sheetNames.map((n) => <option key={n} value={n}>{n}{/rcm/i.test(n) ? " (자동인식)" : ""}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="text-xs text-sub mb-1.5 block">대상 클라이언트 *</span>
                <select value={clientId} onChange={(e) => setClientId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink border border-line2">
                  <option value="">선택</option>
                  {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </label>
            </div>

            <p className="text-xs font-semibold text-ink mb-2">컬럼 매핑 <span className="text-faint font-normal">— 인식된 헤더를 표준 RCM 항목에 연결</span></p>
            <div className="rounded-lg border border-line overflow-hidden mb-4">
              <div className="grid grid-cols-[1fr_200px] gap-2 px-3 py-2 bg-[#fafafa] text-[10px] font-semibold text-faint">
                <span>엑셀 헤더</span><span>매핑 대상</span>
              </div>
              <div className="max-h-52 overflow-y-auto">
                {parsed.headers.map((h) => (
                  <div key={h.col} className="grid grid-cols-[1fr_200px] gap-2 px-3 py-1.5 border-t border-line items-center">
                    <span className="text-xs text-ink truncate" title={h.label}>{h.label}</span>
                    <select value={mapping[h.col] || "ignore"} onChange={(e) => setMapping((m) => ({ ...m, [h.col]: e.target.value }))}
                      className={`w-full px-2 py-1 rounded-lg text-xs border ${mapping[h.col] && mapping[h.col] !== "ignore" ? "border-line2 text-ink" : "border-line text-faint"}`}>
                      {RCM_FIELDS.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
                    </select>
                  </div>
                ))}
              </div>
            </div>

            {previewRows.length > 0 && mappedFields.length > 0 && (
              <div className="mb-2">
                <p className="text-xs font-semibold text-ink mb-2">미리보기 <span className="text-faint font-normal">· 데이터 {parsed.dataRows.length}행 중 {validRows.length}행 등록 예정</span></p>
                <div className="rounded-lg border border-line overflow-x-auto">
                  <table className="text-left text-xs" style={{ minWidth: "100%" }}>
                    <thead>
                      <tr className="bg-[#fafafa]">
                        {RCM_FIELDS.filter((f) => f.key !== "ignore" && mappedFields.includes(f.key)).map((f) => (
                          <th key={f.key} className="px-2.5 py-1.5 text-[10px] font-semibold text-faint whitespace-nowrap border-r border-line">{f.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewRows.map((row, i) => {
                        const p = buildPayload(row);
                        if (!p) return null;
                        const view = { ...p, ...p.rcm };
                        return (
                          <tr key={i} className="border-t border-line">
                            {RCM_FIELDS.filter((f) => f.key !== "ignore" && mappedFields.includes(f.key)).map((f) => {
                              let v = view[f.key];
                              if (Array.isArray(v)) v = v.join(", ");
                              if (typeof v === "boolean") v = v ? "Y" : "N";
                              return <td key={f.key} className="px-2.5 py-1.5 text-ink whitespace-nowrap max-w-[160px] truncate border-r border-line">{String(v ?? "") || "—"}</td>;
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between gap-2 px-6 py-4 border-t border-line">
          <span className="text-[11px] text-faint">{step === "map" && parsed ? `${parsed.headers.length}개 컬럼 · ${validRows.length}행 등록 대상` : ""}</span>
          <div className="flex gap-2">
            <button onClick={close} className="px-3 py-1.5 rounded-lg text-[13px] font-medium text-sub hover:bg-[#f4f4f5] transition">취소</button>
            {step === "map" && (
              <button onClick={doImport} disabled={busy || !clientId || validRows.length === 0}
                className="px-3.5 py-1.5 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition disabled:opacity-40"
                style={{ background: "var(--lnac)" }}>
                {busy ? "등록 중…" : `${validRows.length}건 등록`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
