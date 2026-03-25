import { useState, useEffect, useRef } from "react";
import api from "../api";

const STATUS_MAP = {
  todo: { label: "미착수", color: "#73777f" },
  in_progress: { label: "진행중", color: "#003366" },
  review: { label: "검토대기", color: "#6b4c00" },
  done: { label: "완료", color: "#3a5a2e" },
};

const STATUS_ORDER = ["todo", "in_progress", "review", "done"];

// ---------------------------------------------------------------------------
// SVG Donut Chart
// ---------------------------------------------------------------------------

function DonutChart({ statusCounts, total }) {
  if (!total) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-outline font-body">할일이 없습니다</div>
    );
  }

  const radius = 52;
  const cx = 70;
  const cy = 70;
  const strokeWidth = 20;
  const circumference = 2 * Math.PI * radius;

  let accum = 0;
  const segments = STATUS_ORDER.filter((s) => statusCounts[s]).map((s) => {
    const count = statusCounts[s];
    const pct = count / total;
    const offset = accum;
    accum += pct;
    return { status: s, count, pct, offset };
  });

  return (
    <div className="flex items-center gap-6">
      <svg width="140" height="140" viewBox="0 0 140 140">
        {/* Background circle */}
        <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#e8e8e8" strokeWidth={strokeWidth} />
        {/* Segments */}
        {segments.map((seg) => (
          <circle
            key={seg.status}
            cx={cx} cy={cy} r={radius}
            fill="none"
            stroke={STATUS_MAP[seg.status].color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${seg.pct * circumference} ${circumference}`}
            strokeDashoffset={-seg.offset * circumference}
            strokeLinecap="round"
            transform={`rotate(-90 ${cx} ${cy})`}
          />
        ))}
        {/* Center text */}
        <text x={cx} y={cy - 6} textAnchor="middle" className="text-lg font-bold" fill="#001e40">
          {total > 0 ? Math.round((statusCounts.done || 0) / total * 100) : 0}%
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" className="text-[10px]" fill="#73777f">
          완료율
        </text>
      </svg>

      {/* Legend */}
      <div className="space-y-2">
        {segments.map((seg) => (
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

// ---------------------------------------------------------------------------
// Circular Progress (header)
// ---------------------------------------------------------------------------

function CircularProgress({ pct, size = 64 }) {
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct / 100);
  const center = size / 2;

  return (
    <svg width={size} height={size}>
      <circle cx={center} cy={center} r={radius} fill="none" stroke="#e8e8e8" strokeWidth="6" />
      <circle cx={center} cy={center} r={radius} fill="none"
        stroke={pct >= 100 ? "#3a5a2e" : "#003366"}
        strokeWidth="6" strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={offset}
        transform={`rotate(-90 ${center} ${center})`} />
      <text x={center} y={center + 4} textAnchor="middle" className="text-xs font-bold" fill="#001e40">
        {pct}%
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Stacked Bar
// ---------------------------------------------------------------------------

function ProgressBar({ progress, height = 6 }) {
  return (
    <div className="w-full rounded-full overflow-hidden" style={{ height, backgroundColor: "#e8e8e8" }}>
      <div className="h-full rounded-full transition-all" style={{
        width: `${Math.max(progress, 0)}%`,
        backgroundColor: progress >= 100 ? "#3a5a2e" : "#003366",
      }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Excel Export (CSV fallback – no external library needed)
// ---------------------------------------------------------------------------

function exportToExcel(summary) {
  const BOM = "\uFEFF";
  const rows = [
    ["클라이언트 요약 보고서"],
    [],
    ["클라이언트", summary.client.name],
    ["업종", summary.client.industry || "-"],
    ["결산일", summary.client.report_date || "-"],
    ["전체 진행률", `${summary.progress}%`],
    ["전체 할일", summary.total_tasks],
    ["완료", summary.done_tasks],
    [],
    ["계정과목별 현황"],
    ["계정과목", "Phase", "전체", "완료", "진행률", "다음 마감일"],
    ...summary.accounts.map((a) => [
      a.name, a.phase_name, a.total_tasks, a.done_tasks, `${a.progress}%`, a.next_deadline || "-",
    ]),
    [],
    ["담당자별 현황"],
    ["담당자", "전체", "완료", "완료율"],
    ...summary.assignees.map((a) => [
      a.assignee || "미배정", a.total, a.done, `${a.progress}%`,
    ]),
  ];

  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([BOM + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${summary.client.name}_감사요약.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ClientSummaryPanel({ clientNodeId, useApi, onSelectAccount }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const printRef = useRef(null);

  const dbId = clientNodeId ? parseInt(clientNodeId.replace("client-", "")) : null;

  useEffect(() => {
    if (!dbId || !useApi) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.getClientSummary(dbId).then((data) => {
      setSummary(data);
    }).catch(() => {
      setSummary(null);
    }).finally(() => setLoading(false));
  }, [dbId, useApi]);

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body">
        <span className="material-symbols-outlined text-3xl animate-spin text-outline-variant mr-3">progress_activity</span>
        요약 데이터를 불러오는 중...
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body">
        <div className="text-center">
          <span className="material-symbols-outlined text-5xl text-outline-variant mb-3 block">analytics</span>
          <p className="text-sm">클라이언트 요약을 불러올 수 없습니다</p>
        </div>
      </div>
    );
  }

  const { client, progress, total_tasks, done_tasks, accounts, status_counts, assignees } = summary;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="flex-1 overflow-y-auto" ref={printRef}>
      {/* Header */}
      <div className="flex items-start justify-between mb-6 flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <CircularProgress pct={progress} size={72} />
          <div>
            <h3 className="font-headline text-xl font-bold text-on-surface">{client.name}</h3>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              {client.industry && (
                <span className="inline-flex items-center gap-1 text-xs font-label text-on-surface-variant">
                  <span className="material-symbols-outlined text-[14px]">factory</span>
                  {client.industry}
                </span>
              )}
              {client.report_date && (
                <span className="inline-flex items-center gap-1 text-xs font-label text-on-surface-variant">
                  <span className="material-symbols-outlined text-[14px]">event</span>
                  결산일: {client.report_date}
                </span>
              )}
              <span className="text-xs font-label text-outline">{client.fy_name}</span>
            </div>
            <p className="text-xs text-on-surface-variant font-label mt-1">
              전체 {total_tasks}건 중 {done_tasks}건 완료
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 print:hidden">
          <button onClick={() => exportToExcel(summary)}
            className="px-3 py-1.5 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px]">download</span>
            엑셀 내보내기
          </button>
          <button onClick={handlePrint}
            className="px-3 py-1.5 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px]">print</span>
            보고서 인쇄
          </button>
        </div>
      </div>

      {/* Accounts table */}
      <div className="mb-6">
        <h4 className="text-sm font-headline font-bold text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-primary">account_balance</span>
          계정과목별 현황
        </h4>
        <div className="overflow-x-auto rounded-xl border border-outline-variant">
          <table className="w-full text-xs font-label">
            <thead>
              <tr className="bg-surface-container-low">
                <th className="text-left px-4 py-2.5 font-semibold text-on-surface-variant">계정과목</th>
                <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant">Phase</th>
                <th className="text-center px-3 py-2.5 font-semibold text-on-surface-variant w-16">전체</th>
                <th className="text-center px-3 py-2.5 font-semibold text-on-surface-variant w-16">완료</th>
                <th className="px-3 py-2.5 font-semibold text-on-surface-variant w-32">진행률</th>
                <th className="text-left px-3 py-2.5 font-semibold text-on-surface-variant">다음 마감일</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((acc) => (
                <tr key={acc.id}
                  onClick={() => onSelectAccount && onSelectAccount(acc.node_id)}
                  className={`border-t border-outline-variant/50 cursor-pointer hover:bg-surface-container transition ${
                    acc.progress >= 100 ? "bg-secondary-container/20" : ""
                  }`}>
                  <td className="px-4 py-2.5 font-semibold text-on-surface">{acc.name}</td>
                  <td className="px-3 py-2.5 text-on-surface-variant">{acc.phase_name}</td>
                  <td className="text-center px-3 py-2.5">{acc.total_tasks}</td>
                  <td className="text-center px-3 py-2.5">{acc.done_tasks}</td>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <ProgressBar progress={acc.progress} />
                      <span className="text-[11px] font-bold w-8 text-right">{acc.progress}%</span>
                    </div>
                  </td>
                  <td className={`px-3 py-2.5 ${acc.overdue ? "text-error font-bold" : "text-on-surface-variant"}`}>
                    {acc.next_deadline || "-"}
                    {acc.overdue && <span className="ml-1 text-[10px]">(초과)</span>}
                  </td>
                </tr>
              ))}
              {accounts.length === 0 && (
                <tr><td colSpan={6} className="text-center py-6 text-outline">계정과목이 없습니다</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
        {/* Status chart */}
        <div className="bg-surface-container rounded-xl p-4">
          <h4 className="text-sm font-headline font-bold text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-primary">donut_large</span>
            상태별 요약
          </h4>
          <DonutChart statusCounts={status_counts} total={total_tasks} />
        </div>

        {/* Assignee breakdown */}
        <div className="bg-surface-container rounded-xl p-4">
          <h4 className="text-sm font-headline font-bold text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px] text-primary">group</span>
            담당자별 업무 분배
          </h4>
          {assignees.length === 0 ? (
            <p className="text-xs text-outline font-body py-4 text-center">배정된 할일이 없습니다</p>
          ) : (
            <div className="space-y-3">
              {assignees.map((a) => (
                <div key={a.assignee || "_none"}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-label font-semibold text-on-surface flex items-center gap-1.5">
                      <span className="w-6 h-6 rounded-full bg-primary-container flex items-center justify-center text-[10px] font-bold text-white shrink-0">
                        {(a.assignee || "?")[0]}
                      </span>
                      {a.assignee || "미배정"}
                    </span>
                    <span className="text-[11px] font-label text-on-surface-variant">
                      {a.done}/{a.total}건 ({a.progress}%)
                    </span>
                  </div>
                  <ProgressBar progress={a.progress} height={5} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .print\\:hidden { display: none !important; }
          [data-print-area], [data-print-area] * { visibility: visible; }
        }
      `}</style>
    </div>
  );
}
