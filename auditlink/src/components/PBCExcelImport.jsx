import { useState, useEffect, useRef, useMemo } from "react";
import * as XLSX from "xlsx";

/**
 * PBCExcelImport – 엑셀 파일 → 컬럼 매핑 → PBC 항목 일괄 생성
 *
 * Props:
 *  onClose: () => void
 *  onImport: (items: { name, due_date, auditor, note }[]) => void
 */
export default function PBCExcelImport({ onClose, onImport }) {
  const [step, setStep] = useState("file"); // "file" | "map" | "preview"
  const [sheets, setSheets] = useState([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const fileRef = useRef(null);

  // Mapping state
  const [mapping, setMapping] = useState({
    name: "",       // required: 자료명
    account: "",    // optional: 계정과목
    due_date: "",   // optional: 회신기한
    auditor: "",    // optional: 담당자
  });

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
        const parsed = wb.SheetNames.map((name) => {
          const ws = wb.Sheets[name];
          const json = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "" });
          if (!json.length) return { name, headers: [], rows: [] };
          return { name, headers: json[0].map(String), rows: json.slice(1) };
        });
        setSheets(parsed);
        setActiveSheet(0);
        // Auto-map: guess by header names
        if (parsed[0]?.headers.length) {
          const h = parsed[0].headers;
          const guess = (keywords) => {
            const idx = h.findIndex((col) => keywords.some((k) => col.includes(k)));
            return idx >= 0 ? String(idx) : "";
          };
          setMapping({
            name: guess(["자료", "항목", "자료명", "서류", "내용", "구분"]) || "0",
            account: guess(["계정", "과목"]),
            due_date: guess(["기한", "마감", "일자", "기일", "회신"]),
            auditor: guess(["담당", "감사", "담당자"]),
          });
        }
        setStep("map");
      } catch {
        alert("엑셀 파일을 읽는 중 오류가 발생했습니다.");
      } finally { setLoading(false); }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = "";
  };

  const currentSheet = sheets[activeSheet];
  const headers = currentSheet?.headers || [];

  // Build preview items from mapping
  const previewItems = useMemo(() => {
    if (!currentSheet || !mapping.name) return [];
    const nameIdx = parseInt(mapping.name);
    const accIdx = mapping.account ? parseInt(mapping.account) : -1;
    const dueIdx = mapping.due_date ? parseInt(mapping.due_date) : -1;
    const audIdx = mapping.auditor ? parseInt(mapping.auditor) : -1;

    return currentSheet.rows
      .map((row) => {
        const name = String(row[nameIdx] ?? "").trim();
        if (!name) return null;
        return {
          name,
          account_label: accIdx >= 0 ? String(row[accIdx] ?? "").trim() : "",
          due_date: dueIdx >= 0 ? normalizeDate(String(row[dueIdx] ?? "").trim()) : "",
          auditor: audIdx >= 0 ? String(row[audIdx] ?? "").trim() : "",
        };
      })
      .filter(Boolean);
  }, [currentSheet, mapping]);

  const handleImport = () => {
    if (previewItems.length === 0) return;
    onImport(previewItems);
    onClose();
  };

  // ESC
  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-2xl flex flex-col overflow-hidden max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-xl">upload_file</span>
            </div>
            <div>
              <h3 className="font-headline text-base font-bold text-on-surface">엑셀에서 요청자료 가져오기</h3>
              {fileName && <p className="text-[11px] text-on-surface-variant font-label">{fileName}</p>}
            </div>
          </div>
          <button onClick={onClose} className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        {/* Steps indicator */}
        <div className="px-6 py-3 border-b border-outline-variant/50 flex items-center gap-2 shrink-0">
          {[
            { key: "file", label: "1. 파일 선택", icon: "folder_open" },
            { key: "map", label: "2. 컬럼 매핑", icon: "swap_horiz" },
            { key: "preview", label: "3. 미리보기", icon: "preview" },
          ].map((s, i) => (
            <div key={s.key} className="flex items-center gap-1.5">
              {i > 0 && <span className="material-symbols-outlined text-[14px] text-outline">chevron_right</span>}
              <span className={`flex items-center gap-1 text-[11px] font-label font-semibold px-2 py-1 rounded-lg ${
                step === s.key ? "bg-primary text-white" : "text-on-surface-variant"
              }`}>
                <span className="material-symbols-outlined text-[14px]">{s.icon}</span>
                {s.label}
              </span>
            </div>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step 1: File selection */}
          {step === "file" && (
            <div className="flex items-center justify-center py-8">
              <div className="text-center max-w-sm">
                <div className="w-16 h-16 mx-auto mb-3 rounded-2xl bg-primary/5 flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary text-3xl">upload_file</span>
                </div>
                <h4 className="font-headline text-base font-bold text-on-surface mb-1.5">엑셀 파일 선택</h4>
                <p className="text-xs text-on-surface-variant font-body mb-4">
                  요청자료 목록이 포함된 xlsx/xls 파일을 선택하세요.
                  <br />첫 번째 행은 헤더로 인식됩니다.
                </p>
                <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFile} className="hidden" />
                <button onClick={() => fileRef.current?.click()}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white text-sm font-label font-semibold hover:opacity-90 transition flex items-center gap-2 mx-auto">
                  <span className="material-symbols-outlined text-lg">folder_open</span>파일 선택
                </button>
                {loading && <p className="text-xs text-outline font-label mt-3">읽는 중...</p>}
              </div>
            </div>
          )}

          {/* Step 2: Column mapping */}
          {step === "map" && (
            <div className="space-y-5">
              {/* Sheet selector */}
              {sheets.length > 1 && (
                <div>
                  <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">시트 선택</label>
                  <select value={activeSheet} onChange={(e) => setActiveSheet(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface focus:border-primary focus:outline-none transition">
                    {sheets.map((s, i) => <option key={s.name} value={i}>{s.name} ({s.rows.length}행)</option>)}
                  </select>
                </div>
              )}

              <p className="text-xs text-on-surface-variant font-body">
                엑셀 컬럼을 요청자료 필드에 매핑하세요. <span className="text-error">*</span> 표시는 필수입니다.
              </p>

              {/* Mapping fields */}
              <div className="bg-surface-container rounded-xl p-4 space-y-3">
                <MappingSelect label="자료명" required value={mapping.name} headers={headers}
                  onChange={(v) => setMapping((p) => ({ ...p, name: v }))} />
                <MappingSelect label="계정과목" value={mapping.account} headers={headers}
                  onChange={(v) => setMapping((p) => ({ ...p, account: v }))} />
                <MappingSelect label="회신기한" value={mapping.due_date} headers={headers}
                  onChange={(v) => setMapping((p) => ({ ...p, due_date: v }))} />
                <MappingSelect label="담당자 (감사팀)" value={mapping.auditor} headers={headers}
                  onChange={(v) => setMapping((p) => ({ ...p, auditor: v }))} />
              </div>

              {/* Sample preview */}
              {mapping.name && currentSheet?.rows.length > 0 && (
                <div>
                  <p className="text-[11px] font-label font-semibold text-on-surface-variant mb-1.5">샘플 미리보기 (상위 3행)</p>
                  <div className="rounded-xl border border-outline-variant overflow-hidden">
                    <table className="w-full text-[11px] font-label">
                      <thead>
                        <tr className="bg-surface-container-low">
                          <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">자료명</th>
                          <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">계정과목</th>
                          <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">회신기한</th>
                          <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">담당자</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewItems.slice(0, 3).map((item, i) => (
                          <tr key={i} className="border-t border-outline-variant/50">
                            <td className="px-3 py-1.5 text-on-surface font-semibold">{item.name}</td>
                            <td className="px-3 py-1.5 text-on-surface-variant">{item.account_label || "-"}</td>
                            <td className="px-3 py-1.5 text-on-surface-variant">{item.due_date || "-"}</td>
                            <td className="px-3 py-1.5 text-on-surface-variant">{item.auditor || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Full preview */}
          {step === "preview" && (
            <div>
              <p className="text-xs font-label text-on-surface-variant mb-3">
                총 <span className="font-bold text-on-surface">{previewItems.length}</span>건의 요청자료가 생성됩니다. 확인 후 "가져오기"를 클릭하세요.
              </p>
              <div className="rounded-xl border border-outline-variant overflow-hidden max-h-[400px] overflow-y-auto">
                <table className="w-full text-[11px] font-label">
                  <thead>
                    <tr className="bg-surface-container-low sticky top-0 z-10">
                      <th className="text-center px-2 py-2 font-semibold text-on-surface-variant w-8">#</th>
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">자료명</th>
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">계정과목</th>
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant w-24">회신기한</th>
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant w-20">담당자</th>
                      <th className="text-center px-3 py-2 font-semibold text-on-surface-variant w-16">상태</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewItems.map((item, i) => (
                      <tr key={i} className="border-t border-outline-variant/50">
                        <td className="text-center px-2 py-1.5 text-outline">{i + 1}</td>
                        <td className="px-3 py-1.5 text-on-surface font-semibold">{item.name}</td>
                        <td className="px-3 py-1.5 text-on-surface-variant">{item.account_label || "-"}</td>
                        <td className="px-3 py-1.5 text-on-surface-variant">{item.due_date || "-"}</td>
                        <td className="px-3 py-1.5 text-on-surface-variant">{item.auditor || "-"}</td>
                        <td className="text-center px-3 py-1.5">
                          <span className="inline-flex px-2 py-0.5 rounded-xl text-[10px] font-bold bg-outline-variant/30 text-on-surface-variant">미요청</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-outline-variant shrink-0">
          <div>
            {step !== "file" && (
              <button onClick={() => setStep(step === "preview" ? "map" : "file")}
                className="px-3 py-2 rounded-xl text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">arrow_back</span>이전
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onClose}
              className="px-4 py-2 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition">
              취소
            </button>
            {step === "map" && (
              <button onClick={() => setStep("preview")} disabled={!mapping.name || previewItems.length === 0}
                className={`px-4 py-2 rounded-xl text-xs font-label font-semibold text-white transition flex items-center gap-1 ${mapping.name && previewItems.length > 0 ? "bg-primary hover:opacity-90" : "bg-outline cursor-not-allowed"}`}>
                다음<span className="material-symbols-outlined text-sm">arrow_forward</span>
              </button>
            )}
            {step === "preview" && (
              <button onClick={handleImport}
                className="px-5 py-2 rounded-xl bg-primary text-white text-xs font-label font-semibold hover:opacity-90 transition flex items-center gap-1.5">
                <span className="material-symbols-outlined text-sm">add</span>
                {previewItems.length}건 가져오기
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mapping select row
// ---------------------------------------------------------------------------

function MappingSelect({ label, required, value, headers, onChange }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-label font-semibold text-on-surface-variant w-28 shrink-0">
        {label} {required && <span className="text-error">*</span>}
      </span>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="flex-1 px-3 py-1.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-xs font-label text-on-surface focus:border-primary focus:outline-none transition">
        <option value="">{required ? "컬럼을 선택하세요" : "(사용 안 함)"}</option>
        {headers.map((h, i) => (
          <option key={i} value={i}>{h || `열 ${i + 1}`}</option>
        ))}
      </select>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Date normalizer (handles Excel serial dates and common formats)
// ---------------------------------------------------------------------------

function normalizeDate(val) {
  if (!val) return "";
  // Excel serial number
  if (/^\d{5}$/.test(val)) {
    const d = new Date((Number(val) - 25569) * 86400000);
    return d.toISOString().slice(0, 10);
  }
  // Already YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(val)) return val;
  // Try parsing
  const d = new Date(val);
  if (!isNaN(d.getTime())) return d.toISOString().slice(0, 10);
  return val;
}
