import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", icon: "dashboard", label: "대시보드" },
  { to: "/engagements", icon: "work", label: "감사업무" },
  { to: "/templates", icon: "description", label: "템플릿" },
  { to: "/icfr", icon: "fact_check", label: "내부회계" },
  { to: "/settings", icon: "settings", label: "설정" },
];

export default function Sidebar({ open, onClose }) {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={onClose} />
      )}

      <aside
        className={`fixed left-0 top-0 bottom-0 w-64 bg-surface-container-low border-r border-outline-variant flex flex-col z-50
          transition-transform duration-200
          ${open ? "translate-x-0" : "-translate-x-full"}
          lg:translate-x-0 lg:z-30`}
      >
        {/* Logo + FY */}
        <div className="px-5 py-6 border-b border-outline-variant">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-primary text-[28px]" style={{ fontVariationSettings: '"FILL" 1, "wght" 500' }}>
              verified
            </span>
            <span className="font-headline text-xl font-bold text-primary tracking-tight">
              AuditLink
            </span>
          </div>
          <div className="mt-3 px-3 py-1.5 bg-primary-fixed rounded-xl text-xs font-label font-semibold text-primary inline-block">
            FY 2025
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ to, icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-label font-medium transition-all ${
                  isActive
                    ? "bg-surface-container-lowest shadow-sm text-primary font-semibold"
                    : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
                }`
              }
            >
              <span className="material-symbols-outlined text-[20px]">
                {icon}
              </span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Bottom */}
        <div className="px-5 py-4 border-t border-outline-variant">
          <p className="text-xs text-outline font-label">v0.1.0</p>
        </div>
      </aside>
    </>
  );
}
