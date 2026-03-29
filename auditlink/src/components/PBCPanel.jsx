import { useState, useEffect, useRef } from "react";
import api from "../api";
import PBCExcelUpload from "./PBCExcelUpload";
import PBCExcelImport from "./PBCExcelImport";

const PBC_STATUS_MAP = {
  "미요청": { bg: "bg-outline-variant/30", text: "text-on-surface-variant" },
  "요청완료": { bg: "bg-primary-fixed", text: "text-primary" },
  "수령완료": { bg: "bg-secondary-container", text: "text-on-secondary-container" },
  "보완요청": { bg: "bg-on-tertiary-container/10", text: "text-on-tertiary-container" },
};
const PBC_STATUS_OPTIONS = ["미요청", "요청완료", "수령완료", "보완요청"];

// ---------------------------------------------------------------------------
// Detail Slide Panel
// ---------------------------------------------------------------------------

function PBCDetailPanel({ item, accounts, onClose, onSave, onDelete }) {
  const [form, setForm] = useState({});
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!item) return;
    setForm({
      name: item.name || "",
      account_id: item.account_id || "",
      request_date: item.request_date || "",
      due_date: item.due_date || "",
      status: item.status || "미요청",
      auditor: item.auditor || "",
      client_contact: item.client_contact || "",
      note: item.note || "",
    });
    setDirty(false);
  }, [item]);

  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  if (!item) return null;

  const update = (k, v) => { setForm((p) => ({ ...p, [k]: v })); setDirty(true); };

  const handleSave = () => {
    onSave(item.id, { ...form, account_id: form.account_id || null });
    setDirty(false);
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="fixed top-0 right-0 bottom-0 w-full max-w-[540px] bg-surface-container-lowest border-l border-outline-variant shadow-2xl z-50 flex flex-col animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-lg">description</span>
            </div>
            <span className="text-sm font-label font-semibold text-on-surface-variant">요청자료 상세</span>
          </div>
          <button onClick={onClose} className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {/* Name */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">자료명 *</label>
            <input type="text" value={form.name} onChange={(e) => update("name", e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
          </div>

          {/* Account */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">계정과목</label>
            <select value={form.account_id} onChange={(e) => update("account_id", e.target.value ? Number(e.target.value) : "")}
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition">
              <option value="">전체 (미지정)</option>
              {(accounts || []).map((a) => <option key={a.id} value={a.id}>{a.label || a.name}</option>)}
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">상태</label>
            <div className="flex gap-1.5 flex-wrap">
              {PBC_STATUS_OPTIONS.map((s) => {
                const st = PBC_STATUS_MAP[s];
                return (
                  <button key={s} onClick={() => update("status", s)}
                    className={`px-2.5 py-1 rounded-xl text-[11px] font-label font-bold transition ${form.status === s ? `${st.bg} ${st.text} ring-1 ring-current` : "bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-low"}`}>
                    {s}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">요청일</label>
              <input type="date" value={form.request_date} onChange={(e) => update("request_date", e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
            </div>
            <div>
              <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">회신기한</label>
              <input type="date" value={form.due_date} onChange={(e) => update("due_date", e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">감사팀 담당자</label>
              <input type="text" value={form.auditor} onChange={(e) => update("auditor", e.target.value)} placeholder="감사팀 담당자"
                className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
            </div>
            <div>
              <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">클라이언트 담당자</label>
              <input type="text" value={form.client_contact} onChange={(e) => update("client_contact", e.target.value)} placeholder="클라이언트 담당자"
                className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
            </div>
          </div>

          {/* Note */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">비고</label>
            <textarea value={form.note} onChange={(e) => update("note", e.target.value)} rows={3} placeholder="비고 입력..."
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition resize-none" />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-outline-variant">
          <button onClick={() => { if (confirm(`"${form.name}" 자료를 삭제하시겠습니까?`)) onDelete(item.id); }}
            className="px-3 py-2 rounded-xl text-xs font-label font-semibold text-error hover:bg-error/5 transition flex items-center gap-1.5">
            <span className="material-symbols-outlined text-sm">delete</span>삭제
          </button>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="px-4 py-2 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition">닫기</button>
            <button onClick={handleSave} disabled={!dirty}
              className={`px-5 py-2 rounded-xl text-xs font-label font-semibold text-white transition flex items-center gap-1.5 ${dirty ? "bg-primary hover:opacity-90" : "bg-outline cursor-not-allowed"}`}>
              <span className="material-symbols-outlined text-sm">save</span>저장
            </button>
          </div>
        </div>
      </div>
      <style>{`
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
        .animate-slide-in { animation: slideIn 0.2s ease-out; }
      `}</style>
    </>
  );
}

// ---------------------------------------------------------------------------
// Progress bar
// ---------------------------------------------------------------------------

function ProgressBar({ progress }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-outline-variant/30 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{
          width: `${Math.max(progress, 0)}%`,
          backgroundColor: progress >= 100 ? "#3a5a2e" : "#003366",
        }} />
      </div>
      <span className="text-[11px] font-label font-bold text-on-surface-variant w-10 text-right">{progress}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main PBC Panel
// ---------------------------------------------------------------------------

export default function PBCPanel({ clientId, accountId, filterByAccount, useApi, accounts }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailItem, setDetailItem] = useState(null);
  const [excelOpen, setExcelOpen] = useState(false);
  const [excelImportOpen, setExcelImportOpen] = useState(false);

  const dbClientId = clientId ? parseInt(String(clientId).replace("client-", "")) : null;
  const dbAccountId = accountId && filterByAccount ? parseInt(String(accountId).replace("account-", "")) : null;

  // Load PBC items
  useEffect(() => {
    if (!useApi || !dbClientId) { setLoading(false); return; }
    setLoading(true);
    const params = { client_id: dbClientId };
    if (dbAccountId) params.account_id = dbAccountId;
    api.getPBCItems(params).then(setItems).catch(() => setItems([])).finally(() => setLoading(false));
  }, [dbClientId, dbAccountId, useApi]);

  // Stats
  const total = items.length;
  const received = items.filter((i) => i.status === "수령완료").length;
  const progress = total > 0 ? Math.round(received / total * 100) : 0;

  const handleAdd = () => {
    const name = prompt("요청자료명:");
    if (!name) return;
    const body = {
      client_id: dbClientId,
      account_id: dbAccountId || null,
      name,
      status: "미요청",
      auditor: "",
      client_contact: "",
      note: "",
    };
    if (useApi) {
      api.createPBCItem(body).then((created) => {
        setItems((prev) => [...prev, { ...created, account_name: null }]);
      });
    }
  };

  const handleBulkImport = async () => {
    if (!useApi) return;
    try {
      const templates = await api.getTemplates();
      if (!templates.length) { alert("템플릿이 없습니다."); return; }
      const names = templates.map((t, i) => `${i + 1}. ${t.name}`).join("\n");
      const choice = prompt(`템플릿 선택 (번호 입력):\n${names}`);
      if (!choice) return;
      const idx = parseInt(choice) - 1;
      if (idx < 0 || idx >= templates.length) { alert("잘못된 번호입니다."); return; }
      const tmpl = templates[idx];
      const accs = tmpl.accounts || [];
      const bulkItems = [];
      for (const acc of accs) {
        for (const taskName of (acc.tasks || [])) {
          bulkItems.push({
            client_id: dbClientId,
            account_id: null,
            name: `[${acc.name}] ${taskName}`,
            status: "미요청",
            auditor: "",
            client_contact: "",
            note: `템플릿: ${tmpl.name}`,
          });
        }
      }
      if (!bulkItems.length) { alert("템플릿에 항목이 없습니다."); return; }
      if (!confirm(`${bulkItems.length}건의 요청자료를 추가하시겠습니까?`)) return;
      const created = await api.bulkCreatePBCItems(bulkItems);
      setItems((prev) => [...prev, ...created.map((c) => ({ ...c, account_name: null }))]);
    } catch {
      alert("템플릿 가져오기에 실패했습니다.");
    }
  };

  const handleExcelImport = async (parsedItems) => {
    if (!useApi || !dbClientId) return;
    const bulkItems = parsedItems.map((item) => ({
      client_id: dbClientId,
      account_id: dbAccountId || null,
      name: item.name,
      due_date: item.due_date || null,
      status: "미요청",
      auditor: item.auditor || "",
      client_contact: "",
      note: item.account_label ? `계정: ${item.account_label}` : "",
    }));
    try {
      const created = await api.bulkCreatePBCItems(bulkItems);
      setItems((prev) => [...prev, ...created.map((c) => ({ ...c, account_name: null }))]);
    } catch {
      alert("엑셀 가져오기에 실패했습니다.");
    }
  };

  const handleSave = (id, updates) => {
    if (useApi) api.updatePBCItem(id, updates).catch(() => {});
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...updates } : i)));
    setDetailItem(null);
  };

  const handleDelete = (id) => {
    if (useApi) api.deletePBCItem(id).catch(() => {});
    setItems((prev) => prev.filter((i) => i.id !== id));
    setDetailItem(null);
  };

  const today = new Date().toISOString().slice(0, 10);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-on-surface-variant font-body">
        <span className="material-symbols-outlined text-2xl animate-spin text-outline-variant mr-2">progress_activity</span>
        불러오는 중...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Summary */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-on-surface-variant font-label">전체 {total}건 중 수령완료 {received}건</p>
          <div className="flex items-center gap-2">
            <button onClick={() => setExcelImportOpen(true)}
              className="px-2.5 py-1.5 rounded-xl border border-outline-variant text-[11px] font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">upload_file</span>
              엑셀 가져오기
            </button>
            <button onClick={() => setExcelOpen(true)}
              className="px-2.5 py-1.5 rounded-xl border border-outline-variant text-[11px] font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">table_chart</span>
              PBC 추적
            </button>
            <button onClick={handleAdd}
              className="px-3 py-1.5 bg-gradient-to-r from-primary to-primary-container text-white text-xs font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">add</span>
              추가
            </button>
          </div>
        </div>
        <ProgressBar progress={progress} />
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto rounded-xl border border-outline-variant">
        <table className="w-full text-xs font-label">
          <thead>
            <tr className="bg-surface-container-low sticky top-0 z-10">
              <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant">자료명</th>
              {!filterByAccount && <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant">계정과목</th>}
              <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant w-20">요청일</th>
              <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant w-20">회신기한</th>
              <th className="text-center px-3 py-2.5 font-semibold text-on-surface-variant w-20">상태</th>
              <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant w-16">감사팀</th>
              <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant w-20">클라이언트</th>
              <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant hidden lg:table-cell">비고</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const st = PBC_STATUS_MAP[item.status] || PBC_STATUS_MAP["미요청"];
              const overdue = item.due_date && item.due_date < today && item.status !== "수령완료";
              return (
                <tr key={item.id} onClick={() => setDetailItem(item)}
                  className={`border-t border-outline-variant/50 cursor-pointer hover:bg-surface-container transition ${item.status === "수령완료" ? "bg-secondary-container/10" : ""}`}>
                  <td className="px-3 py-2.5 font-semibold text-on-surface max-w-[200px] truncate">{item.name}</td>
                  {!filterByAccount && <td className="px-3 py-2.5 text-on-surface-variant">{item.account_name || "-"}</td>}
                  <td className="px-3 py-2.5 text-on-surface-variant">{item.request_date || "-"}</td>
                  <td className={`px-3 py-2.5 ${overdue ? "text-error font-bold" : "text-on-surface-variant"}`}>{item.due_date || "-"}{overdue && <span className="text-[9px] ml-0.5">(초과)</span>}</td>
                  <td className="px-3 py-2.5 text-center">
                    <span className={`inline-flex px-2 py-0.5 rounded-xl text-[10px] font-bold ${st.bg} ${st.text}`}>{item.status}</span>
                  </td>
                  <td className="px-3 py-2.5 text-on-surface-variant truncate">{item.auditor || "-"}</td>
                  <td className="px-3 py-2.5 text-on-surface-variant truncate">{item.client_contact || "-"}</td>
                  <td className="px-3 py-2.5 text-on-surface-variant truncate max-w-[150px] hidden lg:table-cell">{item.note || "-"}</td>
                </tr>
              );
            })}
            {items.length === 0 && (
              <tr><td colSpan={filterByAccount ? 7 : 8} className="text-center py-10 text-on-surface-variant font-body">요청자료가 없습니다</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Detail panel */}
      {detailItem && (
        <PBCDetailPanel item={detailItem} accounts={accounts} onClose={() => setDetailItem(null)} onSave={handleSave} onDelete={handleDelete} />
      )}

      {/* Excel PBC tracking modal */}
      {excelOpen && (
        <PBCExcelUpload clientId={clientId} onClose={() => setExcelOpen(false)} />
      )}

      {/* Excel → PBC import modal */}
      {excelImportOpen && (
        <PBCExcelImport onClose={() => setExcelImportOpen(false)} onImport={handleExcelImport} />
      )}
    </div>
  );
}
