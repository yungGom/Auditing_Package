import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useSettings } from "../contexts/SettingsContext";

// ---------------------------------------------------------------------------
// Status badge map (for task results)
// ---------------------------------------------------------------------------

const STATUS_MAP = {
  todo: { label: "미착수", bg: "bg-outline-variant/30", text: "text-on-surface-variant" },
  in_progress: { label: "진행중", bg: "bg-primary-fixed", text: "text-primary" },
  review: { label: "검토대기", bg: "bg-on-tertiary-container/10", text: "text-on-tertiary-container" },
  done: { label: "완료", bg: "bg-secondary-container", text: "text-on-secondary-container" },
};

// ---------------------------------------------------------------------------
// Search Dropdown
// ---------------------------------------------------------------------------

function SearchDropdown({ query, results, loading, onSelect, onClose, activeIdx, setActiveIdx, listRef }) {
  const hasClients = results?.clients?.length > 0;
  const hasAccounts = results?.accounts?.length > 0;
  const hasTasks = results?.tasks?.length > 0;
  const hasResults = hasClients || hasAccounts || hasTasks;

  // Build flat list for keyboard navigation
  const flatItems = [];
  if (hasClients) results.clients.forEach((c) => flatItems.push({ type: "client", data: c }));
  if (hasAccounts) results.accounts.forEach((a) => flatItems.push({ type: "account", data: a }));
  if (hasTasks) results.tasks.forEach((t) => flatItems.push({ type: "task", data: t }));

  // Expose flatItems length to parent
  useEffect(() => {
    if (listRef) listRef.current = flatItems;
  });

  if (!query) return null;

  return (
    <div className="absolute top-full left-0 right-0 mt-1.5 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-2xl max-h-[420px] overflow-y-auto z-50">
      {loading && (
        <div className="px-4 py-3 text-xs text-outline font-label flex items-center gap-2">
          <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
          검색중...
        </div>
      )}

      {!loading && !hasResults && (
        <div className="px-4 py-6 text-center">
          <span className="material-symbols-outlined text-3xl text-outline-variant block mb-2">search_off</span>
          <p className="text-sm text-on-surface-variant font-body">검색 결과가 없습니다</p>
        </div>
      )}

      {!loading && hasResults && (
        <div className="py-1.5">
          {/* Clients */}
          {hasClients && (
            <div>
              <div className="px-4 py-1.5 text-[10px] font-label font-bold text-outline uppercase tracking-wider">클라이언트</div>
              {results.clients.map((c, i) => {
                const flatIdx = i;
                return (
                  <button key={`c-${c.id}`}
                    onClick={() => onSelect("client", c)}
                    onMouseEnter={() => setActiveIdx(flatIdx)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition ${activeIdx === flatIdx ? "bg-primary-fixed/50" : "hover:bg-surface-container"}`}>
                    <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-primary text-[16px]">business</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-label font-semibold text-on-surface truncate">{highlightMatch(c.name, query)}</p>
                      <p className="text-[11px] text-on-surface-variant font-body truncate">{c.path}</p>
                    </div>
                    {c.industry && <span className="text-[10px] font-label text-outline bg-surface-container px-2 py-0.5 rounded-lg shrink-0">{c.industry}</span>}
                  </button>
                );
              })}
            </div>
          )}

          {/* Accounts */}
          {hasAccounts && (
            <div>
              {hasClients && <div className="my-1 border-t border-outline-variant/50" />}
              <div className="px-4 py-1.5 text-[10px] font-label font-bold text-outline uppercase tracking-wider">계정과목</div>
              {results.accounts.map((a, i) => {
                const flatIdx = (results.clients?.length || 0) + i;
                return (
                  <button key={`a-${a.account_id}`}
                    onClick={() => onSelect("account", a)}
                    onMouseEnter={() => setActiveIdx(flatIdx)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition ${activeIdx === flatIdx ? "bg-primary-fixed/50" : "hover:bg-surface-container"}`}>
                    <div className="w-8 h-8 rounded-xl bg-on-tertiary-container/10 flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-on-tertiary-container text-[16px]">account_balance</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-label font-semibold text-on-surface truncate">{highlightMatch(a.title, query)}</p>
                      <p className="text-[11px] text-on-surface-variant font-body truncate">{a.path}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Tasks */}
          {hasTasks && (
            <div>
              {(hasClients || hasAccounts) && <div className="my-1 border-t border-outline-variant/50" />}
              <div className="px-4 py-1.5 text-[10px] font-label font-bold text-outline uppercase tracking-wider">할일</div>
              {results.tasks.map((t, i) => {
                const flatIdx = (results.clients?.length || 0) + (results.accounts?.length || 0) + i;
                const st = STATUS_MAP[t.status] || STATUS_MAP.todo;
                return (
                  <button key={`t-${t.id}`}
                    onClick={() => onSelect("task", t)}
                    onMouseEnter={() => setActiveIdx(flatIdx)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition ${activeIdx === flatIdx ? "bg-primary-fixed/50" : "hover:bg-surface-container"}`}>
                    <div className="w-8 h-8 rounded-xl bg-secondary-container/50 flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-on-secondary-container text-[16px]">task_alt</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-label font-semibold text-on-surface truncate">{highlightMatch(t.title, query)}</p>
                        <span className={`inline-flex px-1.5 py-0.5 rounded-lg text-[10px] font-label font-bold ${st.bg} ${st.text} shrink-0`}>{st.label}</span>
                      </div>
                      <p className="text-[11px] text-on-surface-variant font-body truncate">{t.path}</p>
                    </div>
                    {t.assignee && <span className="text-[11px] font-label text-on-surface-variant shrink-0">{t.assignee}</span>}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Footer hint */}
      <div className="px-4 py-2 border-t border-outline-variant/50 flex items-center gap-3 text-[10px] text-outline font-label">
        <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-surface-container border border-outline-variant text-[9px]">↑↓</kbd> 이동</span>
        <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-surface-container border border-outline-variant text-[9px]">Enter</kbd> 선택</span>
        <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-surface-container border border-outline-variant text-[9px]">Esc</kbd> 닫기</span>
      </div>
    </div>
  );
}

function highlightMatch(text, query) {
  if (!query || !text) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-primary-fixed text-primary font-bold rounded-sm px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

// ---------------------------------------------------------------------------
// Notification Dropdown
// ---------------------------------------------------------------------------

function NotificationDropdown({ data, onSelect, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  const sections = [
    { key: "overdue", label: "기한 초과", icon: "error", items: data?.overdue || [], danger: true },
    { key: "due_today", label: "오늘 마감", icon: "today", items: data?.due_today || [], danger: false },
    { key: "due_week", label: "이번 주 마감 (7일 이내)", icon: "date_range", items: data?.due_week || [], danger: false },
    { key: "review", label: "검토 대기", icon: "rate_review", items: data?.review || [], danger: false },
  ];

  const hasSome = sections.some((s) => s.items.length > 0);

  return (
    <div ref={ref} className="absolute top-full right-0 mt-1.5 w-[380px] bg-surface-container-lowest rounded-xl border border-outline-variant shadow-2xl max-h-[480px] overflow-y-auto z-50">
      <div className="px-4 py-3 border-b border-outline-variant flex items-center gap-2">
        <span className="material-symbols-outlined text-primary text-lg">notifications</span>
        <span className="text-sm font-headline font-bold text-on-surface">알림</span>
        <span className="text-[11px] font-label text-outline ml-auto">{data?.total_count || 0}건</span>
      </div>

      {!hasSome && (
        <div className="px-4 py-8 text-center">
          <span className="material-symbols-outlined text-3xl text-outline-variant block mb-2">notifications_off</span>
          <p className="text-sm text-on-surface-variant font-body">알림이 없습니다</p>
        </div>
      )}

      {sections.map((section) => {
        if (!section.items.length) return null;
        return (
          <div key={section.key}>
            <div className="px-4 py-2 text-[10px] font-label font-bold text-outline uppercase tracking-wider flex items-center gap-1.5 bg-surface-container-low/50">
              <span className={`material-symbols-outlined text-[14px] ${section.danger ? "text-error" : "text-on-surface-variant"}`}>{section.icon}</span>
              {section.label}
              <span className={`ml-auto px-1.5 py-0.5 rounded-lg text-[10px] font-bold ${section.danger ? "bg-error/10 text-error" : "bg-primary-fixed text-primary"}`}>{section.items.length}</span>
            </div>
            {section.items.map((item) => (
              <button key={item.id}
                onClick={() => { onSelect(item); onClose(); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-surface-container transition">
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-label font-semibold truncate ${section.danger ? "text-error" : "text-on-surface"}`}>{item.title}</p>
                  <p className="text-[11px] text-on-surface-variant font-body truncate">{item.client_name}</p>
                </div>
                <div className="text-right shrink-0">
                  {item.due_date && <DdayBadge dueDate={item.due_date} />}
                  <p className="text-[10px] text-outline font-label mt-0.5">{item.due_date}</p>
                </div>
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}

function DdayBadge({ dueDate }) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDate);
  due.setHours(0, 0, 0, 0);
  const diff = Math.round((due - today) / (1000 * 60 * 60 * 24));
  const label = diff === 0 ? "D-Day" : diff < 0 ? `D+${-diff}` : `D-${diff}`;
  const isOverdue = diff < 0;
  const isToday = diff === 0;
  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded-lg text-[10px] font-label font-bold border ${
      isOverdue ? "bg-error/10 text-error border-error/20" : isToday ? "bg-on-tertiary-container/10 text-on-tertiary-container border-on-tertiary-container/20" : "bg-primary-fixed text-primary border-primary/20"
    }`}>{label}</span>
  );
}

// ---------------------------------------------------------------------------
// Startup Alert Modal
// ---------------------------------------------------------------------------

function StartupAlert({ data, onItemClick, onClose }) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || !data) return null;

  const overdueCount = data.overdue?.length || 0;
  const todayCount = data.due_today?.length || 0;
  const weekCount = data.due_week?.length || 0;
  const total = overdueCount + todayCount + weekCount;

  if (total === 0) return null;

  // Check sessionStorage for "don't show today"
  const todayKey = `alert-dismissed-${new Date().toISOString().slice(0, 10)}`;
  if (typeof sessionStorage !== "undefined" && sessionStorage.getItem(todayKey)) return null;

  const handleDismissToday = () => {
    if (typeof sessionStorage !== "undefined") sessionStorage.setItem(todayKey, "1");
    setDismissed(true);
    onClose();
  };

  const allItems = [
    ...(data.overdue || []).map((t) => ({ ...t, _group: "overdue" })),
    ...(data.due_today || []).map((t) => ({ ...t, _group: "today" })),
    ...(data.due_week || []).slice(0, 5).map((t) => ({ ...t, _group: "week" })),
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => { setDismissed(true); onClose(); }} />
      <div className="relative bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-md flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-outline-variant">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-on-tertiary-container/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-on-tertiary-container text-xl">notifications_active</span>
            </div>
            <div>
              <h3 className="font-headline text-base font-bold text-on-surface">오늘의 알림</h3>
              <p className="text-[11px] text-on-surface-variant font-label">{new Date().toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" })}</p>
            </div>
          </div>
          <button onClick={() => { setDismissed(true); onClose(); }} className="w-8 h-8 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-on-surface-variant text-lg">close</span>
          </button>
        </div>

        {/* Summary */}
        <div className="px-5 py-4 flex gap-3">
          {overdueCount > 0 && (
            <div className="flex-1 p-3 rounded-xl bg-error/5 border border-error/10 text-center">
              <p className="text-lg font-headline font-bold text-error">{overdueCount}</p>
              <p className="text-[10px] font-label text-error/80">기한 초과</p>
            </div>
          )}
          {todayCount > 0 && (
            <div className="flex-1 p-3 rounded-xl bg-on-tertiary-container/5 border border-on-tertiary-container/10 text-center">
              <p className="text-lg font-headline font-bold text-on-tertiary-container">{todayCount}</p>
              <p className="text-[10px] font-label text-on-tertiary-container/80">오늘 마감</p>
            </div>
          )}
          {weekCount > 0 && (
            <div className="flex-1 p-3 rounded-xl bg-primary-fixed border border-primary/10 text-center">
              <p className="text-lg font-headline font-bold text-primary">{weekCount}</p>
              <p className="text-[10px] font-label text-primary/80">이번 주 마감</p>
            </div>
          )}
        </div>

        {/* Items */}
        <div className="px-5 pb-2 max-h-48 overflow-y-auto space-y-1.5">
          {allItems.map((item) => (
            <button key={item.id} onClick={() => { onItemClick(item); setDismissed(true); onClose(); }}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left hover:bg-surface-container transition">
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-label font-semibold truncate ${item._group === "overdue" ? "text-error" : "text-on-surface"}`}>{item.title}</p>
                <p className="text-[10px] text-on-surface-variant font-body">{item.client_name}</p>
              </div>
              {item.due_date && <DdayBadge dueDate={item.due_date} />}
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-outline-variant">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" onChange={(e) => { if (e.target.checked) handleDismissToday(); }}
              className="w-3.5 h-3.5 rounded border-outline-variant text-primary focus:ring-primary" />
            <span className="text-[11px] font-label text-on-surface-variant">오늘은 그만 보기</span>
          </label>
          <button onClick={() => { setDismissed(true); onClose(); }}
            className="px-3 py-1.5 rounded-xl text-xs font-label font-semibold text-primary hover:bg-primary-fixed transition">
            확인
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// New Engagement Modal
// ---------------------------------------------------------------------------

function NewEngagementModal({ open, onClose }) {
  const navigate = useNavigate();
  const [fiscalYears, setFiscalYears] = useState([]);
  const [loadingFY, setLoadingFY] = useState(false);
  const [form, setForm] = useState({
    fy_id: "",
    name: "",
    industry: "",
    report_date: "",
    submit_date: "",
  });

  useEffect(() => {
    if (!open) return;
    setLoadingFY(true);
    api.getFiscalYears().then((fys) => {
      setFiscalYears(fys);
      // Prefer is_active FY, otherwise first
      const activeFY = fys.find((f) => f.is_active) || fys[0];
      if (activeFY) setForm((f) => ({ ...f, fy_id: String(activeFY.id) }));
    }).catch(() => {
      setFiscalYears([]);
    }).finally(() => setLoadingFY(false));
  }, [open]);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    if (!form.fy_id) {
      alert("회계연도를 선택해주세요.");
      return;
    }
    try {
      const client = await api.createClient({
        fy_id: Number(form.fy_id),
        name: form.name.trim(),
        industry: form.industry.trim(),
        report_date: form.report_date || null,
      });
      await api.createPhase({ client_id: client.id, name: "기중감사", sort_order: 0 });
      await api.createPhase({ client_id: client.id, name: "기말감사", sort_order: 1 });
      onClose();
      // Force tree reload by navigating with a timestamp param
      navigate(`/engagements?reload=${Date.now()}`);
    } catch (err) {
      console.error("감사업무 생성 실패:", err);
      alert("생성에 실패했습니다. 콘솔을 확인해주세요.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <form onSubmit={handleSubmit} className="relative bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-lg flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-outline-variant">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-xl">add_business</span>
            </div>
            <h3 className="font-headline text-lg font-bold text-on-surface">새 감사업무</h3>
          </div>
          <button type="button" onClick={onClose} className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>
        <div className="p-6 space-y-4">
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">회계연도 (FY) *</span>
            {fiscalYears.length === 0 && !loadingFY ? (
              <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-on-tertiary-container/30 bg-on-tertiary-container/5 text-xs font-label text-on-tertiary-container">
                <span className="material-symbols-outlined text-[16px]">info</span>
                먼저 설정에서 회계연도를 추가하세요
              </div>
            ) : (
              <select value={form.fy_id} onChange={(e) => setForm({ ...form, fy_id: e.target.value })}
                required
                className="appearance-none w-full pl-3 pr-8 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface cursor-pointer focus:border-primary focus:outline-none transition">
                {!form.fy_id && <option value="">선택하세요</option>}
                {fiscalYears.map((fy) => (
                  <option key={fy.id} value={fy.id}>
                    {fy.name}{fy.is_active ? " (활성)" : ""}
                  </option>
                ))}
              </select>
            )}
          </label>
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">클라이언트명 *</span>
            <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="예: 한빛제조" className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
          </label>
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">업종</span>
            <input type="text" value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })}
              placeholder="예: 제조업, IT서비스, 유통업" className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
          </label>
          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">결산일</span>
              <input type="date" value={form.report_date} onChange={(e) => setForm({ ...form, report_date: e.target.value })}
                className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
            </label>
            <label className="block">
              <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">감사보고서 제출일</span>
              <input type="date" value={form.submit_date} onChange={(e) => setForm({ ...form, submit_date: e.target.value })}
                className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
            </label>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 p-6 border-t border-outline-variant">
          <button type="button" onClick={onClose} className="px-4 py-2.5 rounded-xl border border-outline-variant text-sm font-label font-semibold text-on-surface-variant hover:bg-surface-container transition">취소</button>
          <button type="submit" className="px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-label font-semibold hover:opacity-90 transition flex items-center gap-2">
            <span className="material-symbols-outlined text-base">check</span>생성
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Header
// ---------------------------------------------------------------------------

export default function Header({ onMenuToggle }) {
  const navigate = useNavigate();
  const { settings } = useSettings();
  const [modalOpen, setModalOpen] = useState(false);

  // Search state
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const inputRef = useRef(null);
  const wrapperRef = useRef(null);
  const debounceRef = useRef(null);
  const flatItemsRef = useRef([]);

  // Notification state
  const [notifData, setNotifData] = useState(null);
  const [showNotif, setShowNotif] = useState(false);
  const [showStartupAlert, setShowStartupAlert] = useState(false);
  const notifWrapperRef = useRef(null);

  // Load notifications on mount + refresh on window focus
  useEffect(() => {
    const load = () => api.getNotifications().then((data) => {
      setNotifData(data);
      if (data.total_count > 0 && !sessionStorage.getItem("startup-alert-shown")) {
        setShowStartupAlert(true);
        sessionStorage.setItem("startup-alert-shown", "1");
      }
    }).catch(() => {});
    load();
    const onFocus = () => load();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const notifCount = notifData?.total_count || 0;

  const navigateToTask = (item) => {
    navigate(`/engagements?select=${item.node_id}&highlight=${item.id}`);
  };

  // Debounced search
  const doSearch = useCallback((q) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q.trim()) {
      setResults(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(() => {
      api.search(q.trim()).then((r) => {
        setResults(r);
        setActiveIdx(-1);
      }).catch(() => {
        setResults({ clients: [], accounts: [], tasks: [] });
      }).finally(() => setLoading(false));
    }, 300);
  }, []);

  const handleChange = (e) => {
    const v = e.target.value;
    setQuery(v);
    setShowDropdown(true);
    doSearch(v);
  };

  // Handle selection
  const handleSelect = (type, item) => {
    setShowDropdown(false);
    setQuery("");
    setResults(null);

    if (type === "client") {
      // Navigate to engagements with client expanded
      navigate(`/engagements?select=${item.node_id}`);
    } else if (type === "account") {
      navigate(`/engagements?select=${item.node_id}`);
    } else if (type === "task") {
      // Navigate to engagements, select the account, highlight the task
      navigate(`/engagements?select=${item.node_id}&highlight=${item.id}`);
    }
  };

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (!showDropdown || !flatItemsRef.current.length) {
      if (e.key === "Escape") {
        setShowDropdown(false);
        inputRef.current?.blur();
      }
      return;
    }
    const total = flatItemsRef.current.length;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((prev) => (prev + 1) % total);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((prev) => (prev - 1 + total) % total);
    } else if (e.key === "Enter" && activeIdx >= 0 && activeIdx < total) {
      e.preventDefault();
      const item = flatItemsRef.current[activeIdx];
      handleSelect(item.type, item.data);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  };

  // Global keyboard shortcut: Ctrl+K / Ctrl+F
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "f")) {
        e.preventDefault();
        inputRef.current?.focus();
        setShowDropdown(true);
      }
    };
    document.addEventListener("keydown", handler);
    return () => { document.removeEventListener("keydown", handler); if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, []);

  // Click outside to close
  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-20 h-14 bg-surface-container-lowest/80 backdrop-blur-md border-b border-outline-variant flex items-center justify-between px-4 lg:px-6">
        {/* Left: hamburger + search */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <button onClick={onMenuToggle} className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition lg:hidden">
            <span className="material-symbols-outlined text-[22px]">menu</span>
          </button>

          {/* Search wrapper */}
          <div ref={wrapperRef} className="relative w-48 sm:w-64 lg:w-96">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px] pointer-events-none">search</span>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={handleChange}
              onFocus={() => { if (query) setShowDropdown(true); }}
              onKeyDown={handleKeyDown}
              placeholder="검색... (Ctrl+K)"
              className="w-full pl-10 pr-4 py-2 text-sm font-body bg-surface-container rounded-xl border border-outline-variant placeholder:text-outline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition"
            />

            {showDropdown && (
              <SearchDropdown
                query={query}
                results={results}
                loading={loading}
                onSelect={handleSelect}
                onClose={() => setShowDropdown(false)}
                activeIdx={activeIdx}
                setActiveIdx={setActiveIdx}
                listRef={flatItemsRef}
              />
            )}
          </div>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          {/* Notifications bell */}
          <div ref={notifWrapperRef} className="relative">
            <button onClick={() => setShowNotif((v) => !v)}
              className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition relative">
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              {notifCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 rounded-full bg-error text-white text-[10px] font-label font-bold">
                  {notifCount > 99 ? "99+" : notifCount}
                </span>
              )}
            </button>
            {showNotif && notifData && (
              <NotificationDropdown data={notifData} onSelect={navigateToTask} onClose={() => setShowNotif(false)} />
            )}
          </div>

          <button onClick={() => alert("AuditLink v0.1.0\n회계감사 일정관리 데스크톱 앱\n\n단축키:\n• Ctrl+K: 검색\n• ESC: 모달/패널 닫기")}
            className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition hidden sm:flex" title="도움말">
            <span className="material-symbols-outlined text-[20px]">help</span>
          </button>
          <button onClick={() => setModalOpen(true)}
            className="ml-1 sm:ml-2 px-3 sm:px-4 py-2 bg-gradient-to-r from-primary to-primary-container text-white text-xs sm:text-sm font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[18px]">add</span>
            <span className="hidden sm:inline">새 감사업무</span>
          </button>
          <div className="ml-1 sm:ml-2 w-8 h-8 rounded-full bg-primary-container flex items-center justify-center" title={settings.userName || "사용자"}>
            <span className="text-xs font-label font-bold text-white">
              {(settings.userName || "감")[0]}
            </span>
          </div>
        </div>
      </header>

      <NewEngagementModal open={modalOpen} onClose={() => setModalOpen(false)} />

      {showStartupAlert && (
        <StartupAlert data={notifData} onItemClick={navigateToTask} onClose={() => setShowStartupAlert(false)} />
      )}
    </>
  );
}
