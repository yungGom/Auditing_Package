import { useState, useEffect, useRef, useCallback } from "react";
import * as XLSX from "xlsx";
import api from "../api";

// ---------------------------------------------------------------------------
// Progress bar
// ---------------------------------------------------------------------------

function ProgressBar({ progress }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2.5 rounded-full bg-outline-variant/30 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{
          width: `${Math.max(progress, 0)}%`,
          backgroundColor: progress >= 100 ? "#3a5a2e" : "#003366",
        }} />
      </div>
      <span className="text-xs font-label font-bold text-on-surface-variant w-12 text-right">{progress}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ExcelChecklist({ templateId, onClose }) {
  const [workbook, setWorkbook] = useState(null);
  const [sheets, setSheets] = useState([]); // [{ name, headers, rows }]
  const [activeSheet, setActiveSheet] = useState(0);
  const [completed, setCompleted] = useState({}); // { "sheetName::rowIdx": true }
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const fileRef = useRef(null);

  // Load saved checklist state from DB
  const loadSavedState = useCallback(async () => {
    if (!templateId) return;
    try {
      const items = await api.getTemplateChecklists(templateId);
      const map = {};
      for (const item of items) {
        if (item.is_completed) {
          map[`${item.sheet_name}::${item.row_index}`] = true;
        }
      }
      setCompleted(map);
    } catch {
      // ignore
    }
  }, [templateId]);

  useEffect(() => { loadSavedState(); }, [loadSavedState]);

  // Parse Excel file
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
          if (json.length === 0) return { name, headers: [], rows: [] };
          return {
            name,
            headers: json[0].map((h) => String(h)),
            rows: json.slice(1),
          };
        });
        setSheets(parsed);
        setActiveSheet(0);
        loadSavedState();
      } catch {
        alert("엑셀 파일을 읽는 중 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    };
    reader.readAsArrayBuffer(file);
  };

  // Toggle check
  const toggleCheck = (sheetName, rowIdx) => {
    const key = `${sheetName}::${rowIdx}`;
    const newVal = !completed[key];
    setCompleted((prev) => {
      const next = { ...prev };
      if (newVal) next[key] = true;
      else delete next[key];
      return next;
    });
    // Persist to DB
    if (templateId) {
      api.upsertChecklist({
        template_id: templateId,
        sheet_name: sheetName,
        row_index: rowIdx,
        is_completed: newVal,
        note: "",
      }).catch(() => {});
    }
  };

  // Export with completion column
  const handleExport = () => {
    if (!workbook || sheets.length === 0) return;
    const wb = XLSX.utils.book_new();
    for (const sheet of sheets) {
      const header = [...sheet.headers, "완료"];
      const rows = sheet.rows.map((row, idx) => {
        const key = `${sheet.name}::${idx}`;
        return [...row, completed[key] ? "O" : ""];
      });
      const ws = XLSX.utils.aoa_to_sheet([header, ...rows]);
      XLSX.utils.book_append_sheet(wb, ws, sheet.name);
    }
    const baseName = fileName ? fileName.replace(/\.[^.]+$/, "") : "checklist";
    XLSX.writeFile(wb, `${baseName}_체크리스트.xlsx`);
  };

  // Stats
  const currentSheet = sheets[activeSheet];
  const totalRows = currentSheet?.rows.length || 0;
  const completedRows = currentSheet
    ? currentSheet.rows.filter((_, idx) => completed[`${currentSheet.name}::${idx}`]).length
    : 0;
  const progress = totalRows > 0 ? Math.round(completedRows / totalRows * 100) : 0;

  // All sheets stats
  const allTotal = sheets.reduce((s, sh) => s + sh.rows.length, 0);
  const allCompleted = sheets.reduce((s, sh) =>
    s + sh.rows.filter((_, idx) => completed[`${sh.name}::${idx}`]).length, 0);
  const allProgress = allTotal > 0 ? Math.round(allCompleted / allTotal * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex flex-col">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      <div className="relative mx-auto mt-8 mb-8 w-full max-w-6xl flex-1 flex flex-col bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-xl">table_chart</span>
            </div>
            <div>
              <h3 className="font-headline text-base font-bold text-on-surface">
                {fileName || "템플릿 가져오기"}
              </h3>
              {sheets.length > 0 && (
                <p className="text-[11px] text-on-surface-variant font-label">
                  전체 {allTotal}건 중 완료 {allCompleted}건 ({allProgress}%)
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {sheets.length > 0 && (
              <button onClick={handleExport}
                className="px-3 py-1.5 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px]">download</span>
                체크리스트 내보내기
              </button>
            )}
            <button onClick={onClose}
              className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
              <span className="material-symbols-outlined text-on-surface-variant">close</span>
            </button>
          </div>
        </div>

        {/* Body */}
        {sheets.length === 0 ? (
          /* File picker */
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center max-w-md">
              <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-primary/5 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-4xl">upload_file</span>
              </div>
              <h4 className="font-headline text-lg font-bold text-on-surface mb-2">엑셀 파일 선택</h4>
              <p className="text-sm text-on-surface-variant font-body mb-6">
                xlsx 또는 xls 파일을 선택하면 자동으로 체크리스트가 생성됩니다.
                <br />파일은 로컬에서만 읽으며 서버에 업로드되지 않습니다.
              </p>
              <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFile} className="hidden" />
              <button onClick={() => fileRef.current?.click()}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white text-sm font-label font-semibold hover:opacity-90 transition flex items-center gap-2 mx-auto">
                <span className="material-symbols-outlined text-lg">folder_open</span>
                파일 선택
              </button>
              {loading && (
                <p className="text-xs text-outline font-label mt-4 flex items-center justify-center gap-2">
                  <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                  파일 읽는 중...
                </p>
              )}
            </div>
          </div>
        ) : (
          /* Sheet tabs + table */
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Sheet tabs */}
            {sheets.length > 1 && (
              <div className="flex items-center gap-1 px-4 pt-3 pb-0 border-b border-outline-variant/50 shrink-0 overflow-x-auto">
                {sheets.map((sh, i) => (
                  <button key={sh.name} onClick={() => setActiveSheet(i)}
                    className={`px-3 py-2 rounded-t-xl text-xs font-label font-semibold transition whitespace-nowrap ${
                      i === activeSheet
                        ? "text-primary border-b-2 border-primary bg-surface-container-lowest"
                        : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                    }`}>
                    {sh.name}
                    <span className="ml-1.5 text-[10px] text-outline">({sh.rows.length})</span>
                  </button>
                ))}
              </div>
            )}

            {/* Summary bar */}
            <div className="px-6 py-3 border-b border-outline-variant/50 shrink-0">
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-label text-on-surface-variant">
                  <span className="font-semibold text-on-surface">{currentSheet?.name}</span> — 전체 {totalRows}건 중 완료 {completedRows}건
                </p>
                <button onClick={() => fileRef.current?.click()}
                  className="text-[11px] font-label text-primary hover:underline flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">swap_horiz</span>
                  다른 파일
                </button>
                <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFile} className="hidden" />
              </div>
              <ProgressBar progress={progress} />
            </div>

            {/* Table */}
            <div className="flex-1 overflow-auto">
              {currentSheet && currentSheet.headers.length > 0 && (
                <table className="w-full text-xs font-label border-collapse">
                  <thead>
                    <tr className="bg-surface-container-low sticky top-0 z-10">
                      <th className="text-center px-2 py-2.5 font-semibold text-on-surface-variant w-12 border-r border-outline-variant/30">#</th>
                      <th className="text-center px-2 py-2.5 font-semibold text-primary w-14 border-r border-outline-variant/30">완료</th>
                      {currentSheet.headers.map((h, i) => (
                        <th key={i} className="text-left px-3 py-2.5 font-semibold text-on-surface-variant whitespace-nowrap border-r border-outline-variant/30 last:border-r-0">
                          {h || `열 ${i + 1}`}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {currentSheet.rows.map((row, idx) => {
                      const key = `${currentSheet.name}::${idx}`;
                      const checked = !!completed[key];
                      return (
                        <tr key={idx}
                          className={`border-t border-outline-variant/30 transition ${
                            checked ? "bg-secondary-container/15" : "hover:bg-surface-container"
                          }`}>
                          <td className="text-center px-2 py-2 text-outline border-r border-outline-variant/30">{idx + 1}</td>
                          <td className="text-center px-2 py-2 border-r border-outline-variant/30">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleCheck(currentSheet.name, idx)}
                              className="w-4 h-4 rounded border-outline-variant text-primary focus:ring-primary cursor-pointer"
                            />
                          </td>
                          {currentSheet.headers.map((_, ci) => (
                            <td key={ci}
                              className={`px-3 py-2 border-r border-outline-variant/30 last:border-r-0 max-w-[250px] truncate ${
                                checked ? "text-on-surface-variant line-through" : "text-on-surface"
                              }`}>
                              {row[ci] !== undefined && row[ci] !== null ? String(row[ci]) : ""}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                    {currentSheet.rows.length === 0 && (
                      <tr><td colSpan={currentSheet.headers.length + 2} className="text-center py-10 text-on-surface-variant font-body">데이터가 없습니다</td></tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
