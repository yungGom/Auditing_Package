import { useState, useEffect } from "react";
import { Sidebar, Topbar } from "./components/Shell.jsx";
import { CommandPalette } from "./components/CommandPalette.jsx";
import { QuickMemo } from "./components/QuickMemo.jsx";
import { Dashboard } from "./pages/Dashboard.jsx";
import { Engagements } from "./pages/Engagements.jsx";
import { ICFR } from "./pages/ICFR.jsx";
import { Templates } from "./pages/Templates.jsx";
import { Settings } from "./pages/Settings.jsx";
import { api } from "./api.js";

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [settings, setSettings] = useState(null);
  const [fys, setFys] = useState([]);
  const [engModalOpen, setEngModalOpen] = useState(false);

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => {});
    api.getFYs().then(setFys).catch(() => {});
  }, []);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const activeFy = fys.find((f) => f.is_active);

  // Build a minimal search index from fys
  const searchIndex = [
    ...fys.map((f) => ({ group: "이동", icon: "calendar_today", label: f.label, sub: f.is_active ? "활성" : "", nav: "settings" })),
    { group: "이동", icon: "dashboard",   label: "대시보드",  sub: "진척률 · 마감일 · 캘린더", nav: "dashboard" },
    { group: "이동", icon: "work",         label: "감사업무",  sub: "트리 · 할일 · PBC · 인터뷰", nav: "engagements" },
    { group: "이동", icon: "fact_check",   label: "내부회계",  sub: "ICFR 통제활동 테스트", nav: "icfr" },
    { group: "이동", icon: "description",  label: "템플릿",    sub: "업종별 감사 템플릿", nav: "templates" },
    { group: "이동", icon: "settings",     label: "설정",      sub: "회계연도 · 사용자 · 알림", nav: "settings" },
  ];

  const handleNewEng = () => {
    setTab("engagements");
    setEngModalOpen(true);
  };

  const fullWidth = tab === "engagements";

  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar active={tab} onNav={setTab} settings={settings} />
      <div className="flex-1 ml-56 flex flex-col min-w-0">
        <Topbar
          onNew={handleNewEng}
          onOpenSearch={() => setPaletteOpen(true)}
          notifOpen={notifOpen}
          setNotifOpen={setNotifOpen}
          onNav={setTab}
          overdueCount={0}
        />
        <main className={fullWidth ? "flex-1 flex flex-col" : "flex-1 px-8 py-7 max-w-[1200px] w-full mx-auto"}>
          {tab === "dashboard"   && <Dashboard onNav={setTab} activeFyId={activeFy?.id} />}
          {tab === "engagements" && <Engagements modalOpen={engModalOpen} onModalOpenChange={setEngModalOpen} />}
          {tab === "icfr"        && <ICFR />}
          {tab === "templates"   && <Templates />}
          {tab === "settings"    && <Settings onSettingsChange={setSettings} />}
        </main>
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onNav={(nav) => { setTab(nav); setPaletteOpen(false); }}
        searchIndex={searchIndex}
      />

      <QuickMemo />
    </div>
  );
}
