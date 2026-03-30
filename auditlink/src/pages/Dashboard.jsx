// ---------------------------------------------------------------------------
// Dashboard – 대시보드 메인 페이지 (실데이터 연동)
// ---------------------------------------------------------------------------
import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

const CLIENT_COLORS = ["bg-primary", "bg-secondary", "bg-on-tertiary-container", "bg-primary-container"];

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

// --- Calendar ---------------------------------------------------------------

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function CalendarView({ deadlines, onItemClick }) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [selectedDate, setSelectedDate] = useState(null);

  const dateMap = useMemo(() => {
    const m = {};
    for (const dl of deadlines) {
      if (!dl.date) continue;
      if (!m[dl.date]) m[dl.date] = [];
      m[dl.date].push(dl);
    }
    return m;
  }, [deadlines]);

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const prevMonth = () => { if (month === 0) { setYear(year - 1); setMonth(11); } else setMonth(month - 1); setSelectedDate(null); };
  const nextMonth = () => { if (month === 11) { setYear(year + 1); setMonth(0); } else setMonth(month + 1); setSelectedDate(null); };

  const pad = (n) => String(n).padStart(2, "0");
  const toKey = (d) => `${year}-${pad(month + 1)}-${pad(d)}`;
  const todayKey = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
  const selectedTasks = selectedDate ? (dateMap[selectedDate] || []) : [];

  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline text-base font-bold text-on-surface">감사 캘린더</h3>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-sm text-on-surface-variant">chevron_left</span>
          </button>
          <span className="text-sm font-label font-semibold text-on-surface min-w-[100px] text-center">{year}년 {month + 1}월</span>
          <button onClick={nextMonth} className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-sm text-on-surface-variant">chevron_right</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 mb-1">
        {WEEKDAYS.map((w, i) => (
          <div key={w} className={`text-center text-[11px] font-label font-semibold py-1 ${i === 0 ? "text-error" : "text-on-surface-variant"}`}>{w}</div>
        ))}
      </div>

      <div className="grid grid-cols-7">
        {cells.map((day, i) => {
          if (day === null) return <div key={`b-${i}`} />;
          const key = toKey(day);
          const hasTasks = !!dateMap[key];
          const isToday = key === todayKey;
          const isSelected = key === selectedDate;
          const d = hasTasks ? calcDDay(key) : null;

          let dotColor = "bg-primary";
          if (d !== null) {
            if (d <= 7) dotColor = "bg-error";
            else if (d <= 15) dotColor = "bg-on-tertiary-container";
          }

          return (
            <button key={key} onClick={() => setSelectedDate(isSelected ? null : key)}
              className={`relative flex flex-col items-center justify-center py-1.5 rounded-lg text-xs font-label transition ${
                isSelected ? "bg-primary text-white font-bold"
                : isToday ? "bg-primary/10 text-primary font-bold"
                : "text-on-surface hover:bg-surface-container"
              } ${i % 7 === 0 && !isSelected ? "text-error/70" : ""}`}>
              {day}
              {hasTasks && <span className={`absolute bottom-0.5 w-1.5 h-1.5 rounded-full ${isSelected ? "bg-white" : dotColor}`} />}
            </button>
          );
        })}
      </div>

      {selectedDate && (
        <div className="mt-4 pt-4 border-t border-outline-variant">
          <p className="text-xs font-label font-semibold text-on-surface-variant mb-2">
            {selectedDate} 마감 ({selectedTasks.length}건)
          </p>
          {selectedTasks.length === 0 ? (
            <p className="text-xs text-outline font-body">해당 날짜에 마감 할일이 없습니다</p>
          ) : (
            <div className="space-y-2">
              {selectedTasks.map((t) => {
                const d = calcDDay(t.date);
                const badge = dDayBadge(d);
                return (
                  <div key={t.id} onClick={() => onItemClick(t)}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl bg-surface-container-low hover:bg-surface-container cursor-pointer transition">
                    <span className={`inline-flex items-center justify-center min-w-[40px] px-1.5 py-0.5 rounded-lg text-[10px] font-label font-bold border ${badge.bg} ${badge.text} ${badge.border}`}>
                      {dDayLabel(d)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs font-label font-semibold truncate ${d < 0 ? "text-error" : "text-on-surface"}`}>{t.task}</p>
                      <p className="text-[11px] text-on-surface-variant font-body">{t.client}</p>
                    </div>
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

  useEffect(() => {
    api.getDashboard().then(setData).catch(() => {});
  }, []);

  const deadlines = data?.deadlines || [];
  const clients = data?.clients || [];

  const goToTask = (item) => {
    navigate(`/engagements?select=${item.node_id}&highlight=${item.id}`);
  };
  const goToClient = (client) => {
    navigate(`/engagements?select=${client.node_id}`);
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
        <CalendarView deadlines={deadlines} onItemClick={goToTask} />
      </div>
    </div>
  );
}
