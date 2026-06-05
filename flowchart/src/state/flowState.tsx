import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Edge,
  EdgeChange,
  Node,
  NodeChange,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
} from "reactflow";

import type {
  Activity,
  ControlData,
  HeaderInfo,
  RiskData,
} from "../types";
import { genManualId } from "../types";
import type { ShapeKey } from "../shapes";
import type { ActivityNodeData } from "../components/ActivityNode";
import type { NonActivityShape, ShapeNodeData } from "../components/ShapeNode";
import { shapeNodeDesign } from "../design";

/**
 * 멀티 flowchart 컨텍스트.
 *
 *  - flowcharts: 코드별 노드/엣지 셋트 배열 (등장 순)
 *  - activeCode: 현재 캔버스에 표시·편집 중인 flowchart 코드
 *  - 기존 API (nodes, edges, setNodes, setEdges, addNode, ...) 는 모두
 *    "active flowchart 에 대해서만" 동작하도록 유지 → 기존 컴포넌트 무수정.
 */

export type FlowNode = Node<ActivityNodeData | ShapeNodeData>;

export interface FlowchartState {
  code: string; // 예: "FA21", "FA31" or "DEFAULT" (단일 모드)
  name: string; // 예: "유지보수" — 헤더 표 소분류, 드롭다운 라벨에 사용
  nodes: FlowNode[];
  edges: Edge[];
}

export interface FlowContextValue {
  /* ── 활성 flowchart 의 노드/엣지 (기존 API 유지) ── */
  nodes: FlowNode[];
  edges: Edge[];
  setNodes: React.Dispatch<React.SetStateAction<FlowNode[]>>;
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;

  /* ── 멀티 flowchart 제어 ── */
  flowcharts: FlowchartState[]; // read-only 목록 (드롭다운에 사용)
  activeCode: string;
  setActiveCode: (code: string) => void;

  /* ── 노드·엣지 액션 (활성 flowchart 에 적용) ── */
  addNode: (key: ShapeKey, position?: { x: number; y: number }) => void;
  deleteSelected: () => void;
  updateActivityField: (id: string, partial: Partial<Activity>) => void;
  updateShapeField: (id: string, partial: Partial<ShapeNodeData>) => void;
  updateEdge: (id: string, partial: Partial<Edge>) => void;

  /* ── 단일 선택 (편집 패널용) ── */
  selectedNode: FlowNode | null;
  selectedEdge: Edge | null;
  selectedCount: number;

  /* ── 일괄 로드 (엑셀 업로드 결과 반영) ── */
  loadFlowcharts: (input: {
    flowcharts: FlowchartState[];
    headerInfo: HeaderInfo;
    controls?: ControlData[];
    risks?: RiskData[];
    activeCode?: string;
  }) => void;

  /* ── 헤더 정보 ── */
  headerInfo: HeaderInfo;
  setHeaderInfo: (h: HeaderInfo) => void;

  /* ── Undo/Redo (Ctrl+Z / Ctrl+Y) ── */
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;

  /* ── v6: 통제·위험 카탈로그 (엑셀+수기 통합) ── */
  controls: ControlData[];
  risks: RiskData[];
  /** 수기 통제 추가 — 빈 flowchart(START→END)도 함께 생성. 반환: 생성된 통제 ID */
  addControl: (input: Omit<ControlData, "id" | "source">) => string;
  updateControl: (id: string, partial: Partial<ControlData>) => void;
  deleteControl: (id: string) => void;
  duplicateControl: (id: string) => string;
  /** 수기 위험 추가 — 반환: 생성된 위험 ID */
  addRisk: (input: Omit<RiskData, "id" | "source">) => string;
  updateRisk: (id: string, partial: Partial<RiskData>) => void;
  deleteRisk: (id: string) => void;
}

const EMPTY_HEADER: HeaderInfo = {
  company: "",
  processName: "",
  middleCategory: "",
  subProcessName: "",
  flowchartCode: "",
  lastChangeDate: "",
  author: "",
};

const FlowContext = createContext<FlowContextValue | null>(null);

export function useFlow(): FlowContextValue {
  const ctx = useContext(FlowContext);
  if (!ctx) throw new Error("useFlow must be used inside <FlowProvider>");
  return ctx;
}

/* ─────────────────────────────────────────────
 * 새 노드 생성 헬퍼
 * ───────────────────────────────────────────── */

function genNodeId(prefix: string): string {
  const rand = Math.random().toString(36).slice(2, 6);
  return `${prefix}-${Date.now().toString(36)}-${rand}`;
}

function defaultActivity(actNo: number): Activity {
  return {
    actNo,
    rcmRow: 0,
    actName: "새 활동",
    teamOverride: "",
    // v8: 통제 정보 비어있음 — 사용자가 EditPanel 에서 입력
    controlNo: undefined,
    controlTypeRaw: undefined,
    keyCaRaw: undefined,
    subSteps: "",
    docNames: "",
    branchInfo: "",
    note: "",
  };
}

function defaultShapeData(
  key: NonActivityShape,
  existingNodes: FlowNode[],
): ShapeNodeData {
  switch (key) {
    case "startEnd": {
      const hasStart = existingNodes.some(
        (n) =>
          n.type === "shape" &&
          (n.data as ShapeNodeData).shapeKey === "startEnd" &&
          (n.data as ShapeNodeData).label.toUpperCase() === "START",
      );
      const hasEnd = existingNodes.some(
        (n) =>
          n.type === "shape" &&
          (n.data as ShapeNodeData).shapeKey === "startEnd" &&
          (n.data as ShapeNodeData).label.toUpperCase() === "END",
      );
      if (!hasStart) return { shapeKey: key, label: "START" };
      if (!hasEnd) return { shapeKey: key, label: "END" };
      return { shapeKey: key, label: "START" };
    }
    case "link": return { shapeKey: key, label: "" };
    case "diamond": return { shapeKey: key, label: "분기" };
    case "risk": return { shapeKey: key, label: "R.??" };
    case "keyControl": return { shapeKey: key, label: "C.??" };
    case "nonkeyControl": return { shapeKey: key, label: "C.??" };
    case "controlType": return { shapeKey: key, label: "M" };
    case "document": return { shapeKey: key, label: "문서" };
    case "db": return { shapeKey: key, label: "DB" };
    case "interface": return { shapeKey: key, label: "I/F" };
  }
}

function nextActNo(nodes: FlowNode[]): number {
  let max = 0;
  for (const n of nodes) {
    if (n.type === "activity") {
      const a = (n.data as ActivityNodeData).activity;
      if (a.actNo > max) max = a.actNo;
    }
  }
  return max + 1;
}

/**
 * 수기 통제 추가 시 함께 만들어지는 빈 flowchart — START → END 두 도형만.
 * 사용자가 활동을 차곡차곡 추가할 출발점.
 */
function buildEmptyFlowchart(code: string, name: string): FlowchartState {
  const seW = shapeNodeDesign.startEnd.width;
  const seH = shapeNodeDesign.startEnd.height;
  const baseY = 280; // FIRST_ROW_ACT_Y 와 동일 — 활동을 추가했을 때 정렬됨
  const startX = 60;
  const endX = startX + 800; // 활동 4개 + gap 정도 여유

  const start: FlowNode = {
    id: `start-${code.toLowerCase()}`,
    type: "shape",
    position: { x: startX, y: baseY + 48 / 2 - seH / 2 },
    data: { shapeKey: "startEnd", label: "START" } as ShapeNodeData,
  };
  const end: FlowNode = {
    id: `end-${code.toLowerCase()}`,
    type: "shape",
    position: { x: endX, y: baseY + 48 / 2 - seH / 2 },
    data: { shapeKey: "startEnd", label: "END" } as ShapeNodeData,
  };
  void seW; // 다음 활동 추가 시 자동 정렬 로직에서 사용 (현재는 단순 배치)

  return {
    code,
    name,
    nodes: [start, end],
    edges: [],
  };
}

/* ─────────────────────────────────────────────
 * Provider
 * ───────────────────────────────────────────── */

export function FlowProvider({
  children,
  initialFlowcharts,
  initialHeaderInfo,
}: {
  children: ReactNode;
  /** 부트스트랩 시 1개 이상의 flowchart 가 있어야 함. */
  initialFlowcharts: FlowchartState[];
  initialHeaderInfo?: HeaderInfo;
}) {
  const [flowcharts, setFlowcharts] = useState<FlowchartState[]>(
    initialFlowcharts,
  );
  const [activeCode, setActiveCodeRaw] = useState<string>(
    initialFlowcharts[0]?.code ?? "DEFAULT",
  );
  const [headerInfo, setHeaderInfo] = useState<HeaderInfo>(
    initialHeaderInfo ?? EMPTY_HEADER,
  );
  const [controls, setControls] = useState<ControlData[]>([]);
  const [risks, setRisks] = useState<RiskData[]>([]);

  const reactFlow = useReactFlow();
  const addCounter = useRef(0);

  /* ─────────────────────────────────────────────
   * Undo/Redo — 디바운스된 스냅샷 스택
   *
   *   - state 가 바뀌면 300ms idle 후에 *이전* lastCommitted 를 past 로 push.
   *   - past/future 는 shallow snapshot (모든 setter 가 immutable 패턴이라 안전).
   *   - 드래그처럼 짧은 시간에 수많은 변경이 일어나도 한 스냅샷으로 합쳐짐.
   *   - undo/redo 호출은 isApplyingHistoryRef 로 다시 history 에 잡히지 않게.
   * ───────────────────────────────────────────── */
  interface HistorySnapshot {
    flowcharts: FlowchartState[];
    headerInfo: HeaderInfo;
    controls: ControlData[];
    risks: RiskData[];
    activeCode: string;
  }
  const MAX_HISTORY = 50;
  const COMMIT_DEBOUNCE_MS = 300;

  const historyPast = useRef<HistorySnapshot[]>([]);
  const historyFuture = useRef<HistorySnapshot[]>([]);
  const lastCommittedRef = useRef<HistorySnapshot | null>(null);
  const commitTimerRef = useRef<number | null>(null);
  const isApplyingHistoryRef = useRef(false);
  // canUndo/canRedo 갱신용 — past/future 가 변할 때마다 +1
  const [historyVersion, setHistoryVersion] = useState(0);

  const takeSnapshot = useCallback(
    (): HistorySnapshot => ({
      // 얕은 복사 — 모든 setter 가 새 배열/객체를 만드는 immutable 패턴이라
      // 이전 ref 는 그 시점의 상태를 그대로 가리킴.
      flowcharts,
      headerInfo,
      controls,
      risks,
      activeCode,
    }),
    [flowcharts, headerInfo, controls, risks, activeCode],
  );

  // state 변경 → 디바운스된 commit. 변경 시점의 *이전* lastCommitted 를 past 로 push.
  useEffect(() => {
    if (isApplyingHistoryRef.current) {
      isApplyingHistoryRef.current = false;
      return;
    }
    if (commitTimerRef.current !== null) {
      window.clearTimeout(commitTimerRef.current);
    }
    commitTimerRef.current = window.setTimeout(() => {
      const snap = takeSnapshot();
      const last = lastCommittedRef.current;
      if (last) {
        historyPast.current.push(last);
        if (historyPast.current.length > MAX_HISTORY) {
          historyPast.current.shift();
        }
        // 새 변경이 들어왔으므로 redo 스택 비움
        historyFuture.current = [];
      }
      lastCommittedRef.current = snap;
      setHistoryVersion((v) => v + 1);
    }, COMMIT_DEBOUNCE_MS);
    return () => {
      // 다음 effect 호출 직전에 cleanup — 다음 변경이 새 타이머를 설정
    };
  }, [flowcharts, headerInfo, controls, risks, activeCode, takeSnapshot]);

  const applySnapshot = useCallback((snap: HistorySnapshot) => {
    isApplyingHistoryRef.current = true;
    setFlowcharts(snap.flowcharts);
    setHeaderInfo(snap.headerInfo);
    setControls(snap.controls);
    setRisks(snap.risks);
    setActiveCodeRaw(snap.activeCode);
  }, []);

  const undo = useCallback(() => {
    const past = historyPast.current;
    if (past.length === 0) return;
    // 진행 중인 debounce commit 취소 — 안 그러면 undo 직후에 덮어씌워짐
    if (commitTimerRef.current !== null) {
      window.clearTimeout(commitTimerRef.current);
      commitTimerRef.current = null;
    }
    const current = takeSnapshot();
    historyFuture.current.push(current);
    const prev = past.pop()!;
    lastCommittedRef.current = prev;
    applySnapshot(prev);
    setHistoryVersion((v) => v + 1);
  }, [takeSnapshot, applySnapshot]);

  const redo = useCallback(() => {
    const future = historyFuture.current;
    if (future.length === 0) return;
    if (commitTimerRef.current !== null) {
      window.clearTimeout(commitTimerRef.current);
      commitTimerRef.current = null;
    }
    const current = takeSnapshot();
    historyPast.current.push(current);
    const next = future.pop()!;
    lastCommittedRef.current = next;
    applySnapshot(next);
    setHistoryVersion((v) => v + 1);
  }, [takeSnapshot, applySnapshot]);

  // canUndo/canRedo 는 historyVersion 으로 강제 재계산
  const canUndo = historyVersion >= 0 && historyPast.current.length > 0;
  const canRedo = historyVersion >= 0 && historyFuture.current.length > 0;

  // 활성 flowchart 의 nodes/edges 노출 (메모화)
  const active = useMemo(
    () =>
      flowcharts.find((f) => f.code === activeCode) ?? flowcharts[0] ?? null,
    [flowcharts, activeCode],
  );
  const nodes: FlowNode[] = active?.nodes ?? [];
  const edges: Edge[] = active?.edges ?? [];

  /** 활성 flowchart 만 수정하는 헬퍼. 그 외는 그대로 유지. */
  const mutateActive = useCallback(
    (
      mut: (cur: FlowchartState) => Partial<FlowchartState>,
    ) => {
      setFlowcharts((prev) =>
        prev.map((f) =>
          f.code === activeCode ? { ...f, ...mut(f) } : f,
        ),
      );
    },
    [activeCode],
  );

  const setNodes: React.Dispatch<React.SetStateAction<FlowNode[]>> = useCallback(
    (updater) => {
      mutateActive((cur) => ({
        nodes:
          typeof updater === "function"
            ? (updater as (n: FlowNode[]) => FlowNode[])(cur.nodes)
            : updater,
      }));
    },
    [mutateActive],
  );
  const setEdges: React.Dispatch<React.SetStateAction<Edge[]>> = useCallback(
    (updater) => {
      mutateActive((cur) => ({
        edges:
          typeof updater === "function"
            ? (updater as (e: Edge[]) => Edge[])(cur.edges)
            : updater,
      }));
    },
    [mutateActive],
  );

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      mutateActive((cur) => ({
        nodes: applyNodeChanges(changes, cur.nodes) as FlowNode[],
      }));
    },
    [mutateActive],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      mutateActive((cur) => ({
        edges: applyEdgeChanges(changes, cur.edges),
      }));
    },
    [mutateActive],
  );

  const setActiveCode = useCallback((code: string) => {
    setActiveCodeRaw(code);
  }, []);

  const addNode = useCallback(
    (key: ShapeKey, position?: { x: number; y: number }) => {
      let pos = position;
      if (!pos) {
        const containerEl = document.querySelector(
          ".react-flow",
        ) as HTMLElement | null;
        const offset = ((addCounter.current % 6) - 2.5) * 20;
        addCounter.current += 1;
        if (containerEl) {
          const rect = containerEl.getBoundingClientRect();
          const center = reactFlow.screenToFlowPosition({
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2,
          });
          pos = { x: center.x + offset, y: center.y + offset };
        } else {
          pos = { x: 280 + offset, y: 200 + offset };
        }
      }

      let newNode: FlowNode;
      const curNodes = nodes;
      if (key === "activity") {
        const actNo = nextActNo(curNodes);
        newNode = {
          id: genNodeId("act"),
          type: "activity",
          position: pos,
          data: { activity: defaultActivity(actNo) },
          selected: true,
        };
      } else {
        const k = key as NonActivityShape;
        newNode = {
          id: genNodeId(k),
          type: "shape",
          position: pos,
          data: defaultShapeData(k, curNodes),
          selected: true,
        };
      }

      setNodes((prev) => [
        ...prev.map((n) => (n.selected ? { ...n, selected: false } : n)),
        newNode,
      ]);
    },
    [nodes, setNodes, reactFlow],
  );

  const deleteSelected = useCallback(() => {
    setNodes((prev) => prev.filter((n) => !n.selected));
    setEdges((prev) => prev.filter((e) => !e.selected));
  }, [setNodes, setEdges]);

  const updateActivityField = useCallback(
    (id: string, partial: Partial<Activity>) => {
      setNodes((prev) =>
        prev.map((n) => {
          if (n.id !== id || n.type !== "activity") return n;
          const cur = (n.data as ActivityNodeData).activity;
          return {
            ...n,
            data: { activity: { ...cur, ...partial } },
          } as FlowNode;
        }),
      );
    },
    [setNodes],
  );

  const updateShapeField = useCallback(
    (id: string, partial: Partial<ShapeNodeData>) => {
      setNodes((prev) =>
        prev.map((n) => {
          if (n.id !== id || n.type !== "shape") return n;
          return {
            ...n,
            data: { ...(n.data as ShapeNodeData), ...partial },
          } as FlowNode;
        }),
      );
    },
    [setNodes],
  );

  const updateEdge = useCallback(
    (id: string, partial: Partial<Edge>) => {
      setEdges((prev) =>
        prev.map((e) => (e.id === id ? { ...e, ...partial } : e)),
      );
    },
    [setEdges],
  );


  const loadFlowcharts = useCallback(
    (input: {
      flowcharts: FlowchartState[];
      headerInfo: HeaderInfo;
      controls?: ControlData[];
      risks?: RiskData[];
      activeCode?: string;
    }) => {
      setFlowcharts(input.flowcharts);
      setHeaderInfo(input.headerInfo);
      if (input.controls) setControls(input.controls);
      if (input.risks) setRisks(input.risks);
      const next = input.activeCode ?? input.flowcharts[0]?.code ?? "DEFAULT";
      setActiveCodeRaw(next);
    },
    [],
  );

  /* ── v6: 통제/위험 카탈로그 액션 ── */

  /**
   * 수기 통제 추가. 같은 flowchartCode 의 flowchart 가 이미 있으면 그것을 활성화,
   * 없으면 START→END 만 있는 빈 flowchart 를 새로 만들고 활성화한다.
   */
  const addControl = useCallback(
    (input: Omit<ControlData, "id" | "source">): string => {
      const id = genManualId("ctrl");
      const newControl: ControlData = {
        ...input,
        id,
        source: "manual",
      };
      setControls((prevControls) => {
        const isFreshStart = prevControls.length === 0;
        setFlowcharts((prev) => {
          if (prev.some((f) => f.code === newControl.flowchartCode)) return prev;
          const fc = buildEmptyFlowchart(
            newControl.flowchartCode,
            newControl.subProcessName || newControl.flowchartCode,
          );
          // 부트스트랩 "DEFAULT" flowchart 가 있고 카탈로그가 비어있던 첫 수기 추가
          // 라면 DEFAULT 를 새 것으로 교체 (더미 데이터로 시작했다는 신호).
          if (
            isFreshStart &&
            prev.length === 1 &&
            prev[0].code === "DEFAULT"
          ) {
            return [fc];
          }
          return [...prev, fc];
        });
        return [...prevControls, newControl];
      });
      setActiveCodeRaw(newControl.flowchartCode);
      return id;
    },
    [],
  );

  const updateControl = useCallback(
    (id: string, partial: Partial<ControlData>) => {
      setControls((prev) =>
        prev.map((c) => (c.id === id ? { ...c, ...partial } : c)),
      );
      // flowchart 이름(소분류) 동기화
      if (partial.subProcessName != null || partial.flowchartCode != null) {
        setControls((current) => {
          const target = current.find((c) => c.id === id);
          if (!target) return current;
          setFlowcharts((fs) =>
            fs.map((f) =>
              f.code === target.flowchartCode
                ? { ...f, name: target.subProcessName || target.flowchartCode }
                : f,
            ),
          );
          return current;
        });
      }
    },
    [],
  );

  const deleteControl = useCallback((id: string) => {
    setControls((prev) => {
      const target = prev.find((c) => c.id === id);
      // 엑셀 통제는 삭제 불가 — UI 에서 비활성화하지만 안전망으로 한 번 더
      if (target && target.source === "excel") return prev;
      // 연관 위험의 linkedControlId 도 해제
      setRisks((rs) =>
        rs.map((r) =>
          r.linkedControlId === id ? { ...r, linkedControlId: undefined } : r,
        ),
      );
      // 같은 flowchartCode 사용 중인 다른 통제가 없으면 flowchart 도 제거
      if (target) {
        const stillUsed = prev.some(
          (c) => c.id !== id && c.flowchartCode === target.flowchartCode,
        );
        if (!stillUsed) {
          setFlowcharts((fs) => fs.filter((f) => f.code !== target.flowchartCode));
        }
      }
      return prev.filter((c) => c.id !== id);
    });
  }, []);

  const duplicateControl = useCallback(
    (id: string): string => {
      const target = controls.find((c) => c.id === id);
      if (!target) return "";
      const newId = genManualId("ctrl");
      const newCode = `${target.flowchartCode}-COPY`;
      const newControl: ControlData = {
        ...target,
        id: newId,
        source: "manual",
        flowchartCode: newCode,
        controlNo: `${target.controlNo}-copy`,
      };
      setControls((prev) => [...prev, newControl]);
      setFlowcharts((prev) => [
        ...prev,
        buildEmptyFlowchart(newCode, target.subProcessName || newCode),
      ]);
      setActiveCodeRaw(newCode);
      return newId;
    },
    [controls],
  );

  const addRisk = useCallback(
    (input: Omit<RiskData, "id" | "source">): string => {
      const id = genManualId("risk");
      const newRisk: RiskData = { ...input, id, source: "manual" };
      setRisks((prev) => [...prev, newRisk]);
      return id;
    },
    [],
  );

  const updateRisk = useCallback(
    (id: string, partial: Partial<RiskData>) => {
      setRisks((prev) =>
        prev.map((r) => (r.id === id ? { ...r, ...partial } : r)),
      );
    },
    [],
  );

  const deleteRisk = useCallback((id: string) => {
    setRisks((prev) => {
      const target = prev.find((r) => r.id === id);
      if (target && target.source === "excel") return prev;
      return prev.filter((r) => r.id !== id);
    });
  }, []);

  const selectedNodes = useMemo(
    () => nodes.filter((n) => n.selected),
    [nodes],
  );
  const selectedEdges = useMemo(
    () => edges.filter((e) => e.selected),
    [edges],
  );
  const selectedCount = selectedNodes.length + selectedEdges.length;
  const selectedNode =
    selectedNodes.length === 1 && selectedEdges.length === 0
      ? selectedNodes[0]
      : null;
  const selectedEdge =
    selectedEdges.length === 1 && selectedNodes.length === 0
      ? selectedEdges[0]
      : null;

  const value: FlowContextValue = {
    nodes,
    edges,
    setNodes,
    setEdges,
    onNodesChange,
    onEdgesChange,

    flowcharts,
    activeCode,
    setActiveCode,

    addNode,
    deleteSelected,
    updateActivityField,
    updateShapeField,
    updateEdge,

    selectedNode,
    selectedEdge,
    selectedCount,

    loadFlowcharts,

    headerInfo,
    setHeaderInfo,

    undo,
    redo,
    canUndo,
    canRedo,

    controls,
    risks,
    addControl,
    updateControl,
    deleteControl,
    duplicateControl,
    addRisk,
    updateRisk,
    deleteRisk,
  };

  return (
    <FlowContext.Provider value={value}>{children}</FlowContext.Provider>
  );
}
