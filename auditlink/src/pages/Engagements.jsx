import { useState, useEffect, useRef, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../api";
import TaskDetailPanel from "../components/TaskDetailPanel";
import ClientSummaryPanel from "../components/ClientSummaryPanel";
import PBCPanel from "../components/PBCPanel";
import BulkAddModal from "../components/BulkAddModal";
import { usePersistedState, usePersistedScroll } from "../hooks/usePersistedState";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_MAP = {
  todo: { label: "미착수", bg: "bg-outline-variant/30", text: "text-on-surface-variant", icon: "radio_button_unchecked" },
  in_progress: { label: "진행중", bg: "bg-primary-fixed", text: "text-primary", icon: "pending" },
  review: { label: "검토대기", bg: "bg-on-tertiary-container/10", text: "text-on-tertiary-container", icon: "rate_review" },
  done: { label: "완료", bg: "bg-secondary-container", text: "text-on-secondary-container", icon: "check_circle" },
};

const PRIORITY_MAP = {
  high: { label: "상", dot: "bg-error" },
  mid: { label: "중", dot: "bg-on-tertiary-container" },
  low: { label: "하", dot: "bg-secondary" },
};

const STATUS_ORDER = ["todo", "in_progress", "review", "done"];

const TYPE_ICONS = { fy: "calendar_today", client: "business", phase: "folder", account: "account_balance" };

// ---------------------------------------------------------------------------
// Fallback Mock Data
// ---------------------------------------------------------------------------

const fallbackTree = [
  { id: "fy2025", label: "FY2025", type: "fy", children: [
    { id: "hanbit", label: "한빛제조", type: "client", children: [
      { id: "hanbit-interim", label: "기중감사", type: "phase", children: [
        { id: "hanbit-interim-ar", label: "매출채권", type: "account" },
        { id: "hanbit-interim-inv", label: "재고자산", type: "account" },
      ]},
      { id: "hanbit-final", label: "기말감사", type: "phase", children: [
        { id: "hanbit-final-ppe", label: "유형자산", type: "account" },
        { id: "hanbit-final-lease", label: "리스", type: "account" },
      ]},
    ]},
    { id: "seohyun", label: "서현테크", type: "client", children: [
      { id: "seohyun-interim", label: "기중감사", type: "phase", children: [
        { id: "seohyun-interim-rev", label: "수익인식", type: "account" },
        { id: "seohyun-interim-cash", label: "현금및현금성자산", type: "account" },
      ]},
      { id: "seohyun-final", label: "기말감사", type: "phase", children: [
        { id: "seohyun-final-equity", label: "자본", type: "account" },
        { id: "seohyun-final-provision", label: "충당부채", type: "account" },
      ]},
    ]},
  ]},
];

const fallbackTasks = {
  "hanbit-interim-ar": [
    { id: 1, title: "매출채권 확인서 발송", status: "in_progress", assignee: "김감사", deadline: "2025-03-26", priority: "high", memo: "거래처 30곳 대상" },
    { id: 2, title: "대손충당금 적정성 검토", status: "todo", assignee: "이주임", deadline: "2025-03-28", priority: "mid", memo: "" },
    { id: 3, title: "매출채권 회전율 분석", status: "done", assignee: "김감사", deadline: "2025-03-20", priority: "low", memo: "전기 대비 개선" },
  ],
  "hanbit-interim-inv": [
    { id: 4, title: "재고실사 참관 일정 확정", status: "done", assignee: "박대리", deadline: "2025-03-15", priority: "high", memo: "본사 창고 + 외주 창고" },
    { id: 5, title: "재고자산 평가 테스트", status: "in_progress", assignee: "이주임", deadline: "2025-04-01", priority: "mid", memo: "" },
  ],
  "hanbit-final-ppe": [
    { id: 6, title: "유형자산 실사", status: "review", assignee: "박대리", deadline: "2025-04-10", priority: "high", memo: "공장 설비 중심" },
    { id: 7, title: "감가상각비 재계산", status: "todo", assignee: "김감사", deadline: "2025-04-12", priority: "mid", memo: "" },
  ],
  "hanbit-final-lease": [
    { id: 8, title: "리스 계약 검토", status: "todo", assignee: "이주임", deadline: "2025-04-15", priority: "mid", memo: "IFRS 16 적용 확인" },
  ],
  "seohyun-interim-rev": [
    { id: 9, title: "수익인식 기준 검토", status: "in_progress", assignee: "최선임", deadline: "2025-03-30", priority: "high", memo: "K-IFRS 1115" },
    { id: 10, title: "계약 샘플링 테스트", status: "todo", assignee: "정사원", deadline: "2025-04-05", priority: "mid", memo: "" },
  ],
  "seohyun-interim-cash": [
    { id: 11, title: "은행잔고 확인서 수취", status: "done", assignee: "정사원", deadline: "2025-03-18", priority: "high", memo: "5개 은행" },
  ],
  "seohyun-final-equity": [
    { id: 12, title: "자본변동 내역 검토", status: "todo", assignee: "최선임", deadline: "2025-04-20", priority: "low", memo: "" },
  ],
  "seohyun-final-provision": [
    { id: 13, title: "소송충당부채 검토", status: "review", assignee: "최선임", deadline: "2025-04-18", priority: "high", memo: "법률의견서 수취 필요" },
    { id: 14, title: "제품보증충당부채 계산 검증", status: "todo", assignee: "정사원", deadline: "2025-04-22", priority: "mid", memo: "" },
  ],
};

// ---------------------------------------------------------------------------
// Context Menu
// ---------------------------------------------------------------------------

function ContextMenu({ x, y, items, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    document.addEventListener("mousedown", handler);
    document.addEventListener("contextmenu", handler);
    return () => { document.removeEventListener("mousedown", handler); document.removeEventListener("contextmenu", handler); };
  }, [onClose]);

  return (
    <div ref={ref} style={{ position: "fixed", top: y, left: x, zIndex: 100 }} className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xl py-1.5 min-w-[180px]">
      {items.map((item, i) =>
        item.divider ? (
          <div key={i} className="my-1 border-t border-outline-variant" />
        ) : (
          <button key={i} onClick={() => { item.action(); onClose(); }}
            className={`w-full flex items-center gap-2.5 px-4 py-2 text-xs font-label transition hover:bg-surface-container ${item.danger ? "text-error hover:bg-error/5" : "text-on-surface"}`}>
            <span className="material-symbols-outlined text-sm">{item.icon}</span>
            {item.label}
          </button>
        )
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tree
// ---------------------------------------------------------------------------

function TreeNode({ node, selectedId, onSelect, expanded, onToggle, onContextMenu }) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expanded[node.id] !== false;
  const isSelected = selectedId === node.id;
  const isSelectable = node.type === "account" || node.type === "client";

  return (
    <div>
      <div
        className={`group flex items-center gap-1.5 px-2 py-1.5 rounded-xl cursor-pointer text-sm font-label transition-all ${
          isSelected && isSelectable ? "bg-surface-container-lowest shadow-sm text-primary font-semibold" : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
        }`}
        style={{ paddingLeft: `${(node.depth || 0) * 16 + 8}px` }}
        onClick={() => { if (hasChildren) onToggle(node.id); if (isSelectable) onSelect(node.id, node.type); }}
        onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); onContextMenu(e, node); }}
      >
        {hasChildren ? (
          <span className={`material-symbols-outlined text-[16px] text-outline transition-transform ${isExpanded ? "rotate-90" : ""}`}>chevron_right</span>
        ) : <span className="w-4" />}
        <span className="material-symbols-outlined text-[16px]">{TYPE_ICONS[node.type]}</span>
        <span className="flex-1 truncate">{node.label}</span>
      </div>
      {hasChildren && isExpanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={{ ...child, depth: (node.depth || 0) + 1 }} selectedId={selectedId} onSelect={onSelect} expanded={expanded} onToggle={onToggle} onContextMenu={onContextMenu} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Kanban Card (draggable)
// ---------------------------------------------------------------------------

function KanbanCard({ task, onDragStart, onContextMenu, onClick, highlight }) {
  const pr = PRIORITY_MAP[task.priority] || PRIORITY_MAP.mid;
  return (
    <div
      draggable
      onDragStart={(e) => { e.dataTransfer.setData("text/plain", String(task.id)); onDragStart(task); }}
      onContextMenu={(e) => { e.preventDefault(); onContextMenu(e, task); }}
      onClick={() => onClick && onClick(task)}
      className={`bg-surface-container-lowest rounded-xl border p-3 hover:shadow-md transition cursor-pointer active:cursor-grabbing ${highlight ? "border-primary ring-2 ring-primary/30 animate-pulse" : "border-outline-variant"}`}
    >
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="flex items-center gap-1 text-[10px] font-label text-on-surface-variant">
          <span className={`w-1.5 h-1.5 rounded-full ${pr.dot}`} />
          {pr.label}
        </span>
        <span className="text-[10px] text-outline font-label ml-auto">{task.assignee}</span>
      </div>
      <p className="text-xs font-label font-semibold text-on-surface leading-snug">{task.title}</p>
      {task.memo && <p className="text-[11px] text-on-surface-variant font-body mt-1 line-clamp-2">{task.memo}</p>}
      {(task.deadline || task.due_date) && (
        <p className="text-[10px] text-outline font-label mt-1.5">{task.deadline || task.due_date}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Kanban Column
// ---------------------------------------------------------------------------

function KanbanColumn({ status, tasks, onDrop, onDragStart, onTaskContextMenu, onTaskClick, onAddTask, highlightTaskId }) {
  const st = STATUS_MAP[status];
  const [dragOver, setDragOver] = useState(false);

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const taskId = parseInt(e.dataTransfer.getData("text/plain"));
    if (!isNaN(taskId)) onDrop(taskId, status);
  };

  return (
    <div
      className={`flex-1 min-w-[200px] flex flex-col rounded-xl border transition-colors ${dragOver ? "border-primary bg-primary/5" : "border-outline-variant/50 bg-surface-container-low/50"}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Column header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-outline-variant/50">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[11px] font-label font-bold ${st.bg} ${st.text}`}>
            {st.label}
          </span>
          <span className="text-[11px] font-label text-outline">{tasks.length}</span>
        </div>
        <button onClick={() => onAddTask(status)} className="p-0.5 rounded hover:bg-surface-container transition" title="할일 추가">
          <span className="material-symbols-outlined text-[14px] text-outline">add</span>
        </button>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-[80px]">
        {tasks.map((task) => (
          <KanbanCard key={task.id} task={task} onDragStart={onDragStart} onContextMenu={onTaskContextMenu} onClick={onTaskClick} highlight={highlightTaskId === task.id} />
        ))}
        {tasks.length === 0 && (
          <div className="text-center py-6 text-[11px] text-outline font-label">
            드래그하여 이동
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Task Panel (list view + kanban toggle)
// ---------------------------------------------------------------------------

function TaskPanel({ accountId, accountLabel, tasks, viewMode, onViewModeChange, onAddTask, onBulkAddTasks, onToggleStatus, onTaskContextMenu, onTaskClick, onDrop, onReorder, highlightTaskId }) {
  const [dragIdx, setDragIdx] = useState(null);

  // Group tasks by status for kanban – must be before any early return
  const grouped = useMemo(() => {
    const g = {};
    for (const s of STATUS_ORDER) g[s] = [];
    for (const t of tasks) (g[t.status] || (g[t.status] = [])).push(t);
    return g;
  }, [tasks]);

  if (!accountId) {
    return (
      <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body">
        <div className="text-center">
          <span className="material-symbols-outlined text-5xl text-outline-variant mb-3 block">checklist</span>
          <p className="text-sm">왼쪽 트리에서 계정과목을 선택하세요</p>
        </div>
      </div>
    );
  }

  // List drag reorder handlers
  const handleListDragStart = (e, idx) => {
    setDragIdx(idx);
    e.dataTransfer.effectAllowed = "move";
  };
  const handleListDragOver = (e, idx) => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === idx) return;
    onReorder(dragIdx, idx);
    setDragIdx(idx);
  };
  const handleListDragEnd = () => setDragIdx(null);

  return (
    <div className="flex-1 overflow-y-auto flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="font-headline text-lg font-bold text-on-surface">{accountLabel}</h3>
          <p className="text-xs text-on-surface-variant font-label mt-0.5">할일 {tasks.length}건</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex rounded-xl border border-outline-variant overflow-hidden">
            <button
              onClick={() => onViewModeChange("list")}
              className={`px-2.5 py-1.5 text-xs font-label transition ${viewMode === "list" ? "bg-primary text-white" : "text-on-surface-variant hover:bg-surface-container"}`}
            >
              <span className="material-symbols-outlined text-[16px]">view_list</span>
            </button>
            <button
              onClick={() => onViewModeChange("kanban")}
              className={`px-2.5 py-1.5 text-xs font-label transition ${viewMode === "kanban" ? "bg-primary text-white" : "text-on-surface-variant hover:bg-surface-container"}`}
            >
              <span className="material-symbols-outlined text-[16px]">view_kanban</span>
            </button>
          </div>
          <button onClick={onBulkAddTasks}
            className="px-2.5 py-1.5 rounded-xl border border-outline-variant text-[11px] font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">playlist_add</span>
            <span className="hidden sm:inline">일괄</span>
          </button>
          <button onClick={() => onAddTask()}
            className="px-3 py-1.5 bg-gradient-to-r from-primary to-primary-container text-white text-xs font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px]">add</span>
            <span className="hidden sm:inline">추가</span>
          </button>
        </div>
      </div>

      {/* Kanban view */}
      {viewMode === "kanban" ? (
        <div className="flex-1 flex gap-3 overflow-x-auto pb-2">
          {STATUS_ORDER.map((s) => (
            <KanbanColumn key={s} status={s} tasks={grouped[s]} onDrop={onDrop} onDragStart={() => {}} onTaskContextMenu={onTaskContextMenu} onTaskClick={onTaskClick}
              onAddTask={(status) => onAddTask(status)} highlightTaskId={highlightTaskId} />
          ))}
        </div>
      ) : (
        /* List view with drag reorder */
        <div className="space-y-3 flex-1">
          {tasks.map((task, idx) => {
            const st = STATUS_MAP[task.status] || STATUS_MAP.todo;
            const pr = PRIORITY_MAP[task.priority] || PRIORITY_MAP.mid;
            return (
              <div key={task.id}
                draggable
                onDragStart={(e) => handleListDragStart(e, idx)}
                onDragOver={(e) => handleListDragOver(e, idx)}
                onDragEnd={handleListDragEnd}
                onClick={() => onTaskClick && onTaskClick(task)}
                onContextMenu={(e) => { e.preventDefault(); onTaskContextMenu(e, task); }}
                className={`bg-surface-container-lowest rounded-xl border p-4 hover:shadow-sm transition cursor-pointer active:cursor-grabbing ${dragIdx === idx ? "opacity-50" : ""} ${highlightTaskId === task.id ? "border-primary ring-2 ring-primary/30 animate-pulse" : "border-outline-variant"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 shrink-0 mt-0.5 text-outline">
                    <span className="material-symbols-outlined text-[16px]">drag_indicator</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <button onClick={() => onToggleStatus(task.id)}
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-xl text-[11px] font-label font-semibold ${st.bg} ${st.text} hover:opacity-80 transition`}>
                        {st.label}
                      </button>
                      <span className="flex items-center gap-1 text-[11px] font-label text-on-surface-variant">
                        <span className={`w-1.5 h-1.5 rounded-full ${pr.dot}`} />{pr.label}
                      </span>
                    </div>
                    <p className="text-sm font-label font-semibold text-on-surface">{task.title}</p>
                    {task.memo && <p className="text-xs text-on-surface-variant font-body mt-1">{task.memo}</p>}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs font-label text-on-surface-variant">{task.assignee}</p>
                    <p className="text-[11px] text-outline font-label mt-0.5">{task.deadline || task.due_date}</p>
                  </div>
                </div>
              </div>
            );
          })}
          {tasks.length === 0 && (
            <div className="text-center py-10 text-on-surface-variant text-sm font-body">할일이 없습니다</div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

let nextId = 100;

export default function Engagements() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tree, setTree] = useState([]);
  const [tasks, setTasks] = useState({});
  const [useApi, setUseApi] = useState(false);
  const [ctxMenu, setCtxMenu] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const [highlightTaskId, setHighlightTaskId] = useState(null);
  const [detailTask, setDetailTask] = useState(null);
  const [detailPath, setDetailPath] = useState("");

  // ── Persisted across navigation ──
  const [selectedId, setSelectedId] = usePersistedState("eng:selectedId", null);
  const [selectedType, setSelectedType] = usePersistedState("eng:selectedType", "account");
  const [expanded, setExpanded] = usePersistedState("eng:expanded", {});
  const [viewMode, setViewMode] = usePersistedState("eng:viewMode", "kanban");
  const [treeOpen, setTreeOpen] = usePersistedState("eng:treeOpen", true);
  const [activeTab, setActiveTab] = usePersistedState("eng:activeTab", "main");
  const taskScrollRef = usePersistedScroll("eng:taskScroll");
  const [bulkModal, setBulkModal] = useState(null); // null | { mode: "account"|"task", phaseNode? }

  // Helper: expand all ancestors of a node in the tree
  function expandPathTo(nodeId, treeData) {
    const path = [];
    function walk(nodes, trail) {
      for (const n of nodes) {
        if (n.id === nodeId) { path.push(...trail); return true; }
        if (n.children) { if (walk(n.children, [...trail, n.id])) return true; }
      }
      return false;
    }
    walk(treeData, []);
    return path;
  }

  // Load tree (re-run when navigated here with reload/select params)
  const reloadKey = searchParams.get("reload") || "";
  useEffect(() => {
    api.getEngagementTree().then((apiTree) => {
      if (apiTree?.length) {
        setTree(apiTree);
        setUseApi(true);

        // Handle URL params for search navigation
        const selectNode = searchParams.get("select");
        const highlightId = searchParams.get("highlight");

        if (selectNode) {
          // Expand ancestors and select the target node
          const ancestors = expandPathTo(selectNode, apiTree);
          const expMap = {};
          ancestors.forEach((id) => { expMap[id] = true; });
          setExpanded((prev) => ({ ...prev, ...expMap }));

          // If it's a client/phase node, find its first account child
          const node = findNodeById(apiTree, selectNode);
          if (node && node.type === "account") {
            setSelectedId(selectNode);
            setSelectedType("account");
          } else if (node && node.type === "client") {
            setSelectedId(selectNode);
            setSelectedType("account"); // search nav goes to account view
            // If there's a highlight, find the account
            const firstAcc = findFirstAccount(node.children || []);
            if (firstAcc) { setSelectedId(firstAcc.id); setSelectedType("account"); }
          } else if (node && node.children) {
            const firstAcc = findFirstAccount(node.children);
            if (firstAcc) { setSelectedId(firstAcc.id); setSelectedType("account"); }
            else setSelectedId(selectNode);
          } else {
            setSelectedId(selectNode);
          }

          if (highlightId) {
            setHighlightTaskId(Number(highlightId));
            setTimeout(() => setHighlightTaskId(null), 3000);
          }

          // Clear URL params
          setSearchParams({}, { replace: true });
        } else if (!selectedId) {
          // Only auto-select if nothing is persisted from a previous visit
          const first = findFirstAccount(apiTree);
          if (first) { setSelectedId(first.id); setSelectedType("account"); }
        }
      }
    }).catch(() => { setLoadError(true); });
    // Clear reload param after loading
    if (reloadKey) setSearchParams({}, { replace: true });
  }, [reloadKey]);

  function findFirstAccount(nodes) {
    for (const n of nodes) {
      if (n.type === "account") return n;
      if (n.children) { const f = findFirstAccount(n.children); if (f) return f; }
    }
    return null;
  }

  function findNodeById(nodes, id) {
    for (const n of nodes) {
      if (n.id === id) return n;
      if (n.children) { const f = findNodeById(n.children, id); if (f) return f; }
    }
    return null;
  }

  // Find the client node that owns a given node id
  function findClientForNode(nodes, targetId, parentClient) {
    for (const n of nodes) {
      const curClient = n.type === "client" ? n : parentClient;
      if (n.id === targetId) return curClient;
      if (n.children) {
        const found = findClientForNode(n.children, targetId, curClient);
        if (found) return found;
      }
    }
    return null;
  }

  // Collect all accounts under a client node for dropdowns
  function collectAccounts(nodes) {
    const result = [];
    function walk(list) {
      for (const n of list) {
        if (n.type === "account") result.push({ id: n.dbId || parseInt(String(n.id).replace("account-", "")), label: n.label, name: n.label });
        if (n.children) walk(n.children);
      }
    }
    walk(nodes);
    return result;
  }

  const ownerClient = selectedId ? findClientForNode(tree, selectedId, null) : null;
  const ownerClientNodeId = ownerClient ? ownerClient.id : selectedId;
  const clientAccounts = ownerClient?.children ? collectAccounts(ownerClient.children) : [];

  // Load tasks when an account is selected
  useEffect(() => {
    if (!selectedId || !useApi || selectedType !== "account") return;
    const dbId = extractDbId(selectedId);
    if (!dbId) return;
    api.getTasks(dbId).then((apiTasks) => {
      setTasks((prev) => ({ ...prev, [selectedId]: apiTasks.map((t) => ({ ...t, deadline: t.due_date })) }));
    }).catch(() => {});
  }, [selectedId, selectedType, useApi]);

  function extractDbId(nodeId) {
    const m = nodeId.match(/^(?:account|phase|client)-(\d+)$/);
    return m ? parseInt(m[1]) : null;
  }

  const handleTreeSelect = (id, type) => {
    setSelectedId(id);
    setSelectedType(type || "account");
    setActiveTab("main");
  };

  const onToggle = (id) => setExpanded((prev) => ({ ...prev, [id]: prev[id] === false ? true : false }));

  function findLabel(nodes) {
    for (const n of nodes) {
      if (n.id === selectedId) return n.label;
      if (n.children) { const f = findLabel(n.children); if (f) return f; }
    }
    return null;
  }

  // ── Tree mutations ──

  function updateTree(updater) { setTree((prev) => updater(prev)); }

  function addChildToNode(nodeId, childNode) {
    updateTree((nodes) => {
      const walk = (list) => list.map((n) => {
        if (n.id === nodeId) return { ...n, children: [...(n.children || []), childNode] };
        if (n.children) return { ...n, children: walk(n.children) };
        return n;
      });
      return walk(nodes);
    });
  }

  function removeNode(nodeId) {
    updateTree((nodes) => {
      const walk = (list) => list.filter((n) => n.id !== nodeId).map((n) => (n.children ? { ...n, children: walk(n.children) } : n));
      return walk(nodes);
    });
  }

  function renameNode(nodeId, newLabel) {
    updateTree((nodes) => {
      const walk = (list) => list.map((n) => {
        if (n.id === nodeId) return { ...n, label: newLabel };
        if (n.children) return { ...n, children: walk(n.children) };
        return n;
      });
      return walk(nodes);
    });
  }

  // ── CRUD ──

  const doAddClient = (fyNode) => {
    const name = prompt("새 클라이언트 이름:"); if (!name) return;
    if (useApi && fyNode.dbId) {
      api.createClient({ fy_id: fyNode.dbId, name, industry: "" }).then(async (created) => {
        const p1 = await api.createPhase({ client_id: created.id, name: "기중감사", sort_order: 0 });
        const p2 = await api.createPhase({ client_id: created.id, name: "기말감사", sort_order: 1 });
        addChildToNode(fyNode.id, { id: `client-${created.id}`, label: name, type: "client", dbId: created.id, children: [
          { id: `phase-${p1.id}`, label: "기중감사", type: "phase", dbId: p1.id, children: [] },
          { id: `phase-${p2.id}`, label: "기말감사", type: "phase", dbId: p2.id, children: [] },
        ]});
      });
    } else { addChildToNode(fyNode.id, { id: `client-${nextId++}`, label: name, type: "client", children: [] }); }
  };

  const doRenameClient = async (node) => {
    const name = prompt("클라이언트 이름 변경:", node.label); if (!name || name === node.label) return;
    renameNode(node.id, name);
    if (useApi && node.dbId) {
      try { await api.updateClient(node.dbId, { name }); }
      catch { renameNode(node.id, node.label); alert("이름 변경에 실패했습니다."); }
    }
  };

  const doDeleteClient = async (node) => {
    if (!confirm(`"${node.label}" 클라이언트를 삭제하시겠습니까?\n하위 모든 감사업무가 삭제됩니다.`)) return;
    if (useApi && node.dbId) {
      try { await api.deleteClient(node.dbId); }
      catch { alert("삭제에 실패했습니다."); return; }
    }
    removeNode(node.id); setSelectedId(null); setSelectedType("account");
  };

  const doAddPhase = (clientNode) => {
    const name = prompt("새 Phase 이름:"); if (!name) return;
    if (useApi && clientNode.dbId) {
      api.createPhase({ client_id: clientNode.dbId, name, sort_order: (clientNode.children?.length || 0) })
        .then((c) => addChildToNode(clientNode.id, { id: `phase-${c.id}`, label: name, type: "phase", dbId: c.id, children: [] }));
    } else { addChildToNode(clientNode.id, { id: `phase-${nextId++}`, label: name, type: "phase", children: [] }); }
  };

  const doDeletePhase = async (node) => {
    if (!confirm(`"${node.label}" Phase를 삭제하시겠습니까?`)) return;
    if (useApi && node.dbId) {
      try { await api.deletePhase(node.dbId); }
      catch { alert("삭제에 실패했습니다."); return; }
    }
    removeNode(node.id); setSelectedId(null); setSelectedType("account");
  };

  const doAddAccount = (phaseNode) => {
    const name = prompt("새 계정과목 이름:"); if (!name) return;
    if (useApi && phaseNode.dbId) {
      api.createAccount({ phase_id: phaseNode.dbId, name, sort_order: (phaseNode.children?.length || 0) })
        .then((c) => { const id = `account-${c.id}`; addChildToNode(phaseNode.id, { id, label: name, type: "account", dbId: c.id }); setTasks((p) => ({ ...p, [id]: [] })); setSelectedId(id); setSelectedType("account"); });
    } else { const id = `account-${nextId++}`; addChildToNode(phaseNode.id, { id, label: name, type: "account" }); setTasks((p) => ({ ...p, [id]: [] })); setSelectedId(id); setSelectedType("account"); }
  };

  const doDeleteAccount = async (node) => {
    if (!confirm(`"${node.label}" 계정과목을 삭제하시겠습니까?`)) return;
    if (useApi && node.dbId) {
      try { await api.deleteAccount(node.dbId); }
      catch { alert("삭제에 실패했습니다."); return; }
    }
    removeNode(node.id); setTasks((p) => { const c = { ...p }; delete c[node.id]; return c; });
    if (selectedId === node.id) { setSelectedId(null); setSelectedType("account"); }
  };

  const doAddTask = (statusOrAccountId) => {
    const title = prompt("할일 제목:"); if (!title) return;
    const isStatus = STATUS_ORDER.includes(statusOrAccountId);
    const targetAccountId = isStatus ? selectedId : (statusOrAccountId || selectedId);
    const status = isStatus ? statusOrAccountId : "todo";
    const dbId = extractDbId(targetAccountId);
    if (useApi && dbId) {
      api.createTask({ account_id: dbId, title, status, assignee: "미배정", priority: "mid", memo: "" })
        .then((c) => { setTasks((p) => ({ ...p, [targetAccountId]: [...(p[targetAccountId] || []), { ...c, deadline: c.due_date }] })); });
    } else {
      setTasks((p) => ({ ...p, [targetAccountId]: [...(p[targetAccountId] || []), { id: nextId++, title, status, assignee: "미배정", deadline: "미정", priority: "mid", memo: "" }] }));
    }
  };

  // ── Bulk create handlers ──

  const doBulkAddAccounts = async (phaseNode, items) => {
    if (useApi && phaseNode.dbId) {
      const startOrder = phaseNode.children?.length || 0;
      const bodies = items.map((item, i) => ({
        phase_id: phaseNode.dbId, name: item.name, sort_order: startOrder + i,
      }));
      try {
        const created = await api.bulkCreateAccounts(bodies);
        for (const c of created) {
          const newId = `account-${c.id}`;
          addChildToNode(phaseNode.id, { id: newId, label: c.name, type: "account", dbId: c.id });
          setTasks((p) => ({ ...p, [newId]: [] }));
        }
      } catch { alert("일괄 추가에 실패했습니다."); }
    } else {
      for (const item of items) {
        const newId = `account-${nextId++}`;
        addChildToNode(phaseNode.id, { id: newId, label: item.name, type: "account" });
        setTasks((p) => ({ ...p, [newId]: [] }));
      }
    }
  };

  const doBulkAddTasks = async (items) => {
    const dbId = extractDbId(selectedId);
    if (useApi && dbId) {
      const bodies = items.map((item) => ({
        account_id: dbId, title: item.title, status: "todo",
        assignee: item.assignee || "미배정", due_date: item.deadline || null,
        priority: "mid", memo: "",
      }));
      try {
        const created = await api.bulkCreateTasks(bodies);
        setTasks((p) => ({
          ...p,
          [selectedId]: [...(p[selectedId] || []), ...created.map((c) => ({ ...c, deadline: c.due_date }))],
        }));
      } catch { alert("일괄 추가에 실패했습니다."); }
    } else {
      const newTasks = items.map((item) => ({
        id: nextId++, title: item.title, status: "todo",
        assignee: item.assignee || "미배정", deadline: item.deadline || "미정",
        priority: "mid", memo: "",
      }));
      setTasks((p) => ({ ...p, [selectedId]: [...(p[selectedId] || []), ...newTasks] }));
    }
  };

  const doEditTask = async (task) => {
    const title = prompt("할일 제목:", task.title); if (!title || title === task.title) return;
    setTasks((p) => ({ ...p, [selectedId]: p[selectedId].map((t) => (t.id === task.id ? { ...t, title } : t)) }));
    if (useApi) {
      try { await api.updateTask(task.id, { title }); }
      catch { setTasks((p) => ({ ...p, [selectedId]: p[selectedId].map((t) => (t.id === task.id ? { ...t, title: task.title } : t)) })); alert("수정에 실패했습니다."); }
    }
  };

  const doDeleteTask = async (task) => {
    if (!confirm(`"${task.title}" 할일을 삭제하시겠습니까?`)) return;
    if (useApi) {
      try { await api.deleteTask(task.id); }
      catch { alert("삭제에 실패했습니다."); return; }
    }
    setTasks((p) => ({ ...p, [selectedId]: p[selectedId].filter((t) => t.id !== task.id) }));
  };

  const doChangeTaskStatus = async (task, newStatus) => {
    const oldStatus = task.status;
    setTasks((p) => ({ ...p, [selectedId]: p[selectedId].map((t) => (t.id === task.id ? { ...t, status: newStatus } : t)) }));
    if (useApi) {
      try { await api.updateTask(task.id, { status: newStatus }); }
      catch { setTasks((p) => ({ ...p, [selectedId]: p[selectedId].map((t) => (t.id === task.id ? { ...t, status: oldStatus } : t)) })); alert("상태 변경에 실패했습니다."); }
    }
  };

  const onToggleStatus = (taskId) => {
    const task = (tasks[selectedId] || []).find((t) => t.id === taskId); if (!task) return;
    doChangeTaskStatus(task, STATUS_ORDER[(STATUS_ORDER.indexOf(task.status) + 1) % STATUS_ORDER.length]);
  };

  // Kanban drop: change status
  const onKanbanDrop = (taskId, newStatus) => {
    const task = (tasks[selectedId] || []).find((t) => t.id === taskId);
    if (task && task.status !== newStatus) doChangeTaskStatus(task, newStatus);
  };

  // List reorder
  const onReorder = (fromIdx, toIdx) => {
    setTasks((prev) => {
      const list = [...(prev[selectedId] || [])];
      const [moved] = list.splice(fromIdx, 1);
      list.splice(toIdx, 0, moved);
      return { ...prev, [selectedId]: list };
    });
  };

  // ── Task detail panel ──

  const openTaskDetail = (task) => {
    // Load full task detail with path from API if available
    if (useApi && task.id) {
      api.getTask(task.id).then((full) => {
        setDetailTask({ ...task, ...full, deadline: full.due_date });
        setDetailPath(full.path || "");
      }).catch(() => {
        setDetailTask(task);
        setDetailPath("");
      });
    } else {
      setDetailTask(task);
      setDetailPath("");
    }
  };

  const handleDetailSave = async (taskId, updates) => {
    const normalized = { ...updates };
    if (updates.due_date !== undefined) normalized.deadline = updates.due_date;
    if (useApi) {
      try {
        const saved = await api.updateTask(taskId, updates);
        // Use API response for authoritative data
        setTasks((prev) => ({
          ...prev,
          [selectedId]: prev[selectedId].map((t) =>
            t.id === taskId ? { ...t, ...saved, deadline: saved.due_date } : t
          ),
        }));
      } catch {
        // Fallback: use local updates
        setTasks((prev) => ({
          ...prev,
          [selectedId]: prev[selectedId].map((t) =>
            t.id === taskId ? { ...t, ...normalized } : t
          ),
        }));
      }
    } else {
      setTasks((prev) => ({
        ...prev,
        [selectedId]: prev[selectedId].map((t) =>
          t.id === taskId ? { ...t, ...normalized } : t
        ),
      }));
    }
    setDetailTask(null);
  };

  const handleDetailDelete = (taskId) => {
    if (useApi) api.deleteTask(taskId).catch(() => {});
    setTasks((prev) => ({
      ...prev,
      [selectedId]: prev[selectedId].filter((t) => t.id !== taskId),
    }));
    setDetailTask(null);
  };

  // ── Context menus ──

  const buildTreeContextMenu = (e, node) => {
    const items = [];
    switch (node.type) {
      case "fy": items.push({ icon: "person_add", label: "클라이언트 추가", action: () => doAddClient(node) }); break;
      case "client":
        items.push({ icon: "edit", label: "이름 변경", action: () => doRenameClient(node) });
        items.push({ icon: "create_new_folder", label: "Phase 추가", action: () => doAddPhase(node) });
        items.push({ divider: true });
        items.push({ icon: "delete", label: "클라이언트 삭제", danger: true, action: () => doDeleteClient(node) });
        break;
      case "phase":
        items.push({ icon: "add", label: "계정과목 추가", action: () => doAddAccount(node) });
        items.push({ icon: "playlist_add", label: "계정과목 일괄 추가", action: () => setBulkModal({ mode: "account", phaseNode: node }) });
        items.push({ divider: true });
        items.push({ icon: "delete", label: "Phase 삭제", danger: true, action: () => doDeletePhase(node) });
        break;
      case "account":
        items.push({ icon: "add_task", label: "할일 추가", action: () => { setSelectedId(node.id); setSelectedType("account"); setTimeout(() => doAddTask(node.id), 100); } });
        items.push({ divider: true });
        items.push({ icon: "delete", label: "계정과목 삭제", danger: true, action: () => doDeleteAccount(node) });
        break;
    }
    setCtxMenu({ x: e.clientX, y: e.clientY, items });
  };

  const buildTaskContextMenu = (e, task) => {
    const statusItems = STATUS_ORDER.filter((s) => s !== task.status).map((s) => ({
      icon: STATUS_MAP[s].icon, label: `→ ${STATUS_MAP[s].label}`, action: () => doChangeTaskStatus(task, s),
    }));
    setCtxMenu({ x: e.clientX, y: e.clientY, items: [
      { icon: "edit", label: "제목 수정", action: () => doEditTask(task) },
      { divider: true }, ...statusItems, { divider: true },
      { icon: "delete", label: "할일 삭제", danger: true, action: () => doDeleteTask(task) },
    ]});
  };

  return (
    <div className="flex flex-col gap-3 lg:gap-5 h-[calc(100vh-7rem)]">
      {loadError && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-error/10 border border-error/20 text-xs font-label text-error shrink-0">
          <span className="material-symbols-outlined text-sm">error</span>
          데이터를 불러오지 못했습니다. 백엔드 서버를 확인해주세요.
          <button onClick={() => { setLoadError(false); window.location.reload(); }} className="ml-auto underline font-semibold">새로고침</button>
        </div>
      )}
      <div className="flex gap-3 lg:gap-5 flex-1 min-h-0">
      {/* Tree panel - collapsible */}
      <div className={`shrink-0 bg-surface-container-lowest rounded-xl border border-outline-variant overflow-y-auto transition-all duration-200 ${
        treeOpen ? "w-64 lg:w-80 p-3" : "w-10 p-1"
      }`}>
        {treeOpen ? (
          <>
            <div className="flex items-center justify-between px-2 mb-3">
              <h3 className="font-headline text-sm font-bold text-on-surface">감사업무 목록</h3>
              <div className="flex items-center gap-1">
                <button onClick={() => { if (tree.length) doAddClient(tree[0]); }}
                  className="p-1 rounded-lg hover:bg-surface-container transition" title="클라이언트 추가">
                  <span className="material-symbols-outlined text-[16px] text-outline">add</span>
                </button>
                <button onClick={() => setTreeOpen(false)}
                  className="p-1 rounded-lg hover:bg-surface-container transition" title="패널 접기">
                  <span className="material-symbols-outlined text-[16px] text-outline">chevron_left</span>
                </button>
              </div>
            </div>
            {tree.map((node) => (
              <TreeNode key={node.id} node={{ ...node, depth: 0 }} selectedId={selectedId} onSelect={handleTreeSelect} expanded={expanded} onToggle={onToggle} onContextMenu={buildTreeContextMenu} />
            ))}
          </>
        ) : (
          <button onClick={() => setTreeOpen(true)}
            className="w-full flex items-center justify-center p-1.5 rounded-lg hover:bg-surface-container transition" title="패널 열기">
            <span className="material-symbols-outlined text-[18px] text-outline">chevron_right</span>
          </button>
        )}
      </div>

      {/* Right panel with tabs */}
      <div className="flex-1 bg-surface-container-lowest rounded-xl border border-outline-variant p-3 lg:p-5 overflow-hidden min-w-0 flex flex-col">
        {/* Tabs – shown when something is selected */}
        {selectedId && (
          <div className="flex items-center gap-1 mb-4 border-b border-outline-variant/50 pb-2 shrink-0">
            <button onClick={() => setActiveTab("main")}
              className={`px-3 py-1.5 rounded-t-xl text-xs font-label font-semibold transition ${activeTab === "main" ? "text-primary border-b-2 border-primary" : "text-on-surface-variant hover:text-on-surface"}`}>
              <span className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px]">{selectedType === "client" ? "analytics" : "checklist"}</span>
                {selectedType === "client" ? "요약" : "할일"}
              </span>
            </button>
            <button onClick={() => setActiveTab("pbc")}
              className={`px-3 py-1.5 rounded-t-xl text-xs font-label font-semibold transition ${activeTab === "pbc" ? "text-primary border-b-2 border-primary" : "text-on-surface-variant hover:text-on-surface"}`}>
              <span className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px]">description</span>
                요청자료
              </span>
            </button>
          </div>
        )}

        {/* Tab content */}
        <div ref={taskScrollRef} className="flex-1 overflow-hidden flex flex-col min-h-0">
          {activeTab === "pbc" && selectedId ? (
            <PBCPanel
              clientId={ownerClientNodeId}
              accountId={selectedId}
              filterByAccount={selectedType === "account"}
              useApi={useApi}
              accounts={clientAccounts}
            />
          ) : selectedType === "client" && selectedId?.startsWith("client-") ? (
            <ClientSummaryPanel
              clientNodeId={selectedId}
              useApi={useApi}
              onSelectAccount={(accountNodeId) => handleTreeSelect(accountNodeId, "account")}
            />
          ) : (
            <TaskPanel
              accountId={selectedId}
              accountLabel={findLabel(tree)}
              tasks={tasks[selectedId] || []}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              onAddTask={doAddTask}
              onBulkAddTasks={() => setBulkModal({ mode: "task" })}
              onToggleStatus={onToggleStatus}
              onTaskContextMenu={buildTaskContextMenu}
              onTaskClick={openTaskDetail}
              onDrop={onKanbanDrop}
              onReorder={onReorder}
              highlightTaskId={highlightTaskId}
            />
          )}
        </div>
      </div>

      {ctxMenu && <ContextMenu x={ctxMenu.x} y={ctxMenu.y} items={ctxMenu.items} onClose={() => setCtxMenu(null)} />}

      {detailTask && (
        <TaskDetailPanel
          task={detailTask}
          path={detailPath}
          onClose={() => setDetailTask(null)}
          onSave={handleDetailSave}
          onDelete={handleDetailDelete}
          useApi={useApi}
        />
      )}

      {bulkModal && (
        <BulkAddModal
          mode={bulkModal.mode}
          onClose={() => setBulkModal(null)}
          onSubmit={(items) => {
            if (bulkModal.mode === "account" && bulkModal.phaseNode) {
              doBulkAddAccounts(bulkModal.phaseNode, items);
            } else if (bulkModal.mode === "task") {
              doBulkAddTasks(items);
            }
          }}
        />
      )}
      </div>
    </div>
  );
}
