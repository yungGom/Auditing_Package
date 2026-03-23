function App() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-primary text-white px-6 py-4 flex items-center gap-3">
        <span className="material-symbols-outlined text-3xl">verified</span>
        <h1 className="font-headline text-xl font-bold tracking-tight">
          AuditLink
        </h1>
      </header>

      {/* Main Content */}
      <main className="p-6 max-w-5xl mx-auto">
        <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant p-6">
          <h2 className="font-headline text-2xl font-semibold text-on-surface mb-2">
            회계감사 일정관리
          </h2>
          <p className="font-body text-on-surface-variant">
            AuditLink 프로젝트가 성공적으로 초기화되었습니다.
          </p>

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { icon: "dashboard", label: "Dashboard" },
              { icon: "work", label: "Engagements" },
              { icon: "description", label: "Templates" },
            ].map(({ icon, label }) => (
              <div
                key={label}
                className="bg-surface-container-low rounded-xl p-4 border border-outline-variant flex items-center gap-3"
              >
                <span className="material-symbols-outlined text-primary">
                  {icon}
                </span>
                <span className="font-label font-medium text-on-surface">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
