import { useCallback, useEffect, useRef, useState } from "react";

import { SHORTCUT_TO_SHAPE, ShapeKey } from "../shapes";
import { useFlow } from "./flowState";

/**
 * 키보드 단축키 시스템 — 두 가지 모드를 한 번에 처리한다.
 *
 *  ① 탭(눌렀다 떼기)   : 키를 누른 동안 캔버스 클릭이 없으면 → 캔버스 중앙에 1개 추가
 *  ② 홀드(누른 채 클릭): 키를 누른 동안 캔버스 클릭하면 → 그 자리에 추가 (연속 가능)
 *
 *  - `Esc`: 추가 대기 취소 + 도움말 닫기
 *  - `?`  (Shift+/): 단축키 도움말 모달 열기
 *  - 입력 필드 포커스 중에는 단축키 무시 (타이핑 보호)
 *
 *  hook 반환:
 *   - armedShape           : 현재 "추가 대기" 중인 도형. FlowCanvas 가 커서/배지를 그릴 때 사용.
 *   - helpOpen / setHelpOpen: 도움말 모달 표시 상태.
 *   - onCanvasClickWhileArmed(flowPos) : FlowCanvas 가 pane 클릭 시 호출.
 *   - cancelArmed()        : 외부에서 명시적으로 취소할 때.
 */

export interface ShortcutsApi {
  armedShape: ShapeKey | null;
  helpOpen: boolean;
  setHelpOpen: (b: boolean) => void;
  cancelArmed: () => void;
  onCanvasClickWhileArmed: (flowPos: { x: number; y: number }) => void;
}

function inInputField(target: EventTarget | null): boolean {
  if (!target) return false;
  const el = target as HTMLElement;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (el.isContentEditable) return true;
  return false;
}

export function useShortcuts(): ShortcutsApi {
  const [armedShape, setArmedShape] = useState<ShapeKey | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

  // 이벤트 핸들러에서 항상 최신 값을 보기 위한 ref.
  const armedRef = useRef<ShapeKey | null>(null);
  const clickedRef = useRef(false);

  useEffect(() => {
    armedRef.current = armedShape;
  }, [armedShape]);

  const { addNode, undo, redo, nodes, setNodes } = useFlow();

  // 핸들러에서 최신 nodes 참조 (stale closure 방지)
  const nodesRef = useRef(nodes);
  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  // 입력 필드로 포커스가 옮겨가면 즉시 무장 해제 — 타이핑이 도형 추가를 일으키지 않도록.
  useEffect(() => {
    const onFocusIn = (e: FocusEvent) => {
      if (inInputField(e.target)) {
        setArmedShape(null);
        clickedRef.current = false;
      }
    };
    document.addEventListener("focusin", onFocusIn);
    return () => document.removeEventListener("focusin", onFocusIn);
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.repeat) return;

      // Undo/Redo — 입력 필드 안에서도 동작.
      //   controlled input 이라 브라우저 native undo 가 깨져있어서 우리 undo 가
      //   "입력 직전" 상태로 정확히 돌려놓는 게 가장 자연스러움.
      //   Ctrl+Z         → undo
      //   Ctrl+Shift+Z   → redo (Mac 관례)
      //   Ctrl+Y         → redo (Windows 관례)
      //   meta 키도 받아 Cmd+Z 도 지원.
      if ((e.ctrlKey || e.metaKey) && !e.altKey) {
        const lower = e.key.toLowerCase();
        if (lower === "z" && !e.shiftKey) {
          e.preventDefault();
          undo();
          return;
        }
        if ((lower === "z" && e.shiftKey) || lower === "y") {
          e.preventDefault();
          redo();
          return;
        }
      }

      if (inInputField(e.target)) return;

      // ?  (Shift+/) → 도움말 토글
      if (e.key === "?") {
        e.preventDefault();
        setHelpOpen((prev) => !prev);
        return;
      }

      // Esc → 무장 해제 + 도움말 닫기
      if (e.key === "Escape") {
        setHelpOpen(false);
        setArmedShape(null);
        clickedRef.current = false;
        return;
      }

      // 일반 도형 단축키 — modifier 와 조합되면 무시
      if (e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return;

      const k = e.key.toUpperCase();

      // L — 선택된 노드가 있으면 "위치 고정/해제" 토글.
      //   (선택이 없을 때만 Link 도형 단축키로 동작)
      if (k === "L") {
        const selected = nodesRef.current.filter((n) => n.selected);
        if (selected.length > 0) {
          e.preventDefault();
          const ids = new Set(selected.map((n) => n.id));
          // 선택 노드가 모두 잠겨있으면 전부 해제, 하나라도 풀려있으면 전부 잠금.
          const allLocked = selected.every(
            (n) => !!(n.data as { locked?: boolean })?.locked,
          );
          const nextLocked = !allLocked;
          setNodes((prev) =>
            prev.map((n) =>
              ids.has(n.id)
                ? {
                    ...n,
                    draggable: !nextLocked, // 잠그면 드래그 불가
                    data: { ...n.data, locked: nextLocked },
                  }
                : n,
            ),
          );
          return;
        }
      }

      const shapeKey = SHORTCUT_TO_SHAPE[k];
      if (shapeKey) {
        e.preventDefault();
        setArmedShape(shapeKey);
        clickedRef.current = false;
      }
    };

    // keyup 은 입력 필드 가드 없이 처리 — 무장 해제는 항상 안전하게.
    // 무장이 안 된 키는 SHORTCUT_TO_SHAPE 매칭이 없거나 armedRef 가 달라서 자연스럽게 무시됨.
    const onKeyUp = (e: KeyboardEvent) => {
      const k = e.key.toUpperCase();
      const shapeKey = SHORTCUT_TO_SHAPE[k];
      if (!shapeKey) return;
      if (armedRef.current !== shapeKey) return;

      if (!clickedRef.current) {
        // 클릭 없이 키를 떼면 화면 중앙에 1개 추가 (모드 ①)
        addNode(shapeKey);
      }
      setArmedShape(null);
      clickedRef.current = false;
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [addNode, undo, redo, setNodes]);

  const onCanvasClickWhileArmed = useCallback(
    (flowPos: { x: number; y: number }) => {
      const current = armedRef.current;
      if (!current) return;
      addNode(current, flowPos);
      clickedRef.current = true;
      // armedShape 는 유지 — 같은 종류를 연속해서 클릭 추가할 수 있도록.
    },
    [addNode],
  );

  const cancelArmed = useCallback(() => {
    setArmedShape(null);
    clickedRef.current = false;
  }, []);

  return {
    armedShape,
    helpOpen,
    setHelpOpen,
    cancelArmed,
    onCanvasClickWhileArmed,
  };
}
