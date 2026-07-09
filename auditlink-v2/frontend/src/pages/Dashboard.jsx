import { useState, useEffect } from "react";
import { api } from "../api.js";
import { STATUS } from "../constants.js";
import { StatusDot, DDay, Icon, Spinner } from "../components/Tokens.jsx";

function Ring({ value, size = 104, stroke = 7 }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f0f0f0" strokeWidth={stroke} />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke}
        style={{ stroke: "var(--lnac)" }}
        strokeLinecap="round" strokeDasharray={c}
        strokeDashoffset={c - (value / 100) * c}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        className="transition-all duration-700"
      />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        fill="#1a1a1a" fontWeight="600" style={{ fontSize: "20px" }}>
        {value}%
      </text>
    </svg>
  );
}

function Bar({ value, color }) {
  return (
    <div className="w-full h-1.5 bg-line rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${value}%`, background: color || "var(--lnac)" }}
      />
    </div>
  );
}

function StatCards({ tasks, clients }) {
  const statusCounts = tasks.reduce((a, t) => { a[t.status] = (a[t.status] || 0) + 1; return a; }, {});
  const done = statusCounts.done || 0;
  const total = tasks.length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  const unresolved = (statusCounts.todo || 0) + (statusCounts.overdue || 0) + (statusCounts.review || 0);

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="bg-white rounded-lg border border-line p-6 flex items-center gap-6">
        <Ring value={pct} />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-ink">전체 진척률</p>
          <p className="text-xs text-sub">{clients.length}건 진행 중</p>
          <p className="text-xs text-faint">완료 {done} / 전체 {total}</p>
        </div>
      </div>
      <div className="bg-white rounded-lg border border-line p-6">
        <p className="text-sm font-medium text-ink">미처리 항목</p>
        <p className="mt-2 text-3xl font-semibold text-ink tabular-nums">
          {unresolved}<span className="text-sm font-normal text-faint ml-1">건</span>
        </p>
        <div className="mt-4 flex flex-col gap-2">
          {["todo", "overdue", "review"].map((k) => (
            <div key={k} className="flex items-center justify-between">
              <StatusDot k={k} />
              <span className={`text-xs font-medium tabular-nums ${k === "overdue" ? "text-[#ef4444]" : "text-ink"}`}>
                {statusCounts[k] || 0}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="bg-white rounded-lg border border-line p-6">
        <p className="text-sm font-medium text-ink">진행중인 감사</p>
        <p className="mt-2 text-3xl font-semibold text-ink tabular-nums">
          {clients.length}<span className="text-sm font-normal text-faint ml-1">건</span>
        </p>
        <div className="mt-4">
          <Bar value={pct} />
          <div className="mt-2 flex justify-between text-xs text-faint">
            <span>완료 {done}건</span>
            <span>전체 {total}건</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function DeadlineList({ tasks, onSeeAll }) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const upcoming = tasks
    .filter((t) => t.deadline && t.status !== "done")
    .map((t) => {
      const due = new Date(t.deadline); due.setHours(0, 0, 0, 0);
      return { ...t, d: Math.round((due - today) / 86400000) };
    })
    .sort((a, b) => a.d - b.d)
    .slice(0, 8);

  return (
    <div className="bg-white rounded-lg border border-line p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-ink">주요 마감일</h3>
        <button onClick={onSeeAll} className="text-xs text-faint hover:text-sub transition">전체보기</button>
      </div>
      <div className="flex flex-col">
        {upcoming.length === 0 && <p className="text-xs text-faint py-6 text-center">마감 예정 항목이 없습니다</p>}
        {upcoming.map((t) => (
          <div key={t.id} className="flex items-center gap-3 py-2.5 border-b border-line/70 last:border-b-0 hover:bg-[#fafafa] -mx-2 px-2 rounded-lg transition cursor-pointer">
            <span className="w-10 shrink-0"><DDay date={t.deadline} /></span>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-ink truncate">{t.title}</p>
              <p className="text-xs text-faint">{t._clientName || ""}</p>
            </div>
            <span className="text-xs text-faint tabular-nums">{t.deadline?.slice(5)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ClientList({ clients, onSeeAll }) {
  return (
    <div className="bg-white rounded-lg border border-line p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-ink">진행중인 감사</h3>
        <button onClick={onSeeAll} className="text-xs text-faint hover:text-sub transition">전체보기</button>
      </div>
      <div className="flex flex-col">
        {clients.length === 0 && <p className="text-xs text-faint py-6 text-center">진행중인 감사가 없습니다</p>}
        {clients.map((c) => (
          <div key={c.id} className="flex items-center gap-3 py-3 border-b border-line/70 last:border-b-0 hover:bg-[#fafafa] -mx-2 px-2 rounded-lg transition cursor-pointer">
            <span className="w-7 h-7 rounded-full bg-[#f4f4f5] flex items-center justify-center text-[10px] font-semibold text-sub shrink-0">
              {c.name.slice(0, 2)}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-ink truncate">{c.name}</p>
              <p className="text-xs text-faint">{c.industry || ""}</p>
            </div>
            <div className="w-20 shrink-0">
              <Bar value={c._progress || 0} color={c._progress >= 100 ? "#10b981" : undefined} />
            </div>
            <span className="text-xs text-sub font-medium tabular-nums w-9 text-right shrink-0">{c._progress || 0}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Calendar() {
  const [view, setView] = useState("month");
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());

  const weekdays = ["일", "월", "화", "수", "목", "금", "토"];
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const today = now.getDate();
  const isCurrentMonth = now.getFullYear() === year && now.getMonth() === month;
  const monthLabel = `${year}년 ${month + 1}월`;

  const prevMonth = () => { if (month === 0) { setYear(y => y - 1); setMonth(11); } else setMonth(m => m - 1); };
  const nextMonth = () => { if (month === 11) { setYear(y => y + 1); setMonth(0); } else setMonth(m => m + 1); };

  return (
    <div className="bg-white rounded-lg border border-line p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-ink">캘린더</h3>
        <div className="flex bg-[#f4f4f5] rounded-lg p-0.5">
          {[["month", "월간"], ["week", "주간"]].map(([k, l]) => (
            <button key={k} onClick={() => setView(k)}
              className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition ${view === k ? "bg-white text-ink shadow-sm" : "text-faint hover:text-sub"}`}>
              {l}
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-center gap-3 mb-3">
        <button onClick={prevMonth} className="w-6 h-6 rounded-md flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
          <Icon name="chevron_left" className="text-[16px]" />
        </button>
        <span className="text-[13px] font-medium text-ink min-w-[110px] text-center">{monthLabel}</span>
        <button onClick={nextMonth} className="w-6 h-6 rounded-md flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
          <Icon name="chevron_right" className="text-[16px]" />
        </button>
      </div>
      <div className="grid grid-cols-7 mb-1">
        {weekdays.map((w) => (
          <div key={w} className="text-center text-[11px] text-faint py-1">{w}</div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {cells.map((d, i) => {
          if (!d) return <div key={i} />;
          const isToday = isCurrentMonth && d === today;
          return (
            <button key={i}
              className={`flex flex-col items-center justify-center py-1.5 rounded-lg text-xs transition ${
                isToday ? "text-white font-semibold" : "text-sub hover:bg-[#f4f4f5]"
              }`}
              style={isToday ? { background: "var(--lnac)" } : undefined}>
              {d}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function Dashboard({ onNav, activeFyId }) {
  const [clients, setClients] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeFyId) { setLoading(false); return; }
    setLoading(true);
    api.getClients(activeFyId).then(async (cs) => {
      setClients(cs);
      const allTasks = [];
      for (const c of cs) {
        const engs = await api.getEngagements(c.id);
        for (const eng of engs) {
          for (const phase of (eng.phases || [])) {
            const accs = await api.getAccounts(phase.id);
            for (const acc of accs) {
              const ts = await api.getTasks(acc.id);
              ts.forEach((t) => allTasks.push({ ...t, _clientName: c.name }));
            }
          }
        }
      }
      setTasks(allTasks);
      setClients(cs.map((c) => {
        const cTasks = allTasks.filter((t) => t._clientName === c.name);
        const done = cTasks.filter((t) => t.status === "done").length;
        const pct = cTasks.length ? Math.round((done / cTasks.length) * 100) : 0;
        return { ...c, _progress: pct };
      }));
    }).catch(() => {}).finally(() => setLoading(false));
  }, [activeFyId]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h2 className="text-xl font-semibold text-ink">대시보드</h2>
          <p className="mt-1 text-sm text-sub">로딩 중…</p>
        </div>
        <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-semibold text-ink">대시보드</h2>
        <p className="mt-1 text-sm text-sub">{clients.length > 0 ? `${clients.length}개 클라이언트 감사 현황` : "감사업무를 추가하면 현황이 표시됩니다"}</p>
      </div>
      <StatCards tasks={tasks} clients={clients} />
      <div className="grid grid-cols-3 gap-4">
        <DeadlineList tasks={tasks} onSeeAll={() => onNav("engagements")} />
        <ClientList clients={clients} onSeeAll={() => onNav("engagements")} />
        <Calendar />
      </div>
    </div>
  );
}
