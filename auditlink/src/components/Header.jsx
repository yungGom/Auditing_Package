export default function Header() {
  return (
    <header className="sticky top-0 z-20 h-14 bg-surface-container-lowest/80 backdrop-blur-md border-b border-outline-variant flex items-center justify-between px-6">
      {/* Search */}
      <div className="relative w-80">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
          search
        </span>
        <input
          type="text"
          placeholder="검색..."
          className="w-full pl-10 pr-4 py-2 text-sm font-body bg-surface-container rounded-xl border border-outline-variant placeholder:text-outline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition"
        />
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        <button className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition">
          <span className="material-symbols-outlined text-[20px]">
            notifications
          </span>
        </button>
        <button className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition">
          <span className="material-symbols-outlined text-[20px]">
            help
          </span>
        </button>

        <button className="ml-2 px-4 py-2 bg-gradient-to-r from-primary to-primary-container text-white text-sm font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[18px]">add</span>
          새 감사업무
        </button>

        {/* Profile avatar */}
        <div className="ml-2 w-8 h-8 rounded-full bg-primary-container flex items-center justify-center">
          <span className="text-xs font-label font-bold text-primary-fixed">
            감
          </span>
        </div>
      </div>
    </header>
  );
}
