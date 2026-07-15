import { useState, useEffect } from "react";
import { api } from "../api.js";
import { Icon, Spinner } from "../components/Tokens.jsx";

function TemplateModal({ tpl, onClose }) {
  if (!tpl) return null;
  const totalTasks = (tpl.accounts || []).reduce((a, x) => a + (x.task_count || 0), 0);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative bg-white rounded-xl border border-line shadow-xl w-full max-w-md flex flex-col overflow-hidden">
        <div className="flex items-start justify-between px-6 pt-6 pb-4">
          <div>
            <span className="text-[11px] font-medium text-sub px-2 py-0.5 rounded-full bg-[#f4f4f5]">{tpl.industry || "기타"}</span>
            <h3 className="mt-2.5 text-base font-semibold text-ink">{tpl.name}</h3>
            <p className="mt-0.5 text-xs text-faint">계정과목 {(tpl.accounts || []).length} · 할일 {totalTasks}</p>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
            <Icon name="close" className="text-[18px]" />
          </button>
        </div>
        <div className="px-6 pb-4 max-h-[48vh] overflow-y-auto">
          {(tpl.accounts || []).map((a, i) => (
            <div key={i} className="flex items-center gap-3 py-2.5 border-b border-line/70 last:border-b-0">
              <Icon name="account_balance" className="text-[18px] text-faint" />
              <span className="flex-1 text-[13px] text-ink">{a.name}</span>
              <span className="text-xs text-faint tabular-nums">할일 {a.task_count || 0}</span>
            </div>
          ))}
          {(!tpl.accounts || tpl.accounts.length === 0) && (
            <p className="text-xs text-faint py-4 text-center">계정과목이 없습니다</p>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-line">
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-[13px] font-medium text-sub hover:bg-[#f4f4f5] transition">닫기</button>
        </div>
      </div>
    </div>
  );
}

function NewTemplateModal({ open, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [accountsText, setAccountsText] = useState("");
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const accounts = accountsText.split(/\r?\n/).map((l) => {
    const [nm, tc] = l.split(/\t|,/).map((s) => s.trim());
    return nm ? { name: nm, task_count: parseInt(tc) || 0 } : null;
  }).filter(Boolean);

  const submit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const created = await api.createTemplate({ name: name.trim(), industry: industry.trim(), accounts });
      onCreated(created);
      onClose();
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative bg-white rounded-xl border border-line shadow-xl w-full max-w-lg overflow-hidden">
        <div className="flex items-center justify-between px-6 pt-6 pb-2">
          <h3 className="text-base font-semibold text-ink">새 템플릿</h3>
          <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
            <Icon name="close" className="text-[18px]" />
          </button>
        </div>
        <div className="px-6 py-4 flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs text-sub mb-1.5 block">템플릿명 *</span>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                placeholder="예: 제조업 기본"
                className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
            </label>
            <label className="block">
              <span className="text-xs text-sub mb-1.5 block">업종</span>
              <input type="text" value={industry} onChange={(e) => setIndustry(e.target.value)}
                placeholder="예: 제조업"
                className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
            </label>
          </div>
          <label className="block">
            <span className="text-xs text-sub mb-1.5 block">계정과목 <span className="text-faint">(계정명,할일수 — 한 줄에 하나)</span></span>
            <textarea value={accountsText} onChange={(e) => setAccountsText(e.target.value)} rows="6" autoFocus
              placeholder={"매출채권,4\n재고자산,4\n유형자산,3"}
              className="w-full px-3 py-2.5 rounded-lg bg-[#fafafa] text-[13px] text-ink font-mono leading-relaxed resize-none focus:bg-white transition" />
            <p className="mt-1 text-[11px] text-faint">{accounts.length}개 계정과목</p>
          </label>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-line">
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-[13px] font-medium text-sub hover:bg-[#f4f4f5] transition">취소</button>
          <button onClick={submit} disabled={saving || !name.trim()}
            className="px-3.5 py-1.5 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition disabled:opacity-40"
            style={{ background: "var(--lnac)" }}>
            {saving ? "생성 중…" : "생성"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function Templates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);
  const [newOpen, setNewOpen] = useState(false);

  useEffect(() => {
    api.getTemplates().then(setTemplates).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const del = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("템플릿을 삭제하시겠습니까?")) return;
    await api.deleteTemplate(id);
    setTemplates((ts) => ts.filter((t) => t.id !== id));
  };

  if (loading) return <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>;

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-ink">템플릿</h2>
          <p className="mt-1 text-sm text-sub">업종별 감사 템플릿으로 빠르게 시작</p>
        </div>
        <button onClick={() => setNewOpen(true)}
          className="px-3 py-1.5 text-white text-[13px] font-medium rounded-lg hover:opacity-90 transition flex items-center gap-1"
          style={{ background: "var(--lnac)" }}>
          <Icon name="add" className="text-[16px]" style={{ fontVariationSettings: '"wght" 400' }} />
          새 템플릿
        </button>
      </div>

      {templates.length === 0 ? (
        <div className="text-center py-16">
          <Icon name="description" className="text-[48px] text-line2" />
          <p className="mt-3 text-sm text-sub">템플릿이 없습니다</p>
          <button onClick={() => setNewOpen(true)}
            className="mt-4 px-4 py-2 rounded-lg text-sm font-medium text-white hover:opacity-90 transition"
            style={{ background: "var(--lnac)" }}>
            첫 번째 템플릿 만들기
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {templates.map((t) => {
            const totalTasks = (t.accounts || []).reduce((a, x) => a + (x.task_count || 0), 0);
            return (
              <div key={t.id} onClick={() => setDetail(t)}
                className="bg-white rounded-lg border border-line p-6 hover:border-line2 transition cursor-pointer group relative">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-medium text-sub px-2 py-0.5 rounded-full bg-[#f4f4f5]">{t.industry || "기타"}</span>
                  <div className="flex items-center gap-1">
                    <button onClick={(e) => del(e, t.id)}
                      className="opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center rounded text-faint hover:text-[#ef4444] hover:bg-[#f4f4f5] transition">
                      <Icon name="delete" className="text-[15px]" />
                    </button>
                    <Icon name="arrow_outward" className="text-[18px] text-line2 group-hover:text-faint transition" />
                  </div>
                </div>
                <h3 className="mt-4 text-[15px] font-semibold text-ink">{t.name}</h3>
                <div className="mt-5 pt-4 border-t border-line flex items-center gap-5">
                  <span className="text-xs text-sub">계정과목 <span className="text-ink font-medium tabular-nums">{(t.accounts || []).length}</span></span>
                  <span className="text-xs text-sub">할일 <span className="text-ink font-medium tabular-nums">{totalTasks}</span></span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <TemplateModal tpl={detail} onClose={() => setDetail(null)} />
      <NewTemplateModal open={newOpen} onClose={() => setNewOpen(false)}
        onCreated={(t) => setTemplates((ts) => [...ts, t])} />
    </div>
  );
}
