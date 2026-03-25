import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

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
// New Engagement Modal (unchanged)
// ---------------------------------------------------------------------------

function NewEngagementModal({ open, onClose }) {
  const navigate = useNavigate();
  const [fiscalYears, setFiscalYears] = useState([]);
  const [form, setForm] = useState({
    fy_id: "",
    name: "",
    industry: "",
    report_date: "",
    submit_date: "",
  });

  useEffect(() => {
    if (!open) return;
    api.getFiscalYears().then((fys) => {
      setFiscalYears(fys);
      if (fys.length) setForm((f) => ({ ...f, fy_id: String(fys[0].id) }));
    }).catch(() => {});
  }, [open]);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
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
      navigate("/engagements");
    } catch {
      alert("생성에 실패했습니다.");
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
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">회계연도 (FY)</span>
            <select value={form.fy_id} onChange={(e) => setForm({ ...form, fy_id: e.target.value })}
              className="appearance-none w-full pl-3 pr-8 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface cursor-pointer focus:border-primary focus:outline-none transition">
              {fiscalYears.map((fy) => <option key={fy.id} value={fy.id}>{fy.name}</option>)}
            </select>
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
    return () => document.removeEventListener("keydown", handler);
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
          <button className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition hidden sm:flex">
            <span className="material-symbols-outlined text-[20px]">notifications</span>
          </button>
          <button className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition hidden sm:flex">
            <span className="material-symbols-outlined text-[20px]">help</span>
          </button>
          <button onClick={() => setModalOpen(true)}
            className="ml-1 sm:ml-2 px-3 sm:px-4 py-2 bg-gradient-to-r from-primary to-primary-container text-white text-xs sm:text-sm font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[18px]">add</span>
            <span className="hidden sm:inline">새 감사업무</span>
          </button>
          <div className="ml-1 sm:ml-2 w-8 h-8 rounded-full bg-primary-container flex items-center justify-center">
            <span className="text-xs font-label font-bold text-white">감</span>
          </div>
        </div>
      </header>

      <NewEngagementModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </>
  );
}
