import { useState, useEffect, useRef, useCallback } from "react";
import * as XLSX from "xlsx";
import api from "../api";

// ---------------------------------------------------------------------------
// Completion status cycle: "" → "○" → "△" → "×" → ""
// ---------------------------------------------------------------------------
const COMP_CYCLE = ["", "○", "△", "×"];
const COMP_STYLE = {
  "○": "text-[#3a5a2e] font-bold",
  "△": "text-[#6b4c00] font-bold",
  "×": "text-error font-bold",
  "": "text-outline",
};

function nextCompletion(current) {
  const idx = COMP_CYCLE.indexOf(current);
  return COMP_CYCLE[(idx + 1) % COMP_CYCLE.length];
}

// ---------------------------------------------------------------------------
// Note Popover
// ---------------------------------------------------------------------------
function NotePopover({ value, onChange, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [onClose]);

  return (
    <div ref={ref} className="absolute right-0 top-full mt-1 z-50 w-56 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-2xl p-3">
      <label className="text-[10px] font-label font-semibold text-on-surface-variant block mb-1">비고 메모</label>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={3} autoFocus
        className="w-full px-2 py-1.5 text-xs font-body rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:border-primary focus:outline-none resize-none" />
      <button onClick={onClose} className="mt-1.5 w-full px-2 py-1 rounded-lg bg-primary text-white text-[10px] font-label font-semibold hover:opacity-90 transition">닫기</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Progress bar
// ---------------------------------------------------------------------------
function ProgressBar({ progress }) {
  return (
    <div className="flex-1 h-2 rounded-full bg-outline-variant/30 overflow-hidden">
      <div className="h-full rounded-full transition-all" style={{
        width: `${Math.max(progress, 0)}%`,
        backgroundColor: progress >= 100 ? "#3a5a2e" : "#003366",
      }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
export default function PBCExcelUpload({ clientId, onClose }) {
  const [sheets, setSheets] = useState([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [fileName, setFileName] = useState("");
  const [workbook, setWorkbook] = useState(null);
  const [loading, setLoading] = useState(false);
  // rowState: { "sheetName::rowIdx": { is_received, received_date, completion_status, note } }
  const [rowState, setRowState] = useState({});
  const [notePopover, setNotePopover] = useState(null); // { key, x, y }
  const fileRef = useRef(null);

  const dbClientId = clientId ? parseInt(String(clientId).replace("client-", "")) : null;

  // Load saved state
  const loadSavedState = useCallback(async (fName) => {
    if (!dbClientId || !fName) return;
    try {
      const items = await api.getPBCExcelItems(dbClientId, fName);
      const map = {};
      for (const item of items) {
        map[`${item.sheet_name}::${item.row_index}`] = {
          is_received: !!item.is_received,
          received_date: item.received_date || "",
          completion_status: item.completion_status || "",
          note: item.note || "",
        };
      }
      setRowState(map);
    } catch { /* ignore */ }
  }, [dbClientId]);

  // Parse file
  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const data = new Uint8Array(evt.target.result);
        const wb = XLSX.read(data, { type: "array" });
        setWorkbook(wb);
        const parsed = wb.SheetNames.map((name) => {
          const ws = wb.Sheets[name];
          const json = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "" });
          if (!json.length) return { name, headers: [], rows: [] };
          return { name, headers: json[0].map(String), rows: json.slice(1) };
        });
        setSheets(parsed);
        setActiveSheet(0);
        loadSavedState(file.name);
      } catch { alert("엑셀 파일을 읽는 중 오류가 발생했습니다."); }
      finally { setLoading(false); }
    };
    reader.readAsArrayBuffer(file);
    // Reset the input so re-selecting the same file triggers onChange
    e.target.value = "";
  };

  // Get/set row state helper
  const getRS = (key) => rowState[key] || { is_received: false, received_date: "", completion_status: "", note: "" };

  const updateRow = (sheetName, rowIdx, patch) => {
    const key = `${sheetName}::${rowIdx}`;
    setRowState((prev) => {
      const cur = prev[key] || { is_received: false, received_date: "", completion_status: "", note: "" };
      const next = { ...cur, ...patch };
      // Persist
      if (dbClientId && fileName) {
        api.upsertPBCExcelItem({
          client_id: dbClientId,
          file_name: fileName,
          sheet_name: sheetName,
          row_index: rowIdx,
          ...next,
        }).catch(() => {});
      }
      return { ...prev, [key]: next };
    });
  };

  const toggleReceived = (sheetName, rowIdx) => {
    const key = `${sheetName}::${rowIdx}`;
    const cur = getRS(key);
    const newVal = !cur.is_received;
    updateRow(sheetName, rowIdx, {
      is_received: newVal,
      received_date: newVal ? (cur.received_date || new Date().toISOString().slice(0, 10)) : cur.received_date,
    });
  };

  const cycleCompletion = (sheetName, rowIdx) => {
    const key = `${sheetName}::${rowIdx}`;
    const cur = getRS(key);
    updateRow(sheetName, rowIdx, { completion_status: nextCompletion(cur.completion_status) });
  };

  // Export
  const handleExport = () => {
    if (!workbook || !sheets.length) return;
    const wb = XLSX.utils.book_new();
    for (const sheet of sheets) {
      const header = [...sheet.headers, "수령여부", "수령일", "완성도", "비고"];
      const rows = sheet.rows.map((row, idx) => {
        const key = `${sheet.name}::${idx}`;
        const rs = getRS(key);
        return [...row, rs.is_received ? "O" : "", rs.received_date || "", rs.completion_status || "", rs.note || ""];
      });
      const ws = XLSX.utils.aoa_to_sheet([header, ...rows]);
      XLSX.utils.book_append_sheet(wb, ws, sheet.name);
    }
    const baseName = fileName.replace(/\.[^.]+$/, "");
    XLSX.writeFile(wb, `${baseName}_PBC추적.xlsx`);
  };

  // Stats
  const currentSheet = sheets[activeSheet];
  const allRows = sheets.flatMap((sh) => sh.rows.map((_, idx) => `${sh.name}::${idx}`));
  const receivedCount = allRows.filter((k) => getRS(k).is_received).length;
  const totalCount = allRows.length;
  const progress = totalCount > 0 ? Math.round(receivedCount / totalCount * 100) : 0;

  const compCounts = { "○": 0, "△": 0, "×": 0 };
  allRows.forEach((k) => { const s = getRS(k).completion_status; if (compCounts[s] !== undefined) compCounts[s]++; });

  return (
    <div className="fixed inset-0 z-50 flex flex-col">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative mx-auto mt-6 mb-6 w-full max-w-7xl flex-1 flex flex-col bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-outline-variant shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-lg">table_chart</span>
            </div>
            <div>
              <h3 className="font-headline text-sm font-bold text-on-surface">{fileName || "엑셀 PBC 추적"}</h3>
              {sheets.length > 0 && (
                <p className="text-[10px] text-on-surface-variant font-label">
                  전체 {totalCount}건 중 수령완료 {receivedCount}건 ({progress}%)
                  <span className="ml-2">
                    <span className="text-[#3a5a2e]">○</span> {compCounts["○"]}
                    <span className="ml-1 text-[#6b4c00]">△</span> {compCounts["△"]}
                    <span className="ml-1 text-error">×</span> {compCounts["×"]}
                  </span>
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {sheets.length > 0 && (
              <button onClick={handleExport}
                className="px-3 py-1.5 rounded-xl border border-outline-variant text-[11px] font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">download</span>내보내기
              </button>
            )}
            <button onClick={onClose} className="w-8 h-8 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
              <span className="material-symbols-outlined text-on-surface-variant text-lg">close</span>
            </button>
          </div>
        </div>

        {sheets.length === 0 ? (
          /* File picker */
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center max-w-sm">
              <div className="w-16 h-16 mx-auto mb-3 rounded-2xl bg-primary/5 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-3xl">upload_file</span>
              </div>
              <h4 className="font-headline text-base font-bold text-on-surface mb-1.5">엑셀 파일 선택</h4>
              <p className="text-xs text-on-surface-variant font-body mb-4">
                xlsx 또는 xls 파일을 선택하면 PBC 추적 테이블이 생성됩니다.
              </p>
              <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFile} className="hidden" />
              <button onClick={() => fileRef.current?.click()}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white text-sm font-label font-semibold hover:opacity-90 transition flex items-center gap-2 mx-auto">
                <span className="material-symbols-outlined text-lg">folder_open</span>파일 선택
              </button>
              {loading && <p className="text-xs text-outline font-label mt-3 flex items-center justify-center gap-1"><span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>읽는 중...</p>}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Sheet tabs + summary bar */}
            <div className="px-4 pt-2 pb-0 border-b border-outline-variant/50 shrink-0">
              <div className="flex items-center gap-3 mb-2">
                {sheets.length > 1 && sheets.map((sh, i) => (
                  <button key={sh.name} onClick={() => setActiveSheet(i)}
                    className={`px-3 py-1.5 rounded-t-xl text-[11px] font-label font-semibold transition whitespace-nowrap ${
                      i === activeSheet ? "text-primary border-b-2 border-primary" : "text-on-surface-variant hover:text-on-surface"
                    }`}>
                    {sh.name} <span className="text-[10px] text-outline">({sh.rows.length})</span>
                  </button>
                ))}
                <div className="ml-auto flex items-center gap-2">
                  <button onClick={() => fileRef.current?.click()} className="text-[10px] font-label text-primary hover:underline flex items-center gap-0.5">
                    <span className="material-symbols-outlined text-[12px]">swap_horiz</span>다른 파일
                  </button>
                  <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFile} className="hidden" />
                </div>
              </div>
              {/* Mini progress */}
              <div className="flex items-center gap-2 pb-2">
                <span className="text-[10px] font-label text-on-surface-variant shrink-0">{receivedCount}/{totalCount}</span>
                <ProgressBar progress={progress} />
                <span className="text-[10px] font-label font-bold text-on-surface-variant shrink-0">{progress}%</span>
              </div>
            </div>

            {/* Table with sticky tracking columns */}
            {currentSheet && currentSheet.headers.length > 0 && (
              <div className="flex-1 overflow-auto relative">
                <table className="text-[11px] font-label border-collapse" style={{ minWidth: "100%" }}>
                  <thead>
                    <tr className="bg-surface-container-low sticky top-0 z-20">
                      <th className="sticky left-0 z-30 bg-surface-container-low text-center px-2 py-2 font-semibold text-on-surface-variant w-9 border-r border-outline-variant/30">#</th>
                      {currentSheet.headers.map((h, i) => (
                        <th key={i} className="text-left px-2.5 py-2 font-semibold text-on-surface-variant whitespace-nowrap border-r border-outline-variant/30">
                          {h || `열${i + 1}`}
                        </th>
                      ))}
                      {/* Sticky tracking columns */}
                      <th className="sticky right-[168px] z-30 bg-surface-container-low text-center px-2 py-2 font-semibold text-primary w-14 border-l-2 border-primary/20">수령</th>
                      <th className="sticky right-[88px] z-30 bg-surface-container-low text-center px-2 py-2 font-semibold text-primary w-20">수령일</th>
                      <th className="sticky right-[40px] z-30 bg-surface-container-low text-center px-2 py-2 font-semibold text-primary w-12">완성도</th>
                      <th className="sticky right-0 z-30 bg-surface-container-low text-center px-2 py-2 font-semibold text-on-surface-variant w-10">비고</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentSheet.rows.map((row, idx) => {
                      const key = `${currentSheet.name}::${idx}`;
                      const rs = getRS(key);
                      return (
                        <tr key={idx} className={`border-t border-outline-variant/30 transition ${rs.is_received ? "bg-secondary-container/15" : "hover:bg-surface-container/50"}`}>
                          <td className="sticky left-0 z-10 bg-inherit text-center px-2 py-1.5 text-outline border-r border-outline-variant/30">{idx + 1}</td>
                          {currentSheet.headers.map((_, ci) => (
                            <td key={ci} className={`px-2.5 py-1.5 border-r border-outline-variant/30 max-w-[220px] truncate ${rs.is_received ? "text-on-surface-variant" : "text-on-surface"}`}>
                              {row[ci] !== undefined && row[ci] !== null ? String(row[ci]) : ""}
                            </td>
                          ))}
                          {/* Sticky: 수령 */}
                          <td className="sticky right-[168px] z-10 bg-inherit text-center px-2 py-1.5 border-l-2 border-primary/20">
                            <input type="checkbox" checked={rs.is_received}
                              onChange={() => toggleReceived(currentSheet.name, idx)}
                              className="w-3.5 h-3.5 rounded border-outline-variant text-primary focus:ring-primary cursor-pointer" />
                          </td>
                          {/* Sticky: 수령일 */}
                          <td className="sticky right-[88px] z-10 bg-inherit text-center px-1 py-1.5">
                            <input type="date" value={rs.received_date}
                              onChange={(e) => updateRow(currentSheet.name, idx, { received_date: e.target.value })}
                              className="w-full text-[10px] px-1 py-0.5 rounded border border-outline-variant/50 bg-transparent text-on-surface focus:border-primary focus:outline-none" />
                          </td>
                          {/* Sticky: 완성도 */}
                          <td className="sticky right-[40px] z-10 bg-inherit text-center px-2 py-1.5">
                            <button onClick={() => cycleCompletion(currentSheet.name, idx)}
                              className={`w-7 h-7 rounded-lg hover:bg-surface-container transition text-base ${COMP_STYLE[rs.completion_status] || COMP_STYLE[""]}`}>
                              {rs.completion_status || "–"}
                            </button>
                          </td>
                          {/* Sticky: 비고 */}
                          <td className="sticky right-0 z-10 bg-inherit text-center px-1 py-1.5 relative">
                            <button onClick={() => setNotePopover(notePopover === key ? null : key)}
                              className={`w-6 h-6 rounded-lg transition text-[12px] ${rs.note ? "bg-primary-fixed text-primary" : "hover:bg-surface-container text-outline"}`}
                              title={rs.note || "메모 추가"}>
                              <span className="material-symbols-outlined text-[14px]">{rs.note ? "sticky_note_2" : "add_comment"}</span>
                            </button>
                            {notePopover === key && (
                              <NotePopover
                                value={rs.note}
                                onChange={(v) => updateRow(currentSheet.name, idx, { note: v })}
                                onClose={() => setNotePopover(null)}
                              />
                            )}
                          </td>
                        </tr>
                      );
                    })}
                    {currentSheet.rows.length === 0 && (
                      <tr><td colSpan={currentSheet.headers.length + 5} className="text-center py-8 text-on-surface-variant font-body text-xs">데이터가 없습니다</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
