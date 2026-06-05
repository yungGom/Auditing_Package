import { CSSProperties } from "react";
import { SHAPES, ShapeDef, ShapeKey } from "../shapes";
import { shellDesign } from "../design";
import { useFlow } from "../state/flowState";
import { EditPanel } from "./EditPanel";

/**
 * 우측 사이드바 — 두 섹션이 위/아래로 들어간다.
 *   1) 도형 11종 추가 툴바 (항상 보임) — 클릭 시 useFlow().addNode() 호출
 *   2) 선택된 노드/엣지 편집 패널 — 선택 없으면 빈 상태
 */
export function Sidebar() {
  return (
    <aside
      className="flex shrink-0 flex-col border-l border-slate-200 bg-white"
      style={{ width: shellDesign.sidebarWidth }}
    >
      <ShapeToolbar />
      <div className="h-px bg-slate-200" />
      <EditPanel />
    </aside>
  );
}

/* ─────────────────────────────────────────────
 * 도형 툴바
 * ───────────────────────────────────────────── */

function ShapeToolbar() {
  const { addNode } = useFlow();
  return (
    <section className="flex flex-col gap-2 p-3">
      <SectionLabel>도형 추가</SectionLabel>
      <p className="text-[11px] leading-snug text-slate-500">
        클릭하면 캔버스에 새 도형이 추가됩니다.
        <br />
        단축키 + 캔버스 클릭으로 위치 지정 추가는 다음 단계.
      </p>
      <div className="mt-1 grid grid-cols-1 gap-1">
        {SHAPES.map((s) => (
          <ShapeButton key={s.key} shape={s} onAdd={() => addNode(s.key)} />
        ))}
      </div>
    </section>
  );
}

function ShapeButton({
  shape,
  onAdd,
}: {
  shape: ShapeDef;
  onAdd: () => void;
}) {
  return (
    <button
      type="button"
      title={shape.description}
      onClick={onAdd}
      className="group flex w-full items-center gap-3 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-left transition hover:border-slate-400 hover:bg-slate-50"
      style={{ minHeight: shellDesign.sidebarShapeBtnHeight }}
    >
      <div className="flex h-7 w-9 shrink-0 items-center justify-center">
        <ShapeIcon shape={shape} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-semibold text-slate-900">
          {shape.label}
        </div>
        <div className="truncate text-[10px] text-slate-500">
          {shape.description.split(" — ")[0]}
        </div>
      </div>
      {shape.shortcut ? (
        <ShortcutChip k={shape.shortcut} />
      ) : (
        <span className="text-[10px] text-slate-300">·</span>
      )}
    </button>
  );
}

function ShortcutChip({ k }: { k: string }) {
  return (
    <span className="rounded border border-slate-300 bg-slate-50 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-slate-600">
      {k}
    </span>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
      {children}
    </div>
  );
}

/* ─────────────────────────────────────────────
 * 도형 미리보기 아이콘 — 단순화된 SVG.
 * 후속 단계에서 실제 노드 컴포넌트와 시각이 일치하도록 다듬을 예정.
 * ───────────────────────────────────────────── */

function ShapeIcon({ shape }: { shape: ShapeDef }) {
  const W = 36;
  const H = 26;
  const common: CSSProperties = { display: "block" };

  const fill = shape.fill;
  const stroke = shape.stroke;
  const strokeWidth = 1.25;

  switch (shape.key as ShapeKey) {
    case "activity":
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <rect
            x={0.5}
            y={0.5}
            width={W - 1}
            height={H - 1}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
          <rect x={0.5} y={0.5} width={W - 1} height={7} fill="#EAEAEA" />
          <line
            x1={0.5}
            y1={7.5}
            x2={W - 0.5}
            y2={7.5}
            stroke={stroke}
            strokeWidth={1}
          />
          <line
            x1={10}
            y1={0.5}
            x2={10}
            y2={7.5}
            stroke={stroke}
            strokeWidth={1}
          />
          <line
            x1={0.5}
            y1={H - 7}
            x2={W - 0.5}
            y2={H - 7}
            stroke={stroke}
            strokeWidth={1}
          />
        </svg>
      );

    case "startEnd":
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <rect
            x={0.5}
            y={3.5}
            width={W - 1}
            height={H - 7}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
        </svg>
      );

    case "link":
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <rect
            x={0.5}
            y={4.5}
            width={W - 1}
            height={H - 9}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
          <line
            x1={W / 3}
            y1={4.5}
            x2={W / 3}
            y2={H - 4.5}
            stroke={stroke}
            strokeWidth={1}
          />
          <line
            x1={(2 * W) / 3}
            y1={4.5}
            x2={(2 * W) / 3}
            y2={H - 4.5}
            stroke={stroke}
            strokeWidth={1}
          />
        </svg>
      );

    case "controlType": {
      const s = H - 6;
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <rect
            x={(W - s) / 2}
            y={3}
            width={s}
            height={s}
            fill={fill}
            stroke={fill}
            strokeWidth={strokeWidth}
          />
          <text
            x={W / 2}
            y={H / 2 + 3}
            fontSize="9"
            fontWeight="700"
            fill="#FFFFFF"
            textAnchor="middle"
          >
            M
          </text>
        </svg>
      );
    }

    case "diamond":
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <polygon
            points={`${W / 2},1 ${W - 1},${H / 2} ${W / 2},${H - 1} 1,${H / 2}`}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
        </svg>
      );

    case "risk":
    case "keyControl":
    case "nonkeyControl":
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <rect
            x={1}
            y={3}
            width={W - 2}
            height={H - 6}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
        </svg>
      );

    case "document":
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <path
            d={`M 1 2
                L ${W - 1} 2
                L ${W - 1} ${H - 5}
                Q ${(W * 3) / 4} ${H - 1}, ${W / 2} ${H - 4}
                Q ${W / 4} ${H - 7}, 1 ${H - 3}
                Z`}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
        </svg>
      );

    case "db":
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <path
            d={`M 3 4
                L 3 ${H - 4}
                Q ${W / 2} ${H + 1}, ${W - 3} ${H - 4}
                L ${W - 3} 4
                Q ${W / 2} -3, 3 4
                Z`}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
          <path
            d={`M 3 4 Q ${W / 2} 9, ${W - 3} 4`}
            fill="none"
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
        </svg>
      );

    case "interface":
      return (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={common}>
          <circle
            cx={W / 2}
            cy={H / 2}
            r={Math.min(W, H) / 2 - 2}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
        </svg>
      );
  }
}
