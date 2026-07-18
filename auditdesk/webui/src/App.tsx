// 셸: 3모듈 네비 + 신뢰 뱃지 헤더 — 참조 구현(v2 standalone) 그대로 이식
import React, { useState } from "react";
import Home from "./Home";
import Session from "./Session";
import StatusPage from "./StatusPage";
import { SearchScreen, SettingsScreen, XbrlScreen } from "./Explorer";
import {
  DimScreen, MappingScreen, TaxoScreen, TreeScreen, WorksheetScreen,
} from "./Studio";
import { chip, F_HEAD, F_LABEL, Icon } from "./ui";

export type Route = {
  screen: string; sessionId?: string; tab?: string;
};

const STUDIO_SCREENS = ["taxo", "mapping", "worksheet", "dimtable", "tree"];
const EXPLORER_SCREENS = ["search", "xbrl", "settings"];

const TITLES: Record<string, [string, string]> = {
  home: ["AuditDesk", "홈 — 시즌 여정"],
  session: ["DSD Workbench", "세션 상세"],
  status: ["상태", "E-0"],
  taxo: ["XBRL Studio", "택사노미 체크"],
  mapping: ["XBRL Studio", "매핑 확정"],
  worksheet: ["XBRL Studio", "작성 워크시트"],
  dimtable: ["XBRL Studio", "차원 표 뷰어"],
  tree: ["XBRL Studio", "트리 뷰"],
  search: ["DART Explorer", "공시 검색"],
  xbrl: ["DART Explorer", "XBRL 파이프라인"],
  settings: ["DART Explorer", "설정"],
};

function NavItem({ icon, label, active, chip: chipEl, onClick }: {
  icon: string; label: string; active?: boolean;
  chip?: React.ReactNode; onClick?: () => void;
}) {
  return (
    <div className="navitem" onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 10, padding: "9px 12px",
      borderRadius: 8, font: `${active ? 600 : 500} 13px ${F_LABEL}`,
      color: active ? "#001e40" : "#43474f", cursor: "pointer",
      background: active ? "#fff" : undefined,
      boxShadow: active ? "0 1px 2px rgba(0,0,0,0.05)" : undefined,
    }}>
      <Icon name={icon} size={19} />
      <span style={{
        flex: 1, overflow: "hidden", textOverflow: "ellipsis",
        whiteSpace: "nowrap",
      }}>{label}</span>
      {chipEl}
    </div>
  );
}

function SectionHead({ label, tag, tagFg, tagBg }: {
  label: string; tag: string; tagFg: string; tagBg: string;
}) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0 8px 6px",
    }}>
      <span style={{
        font: `700 10px ${F_LABEL}`, letterSpacing: "0.06em",
        color: "#737780",
      }}>{label}</span>
      <span style={{
        font: `600 9px ${F_LABEL}`, color: tagFg, background: tagBg,
        borderRadius: 4, padding: "2px 6px",
      }}>{tag}</span>
    </div>
  );
}

function parseHash(): Route {
  const h = window.location.hash.replace(/^#\/?/, "");
  const [a, b, c] = h.split("/");
  if (a === "session" && b) return { screen: "session", sessionId: b, tab: c };
  if (a === "status" || STUDIO_SCREENS.includes(a) ||
      EXPLORER_SCREENS.includes(a)) return { screen: a };
  return { screen: "home" };
}

function writeHash(r: Route) {
  window.location.hash =
    r.screen === "home" ? "/" :
    r.screen === "session"
      ? `/session/${r.sessionId}${r.tab ? "/" + r.tab : ""}`
      : `/${r.screen}`;
}

export default function App() {
  const [route, setRouteRaw] = useState<Route>(parseHash);
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  const [xbrlPreset, setXbrlPreset] = useState<
    { corp: string; year: number; report: string } | null>(null);
  const [worksheetDsd, setWorksheetDsd] = useState<string | null>(null);
  const setRoute = (r: Route) => { writeHash(r); setRouteRaw(r); };
  React.useEffect(() => {
    const onHash = () => setRouteRaw(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const [title, sub] = TITLES[route.screen] || TITLES.home;
  // 신뢰 뱃지 — 모듈별 (참조 구현 그대로)
  const trust = EXPLORER_SCREENS.includes(route.screen)
    ? { icon: "public", label: "OpenDART 수신 전용",
        colors: { color: "#4e6874", background: "#cbe7f5" } }
    : STUDIO_SCREENS.includes(route.screen)
      ? { icon: "lock", label: "분석·작성은 로컬 — 코퍼스는 공개데이터",
          colors: { color: "#3a5a2e", background: "#dcead2" } }
      : { icon: "lock", label: "로컬 전용 — 외부 전송 없음",
          colors: { color: "#001e40", background: "#d5e3ff" } };

  const openSession = (sessionId: string, label?: string, tab?: string) => {
    if (label) setSessionLabel(label);
    setRoute({ screen: "session", sessionId, tab });
  };

  return (
    <div style={{
      display: "flex", height: "100vh", overflow: "hidden",
      background: "#f8f9fa", fontFamily: F_LABEL,
    }}>
      {/* ======== SIDEBAR ======== */}
      <nav style={{
        width: 248, flex: "none", background: "#f3f4f5",
        borderRight: "1px solid #c3c6d1", display: "flex",
        flexDirection: "column", padding: "14px 10px 10px",
        overflow: "auto",
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "0 6px 14px", borderBottom: "1px solid #c3c6d1",
          marginBottom: 12,
        }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8, background: "#001e40",
            display: "flex", alignItems: "center", justifyContent: "center",
            flex: "none",
          }}>
            <Icon name="table_view" size={20} color="#fff" fill />
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{
              font: `700 17px ${F_HEAD}`, color: "#001e40",
              letterSpacing: "-0.02em", lineHeight: 1.1,
            }}>AuditDesk</span>
            <span style={{
              font: `600 9px ${F_LABEL}`, color: "#737780",
              letterSpacing: "0.05em",
            }}>DSD · XBRL · DART TOOLKIT</span>
          </div>
        </div>

        <div style={{ marginBottom: 14 }}>
          <SectionHead label="DSD WORKBENCH" tag="로컬 전용"
            tagFg="#001e40" tagBg="#d5e3ff" />
          <NavItem icon="home" label="홈 · 작업 목록"
            active={route.screen === "home"}
            onClick={() => setRoute({ screen: "home" })} />
          {route.screen === "session" && (
            <NavItem icon="table_chart" label={sessionLabel || "세션"} active />
          )}
        </div>
        <div style={{ marginBottom: 14 }}>
          <SectionHead label="XBRL STUDIO" tag="로컬 분석"
            tagFg="#3a5a2e" tagBg="#dcead2" />
          {[["fact_check", "택사노미 체크", "taxo"],
            ["join_inner", "매핑 확정", "mapping"],
            ["edit_note", "작성 워크시트", "worksheet"],
            ["pivot_table_chart", "차원 표 뷰어", "dimtable"],
            ["account_tree", "트리 뷰", "tree"]].map(([ic, lb, key]) => (
            <NavItem key={key} icon={ic} label={lb}
              active={route.screen === key}
              onClick={() => setRoute({ screen: key })} />
          ))}
        </div>
        <div style={{ marginBottom: 14 }}>
          <SectionHead label="DART EXPLORER" tag="수신 전용"
            tagFg="#4e6874" tagBg="#cbe7f5" />
          {[["search", "공시 검색", "search"],
            ["cloud_download", "XBRL 파이프라인", "xbrl"],
            ["settings", "설정", "settings"]].map(([ic, lb, key]) => (
            <NavItem key={key} icon={ic} label={lb}
              active={route.screen === key}
              onClick={() => setRoute({ screen: key })} />
          ))}
        </div>

        <div style={{ flex: 1 }} />
        <div style={{ borderTop: "1px solid #c3c6d1", paddingTop: 8 }}>
          <NavItem icon="monitor_heart" label="상태"
            active={route.screen === "status"}
            chip={<span style={{
              font: `600 9px ${F_LABEL}`, color: "#737780",
              background: "#e1e3e4", borderRadius: 4, padding: "2px 6px",
            }}>E-0</span>}
            onClick={() => setRoute({ screen: "status" })} />
          <div style={{
            padding: "8px 12px 2px", font: `500 10px ${F_LABEL}`,
            color: "#737780",
          }}>v2.0 · 로컬 실행 (localhost:8710)</div>
        </div>
      </nav>

      {/* ======== MAIN ======== */}
      <div style={{
        flex: 1, display: "flex", flexDirection: "column", minWidth: 0,
      }}>
        <header style={{
          height: 56, flex: "none", display: "flex", alignItems: "center",
          gap: 12, padding: "0 24px", background: "rgba(255,255,255,0.8)",
          backdropFilter: "blur(12px)", borderBottom: "1px solid #c3c6d1",
          position: "relative", zIndex: 5,
        }}>
          <h1 style={{
            margin: 0, font: `700 18px ${F_HEAD}`, color: "#191c1d",
            letterSpacing: "-0.01em",
          }}>{title}</h1>
          <span style={{ font: `500 12px ${F_LABEL}`, color: "#737780" }}>
            {sub}</span>
          <div style={{ flex: 1 }} />
          <div style={{ ...chip(trust.colors.color, trust.colors.background),
            gap: 5, padding: "4px 10px" }}>
            <Icon name={trust.icon} size={15} />
            <span>{trust.label}</span>
          </div>
        </header>

        <main style={{ flex: 1, overflow: "auto", minHeight: 0 }}>
          {route.screen === "home" && <Home openSession={openSession} />}
          {route.screen === "status" && <StatusPage />}
          {route.screen === "session" && (
            <Session key={route.sessionId} sessionId={route.sessionId!}
              initialTab={route.tab} />
          )}
          {route.screen === "taxo" && <TaxoScreen />}
          {route.screen === "mapping" && <MappingScreen />}
          {route.screen === "worksheet" && (
            <WorksheetScreen key={worksheetDsd || "ws"}
              presetDsd={worksheetDsd} />
          )}
          {route.screen === "dimtable" && <DimScreen />}
          {route.screen === "tree" && <TreeScreen />}
          {route.screen === "search" && (
            <SearchScreen goXbrl={(corp, year, report) => {
              setXbrlPreset({ corp, year, report });
              setRoute({ screen: "xbrl" });
            }} goWorksheet={(dsdPath) => {
              setWorksheetDsd(dsdPath);
              setRoute({ screen: "worksheet" });
            }} />
          )}
          {route.screen === "xbrl" && (
            <XbrlScreen key={JSON.stringify(xbrlPreset)}
              preset={xbrlPreset} />
          )}
          {route.screen === "settings" && <SettingsScreen />}
        </main>
      </div>
    </div>
  );
}
