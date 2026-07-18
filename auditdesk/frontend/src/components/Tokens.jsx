import { STATUS, PRIORITY } from "../constants.js";

export function StatusDot({ k, labelOverride }) {
  const s = STATUS[k] || STATUS.todo;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-sub whitespace-nowrap">
      <span className="w-[7px] h-[7px] rounded-full shrink-0" style={{ background: s.color }} />
      {labelOverride || s.label}
    </span>
  );
}

export function StatusPill({ k, children }) {
  const s = STATUS[k] || STATUS.todo;
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap"
      style={{ background: `${s.color}14`, color: s.color }}
    >
      <span className="w-[6px] h-[6px] rounded-full" style={{ background: s.color }} />
      {children || s.label}
    </span>
  );
}

export function PriorityDot({ p }) {
  const pr = PRIORITY[p] || PRIORITY.mid;
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-faint">
      <span className="w-[6px] h-[6px] rounded-full" style={{ background: pr.color }} />
      {pr.label}
    </span>
  );
}

export function DDay({ date }) {
  if (!date) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(date);
  due.setHours(0, 0, 0, 0);
  const d = Math.round((due - today) / 86400000);
  const label = d === 0 ? "D-Day" : d < 0 ? `D+${-d}` : `D-${d}`;
  const cls = d <= 0 ? "text-[#ef4444]" : d <= 7 ? "text-[#f59e0b]" : "text-sub";
  return <span className={`text-xs font-medium tabular-nums ${cls}`}>{label}</span>;
}

export function Icon({ name, className = "", style }) {
  return (
    <span className={`material-symbols-outlined ${className}`} style={style}>
      {name}
    </span>
  );
}

export function Spinner({ className = "w-5 h-5" }) {
  return (
    <svg className={`animate-spin text-sub ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
