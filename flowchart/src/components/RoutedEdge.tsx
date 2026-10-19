import { memo } from "react";
import { BaseEdge, EdgeLabelRenderer, EdgeProps } from "reactflow";

import {
  branchLabelAnchor,
  pointsToSvgPath,
  routePoints,
  type EdgeRoute,
  type Side,
} from "../parsing/edgeRouting";

/**
 * 배치 엔진이 지정한 통로(corridor)를 따라 그리는 직각 화살표.
 *   - 통로가 없으면 smoothstep 과 같은 경로
 *   - 분기 라벨(Y/N 등)은 출발 핸들 바로 옆에 표시
 *   - 경로는 현재 핸들 좌표 기준으로 매번 계산 → 노드를 옮겨도 끊기지 않음
 *   - PPT 는 같은 routePoints 로 그려서 화면과 일치
 */

export interface RoutedEdgeData {
  route?: EdgeRoute;
}

function RoutedEdgeImpl({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  label,
  markerEnd,
  style,
  interactionWidth,
}: EdgeProps<RoutedEdgeData>) {
  const sSide = sourcePosition as unknown as Side;
  const tSide = targetPosition as unknown as Side;
  const points = routePoints(
    { x: sourceX, y: sourceY },
    sSide,
    { x: targetX, y: targetY },
    tSide,
    data?.route,
  );
  const path = pointsToSvgPath(points, 6);
  const anchor = label ? branchLabelAnchor(points, sSide) : null;

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={style}
        interactionWidth={interactionWidth}
      />
      {anchor && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan"
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${anchor.x}px, ${anchor.y}px)`,
              fontSize: 11,
              fontWeight: 700,
              color: "#334155",
              background: "#FFFFFF",
              padding: "0 2px",
              lineHeight: 1.2,
              pointerEvents: "none",
              whiteSpace: "nowrap",
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const RoutedEdge = memo(RoutedEdgeImpl);
