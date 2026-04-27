import { useState, useEffect, useRef, useMemo } from "react";
import api from "../api";

const STATUS_MAP = {
  todo: { label: "미착수", color: "#73777f" },
  in_progress: { label: "진행중", color: "#003366" },
  review: { label: "검토대기", color: "#6b4c00" },
  done: { label: "완료", color: "#3a5a2e" },
};
const STATUS_ORDER = ["todo", "in_progress", "review", "done"];

const PBC_STATUS_MAP = {
  "미요청": "bg-outline-variant/30 text-on-surface-variant",
  "요청완료": "bg-primary-fixed text-primary",
  "수령완료": "bg-secondary-container text-on-secondary-container",
  "보완요청": "bg-on-tertiary-container/10 text-on-tertiary-container",
};

const IV_STATUS = {
  "진행중": "bg-primary-fixed text-primary",
  "완료": "bg-secondary-container text-on-secondary-container",
};

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

function ProgressBar({ progress, height = 6 }) {
  return (
    <div className="w-full rounded-full overflow-hidden" style={{ height, backgroundColor: "#e8e8e8" }}>
      <div className="h-full rounded-full transition-all" style={{ width: `${Math.max(progress, 0)}%`, backgroundColor: progress >= 100 ? "#3a5a2e" : "#003366" }} />
    </div>
  );
}

function CircularProgress({ pct, size = 72 }) {
  const r = (size - 10) / 2, c = 2 * Math.PI * r, off = c * (1 - pct / 100), cx = size / 2;
  return (
    <svg width={size} height={size}>
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e8e8e8" strokeWidth="6" />
      <circle cx={cx} cy={cx} r={r} fill="none" stroke={pct >= 100 ? "#3a5a2e" : "#003366"} strokeWidth="6" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} transform={`rotate(-90 ${cx} ${cx})`} />
      <text x={cx} y={cx + 4} textAnchor="middle" className="text-xs font-bold" fill="#001e40">{pct}%</text>
    </svg>
  );
}

function DonutChart({ statusCounts, total }) {
  if (!total) return <div className="flex items-center justify-center h-40 text-sm text-outline font-body">할일이 없습니다</div>;
  const r = 52, cx = 70, sw = 20, circ = 2 * Math.PI * r;
  let accum = 0;
  const segs = STATUS_ORDER.filter((s) => statusCounts[s]).map((s) => { const pct = statusCounts[s] / total; const o = accum; accum += pct; return { status: s, count: statusCounts[s], pct, offset: o }; });
  return (
    <div className="flex items-center gap-6">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e8e8e8" strokeWidth={sw} />
        {segs.map((seg) => <circle key={seg.status} cx={cx} cy={cx} r={r} fill="none" stroke={STATUS_MAP[seg.status].color} strokeWidth={sw} strokeDasharray={`${seg.pct * circ} ${circ}`} strokeDashoffset={-seg.offset * circ} strokeLinecap="round" transform={`rotate(-90 ${cx} ${cx})`} />)}
        <text x={cx} y={cx - 6} textAnchor="middle" className="text-lg font-bold" fill="#001e40">{total > 0 ? Math.round((statusCounts.done || 0) / total * 100) : 0}%</text>
        <text x={cx} y={cx + 12} textAnchor="middle" className="text-[10px]" fill="#73777f">완료율</text>
      </svg>
      <div className="space-y-2">
        {segs.map((seg) => (
          <div key={seg.status} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: STATUS_MAP[seg.status].color }} />
            <span className="text-xs font-label text-on-surface">{STATUS_MAP[seg.status].label}</span>
            <span className="text-xs font-label font-bold text-on-surface ml-auto">{seg.count}건</span>
            <span className="text-[10px] text-outline font-label w-10 text-right">{Math.round(seg.pct * 100)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function exportCSV(filename, rows) {
  const BOM = "﻿";
  const csv = rows.map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([BOM + csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = filename; a.click();
}

// ---------------------------------------------------------------------------
// Tab 1: 업무현황
// ---------------------------------------------------------------------------

function WorkStatusTab({ summary, onSelectAccount }) {
  const { accounts, status_counts, assignees, total_tasks } = summary;
  const today = new Date().toISOString().slice(0, 10);
  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <button onClick={() => {
          const rows = [["계정과목", "Phase", "전체", "완료", "진행률", "다음 마감일"], ...accounts.map((a) => [a.name, a.phase_name, a.total_tasks, a.done_tasks, `${a.progress}%`, a.next_deadline || "-"])];
          exportCSV(`${summary.client.name}_업무현황.csv`, rows);
        }} className="px-2.5 py-1 rounded-xl border border-outline-variant text-[11px] font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px]">download</span>엑셀 내보내기
        </button>
      </div>
      {/* Accounts table */}
      <div className="overflow-x-auto rounded-xl border border-outline-variant">
        <table className="w-full text-xs font-label">
          <thead><tr className="bg-surface-container-low">
            <th className="text-left px-4 py-2.5 font-semibold text-on-surface-variant">계정과목</th>
            <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant">Phase</th>
            <th className="text-center px-3 py-2.5 font-semibold text-on-surface-variant w-16">전체</th>
            <th className="text-center px-3 py-2.5 font-semibold text-on-surface-variant w-16">완료</th>
            <th className="px-3 py-2.5 font-semibold text-on-surface-variant w-32">진행률</th>
            <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant">다음 마감일</th>
          </tr></thead>
          <tbody>
            {accounts.map((acc) => (
              <tr key={acc.id} onClick={() => onSelectAccount?.(acc.node_id)} className={`border-t border-outline-variant/50 cursor-pointer hover:bg-surface-container transition ${acc.progress >= 100 ? "bg-secondary-container/20" : ""}`}>
                <td className="px-4 py-2.5 font-semibold text-on-surface">{acc.name}</td>
                <td className="px-3 py-2.5 text-on-surface-variant">{acc.phase_name}</td>
                <td className="text-center px-3 py-2.5">{acc.total_tasks}</td>
                <td className="text-center px-3 py-2.5">{acc.done_tasks}</td>
                <td className="px-3 py-2.5"><div className="flex items-center gap-2"><ProgressBar progress={acc.progress} /><span className="text-[11px] font-bold w-8 text-right">{acc.progress}%</span></div></td>
                <td className={`px-3 py-2.5 ${acc.overdue ? "text-error font-bold" : "text-on-surface-variant"}`}>{acc.next_deadline || "-"}{acc.overdue && <span className="ml-1 text-[10px]">(초과)</span>}</td>
              </tr>
            ))}
            {accounts.length === 0 && <tr><td colSpan={6} className="text-center py-6 text-outline">계정과목이 없습니다</td></tr>}
          </tbody>
        </table>
      </div>
      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-surface-container rounded-xl p-4">
          <h4 className="text-sm font-headline font-bold text-on-surface mb-4 flex items-center gap-2"><span className="material-symbols-outlined text-[18px] text-primary">donut_large</span>상태별 요약</h4>
          <DonutChart statusCounts={status_counts} total={total_tasks} />
        </div>
        <div className="bg-surface-container rounded-xl p-4">
          <h4 className="text-sm font-headline font-bold text-on-surface mb-4 flex items-center gap-2"><span className="material-symbols-outlined text-[18px] text-primary">group</span>담당자별 업무 분배</h4>
          {assignees.length === 0 ? <p className="text-xs text-outline font-body py-4 text-center">배정된 할일이 없습니다</p> : (
            <div className="space-y-3">
              {assignees.map((a) => (
                <div key={a.assignee || "_"}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-label font-semibold text-on-surface flex items-center gap-1.5">
                      <span className="w-6 h-6 rounded-full bg-primary-container flex items-center justify-center text-[10px] font-bold text-white shrink-0">{(a.assignee || "?")[0]}</span>
                      {a.assignee || "미배정"}
                    </span>
                    <span className="text-[11px] font-label text-on-surface-variant">{a.done}/{a.total}건 ({a.progress}%)</span>
                  </div>
                  <ProgressBar progress={a.progress} height={5} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 2: 요청자료
// ---------------------------------------------------------------------------

function PBCOverviewTab({ pbc, clientName }) {
  const [filter, setFilter] = useState("전체");
  const [detail, setDetail] = useState(null);
  const today = new Date().toISOString().slice(0, 10);

  const filtered = useMemo(() => {
    if (filter === "전체") return pbc.items;
    if (filter === "기한초과") return pbc.items.filter((i) => i.due_date && i.due_date < today && i.status !== "수령완료");
    return pbc.items.filter((i) => i.status === filter);
  }, [pbc.items, filter, today]);

  return (
    <div className="space-y-4">
      {/* Summary chips */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs font-label text-on-surface-variant">전체 <b className="text-on-surface">{pbc.total}</b>건</span>
        <span className="text-xs font-label text-on-secondary-container">수령완료 <b>{pbc.received}</b></span>
        <span className="text-xs font-label text-on-tertiary-container">보완요청 <b>{pbc.supplement}</b></span>
        {pbc.overdue > 0 && <span className="text-xs font-label text-error">기한초과 <b>{pbc.overdue}</b></span>}
        <div className="ml-auto flex items-center gap-2">
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="px-2 py-1 rounded-lg border border-outline-variant text-[11px] font-label bg-surface-container-lowest focus:border-primary focus:outline-none">
            <option value="전체">전체</option><option value="미요청">미요청</option><option value="요청완료">요청완료</option><option value="수령완료">수령완료</option><option value="보완요청">보완요청</option><option value="기한초과">기한초과</option>
          </select>
          <button onClick={() => {
            const rows = [["계정과목", "자료명", "요청일", "회신기한", "상태", "감사팀", "클라이언트"], ...pbc.items.map((i) => [i.account_name || "-", i.name, i.request_date || "-", i.due_date || "-", i.status, i.auditor || "-", i.client_contact || "-"])];
            exportCSV(`${clientName}_요청자료.csv`, rows);
          }} className="px-2.5 py-1 rounded-xl border border-outline-variant text-[11px] font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">download</span>내보내기
          </button>
        </div>
      </div>

      <div className="overflow-auto rounded-xl border border-outline-variant max-h-[400px]">
        <table className="w-full text-xs font-label">
          <thead><tr className="bg-surface-container-low sticky top-0 z-10">
            <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant">계정과목</th>
            <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant">자료명</th>
            <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant w-20">요청일</th>
            <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant w-20">회신기한</th>
            <th className="text-center px-3 py-2.5 font-semibold text-on-surface-variant w-20">상태</th>
            <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant w-16">감사팀</th>
            <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant w-20">클라이언트</th>
          </tr></thead>
          <tbody>
            {filtered.map((item) => {
              const overdue = item.due_date && item.due_date < today && item.status !== "수령완료";
              return (
                <tr key={item.id} className={`border-t border-outline-variant/50 hover:bg-surface-container transition cursor-pointer ${item.status === "수령완료" ? "bg-secondary-container/10" : ""}`}>
                  <td className="px-3 py-2.5 text-on-surface-variant">{item.account_name || "-"}</td>
                  <td className="px-3 py-2.5 font-semibold text-on-surface max-w-[200px] truncate">{item.name}</td>
                  <td className="px-3 py-2.5 text-on-surface-variant">{item.request_date || "-"}</td>
                  <td className={`px-3 py-2.5 ${overdue ? "text-error font-bold" : "text-on-surface-variant"}`}>{item.due_date || "-"}{overdue && <span className="text-[9px] ml-0.5">(초과)</span>}</td>
                  <td className="px-3 py-2.5 text-center"><span className={`inline-flex px-2 py-0.5 rounded-xl text-[10px] font-bold ${PBC_STATUS_MAP[item.status] || PBC_STATUS_MAP["미요청"]}`}>{item.status}</span></td>
                  <td className="px-3 py-2.5 text-on-surface-variant truncate">{item.auditor || "-"}</td>
                  <td className="px-3 py-2.5 text-on-surface-variant truncate">{item.client_contact || "-"}</td>
                </tr>
              );
            })}
            {filtered.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-outline font-body">요청자료가 없습니다</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 3: 인터뷰
// ---------------------------------------------------------------------------

function InterviewOverviewTab({ interviews, clientName }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs font-label text-on-surface-variant">전체 <b className="text-on-surface">{interviews.total}</b>건</span>
        <span className="text-xs font-label text-on-secondary-container">완료 <b>{interviews.completed}</b></span>
        {interviews.followup_needed > 0 && <span className="text-xs font-label text-on-tertiary-container">후속조치 필요 <b>{interviews.followup_needed}</b></span>}
        <button onClick={() => {
          const rows = [["날짜", "대상자", "직책", "주제", "상태", "질의건수", "후속조치"], ...interviews.items.map((iv) => [iv.date, iv.interviewee, iv.position, iv.topic, iv.status, iv.question_count, iv.followup_count > 0 ? "필요" : "-"])];
          exportCSV(`${clientName}_인터뷰.csv`, rows);
        }} className="ml-auto px-2.5 py-1 rounded-xl border border-outline-variant text-[11px] font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px]">download</span>내보내기
        </button>
      </div>

      <div className="space-y-2.5 max-h-[400px] overflow-y-auto">
        {interviews.items.map((iv) => (
          <div key={iv.id} className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 hover:shadow-sm hover:border-primary/30 transition cursor-pointer">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-xs font-label font-bold text-on-surface">{iv.date}</span>
                  <span className={`inline-flex px-2 py-0.5 rounded-xl text-[10px] font-label font-bold ${IV_STATUS[iv.status] || IV_STATUS["진행중"]}`}>{iv.status}</span>
                  {iv.followup_count > 0 && <span className="inline-flex px-2 py-0.5 rounded-xl text-[10px] font-label font-bold bg-on-tertiary-container/10 text-on-tertiary-container">후속조치 {iv.followup_count}</span>}
                </div>
                <p className="text-sm font-label font-semibold text-on-surface truncate">{iv.interviewee}{iv.position ? ` (${iv.position})` : ""}</p>
                {iv.topic && <p className="text-xs text-on-surface-variant font-body mt-0.5 truncate">{iv.topic}</p>}
              </div>
              <span className="text-[11px] font-label text-on-surface-variant flex items-center gap-1 shrink-0">
                <span className="material-symbols-outlined text-[14px]">quiz</span>질의 {iv.question_count || 0}건
              </span>
            </div>
          </div>
        ))}
        {interviews.items.length === 0 && <div className="text-center py-10 text-on-surface-variant text-sm font-body">인터뷰 기록이 없습니다</div>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ClientSummaryPanel({ clientNodeId, useApi, onSelectAccount }) {
  const [summary, setSummary] = useState(null);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("work");

  const dbId = clientNodeId ? parseInt(clientNodeId.replace("client-", "")) : null;

  useEffect(() => {
    if (!dbId || !useApi) { setLoading(false); return; }
    setLoading(true);
    Promise.all([
      api.getClientSummary(dbId),
      api.getClientOverview(dbId),
    ]).then(([sum, ov]) => {
      setSummary(sum);
      setOverview(ov);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [dbId, useApi]);

  if (loading) return <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body"><span className="material-symbols-outlined text-3xl animate-spin text-outline-variant mr-3">progress_activity</span>요약 데이터를 불러오는 중...</div>;
  if (!summary) return <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body"><div className="text-center"><span className="material-symbols-outlined text-5xl text-outline-variant mb-3 block">analytics</span><p className="text-sm">클라이언트 요약을 불러올 수 없습니다</p></div></div>;

  const { client, progress, total_tasks, done_tasks } = summary;

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-5 flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <CircularProgress pct={progress} size={72} />
          <div>
            <h3 className="font-headline text-xl font-bold text-on-surface">{client.name}</h3>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              {client.industry && <span className="inline-flex items-center gap-1 text-xs font-label text-on-surface-variant"><span className="material-symbols-outlined text-[14px]">factory</span>{client.industry}</span>}
              {client.report_date && <span className="inline-flex items-center gap-1 text-xs font-label text-on-surface-variant"><span className="material-symbols-outlined text-[14px]">event</span>결산일: {client.report_date}</span>}
              <span className="text-xs font-label text-outline">{client.fy_name}</span>
            </div>
            <p className="text-xs text-on-surface-variant font-label mt-1">전체 {total_tasks}건 중 {done_tasks}건 완료</p>
          </div>
        </div>
        <button onClick={() => window.print()} className="px-3 py-1.5 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1.5 print:hidden">
          <span className="material-symbols-outlined text-[16px]">print</span>인쇄
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-4 border-b border-outline-variant/50 pb-2">
        {[
          { key: "work", label: "업무현황", icon: "analytics" },
          { key: "pbc", label: "요청자료", icon: "description", count: overview?.pbc?.total },
          { key: "interview", label: "인터뷰", icon: "record_voice_over", count: overview?.interviews?.total },
        ].map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`px-3 py-1.5 rounded-t-xl text-xs font-label font-semibold transition ${activeTab === t.key ? "text-primary border-b-2 border-primary" : "text-on-surface-variant hover:text-on-surface"}`}>
            <span className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px]">{t.icon}</span>
              {t.label}
              {t.count !== undefined && <span className="text-[10px] text-outline">({t.count})</span>}
            </span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "work" && <WorkStatusTab summary={summary} onSelectAccount={onSelectAccount} />}
      {activeTab === "pbc" && overview && <PBCOverviewTab pbc={overview.pbc} clientName={client.name} />}
      {activeTab === "interview" && overview && <InterviewOverviewTab interviews={overview.interviews} clientName={client.name} />}
    </div>
  );
}
