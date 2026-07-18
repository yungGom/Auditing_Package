import { useState, useEffect } from "react";
import { api } from "../api.js";
import { Icon, Spinner } from "../components/Tokens.jsx";

function Section({ title, subtitle, children }) {
  return (
    <section className="bg-white rounded-lg border border-line p-6">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-0.5 text-xs text-faint">{subtitle}</p>
      <div className="mt-5">{children}</div>
    </section>
  );
}

const INPUT = "w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink";

function FYSection({ fys, onFysChange }) {
  const [newFyOpen, setNewFyOpen] = useState(false);
  const [form, setForm] = useState({ label: "", start_date: "", end_date: "" });
  const [saving, setSaving] = useState(false);

  const activate = async (id) => {
    const updated = await api.updateFY(id, { is_active: true });
    onFysChange((fs) => fs.map((f) => f.id === updated.id ? updated : { ...f, is_active: false }));
  };

  const del = async (id) => {
    if (!window.confirm("회계연도를 삭제하시겠습니까?")) return;
    await api.deleteFY(id);
    onFysChange((fs) => fs.filter((f) => f.id !== id));
  };

  const createFY = async () => {
    if (!form.label.trim()) return;
    setSaving(true);
    try {
      const created = await api.createFY(form);
      onFysChange((fs) => created.is_active ? [...fs.map((f) => ({ ...f, is_active: false })), created] : [...fs, created]);
      setNewFyOpen(false);
      setForm({ label: "", start_date: "", end_date: "" });
    } finally { setSaving(false); }
  };

  return (
    <Section title="회계연도" subtitle="활성 회계연도는 트리와 대시보드에 표시됩니다">
      <div className="flex flex-col">
        {fys.length === 0 && <p className="text-xs text-faint py-4 text-center">회계연도가 없습니다</p>}
        {fys.map((fy) => (
          <div key={fy.id} className="flex items-center gap-3 py-3 border-b border-line/70 last:border-b-0">
            <Icon name="date_range" className="text-[20px] text-faint" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium text-ink">{fy.label}</span>
                {fy.is_active && (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
                    style={{ background: "color-mix(in srgb, var(--lnac) 10%, transparent)", color: "var(--lnac)" }}>활성</span>
                )}
              </div>
              <p className="text-[11px] text-faint">{fy.start_date} ~ {fy.end_date}</p>
            </div>
            <div className="flex items-center gap-1">
              {!fy.is_active && (
                <button onClick={() => activate(fy.id)}
                  className="px-2.5 py-1 rounded-lg text-[11px] font-medium text-sub hover:bg-[#f4f4f5] transition">활성화</button>
              )}
              {!fy.is_active && (
                <button onClick={() => del(fy.id)}
                  className="w-6 h-6 flex items-center justify-center rounded text-faint hover:text-[#ef4444] hover:bg-[#f4f4f5] transition">
                  <Icon name="delete" className="text-[15px]" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {newFyOpen ? (
        <div className="mt-4 p-4 bg-[#fafafa] rounded-lg border border-line flex flex-col gap-3">
          <input placeholder="회계연도명 * (예: FY2026)" value={form.label} onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
            className={`${INPUT} bg-white`} />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] text-faint block mb-1">시작일</label>
              <input type="date" value={form.start_date} onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                className={`${INPUT} bg-white`} />
            </div>
            <div>
              <label className="text-[11px] text-faint block mb-1">종료일</label>
              <input type="date" value={form.end_date} onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                className={`${INPUT} bg-white`} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setNewFyOpen(false)} className="px-3 py-1.5 text-xs text-sub hover:bg-[#f0f0f0] rounded-lg transition">취소</button>
            <button onClick={createFY} disabled={saving || !form.label.trim()}
              className="px-3.5 py-1.5 rounded-lg text-white text-xs font-medium hover:opacity-90 transition disabled:opacity-40"
              style={{ background: "var(--lnac)" }}>
              {saving ? "생성 중…" : "생성"}
            </button>
          </div>
        </div>
      ) : (
        <button onClick={() => setNewFyOpen(true)}
          className="mt-4 w-full py-2 rounded-lg border border-dashed border-line2 text-xs font-medium text-faint hover:text-sub hover:bg-[#fafafa] transition flex items-center justify-center gap-1">
          <Icon name="add" className="text-[16px]" />새 회계연도
        </button>
      )}
    </Section>
  );
}

function UserSection({ settings, onSaved }) {
  const [form, setForm] = useState({ user_name: "", org: "", email: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) setForm({ user_name: settings.user_name || "", org: settings.org || "", email: settings.email || "" });
  }, [settings]);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.updateSettings(form);
      onSaved(updated);
    } finally { setSaving(false); }
  };

  return (
    <Section title="사용자 정보" subtitle="보고서와 할일 담당자에 사용됩니다">
      <div className="flex flex-col gap-4">
        <label className="block">
          <span className="text-xs text-sub mb-1.5 block">이름</span>
          <input type="text" value={form.user_name} onChange={(e) => setForm((f) => ({ ...f, user_name: e.target.value }))} className={INPUT} />
        </label>
        <label className="block">
          <span className="text-xs text-sub mb-1.5 block">소속</span>
          <input type="text" value={form.org} onChange={(e) => setForm((f) => ({ ...f, org: e.target.value }))} className={INPUT} />
        </label>
        <label className="block">
          <span className="text-xs text-sub mb-1.5 block">이메일</span>
          <input type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} className={INPUT} />
        </label>
        <div className="flex justify-end">
          <button onClick={save} disabled={saving}
            className="px-3.5 py-1.5 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition disabled:opacity-40"
            style={{ background: "var(--lnac)" }}>
            {saving ? "저장 중…" : "저장"}
          </button>
        </div>
      </div>
    </Section>
  );
}

function AlertSection({ settings, onSaved }) {
  const [threshold, setThreshold] = useState("D-7");
  const [startup, setStartup] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setThreshold(settings.deadline_threshold || "D-7");
      setStartup(settings.startup_alert !== false);
    }
  }, [settings]);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.updateSettings({ deadline_threshold: threshold, startup_alert: startup });
      onSaved(updated);
    } finally { setSaving(false); }
  };

  return (
    <Section title="마감 알림" subtitle="시작 시 오늘의 알림에 표시할 기준">
      <div className="flex flex-col">
        <div className="flex items-center justify-between py-3 border-b border-line/70">
          <span className="text-[13px] text-ink">마감 임박 기준</span>
          <select value={threshold} onChange={(e) => setThreshold(e.target.value)}
            className="pl-2.5 pr-7 py-1.5 rounded-lg bg-white text-xs text-sub focus:ring-0">
            <option>D-3 이내</option>
            <option>D-7 이내</option>
            <option>D-14 이내</option>
          </select>
        </div>
        <div className="flex items-center justify-between py-3">
          <span className="text-[13px] text-ink">시작 시 오늘의 알림 표시</span>
          <button onClick={() => setStartup((o) => !o)}
            className={`w-10 h-5 rounded-full transition-colors ${startup ? "bg-[color:var(--lnac)]" : "bg-line2"}`}
            style={{ position: "relative" }}>
            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${startup ? "translate-x-5" : "translate-x-0.5"}`} />
          </button>
        </div>
      </div>
      <div className="flex justify-end mt-4">
        <button onClick={save} disabled={saving}
          className="px-3.5 py-1.5 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition disabled:opacity-40"
          style={{ background: "var(--lnac)" }}>
          {saving ? "저장 중…" : "저장"}
        </button>
      </div>
    </Section>
  );
}

export function Settings({ onSettingsChange }) {
  const [fys, setFys] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getFYs(), api.getSettings()])
      .then(([fs, s]) => { setFys(fs); setSettings(s); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const onSettingsSaved = (s) => {
    setSettings(s);
    onSettingsChange?.(s);
  };

  if (loading) return <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-ink">설정</h2>
        <p className="mt-1 text-sm text-sub">회계연도, 사용자 정보, 알림</p>
      </div>
      <div className="grid grid-cols-2 gap-4 max-w-4xl">
        <FYSection fys={fys} onFysChange={setFys} />
        <UserSection settings={settings} onSaved={onSettingsSaved} />
        <AlertSection settings={settings} onSaved={onSettingsSaved} />
      </div>
    </div>
  );
}
