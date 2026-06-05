import { CSSProperties } from "react";

/**
 * 노드 우상단 자물쇠 배지 — 위치가 고정(lock)된 노드에 표시.
 *   - pointerEvents none 으로 클릭/드래그를 방해하지 않음
 *   - 단축키 L 또는 상단바 "전체 잠금" 으로 토글
 */
const style: CSSProperties = {
  position: "absolute",
  top: -8,
  right: -8,
  width: 16,
  height: 16,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: "50%",
  backgroundColor: "#1F2937",
  color: "#FFFFFF",
  fontSize: 9,
  lineHeight: 1,
  boxShadow: "0 1px 2px rgba(0,0,0,0.3)",
  userSelect: "none",
  pointerEvents: "none",
  zIndex: 10,
};

export function LockBadge() {
  return (
    <div style={style} aria-label="위치 고정됨" title="위치 고정됨 (L 로 해제)">
      🔒
    </div>
  );
}
