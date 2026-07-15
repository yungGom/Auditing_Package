import { NAV } from "../constants.js";
import { Icon } from "./Tokens.jsx";

export function Sidebar({ active, onNav, settings }) {
  const name = settings?.user_name || "사용자";
  const org = settings?.org || "";
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-56 bg-canvas border-r border-line flex flex-col z-30">
      <div className="px-4 pt-5 pb-4">
        <div className="flex items-center gap-2">
          <Icon name="verified" className="text-[20px]" style={{ color: "var(--lnac)", fontVariationSettings: '"FILL" 1' }} />
          <span className="text-sm font-semibold text-ink">AuditLink</span>
          <span className="ml-auto text-[11px] text-faint font-medium px-1.5 py-0.5 rounded bg-line/60">v2</span>
        </div>
      </div>
      <nav className="flex-1 px-2 flex flex-col gap-0.5">
        {NAV.map(({ key, icon, label }) => {
          const isActive = active === key;
          return (
            <button
              key={key}
              onClick={() => onNav(key)}
              className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-sm transition-colors ${
                isActive ? "text-[color:var(--lnac)] font-medium" : "text-sub hover:bg-[#f4f4f5] hover:text-ink"
              }`}
              style={isActive ? { background: "color-mix(in srgb, var(--lnac) 8%, transparent)" } : undefined}
            >
              <Icon name={icon} className={`text-[20px] ${isActive ? "text-[color:var(--lnac)]" : "text-faint"}`} />
              {label}
            </button>
          );
        })}
      </nav>
      <div className="px-4 py-4 flex items-center gap-2.5">
        <span className="w-6 h-6 rounded-full bg-line2 flex items-center justify-center text-[10px] font-semibold text-sub shrink-0">
          {name.slice(0, 1)}
        </span>
        <div className="min-w-0">
          <p className="text-xs font-medium text-ink truncate">{name}</p>
          <p className="text-[10px] text-faint truncate">{org}</p>
        </div>
      </div>
    </aside>
  );
}

export function Topbar({ onNew, onOpenSearch, notifOpen, setNotifOpen, onNav, overdueCount }) {
  return (
    <header className="sticky top-0 z-20 h-12 bg-canvas/90 backdrop-blur border-b border-line flex items-center justify-between px-6">
      <button
        onClick={onOpenSearch}
        className="relative w-72 flex items-center gap-2 pl-2.5 pr-2 py-1.5 text-sm bg-[#f4f4f5] rounded-lg text-faint hover:bg-[#eeeef0] transition"
      >
        <Icon name="search" className="text-[16px]" />
        <span className="flex-1 text-left">검색</span>
        <span className="text-[10px] border border-line2 rounded px-1 py-px">⌘K</span>
      </button>
      <div className="flex items-center gap-1">
        <div className="relative">
          <button
            onClick={() => setNotifOpen((o) => !o)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] hover:text-sub transition relative"
          >
            <Icon name="notifications" className="text-[20px]" />
            {overdueCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-[#ef4444]" />
            )}
          </button>
          {notifOpen && <NotifDropdown onClose={() => setNotifOpen(false)} onNav={onNav} />}
        </div>
        <button
          onClick={onNew}
          className="ml-2 px-3 py-1.5 text-white text-[13px] font-medium rounded-lg hover:opacity-90 transition flex items-center gap-1"
          style={{ background: "var(--lnac)" }}
        >
          <Icon name="add" className="text-[16px]" style={{ fontVariationSettings: '"wght" 400' }} />
          새 감사업무
        </button>
      </div>
    </header>
  );
}

function NotifDropdown({ onClose, onNav }) {
  return (
    <div>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="absolute right-0 top-10 z-50 w-72 bg-white rounded-xl border border-line shadow-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="text-sm font-semibold text-ink">알림</span>
          <button onClick={onClose} className="text-[11px] text-faint hover:text-sub transition">닫기</button>
        </div>
        <div className="px-4 py-6 text-center text-xs text-faint">
          새 알림이 없습니다
        </div>
      </div>
    </div>
  );
}
