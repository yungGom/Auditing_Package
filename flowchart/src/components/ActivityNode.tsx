import { CSSProperties, memo, useCallback } from "react";
import { Handle, NodeProps, NodeResizer, Position } from "reactflow";
import type { Activity } from "../types";
import {
  activityAutoHeight,
  activityLocation,
  activityTeam,
  parseSubSteps,
  STEP_NUMBERS,
  subStepsFontSize,
} from "../types";
import {
  activityNodeDesign as N,
  icfrColors,
} from "../design";
import { useFlow } from "../state/flowState";
import { LockBadge } from "./LockBadge";

/**
 * 활동(Activity) 노드 — 4분할 박스.
 *
 * 외곽 크기는 data.customWidth / data.customHeight 가 있으면 그 값, 없으면
 * design.ts 기본값 (180 × 88). NodeResizer 와 EditPanel 모두 이 두 필드를
 * 갱신해 단일 소스로 유지된다.
 */

export interface ActivityNodeData {
  activity: Activity;
  customWidth?: number;
  customHeight?: number;
  /** 위치 고정 여부 — true 면 드래그 불가(자물쇠 표시). 단축키 L 로 토글. */
  locked?: boolean;
}

const DEFAULT_HEIGHT = 88;

export function ActivityNodeBody({
  activity,
  selected = false,
  width,
  height,
}: {
  activity: Activity;
  selected?: boolean;
  width?: number;
  height?: number;
}) {
  // v5: SUB_STEPS 한 셀에 줄바꿈으로 여러 단계 입력 → ①②③ 자동 번호로 박스 안에 표시.
  const steps = parseSubSteps(activity.subSteps);
  const stepCount = steps.length;
  const autoH = activityAutoHeight(stepCount, steps);
  const stepFontPx = subStepsFontSize(stepCount); // pt 와 px 차이 있지만 작아도 차이 작음
  const W = width ?? N.width;
  const H = height ?? autoH;
  const team = activityTeam(activity);
  const location = activityLocation(activity);

  const cardStyle: CSSProperties = {
    width: W,
    height: H,
    borderWidth: N.borderWidth,
    borderColor: icfrColors.border,
    backgroundColor: icfrColors.actBody,
    borderStyle: "solid",
    boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
    position: "relative",
    userSelect: "none",
    outline: selected ? `2px solid ${icfrColors.keyCtrl}` : undefined,
    outlineOffset: selected ? 2 : undefined,
    display: "flex",
    flexDirection: "column",
    boxSizing: "border-box",
  };

  // 헤더/푸터는 고정 픽셀 높이 (활동이 커져도 일정). 본문이 나머지를 차지.
  const HDR_PX = 24;
  const FOOT_PX = 20;
  const headerRowStyle: CSSProperties = {
    display: "flex",
    flex: `0 0 ${HDR_PX}px`,
    backgroundColor: icfrColors.actHdr,
    borderBottom: `${N.borderWidth}px solid ${icfrColors.border}`,
  };

  const actNoStyle: CSSProperties = {
    width: N.actNoColWidth,
    borderRight: `${N.borderWidth}px solid ${icfrColors.border}`,
    fontSize: N.actNoFontSize,
    fontWeight: N.actNoFontWeight,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  const teamStyle: CSSProperties = {
    flex: 1,
    paddingLeft: 6,
    paddingRight: 6,
    fontSize: N.teamFontSize,
    lineHeight: 1.2,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
  };

  const bodyStyle: CSSProperties = {
    flex: "1 1 auto",
    paddingLeft: N.bodyPaddingX,
    paddingRight: N.bodyPaddingX,
    paddingTop: 4,
    paddingBottom: 4,
    display: "flex",
    flexDirection: "column",
    alignItems: "stretch",
    justifyContent: stepCount > 0 ? "flex-start" : "center",
    textAlign: stepCount > 0 ? "left" : "center",
    overflow: "hidden",
  };

  const bodyTitleStyle: CSSProperties = {
    fontSize: N.bodyTitleFontSize,
    fontWeight: N.bodyTitleFontWeight,
    lineHeight: N.bodyLineHeight,
    textAlign: "center",
    marginBottom: stepCount > 0 ? 2 : 0,
  };

  const stepListStyle: CSSProperties = {
    fontSize: stepFontPx,
    lineHeight: 1.25,
    color: "#0F172A",
  };
  const stepStyle: CSSProperties = {
    display: "block",
    marginTop: 1,
  };

  const footerStyle: CSSProperties = {
    flex: `0 0 ${FOOT_PX}px`,
    backgroundColor: icfrColors.actHdr,
    borderTop: `${N.borderWidth}px solid ${icfrColors.border}`,
    fontSize: N.locationFontSize,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  return (
    <div style={cardStyle}>
      <div style={headerRowStyle}>
        <div style={actNoStyle}>{activity.actNo}</div>
        <div style={teamStyle}>{team || " "}</div>
      </div>

      <div style={bodyStyle}>
        <div style={bodyTitleStyle}>{activity.actName}</div>
        {stepCount > 0 && (
          <div style={stepListStyle}>
            {steps.map((s, i) => (
              <span key={i} style={stepStyle}>
                <span style={{ marginRight: 2 }}>
                  {STEP_NUMBERS[i] ?? `${i + 1}.`}
                </span>
                {s}
              </span>
            ))}
          </div>
        )}
      </div>

      <div style={footerStyle}>{location}</div>
    </div>
  );
}

const HANDLE_STYLE = {
  width: 8,
  height: 8,
  background: "#FFFFFF",
  border: `1px solid ${icfrColors.border}`,
};

function ActivityNodeImpl({ id, data, selected }: NodeProps<ActivityNodeData>) {
  const { setNodes } = useFlow();
  const W = data.customWidth ?? N.width;
  const H = data.customHeight ?? DEFAULT_HEIGHT;

  const onResize = useCallback(
    (_e: unknown, params: { width: number; height: number }) => {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === id
            ? {
                ...n,
                data: {
                  ...(n.data as ActivityNodeData),
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
        minWidth={120}
        minHeight={60}
        onResize={onResize}
        lineStyle={{ borderColor: icfrColors.keyCtrl }}
        handleStyle={{
          width: 6,
          height: 6,
          backgroundColor: icfrColors.keyCtrl,
          border: "1px solid #FFFFFF",
        }}
      />
      <Handle id="left" type="source" position={Position.Left} style={HANDLE_STYLE} />
      <Handle id="right" type="source" position={Position.Right} style={HANDLE_STYLE} />
      <Handle id="top" type="source" position={Position.Top} style={HANDLE_STYLE} />
      <Handle id="bottom" type="source" position={Position.Bottom} style={HANDLE_STYLE} />
      <ActivityNodeBody
        activity={data.activity}
        selected={selected}
        width={W}
        height={H}
      />
      {locked && <LockBadge />}
    </>
  );
}

export const ActivityNode = memo(ActivityNodeImpl);
