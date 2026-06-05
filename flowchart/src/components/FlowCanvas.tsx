import { MouseEvent as ReactMouseEvent, useCallback, useState } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Connection,
  ConnectionMode,
  Controls,
  MarkerType,
  MiniMap,
  NodeTypes,
  SelectionMode,
  addEdge,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";

import { ActivityNode } from "./ActivityNode";
import { ShapeNode } from "./ShapeNode";
import { CanvasHeaderTable } from "./CanvasHeaderTable";
import {
  canvasDesign as C,
  EdgeShape,
  EDGE_SHAPE_LABELS,
} from "../design";
import { useFlow } from "../state/flowState";
import { SHAPES, ShapeKey } from "../shapes";

const nodeTypes: NodeTypes = {
  activity: ActivityNode,
  shape: ShapeNode,
};

/* ─────────────────────────────────────────────
 * 캔버스 본체
 *
 * v10: 자석(snap-to-grid / 핸들·축 정렬 스냅) 제거 → 자유 픽셀 이동.
 *      대신 노드 고정(lock) 으로 위치를 잠근다 (단축키 L · 상단바 전체잠금).
 * ───────────────────────────────────────────── */

export interface FlowCanvasProps {
  armedShape: ShapeKey | null;
  onCanvasClickWhileArmed: (flowPos: { x: number; y: number }) => void;
  onCancelArmed: () => void;
}

export function FlowCanvas({
  armedShape,
  onCanvasClickWhileArmed,
  onCancelArmed,
}: FlowCanvasProps) {
  const {
    nodes,
    edges,
    setEdges,
    onNodesChange,
    onEdgesChange,
  } = useFlow();

  // edgeShape 는 "새로 그리는 엣지의 기본 모양" 으로만 동작한다.
  //   - onConnect / defaultEdgeOptions 가 이 값을 사용해서 새 엣지를 만든다.
  //   - 기존 엣지는 자동으로 덮어쓰지 않는다 — 엣지 클릭 → 우측 EditPanel 에서 개별 변경.
  //   - 일괄 변경이 필요하면 셀렉터 옆 "전체 적용" 버튼으로 명시적으로 호출.
  const [edgeShape, setEdgeShape] = useState<EdgeShape>("smoothstep");

  const applyEdgeShapeToAll = useCallback(() => {
    setEdges((prev) => prev.map((e) => ({ ...e, type: edgeShape })));
  }, [edgeShape, setEdges]);

  const reactFlow = useReactFlow();

  const onConnect = useCallback(
    (conn: Connection) =>
      setEdges((eds) =>
        addEdge(
          {
            ...conn,
            type: edgeShape,
            markerEnd: { type: MarkerType.ArrowClosed, color: C.edgeStroke },
            style: { stroke: C.edgeStroke, strokeWidth: C.edgeStrokeWidth },
          },
          eds,
        ),
      ),
    [setEdges, edgeShape],
  );

  // armed 모드에서 빈 캔버스(pane) 클릭 시: flow 좌표 변환 후 단축키 hook 에 위임.
  const onPaneClick = useCallback(
    (e: ReactMouseEvent) => {
      if (!armedShape) return;
      const flowPos = reactFlow.screenToFlowPosition({
        x: e.clientX,
        y: e.clientY,
      });
      onCanvasClickWhileArmed(flowPos);
    },
    [armedShape, onCanvasClickWhileArmed, reactFlow],
  );

  return (
    <div
      className={
        "relative h-full w-full " +
        (armedShape ? "cursor-crosshair" : "")
      }
    >
      <CanvasHeaderTable />
      <EdgeShapeSelector
        value={edgeShape}
        onChange={setEdgeShape}
        onApplyAll={applyEdgeShapeToAll}
      />

      {armedShape && (
        <ArmedShapeBadge shapeKey={armedShape} onCancel={onCancelArmed} />
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        connectionRadius={C.connectionRadius}
        // loose 모드: 어느 핸들(left/right/top/bottom) ↔ 어느 핸들이든 연결 가능
        connectionMode={ConnectionMode.Loose}
        selectionMode={SelectionMode.Partial}
        multiSelectionKeyCode="Control"
        deleteKeyCode={["Delete", "Backspace"]}
        defaultEdgeOptions={{
          type: edgeShape,
          markerEnd: { type: MarkerType.ArrowClosed, color: C.edgeStroke },
          style: { stroke: C.edgeStroke, strokeWidth: C.edgeStrokeWidth },
        }}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={C.bgDotGap}
          size={C.bgDotSize}
        />
        <Controls position="bottom-right" />
        <MiniMap pannable zoomable position="top-right" />
      </ReactFlow>
    </div>
  );
}

/* ─────────────────────────────────────────────
 * 좌상단 화살표 모양 셀렉터
 * ───────────────────────────────────────────── */

function EdgeShapeSelector({
  value,
  onChange,
  onApplyAll,
}: {
  value: EdgeShape;
  onChange: (v: EdgeShape) => void;
  onApplyAll: () => void;
}) {
  const options: EdgeShape[] = ["straight", "smoothstep", "default"];
  return (
    <div className="pointer-events-auto absolute left-3 top-12 z-10 flex items-center gap-2 rounded-md border border-slate-300 bg-white/95 px-2 py-1 shadow-sm backdrop-blur">
      <span
        className="text-[10px] font-medium uppercase tracking-wider text-slate-500"
        title="새로 그리는 엣지의 기본 모양. 기존 엣지는 클릭 후 우측 패널에서 개별 변경."
      >
        새 엣지 기본
      </span>
      <div className="inline-flex overflow-hidden rounded border border-slate-300 text-xs">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={
              "px-2 py-0.5 transition " +
              (value === opt
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-700 hover:bg-slate-100")
            }
          >
            {EDGE_SHAPE_LABELS[opt]}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={onApplyAll}
        className="rounded border border-slate-300 px-2 py-0.5 text-[11px] text-slate-600 hover:border-slate-500 hover:bg-slate-100"
        title={`현재 모든 엣지를 "${EDGE_SHAPE_LABELS[value]}" 으로 일괄 변경`}
      >
        ↻ 전체 적용
      </button>
    </div>
  );
}

/* ─────────────────────────────────────────────
 * "추가 대기 중" 배지 — armed 상태에서 캔버스 상단 중앙에 표시
 * ───────────────────────────────────────────── */

function ArmedShapeBadge({
  shapeKey,
  onCancel,
}: {
  shapeKey: ShapeKey;
  onCancel: () => void;
}) {
  const def = SHAPES.find((s) => s.key === shapeKey);
  return (
    <div className="pointer-events-auto absolute left-1/2 top-12 z-10 flex -translate-x-1/2 items-center gap-2 rounded-md border border-slate-900 bg-slate-900 px-3 py-1.5 text-xs text-white shadow-lg">
      {def?.shortcut && (
        <kbd className="rounded border border-slate-600 bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] font-semibold">
          {def.shortcut}
        </kbd>
      )}
      <span className="font-semibold">{def?.label ?? shapeKey}</span>
      <span className="text-slate-300">
        추가 대기 — 캔버스 클릭으로 위치 지정 (연속 가능)
      </span>
      <button
        type="button"
        onClick={onCancel}
        className="rounded border border-slate-600 px-1.5 py-0.5 text-[10px] hover:bg-slate-800"
        title="Esc"
      >
        취소
      </button>
    </div>
  );
}
