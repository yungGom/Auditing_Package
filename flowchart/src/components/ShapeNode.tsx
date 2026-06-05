import { CSSProperties, memo, useCallback } from "react";
import { Handle, NodeProps, NodeResizer, Position } from "reactflow";
import { ShapeKey, SHAPES } from "../shapes";
import { icfrColors, shapeNodeDesign } from "../design";
import { useFlow } from "../state/flowState";
import { LockBadge } from "./LockBadge";

/**
 * Activity 외의 도형 10종 — 한 컴포넌트.
 *  - Link, StartEnd, Diamond, Risk, KeyControl, NonKeyControl, ControlType,
 *    Document, DB, Interface
 *
 * 컨테이너는 부모(React Flow wrapper) 크기를 100% 채우고, SVG 는 viewBox 로
 * 자동 스케일된다. NodeResizer 가 wrapper 의 width/height 를 갱신하면
 * 도형이 따라서 늘어남.
 */

export type NonActivityShape = Exclude<ShapeKey, "activity">;

export interface ShapeNodeData {
  shapeKey: NonActivityShape;
  label: string;
  sublabel?: string;
  /** 사용자 지정 외곽 치수 (px). 미설정 시 shapeNodeDesign 기본값 사용. */
  customWidth?: number;
  customHeight?: number;
  /**
   * keyControl / nonkeyControl 박스에 통제유형 M 칩을 내장 표시할 때 사용.
   * "A" / "M" / "I" — 박스 우측에 정사각형 색 칩이 따라붙는다.
   * 회사 양식: 위에서 아래로 [R 박스] [C 박스(우측에 M 칩)] [활동] 누적.
   */
  controlType?: "A" | "M" | "I";
  /**
   * KEY_CA 공란 (v8 매핑 시트: CONTROL_NO 있으나 KEY_CA 미입력) 일 때 true.
   * nonkeyControl shapeKey 를 쓰되 배경색을 회색(neutralCtrl)으로 표시.
   */
  neutralControl?: boolean;
  /** 위치 고정 여부 — true 면 드래그 불가(자물쇠 표시). 단축키 L 로 토글. */
  locked?: boolean;
}

const SHAPE_DEF = Object.fromEntries(SHAPES.map((s) => [s.key, s]));

const CTRL_TYPE_COLORS: Record<"A" | "M" | "I", { bg: string; fg: string }> = {
  A: { bg: icfrColors.ctrlA, fg: "#FFFFFF" },
  M: { bg: icfrColors.ctrlM, fg: "#FFFFFF" },
  I: { bg: icfrColors.ctrlI, fg: "#0F172A" },
};

interface ShapeRender {
  /** SVG viewBox 의 폭/높이 — 도형 그리기 좌표계의 기준 (디자인 기본값) */
  refWidth: number;
  refHeight: number;
  /** 텍스트 폰트 */
  fontSize: number;
  fontWeight?: number;
  fontColor: string;
  /** 텍스트 영역 padding (실제 px 이 아니라 viewBox 좌표) */
  padX: number;
  padY: number;
  /** SVG 도형 본체 (viewBox 좌표계로 그림) */
  bg: (selected: boolean) => React.ReactNode;
  /** 핸들 위치들 */
  handles: Position[];
  /** SVG 종횡비 유지 여부 — 사각형 류는 'none' 으로 자유 스트레치 */
  preserveAspect: "none" | "xMidYMid meet";
  /** 리사이즈 최소값 */
  minWidth: number;
  minHeight: number;
}

function getRender(
  shapeKey: NonActivityShape,
  data: ShapeNodeData,
): ShapeRender {
  const def = SHAPE_DEF[shapeKey];
  const sw = shapeNodeDesign.borderWidth;

  switch (shapeKey) {
    case "startEnd": {
      const { width, height, fontSize, fontWeight } = shapeNodeDesign.startEnd;
      return {
        refWidth: width, refHeight: height,
        fontSize, fontWeight, fontColor: "#0F172A",
        padX: 8, padY: 4,
        handles: [Position.Left, Position.Right, Position.Top, Position.Bottom],
        preserveAspect: "none",
        minWidth: 60, minHeight: 28,
        bg: (sel) => (
          <rect x={sw / 2} y={sw / 2}
            width={width - sw} height={height - sw}
            fill={def.fill}
            stroke={sel ? icfrColors.keyCtrl : def.stroke}
            strokeWidth={sel ? 2 : sw}
            vectorEffect="non-scaling-stroke" />
        ),
      };
    }
    case "link": {
      const { width, height, fontSize } = shapeNodeDesign.link;
      const sideW = (width - 14) / 2;
      const midX1 = sideW;
      const midX2 = sideW + 14;
      return {
        refWidth: width, refHeight: height,
        fontSize, fontColor: "#0F172A",
        padX: 8, padY: 4,
        handles: [Position.Left, Position.Right],
        preserveAspect: "none",
        minWidth: 60, minHeight: 24,
        bg: (sel) => (
          <>
            <rect x={sw / 2} y={sw / 2}
              width={width - sw} height={height - sw}
              fill={def.fill}
              stroke={sel ? icfrColors.keyCtrl : def.stroke}
              strokeWidth={sel ? 2 : sw} vectorEffect="non-scaling-stroke" />
            <line x1={midX1} y1={sw} x2={midX1} y2={height - sw}
              stroke={def.stroke} strokeWidth={sw} vectorEffect="non-scaling-stroke" />
            <line x1={midX2} y1={sw} x2={midX2} y2={height - sw}
              stroke={def.stroke} strokeWidth={sw} vectorEffect="non-scaling-stroke" />
          </>
        ),
      };
    }
    case "diamond": {
      const { width, height, fontSize } = shapeNodeDesign.diamond;
      return {
        refWidth: width, refHeight: height,
        fontSize, fontColor: "#0F172A",
        padX: 14, padY: 6,
        handles: [Position.Left, Position.Right, Position.Top, Position.Bottom],
        preserveAspect: "none",
        minWidth: 70, minHeight: 50,
        bg: (sel) => (
          <polygon
            points={`${width / 2},${sw} ${width - sw},${height / 2} ${width / 2},${height - sw} ${sw},${height / 2}`}
            fill={def.fill}
            stroke={sel ? icfrColors.keyCtrl : def.stroke}
            strokeWidth={sel ? 2 : sw} vectorEffect="non-scaling-stroke" />
        ),
      };
    }
    case "risk":
    case "keyControl":
    case "nonkeyControl": {
      const cfg =
        shapeKey === "risk"
          ? shapeNodeDesign.risk
          : shapeKey === "keyControl"
            ? shapeNodeDesign.keyControl
            : shapeNodeDesign.nonkeyControl;
      const { width, height, fontSize, fontWeight } = cfg;
      const isRisk = shapeKey === "risk";
      // neutralControl: KEY_CA 공란 → 회색 박스, 텍스트 어둡게
      const isNeutral = !isRisk && !!data.neutralControl;
      const fillColor = isNeutral ? icfrColors.neutralCtrl : def.fill;
      const strokeColor = isNeutral ? icfrColors.neutralCtrl : def.stroke;
      return {
        refWidth: width, refHeight: height,
        fontSize, fontWeight,
        fontColor: isRisk ? "#0F172A" : (isNeutral ? "#0F172A" : "#FFFFFF"),
        padX: 4, padY: 2,
        handles: [Position.Left, Position.Right, Position.Bottom],
        preserveAspect: "none",
        minWidth: 40, minHeight: 16,
        bg: (sel) => (
          <rect x={sw / 2} y={sw / 2}
            width={width - sw} height={height - sw}
            rx={6} ry={6}
            fill={fillColor}
            stroke={sel ? icfrColors.keyCtrl : strokeColor}
            strokeWidth={sel ? 2 : sw} vectorEffect="non-scaling-stroke" />
        ),
      };
    }
    case "controlType": {
      const { width, height, fontSize, fontWeight } = shapeNodeDesign.controlType;
      const letter = (data.label || "M").toUpperCase().charAt(0) as
        | "A" | "M" | "I";
      const safe = letter === "A" || letter === "M" || letter === "I"
        ? letter : "M";
      const c = CTRL_TYPE_COLORS[safe];
      return {
        refWidth: width, refHeight: height,
        fontSize, fontWeight, fontColor: c.fg,
        padX: 2, padY: 2,
        handles: [Position.Left, Position.Right],
        preserveAspect: "xMidYMid meet",
        minWidth: 18, minHeight: 18,
        bg: (sel) => (
          <rect x={sw / 2} y={sw / 2}
            width={width - sw} height={height - sw}
            fill={c.bg}
            stroke={sel ? "#FFFFFF" : c.bg}
            strokeWidth={sel ? 2 : sw} vectorEffect="non-scaling-stroke" />
        ),
      };
    }
    case "document": {
      const { width, height, fontSize } = shapeNodeDesign.document;
      return {
        refWidth: width, refHeight: height,
        fontSize, fontColor: "#0F172A",
        padX: 8, padY: 4,
        handles: [Position.Left, Position.Right, Position.Top],
        preserveAspect: "none",
        minWidth: 60, minHeight: 32,
        bg: (sel) => (
          <path
            d={`M ${sw} ${sw}
                L ${width - sw} ${sw}
                L ${width - sw} ${height - 9}
                Q ${(width * 3) / 4} ${height - sw}, ${width / 2} ${height - 7}
                Q ${width / 4} ${height - 14}, ${sw} ${height - 4}
                Z`}
            fill={def.fill}
            stroke={sel ? icfrColors.keyCtrl : def.stroke}
            strokeWidth={sel ? 2 : sw} vectorEffect="non-scaling-stroke" />
        ),
      };
    }
    case "db": {
      const { width, height, fontSize, fontWeight } = shapeNodeDesign.db;
      const ry = 7;
      return {
        refWidth: width, refHeight: height,
        fontSize, fontWeight, fontColor: "#FFFFFF",
        padX: 8, padY: ry + 4,
        handles: [Position.Left, Position.Right, Position.Top, Position.Bottom],
        preserveAspect: "none",
        minWidth: 50, minHeight: 40,
        bg: (sel) => (
          <>
            <path
              d={`M ${sw} ${ry}
                  L ${sw} ${height - ry}
                  Q ${width / 2} ${height + ry * 0.6}, ${width - sw} ${height - ry}
                  L ${width - sw} ${ry}
                  Q ${width / 2} ${-ry * 0.6}, ${sw} ${ry}
                  Z`}
              fill={def.fill}
              stroke={sel ? "#FFFFFF" : def.stroke}
              strokeWidth={sel ? 2 : sw} vectorEffect="non-scaling-stroke" />
            <path
              d={`M ${sw} ${ry} Q ${width / 2} ${ry * 2.1}, ${width - sw} ${ry}`}
              fill="none" stroke={def.stroke}
              strokeWidth={sw} vectorEffect="non-scaling-stroke" />
          </>
        ),
      };
    }
    case "interface": {
      const { width, height, fontSize, fontWeight } = shapeNodeDesign.interface;
      return {
        refWidth: width, refHeight: height,
        fontSize, fontWeight, fontColor: "#0F172A",
        padX: 4, padY: 4,
        handles: [Position.Left, Position.Right, Position.Top, Position.Bottom],
        preserveAspect: "xMidYMid meet",
        minWidth: 32, minHeight: 32,
        bg: (sel) => (
          <circle cx={width / 2} cy={height / 2}
            r={Math.min(width, height) / 2 - sw}
            fill={def.fill}
            stroke={sel ? icfrColors.keyCtrl : icfrColors.border}
            strokeWidth={sel ? 2 : sw} vectorEffect="non-scaling-stroke" />
        ),
      };
    }
    case "textBox": {
      const { width, height, fontSize, fontWeight } = shapeNodeDesign.textBox;
      return {
        refWidth: width, refHeight: height,
        fontSize, fontWeight, fontColor: "#0F172A",
        padX: 4, padY: 2,
        handles: [Position.Left, Position.Right, Position.Top, Position.Bottom],
        preserveAspect: "none",
        minWidth: 30, minHeight: 18,
        bg: (sel) => (
          <rect x={0} y={0}
            width={width} height={height}
            fill="transparent"
            stroke={sel ? icfrColors.keyCtrl : "transparent"}
            strokeWidth={sel ? 1 : 0}
            strokeDasharray={sel ? "4 3" : "none"}
            vectorEffect="non-scaling-stroke" />
        ),
      };
    }
  }
}

/* ─────────────────────────────────────────────
 * 본체 (DesignPreview / NodeResizer 외부에서도 재사용)
 *
 *   외곽 크기는 data.customWidth / customHeight 가 있으면 그 값, 없으면 design.ts.
 *   SVG 는 viewBox 로 자동 스케일.
 * ───────────────────────────────────────────── */
export function ShapeNodeBody({
  data,
  selected = false,
}: {
  data: ShapeNodeData;
  selected?: boolean;
}) {
  const r = getRender(data.shapeKey, data);
  const W = data.customWidth ?? r.refWidth;
  const H = data.customHeight ?? r.refHeight;

  // M 칩 표시 — keyControl / nonkeyControl 박스에 controlType 이 있을 때만.
  // 칩은 SVG 가 아닌 HTML overlay 로 그려 항상 정사각형(H × H) 유지 (X stretch 영향 안 받음).
  const showChip =
    (data.shapeKey === "keyControl" || data.shapeKey === "nonkeyControl") &&
    !!data.controlType;
  const chipLetter = (data.controlType ?? "M") as "A" | "M" | "I";
  // 칩 배경/글자색: 기준 통제구분 색 (A=핑크/흰, M=연핑크/검정, I=골드/검정)
  const chipColors = CTRL_TYPE_COLORS;
  const chipW = showChip ? H : 0; // 칩은 정사각형

  const containerStyle: CSSProperties = {
    position: "relative",
    width: W,
    height: H,
  };

  const textStyle: CSSProperties = {
    position: "absolute",
    top: 0,
    left: 0,
    right: chipW, // M 칩 자리 비워둠 (텍스트 영역 축소)
    bottom: 0,
    padding: `4px ${r.padX}px`,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    fontSize: r.fontSize,
    fontWeight: r.fontWeight ?? 500,
    color: r.fontColor,
    lineHeight: 1.2,
    userSelect: "none",
    pointerEvents: "none",
    overflow: "hidden",
  };

  return (
    <div style={containerStyle}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${r.refWidth} ${r.refHeight}`}
        preserveAspectRatio={r.preserveAspect}
        style={{ position: "absolute", inset: 0 }}
      >
        {r.bg(selected)}
      </svg>
      <div style={textStyle}>
        <div style={{ width: "100%" }}>{data.label}</div>
        {data.sublabel && (
          <div
            style={{
              marginTop: 1,
              fontSize: Math.max(9, r.fontSize - 1),
              fontWeight: 400,
              opacity: 0.85,
            }}
          >
            {data.sublabel}
          </div>
        )}
      </div>
      {showChip && (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: 0,
            width: chipW,
            height: H,
            backgroundColor: chipColors[chipLetter].bg,
            color: chipColors[chipLetter].fg,
            borderRadius: 4,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: Math.max(9, r.fontSize),
            fontWeight: 700,
            userSelect: "none",
            pointerEvents: "none",
          }}
        >
          {chipLetter}
        </div>
      )}
    </div>
  );
}

function ShapeNodeImpl({ id, data, selected }: NodeProps<ShapeNodeData>) {
  const r = getRender(data.shapeKey, data);
  const { setNodes } = useFlow();

  const onResize = useCallback(
    (_e: unknown, params: { width: number; height: number }) => {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === id
            ? {
                ...n,
                data: {
                  ...(n.data as ShapeNodeData),
                  customWidth: params.width,
                  customHeight: params.height,
                },
              }
            : n,
        ),
      );
    },
    [id, setNodes],
  );

  const locked = !!data.locked;

  return (
    <>
      <NodeResizer
        isVisible={selected && !locked}
        minWidth={r.minWidth}
        minHeight={r.minHeight}
        onResize={onResize}
        lineStyle={{ borderColor: icfrColors.keyCtrl }}
        handleStyle={{
          width: 6,
          height: 6,
          backgroundColor: icfrColors.keyCtrl,
          border: "1px solid #FFFFFF",
        }}
      />
      {r.handles.map((pos) => (
        <Handle
          key={pos}
          id={pos}
          type="source"
          position={pos}
          style={{
            width: 6,
            height: 6,
            background: "#FFFFFF",
            border: `1px solid ${icfrColors.border}`,
          }}
        />
      ))}
      <ShapeNodeBody data={data} selected={selected} />
      {locked && <LockBadge />}
    </>
  );
}

export const ShapeNode = memo(ShapeNodeImpl);
