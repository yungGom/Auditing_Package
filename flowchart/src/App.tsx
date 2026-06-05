import { useMemo, useState } from "react";
import { ReactFlowProvider } from "reactflow";

import { FlowCanvas } from "./components/FlowCanvas";
import { DesignPreview } from "./components/DesignPreview";
import { LeftSidebar } from "./components/LeftSidebar";
import { Sidebar } from "./components/Sidebar";
import { Topbar, AppView } from "./components/Topbar";
import { ShortcutHelpModal } from "./components/ShortcutHelpModal";
import { FlowProvider, FlowchartState, FlowNode } from "./state/flowState";
import { buildInitialFlow } from "./state/initialFlow";
import { useShortcuts } from "./state/useShortcuts";
import { useCopyPaste } from "./state/useCopyPaste";

export default function App() {
  const [view, setView] = useState<AppView>("canvas");

  // 부트스트랩 더미 — 후속 단계에서 엑셀 파싱 결과로 교체됨.
  // 부트스트랩은 "DEFAULT" 한 개의 flowchart 만 가진 상태로 시작한다.
  const initialFlowcharts = useMemo<FlowchartState[]>(() => {
    const { nodes, edges } = buildInitialFlow();
    return [
      {
        code: "DEFAULT",
        name: "부트스트랩 샘플",
        nodes: nodes as FlowNode[],
        edges,
      },
    ];
  }, []);

  return (
    <ReactFlowProvider>
      <FlowProvider initialFlowcharts={initialFlowcharts}>
        <AppShell view={view} setView={setView} />
      </FlowProvider>
    </ReactFlowProvider>
  );
}

/**
 * AppShell 은 FlowProvider 내부에서 렌더되어야 useShortcuts(→ useFlow) 가
 * 정상 동작한다. 그래서 App 본체 트리에서 한 단계 더 들어간 컴포넌트로 분리.
 */
function AppShell({
  view,
  setView,
}: {
  view: AppView;
  setView: (v: AppView) => void;
}) {
  const {
    armedShape,
    helpOpen,
    setHelpOpen,
    cancelArmed,
    onCanvasClickWhileArmed,
  } = useShortcuts();

  // Ctrl+C/V/D/A — 복사·붙여넣기·복제·전체선택
  useCopyPaste();

  return (
    <div className="flex h-full flex-col">
      <Topbar
        view={view}
        onChangeView={setView}
        onOpenHelp={() => setHelpOpen(true)}
      />
      {view === "canvas" ? (
        <div className="flex min-h-0 flex-1">
          <LeftSidebar />
          <main className="min-w-0 flex-1 bg-slate-50">
            <FlowCanvas
              armedShape={armedShape}
              onCanvasClickWhileArmed={onCanvasClickWhileArmed}
              onCancelArmed={cancelArmed}
            />
          </main>
          <Sidebar />
        </div>
      ) : (
        <main className="flex-1 bg-slate-50">
          <DesignPreview />
        </main>
      )}

      <ShortcutHelpModal
        open={helpOpen}
        onClose={() => setHelpOpen(false)}
      />
    </div>
  );
}
