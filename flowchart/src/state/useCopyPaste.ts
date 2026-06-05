import { useCallback, useEffect, useRef } from "react";
import type { Edge } from "reactflow";

import type { FlowNode } from "./flowState";
import { useFlow } from "./flowState";

/**
 * 복사·붙여넣기·복제·전체선택 단축키 훅.
 *
 *   Ctrl+C  : 선택된 노드·엣지를 내부 클립보드에 저장
 *   Ctrl+V  : 클립보드 내용을 +40px 오프셋 위치에 붙여넣기 (활성 flowchart)
 *   Ctrl+D  : 선택 노드를 즉시 복제 (클립보드 변경 없음)
 *   Ctrl+A  : 활성 flowchart 의 모든 노드 선택
 *
 *   입력 필드 포커스 중에는 동작하지 않습니다 (브라우저 기본 동작 유지).
 *   Cmd 키(Mac)도 동일하게 처리.
 */

const PASTE_OFFSET = 40; // px — 원본보다 오른쪽·아래로 이동

interface ClipboardData {
  nodes: FlowNode[];
  edges: Edge[];
}

function inInputField(target: EventTarget | null): boolean {
  if (!target) return false;
  const el = target as HTMLElement;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (el.isContentEditable) return true;
  return false;
}

/** 붙여넣기용 새 ID — 원본 ID 에 타임스탬프 suffix 를 붙여 중복 방지 */
function newId(original: string): string {
  return `${original}_p${Date.now().toString(36)}`;
}

export function useCopyPaste(): void {
  const { nodes, edges, setNodes, setEdges } = useFlow();

  // 최신 nodes/edges 를 ref 에 유지 → 키보드 리스너가 항상 최신 값 읽도록
  //   (이벤트 리스너 deps 에 nodes/edges 를 넣으면 매 변경마다 재등록됨 — 불필요)
  const nodesRef = useRef<FlowNode[]>(nodes);
  const edgesRef = useRef<Edge[]>(edges);
  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);
  useEffect(() => {
    edgesRef.current = edges;
  }, [edges]);

  const clipboardRef = useRef<ClipboardData>({ nodes: [], edges: [] });

  /* ── Ctrl+C ── */
  const copy = useCallback(() => {
    const selected = nodesRef.current.filter((n) => n.selected);
    if (selected.length === 0) return;
    const ids = new Set(selected.map((n) => n.id));
    const selectedEdges = edgesRef.current.filter(
      (e) => ids.has(e.source) && ids.has(e.target),
    );
    clipboardRef.current = { nodes: selected, edges: selectedEdges };
  }, []); // ref 만 사용 → stable

  /* ── Ctrl+V ── */
  const paste = useCallback(() => {
    const { nodes: cbNodes, edges: cbEdges } = clipboardRef.current;
    if (cbNodes.length === 0) return;

    const idMap = new Map<string, string>();
    const newNodes: FlowNode[] = cbNodes.map((n) => {
      const id = newId(n.id);
      idMap.set(n.id, id);
      return {
        ...n,
        id,
        position: { x: n.position.x + PASTE_OFFSET, y: n.position.y + PASTE_OFFSET },
        selected: true,
      };
    });

    const newEdges: Edge[] = cbEdges.map((e) => ({
      ...e,
      id: newId(e.id),
      source: idMap.get(e.source) ?? e.source,
      target: idMap.get(e.target) ?? e.target,
      selected: false,
    }));

    // 기존 선택 해제 → 붙여넣은 노드만 선택
    setNodes((prev) => [...prev.map((n) => ({ ...n, selected: false })), ...newNodes]);
    setEdges((prev) => [...prev, ...newEdges]);
  }, [setNodes, setEdges]);

  /* ── Ctrl+D ── 클립보드를 건드리지 않고 즉시 복제 */
  const duplicate = useCallback(() => {
    const selected = nodesRef.current.filter((n) => n.selected);
    if (selected.length === 0) return;
    const ids = new Set(selected.map((n) => n.id));
    const selectedEdges = edgesRef.current.filter(
      (e) => ids.has(e.source) && ids.has(e.target),
    );

    const idMap = new Map<string, string>();
    const newNodes: FlowNode[] = selected.map((n) => {
      const id = newId(n.id);
      idMap.set(n.id, id);
      return {
        ...n,
        id,
        position: { x: n.position.x + PASTE_OFFSET, y: n.position.y + PASTE_OFFSET },
        selected: true,
      };
    });

    const newEdges: Edge[] = selectedEdges.map((e) => ({
      ...e,
      id: newId(e.id),
      source: idMap.get(e.source) ?? e.source,
      target: idMap.get(e.target) ?? e.target,
      selected: false,
    }));

    setNodes((prev) => [...prev.map((n) => ({ ...n, selected: false })), ...newNodes]);
    setEdges((prev) => [...prev, ...newEdges]);
  }, [setNodes, setEdges]);

  /* ── Ctrl+A ── */
  const selectAll = useCallback(() => {
    setNodes((prev) => prev.map((n) => ({ ...n, selected: true })));
  }, [setNodes]);

  /* ── 키보드 리스너 등록 ── */
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      if (e.altKey) return;
      // 입력 필드: 브라우저 기본 동작 (텍스트 복사·붙여넣기·전체선택) 유지
      if (inInputField(e.target)) return;

      const key = e.key.toLowerCase();
      if (key === "c") {
        e.preventDefault();
        copy();
      } else if (key === "v") {
        e.preventDefault();
        paste();
      } else if (key === "d") {
        e.preventDefault(); // 브라우저 북마크 방지
        duplicate();
      } else if (key === "a") {
        e.preventDefault();
        selectAll();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [copy, paste, duplicate, selectAll]); // 모두 stable → 1회만 등록
}
