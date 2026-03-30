// ---------------------------------------------------------------------------
// Dashboard – 대시보드 메인 페이지 (실데이터 연동)
// ---------------------------------------------------------------------------
import { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

const CLIENT_COLORS = ["bg-primary", "bg-secondary", "bg-on-tertiary-container", "bg-primary-container"];

const STATUS_MAP = {
  todo: { label: "미착수", bg: "bg-outline-variant/30", text: "text-on-surface-variant" },
  in_progress: { label: "진행중", bg: "bg-primary-fixed", text: "text-primary" },
  review: { label: "검토대기", bg: "bg-on-tertiary-container/10", text: "text-on-tertiary-container" },
  done: { label: "완료", bg: "bg-secondary-container", text: "text-on-secondary-container" },
};
const STATUS_ORDER = ["todo", "in_progress", "review", "done"];

// --- Helpers ----------------------------------------------------------------

function calcDDay(dateStr) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const due = new Date(dateStr); due.setHours(0, 0, 0, 0);
  return Math.round((due - today) / 86400000);
}

function dDayLabel(d) {
  if (d === 0) return "D-Day";
  if (d < 0) return `D+${-d}`;
  return `D-${d}`;
}

function dDayBadge(d) {
  if (d <= 0) return { bg: "bg-error/10", text: "text-error", border: "border-error/30" };
  if (d <= 7) return { bg: "bg-error/10", text: "text-error", border: "border-error/30" };
  if (d <= 15) return { bg: "bg-on-tertiary-container/10", text: "text-on-tertiary-container", border: "border-on-tertiary-container/30" };
  return { bg: "bg-secondary/10", text: "text-secondary", border: "border-secondary/30" };
}

// --- Sub-components ---------------------------------------------------------

function CircularProgress({ value, size = 120, strokeWidth = 10 }) {
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (value / 100) * circumference;
  return (
    <svg width={size} height={size} className="block">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e1e3e4" strokeWidth={strokeWidth} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#001e40" strokeWidth={strokeWidth}
        strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`} className="transition-all duration-700" />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" className="fill-on-surface font-headline text-2xl font-bold">{value}%</text>
    </svg>
  );
}

function StatCards({ data }) {
  const overallPct = data?.overallProgress ?? 0;
  const clientCount = data?.clients?.length ?? 0;
  const todoCount = data?.todoCount ?? 0;
  const overdueCount = data?.overdueCount ?? 0;
  const reviewCount = data?.reviewCount ?? 0;
  const pendingTotal = todoCount + overdueCount;
  const icfrTotal = data?.icfrTotal ?? 0;
  const icfrDone = data?.icfrCompleted ?? 0;
  const icfrPct = icfrTotal > 0 ? Math.round(icfrDone / icfrTotal * 100) : 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-5">
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 flex flex-col items-center gap-3">
        <h3 className="text-sm font-label font-semibold text-on-surface-variant w-full">전체 감사 진척률</h3>
        <CircularProgress value={overallPct} />
        <p className="text-xs text-outline font-label">{clientCount}건 진행 중 · 평균 {overallPct}%</p>
      </div>

      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 border-l-4 border-l-error">
        <h3 className="text-sm font-label font-semibold text-on-surface-variant">미처리 항목</h3>
        <div className="mt-4 flex items-end gap-2">
          <span className="text-4xl font-headline font-bold text-error">{pendingTotal}</span>
          <span className="text-sm text-on-surface-variant font-body mb-1">건</span>
        </div>
        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-xs font-label">
            <span className="text-on-surface-variant">미착수</span>
            <span className="font-semibold text-on-surface">{todoCount}건</span>
          </div>
          <div className="flex justify-between text-xs font-label">
            <span className="text-error">마감 초과</span>
            <span className="font-semibold text-error">{overdueCount}건</span>
          </div>
          <div className="flex justify-between text-xs font-label">
            <span className="text-on-surface-variant">검토 대기</span>
            <span className="font-semibold text-on-surface">{reviewCount}건</span>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
        <h3 className="text-sm font-label font-semibold text-on-surface-variant">내부회계 테스트 완료율</h3>
        <div className="mt-4 flex items-end gap-2">
          <span className="text-4xl font-headline font-bold text-primary">{icfrPct}</span>
          <span className="text-sm text-on-surface-variant font-body mb-1">%</span>
        </div>
        <div className="mt-4">
          <div className="w-full h-2.5 bg-surface-container-highest rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-primary to-primary-container rounded-full transition-all duration-700" style={{ width: `${icfrPct}%` }} />
          </div>
          <div className="mt-2 flex justify-between text-xs font-label text-on-surface-variant">
            <span>완료 {icfrDone}건</span>
            <span>전체 {icfrTotal}건</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function DeadlinesSection({ deadlines, onViewAll, onItemClick }) {
  // Show top 8 sorted by due_date (overdue first)
  const sorted = useMemo(() => {
    return [...deadlines]
      .map((dl) => ({ ...dl, _d: calcDDay(dl.date) }))
      .sort((a, b) => a._d - b._d)
      .slice(0, 8);
  }, [deadlines]);

  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline text-base font-bold text-on-surface">주요 마감일</h3>
        <button onClick={onViewAll} className="text-xs font-label text-primary font-semibold hover:underline">전체보기</button>
      </div>
      <div className="space-y-2.5">
        {sorted.map((item) => {
          const d = item._d;
          const badge = dDayBadge(d);
          return (
            <div key={item.id} onClick={() => onItemClick(item)}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-surface-container-low hover:bg-surface-container transition cursor-pointer">
              <span className={`inline-flex items-center justify-center min-w-[48px] px-1.5 py-0.5 rounded-xl text-[11px] font-label font-bold border ${badge.bg} ${badge.text} ${badge.border}`}>
                {dDayLabel(d)}
              </span>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-label font-semibold truncate ${d < 0 ? "text-error" : "text-on-surface"}`}>{item.task}</p>
                <p className="text-[11px] text-on-surface-variant font-body">{item.client}</p>
              </div>
              <span className="text-[11px] text-outline font-label whitespace-nowrap">{item.date}</span>
            </div>
          );
        })}
        {sorted.length === 0 && (
          <p className="text-xs text-outline font-body text-center py-4">마감일이 설정된 할일이 없습니다</p>
        )}
      </div>
    </div>
  );
}

function EngagementsTable({ engagements, onViewAll, onRowClick }) {
  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline text-base font-bold text-on-surface">진행중인 감사</h3>
        <button onClick={onViewAll} className="text-xs font-label text-primary font-semibold hover:underline">전체보기</button>
      </div>
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-outline-variant text-xs font-label text-on-surface-variant">
            <th className="pb-3 font-semibold">클라이언트</th>
            <th className="pb-3 font-semibold">업종</th>
            <th className="pb-3 font-semibold">진행률</th>
            <th className="pb-3 font-semibold text-right">다음 마감일</th>
          </tr>
        </thead>
        <tbody>
          {engagements.map((e, i) => {
            const progress = e.progress ?? (e.total_tasks > 0 ? Math.round(e.done_tasks / e.total_tasks * 100) : 0);
            const color = CLIENT_COLORS[i % CLIENT_COLORS.length];
            const deadlineD = e.next_deadline ? calcDDay(e.next_deadline) : null;
            return (
              <tr key={e.id} onClick={() => onRowClick(e)}
                className="border-b border-outline-variant/50 last:border-b-0 hover:bg-surface-container-low transition cursor-pointer">
                <td className="py-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full ${color} flex items-center justify-center`}>
                      <span className="text-[10px] font-label font-bold text-white">{e.name.slice(0, 2)}</span>
                    </div>
                    <span className="text-sm font-label font-semibold text-on-surface">{e.name}</span>
                  </div>
                </td>
                <td className="py-3">
                  <span className="text-xs font-label text-on-surface-variant px-2 py-0.5 bg-surface-container rounded-xl">{e.industry || "-"}</span>
                </td>
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-700 ${progress >= 100 ? "bg-[#3a5a2e]" : "bg-primary"}`} style={{ width: `${progress}%` }} />
                    </div>
                    <span className="text-xs font-label font-semibold text-on-surface w-8 text-right">{progress}%</span>
                  </div>
                </td>
                <td className="py-3 text-right">
                  {e.next_deadline ? (
                    <span className={`text-xs font-label ${deadlineD !== null && deadlineD < 0 ? "text-error font-bold" : "text-on-surface-variant"}`}>
                      {e.next_deadline}
                    </span>
                  ) : <span className="text-xs text-outline">—</span>}
                </td>
              </tr>
            );
          })}
          {engagements.length === 0 && (
            <tr><td colSpan={4} className="text-center py-6 text-outline text-xs">클라이언트가 없습니다</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// --- Quick Add Modal --------------------------------------------------------

function QuickAddModal({ date, clients, onClose, onCreated }) {
  const [tree, setTree] = useState([]);
  const [form, setForm] = useState({ title: "", client_id: "", account_id: "", assignee: "" });
  const [accountOptions, setAccountOptions] = useState([]);

  useEffect(() => {
    api.getEngagementTree().then(setTree).catch(() => {});
  }, []);

  // Build client list from tree
  const clientList = useMemo(() => {
    const result = [];
    for (const fy of tree) {
      for (const c of (fy.children || [])) {
        result.push({ id: c.dbId, name: c.label, node: c });
      }
    }
    return result;
  }, [tree]);

  // Update account options when client changes
  useEffect(() => {
    if (!form.client_id) { setAccountOptions([]); return; }
    const cl = clientList.find((c) => c.id === Number(form.client_id));
    if (!cl) return;
    const accs = [];
    for (const ph of (cl.node.children || [])) {
      for (const acc of (ph.children || [])) {
        accs.push({ id: acc.dbId, name: `${ph.label} > ${acc.label}` });
      }
    }
    setAccountOptions(accs);
    setForm((f) => ({ ...f, account_id: accs[0]?.id ? String(accs[0].id) : "" }));
  }, [form.client_id, clientList]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.account_id) return;
    try {
      const created = await api.createTask({
        account_id: Number(form.account_id),
        title: form.title.trim(),
        status: "todo",
        assignee: form.assignee.trim() || "미배정",
        due_date: date,
        priority: "mid",
        memo: "",
      });
      onCreated({ ...created, date, task: created.title, client: clientList.find((c) => c.id === Number(form.client_id))?.name || "", node_id: `account-${form.account_id}`, account_id: Number(form.account_id) });
      onClose();
    } catch { alert("할일 생성에 실패했습니다."); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <form onSubmit={handleSubmit} className="relative bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-md flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b border-outline-variant">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-lg">add_task</span>
            </div>
            <div>
              <h3 className="font-headline text-sm font-bold text-on-surface">할일 빠른 추가</h3>
              <p className="text-[11px] text-on-surface-variant font-label">마감일: {date}</p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="w-8 h-8 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-on-surface-variant text-lg">close</span>
          </button>
        </div>
        <div className="p-5 space-y-3">
          <input type="text" required autoFocus value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="할일 제목 *"
            className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
          <select value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value, account_id: "" })} required
            className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface focus:border-primary focus:outline-none transition">
            <option value="">클라이언트 선택 *</option>
            {clientList.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <select value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })} required
            className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface focus:border-primary focus:outline-none transition">
            <option value="">계정과목 선택 *</option>
            {accountOptions.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
          <input type="text" value={form.assignee} onChange={(e) => setForm({ ...form, assignee: e.target.value })}
            placeholder="담당자"
            className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
        </div>
        <div className="flex items-center justify-end gap-2 p-5 border-t border-outline-variant">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition">취소</button>
          <button type="submit" className="px-5 py-2 rounded-xl bg-primary text-white text-xs font-label font-semibold hover:opacity-90 transition flex items-center gap-1.5">
            <span className="material-symbols-outlined text-sm">add</span>추가
          </button>
        </div>
      </form>
    </div>
  );
}

// --- Calendar ---------------------------------------------------------------

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function CalendarView({ deadlines, onItemClick, onStatusChange, onQuickAdd, clients }) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [selectedDate, setSelectedDate] = useState(null);
  const [viewMode, setViewMode] = useState("month"); // "month" | "week"
  const clickTimer = useRef(null);

  const dateMap = useMemo(() => {
    const m = {};
    for (const dl of deadlines) {
      if (!dl.date) continue;
      if (!m[dl.date]) m[dl.date] = [];
      m[dl.date].push(dl);
    }
    return m;
  }, [deadlines]);

  const pad = (n) => String(n).padStart(2, "0");
  const toDateKey = (y, m, d) => `${y}-${pad(m + 1)}-${pad(d)}`;
  const todayKey = toDateKey(today.getFullYear(), today.getMonth(), today.getDate());

  // Month cells
  const monthCells = useMemo(() => {
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells = [];
    for (let i = 0; i < firstDay; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    return cells;
  }, [year, month]);

  // Week cells (current week containing selected or today)
  const weekCells = useMemo(() => {
    const ref = selectedDate ? new Date(selectedDate) : today;
    const dow = ref.getDay();
    const start = new Date(ref); start.setDate(start.getDate() - dow);
    const cells = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(start); d.setDate(start.getDate() + i);
      cells.push({ date: d, key: toDateKey(d.getFullYear(), d.getMonth(), d.getDate()), day: d.getDate(), isOtherMonth: d.getMonth() !== month });
    }
    return cells;
  }, [year, month, selectedDate]);

  const nav = (dir) => {
    if (viewMode === "week") {
      const ref = selectedDate ? new Date(selectedDate) : today;
      ref.setDate(ref.getDate() + dir * 7);
      setYear(ref.getFullYear()); setMonth(ref.getMonth());
      setSelectedDate(toDateKey(ref.getFullYear(), ref.getMonth(), ref.getDate()));
    } else {
      if (dir < 0) { if (month === 0) { setYear(year - 1); setMonth(11); } else setMonth(month - 1); }
      else { if (month === 11) { setYear(year + 1); setMonth(0); } else setMonth(month + 1); }
      setSelectedDate(null);
    }
  };

  // Single click = select, double click = quick add
  const handleDayClick = (key) => {
    if (clickTimer.current) { clearTimeout(clickTimer.current); clickTimer.current = null; onQuickAdd(key); return; }
    clickTimer.current = setTimeout(() => { clickTimer.current = null; setSelectedDate(selectedDate === key ? null : key); }, 250);
  };

  const selectedTasks = selectedDate ? (dateMap[selectedDate] || []) : [];

  const renderDayCell = (day, key, i, isOtherMonth) => {
    const tasks = dateMap[key];
    const count = tasks?.length || 0;
    const isToday = key === todayKey;
    const isSelected = key === selectedDate;
    const d = count > 0 ? calcDDay(key) : null;
    let dotColor = "bg-primary";
    if (d !== null) { if (d <= 7) dotColor = "bg-error"; else if (d <= 15) dotColor = "bg-on-tertiary-container"; }

    return (
      <button key={key} onClick={() => handleDayClick(key)}
        className={`relative flex flex-col items-center justify-center py-1.5 rounded-lg text-xs font-label transition ${
          isSelected ? "bg-primary text-white font-bold"
          : isToday ? "bg-primary/10 text-primary font-bold"
          : isOtherMonth ? "text-outline"
          : "text-on-surface hover:bg-surface-container"
        } ${i % 7 === 0 && !isSelected ? "text-error/70" : ""}`}>
        {day}
        {count > 0 && (
          count >= 3
            ? <span className={`absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] flex items-center justify-center px-0.5 rounded-full text-[8px] font-bold text-white ${d <= 7 ? "bg-error" : d <= 15 ? "bg-on-tertiary-container" : "bg-primary"}`}>{count}</span>
            : <span className={`absolute bottom-0.5 w-1.5 h-1.5 rounded-full ${isSelected ? "bg-white" : dotColor}`} />
        )}
      </button>
    );
  };

  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-headline text-base font-bold text-on-surface">감사 캘린더</h3>
        <div className="flex rounded-xl border border-outline-variant overflow-hidden">
          <button onClick={() => setViewMode("month")}
            className={`px-2 py-1 text-[10px] font-label font-semibold transition ${viewMode === "month" ? "bg-primary text-white" : "text-on-surface-variant hover:bg-surface-container"}`}>월간</button>
          <button onClick={() => setViewMode("week")}
            className={`px-2 py-1 text-[10px] font-label font-semibold transition ${viewMode === "week" ? "bg-primary text-white" : "text-on-surface-variant hover:bg-surface-container"}`}>주간</button>
        </div>
      </div>

      {/* Nav */}
      <div className="flex items-center justify-center gap-2 mb-3">
        <button onClick={() => nav(-1)} className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-surface-container transition">
          <span className="material-symbols-outlined text-sm text-on-surface-variant">chevron_left</span>
        </button>
        <span className="text-sm font-label font-semibold text-on-surface min-w-[100px] text-center">
          {viewMode === "week" && selectedDate ? `${selectedDate.slice(5)} 주` : `${year}년 ${month + 1}월`}
        </span>
        <button onClick={() => nav(1)} className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-surface-container transition">
          <span className="material-symbols-outlined text-sm text-on-surface-variant">chevron_right</span>
        </button>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1">
        {WEEKDAYS.map((w, i) => (
          <div key={w} className={`text-center text-[11px] font-label font-semibold py-1 ${i === 0 ? "text-error" : "text-on-surface-variant"}`}>{w}</div>
        ))}
      </div>

      {/* Days grid */}
      {viewMode === "month" ? (
        <div className="grid grid-cols-7">
          {monthCells.map((day, i) => {
            if (day === null) return <div key={`b-${i}`} />;
            const key = toDateKey(year, month, day);
            return renderDayCell(day, key, i, false);
          })}
        </div>
      ) : (
        /* Week view: taller cells with task previews */
        <div className="grid grid-cols-7 gap-0.5">
          {weekCells.map((cell, i) => {
            const tasks = dateMap[cell.key] || [];
            const isToday = cell.key === todayKey;
            const isSelected = cell.key === selectedDate;
            return (
              <div key={cell.key} onClick={() => handleDayClick(cell.key)}
                className={`flex flex-col items-center rounded-lg p-1 min-h-[72px] cursor-pointer transition ${
                  isSelected ? "bg-primary/10 ring-1 ring-primary" : isToday ? "bg-primary/5" : "hover:bg-surface-container"
                }`}>
                <span className={`text-xs font-label font-semibold mb-1 ${isToday ? "text-primary" : cell.isOtherMonth ? "text-outline" : "text-on-surface"}`}>{cell.day}</span>
                {tasks.slice(0, 3).map((t) => {
                  const d = calcDDay(t.date);
                  return (
                    <div key={t.id} className={`w-full px-1 py-0.5 rounded text-[8px] font-label truncate mb-0.5 ${d <= 0 ? "bg-error/10 text-error" : d <= 7 ? "bg-on-tertiary-container/10 text-on-tertiary-container" : "bg-primary-fixed text-primary"}`}>
                      {t.task}
                    </div>
                  );
                })}
                {tasks.length > 3 && <span className="text-[8px] text-outline">+{tasks.length - 3}</span>}
              </div>
            );
          })}
        </div>
      )}

      <p className="text-[9px] text-outline font-label mt-1.5 text-center">날짜 더블클릭으로 할일 빠른 추가</p>

      {/* Selected date tasks */}
      {selectedDate && (
        <div className="mt-3 pt-3 border-t border-outline-variant">
          <p className="text-xs font-label font-semibold text-on-surface-variant mb-2">
            {selectedDate} ({selectedTasks.length}건)
          </p>
          {selectedTasks.length === 0 ? (
            <p className="text-xs text-outline font-body">마감 할일이 없습니다</p>
          ) : (
            <div className="space-y-1.5">
              {selectedTasks.map((t) => {
                const d = calcDDay(t.date);
                const badge = dDayBadge(d);
                const st = STATUS_MAP[t.status] || STATUS_MAP.todo;
                return (
                  <div key={t.id} className="flex items-center gap-2 px-2.5 py-2 rounded-xl bg-surface-container-low hover:bg-surface-container transition">
                    {/* Status badge – clickable */}
                    <button onClick={(e) => { e.stopPropagation(); onStatusChange(t); }}
                      className={`inline-flex px-1.5 py-0.5 rounded-lg text-[9px] font-label font-bold shrink-0 ${st.bg} ${st.text} hover:opacity-80 transition`} title="클릭하여 상태 변경">
                      {st.label}
                    </button>
                    <div className="flex-1 min-w-0 cursor-pointer" onClick={() => onItemClick(t)}>
                      <p className={`text-[11px] font-label font-semibold truncate ${d < 0 ? "text-error" : "text-on-surface"}`}>{t.task}</p>
                      <p className="text-[10px] text-on-surface-variant font-body">{t.client}</p>
                    </div>
                    <span className={`inline-flex items-center justify-center min-w-[36px] px-1 py-0.5 rounded-lg text-[9px] font-label font-bold border shrink-0 ${badge.bg} ${badge.text} ${badge.border}`}>
                      {dDayLabel(d)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// --- Main -------------------------------------------------------------------

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [quickAddDate, setQuickAddDate] = useState(null);

  const reload = () => api.getDashboard().then(setData).catch(() => {});
  useEffect(() => { reload(); }, []);

  const deadlines = data?.deadlines || [];
  const clients = data?.clients || [];

  const goToTask = (item) => {
    navigate(`/engagements?select=${item.node_id}&highlight=${item.id}`);
  };
  const goToClient = (client) => {
    navigate(`/engagements?select=${client.node_id}`);
  };

  const handleStatusChange = async (task) => {
    const idx = STATUS_ORDER.indexOf(task.status);
    const newStatus = STATUS_ORDER[(idx + 1) % STATUS_ORDER.length];
    try {
      await api.updateTask(task.id, { status: newStatus });
      reload();
    } catch {}
  };

  const handleQuickAddCreated = (newTask) => {
    // Reload dashboard data to reflect the new task
    reload();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-headline text-2xl font-bold text-on-surface">대시보드</h2>
        <p className="mt-1 text-sm text-on-surface-variant font-body">
          {data?.clients?.length ? `${data.clients.length}개 클라이언트 감사 현황 요약` : "감사 현황 요약"}
        </p>
      </div>

      <StatCards data={data} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-5">
        <DeadlinesSection deadlines={deadlines} onViewAll={() => navigate("/engagements")} onItemClick={goToTask} />
        <EngagementsTable engagements={clients} onViewAll={() => navigate("/engagements")} onRowClick={goToClient} />
        <CalendarView
          deadlines={deadlines}
          clients={clients}
          onItemClick={goToTask}
          onStatusChange={handleStatusChange}
          onQuickAdd={(date) => setQuickAddDate(date)}
        />
      </div>

      {quickAddDate && (
        <QuickAddModal
          date={quickAddDate}
          clients={clients}
          onClose={() => setQuickAddDate(null)}
          onCreated={handleQuickAddCreated}
        />
      )}
    </div>
  );
}
