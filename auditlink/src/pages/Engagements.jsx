import { useState } from "react";

// ---------------------------------------------------------------------------
// Mock Data
// ---------------------------------------------------------------------------

const STATUS_MAP = {
  todo: { label: "미착수", bg: "bg-outline-variant/30", text: "text-on-surface-variant" },
  in_progress: { label: "진행중", bg: "bg-primary-fixed", text: "text-primary" },
  review: { label: "검토대기", bg: "bg-on-tertiary-container/10", text: "text-on-tertiary-container" },
  done: { label: "완료", bg: "bg-secondary-container", text: "text-on-secondary-container" },
};

const PRIORITY_MAP = {
  high: { label: "상", dot: "bg-error" },
  mid: { label: "중", dot: "bg-on-tertiary-container" },
  low: { label: "하", dot: "bg-secondary" },
};

const initialTree = [
  {
    id: "fy2025",
    label: "FY2025",
    type: "fy",
    children: [
      {
        id: "hanbit",
        label: "한빛제조",
        type: "client",
        children: [
          {
            id: "hanbit-interim",
            label: "기중감사",
            type: "phase",
            children: [
              { id: "hanbit-interim-ar", label: "매출채권", type: "account" },
              { id: "hanbit-interim-inv", label: "재고자산", type: "account" },
            ],
          },
          {
            id: "hanbit-final",
            label: "기말감사",
            type: "phase",
            children: [
              { id: "hanbit-final-ppe", label: "유형자산", type: "account" },
              { id: "hanbit-final-lease", label: "리스", type: "account" },
            ],
          },
        ],
      },
      {
        id: "seohyun",
        label: "서현테크",
        type: "client",
        children: [
          {
            id: "seohyun-interim",
            label: "기중감사",
            type: "phase",
            children: [
              { id: "seohyun-interim-rev", label: "수익인식", type: "account" },
              { id: "seohyun-interim-cash", label: "현금및현금성자산", type: "account" },
            ],
          },
          {
            id: "seohyun-final",
            label: "기말감사",
            type: "phase",
            children: [
              { id: "seohyun-final-equity", label: "자본", type: "account" },
              { id: "seohyun-final-provision", label: "충당부채", type: "account" },
            ],
          },
        ],
      },
    ],
  },
];

const initialTasks = {
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
// Tree Component
// ---------------------------------------------------------------------------

const TYPE_ICONS = {
  fy: "calendar_today",
  client: "business",
  phase: "folder",
  account: "account_balance",
};

function TreeNode({ node, selectedId, onSelect, expanded, onToggle, onAddAccount, onDeleteAccount }) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = expanded[node.id] !== false; // default open
  const isSelected = selectedId === node.id;
  const isAccount = node.type === "account";
  const isPhase = node.type === "phase";

  return (
    <div>
      <div
        className={`group flex items-center gap-1.5 px-2 py-1.5 rounded-xl cursor-pointer text-sm font-label transition-all ${
          isSelected && isAccount
            ? "bg-surface-container-lowest shadow-sm text-primary font-semibold"
            : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
        }`}
        style={{ paddingLeft: `${(node.depth || 0) * 16 + 8}px` }}
        onClick={() => {
          if (hasChildren) onToggle(node.id);
          if (isAccount) onSelect(node.id);
        }}
      >
        {/* expand / collapse */}
        {hasChildren ? (
          <span className={`material-symbols-outlined text-[16px] text-outline transition-transform ${isExpanded ? "rotate-90" : ""}`}>
            chevron_right
          </span>
        ) : (
          <span className="w-4" />
        )}

        <span className="material-symbols-outlined text-[16px]">
          {TYPE_ICONS[node.type]}
        </span>

        <span className="flex-1 truncate">{node.label}</span>

        {/* Phase: add account button */}
        {isPhase && (
          <button
            onClick={(e) => { e.stopPropagation(); onAddAccount(node.id); }}
            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-surface-container-highest transition"
            title="계정과목 추가"
          >
            <span className="material-symbols-outlined text-[14px] text-outline">add</span>
          </button>
        )}

        {/* Account: delete button */}
        {isAccount && (
          <button
            onClick={(e) => { e.stopPropagation(); onDeleteAccount(node.id); }}
            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-error/10 transition"
            title="계정과목 삭제"
          >
            <span className="material-symbols-outlined text-[14px] text-error">close</span>
          </button>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={{ ...child, depth: (node.depth || 0) + 1 }}
              selectedId={selectedId}
              onSelect={onSelect}
              expanded={expanded}
              onToggle={onToggle}
              onAddAccount={onAddAccount}
              onDeleteAccount={onDeleteAccount}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Task Panel
// ---------------------------------------------------------------------------

function TaskPanel({ accountId, accountLabel, tasks, onAddTask, onToggleStatus }) {
  if (!accountId) {
    return (
      <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body">
        <div className="text-center">
          <span className="material-symbols-outlined text-5xl text-outline-variant mb-3 block">
            checklist
          </span>
          <p className="text-sm">왼쪽 트리에서 계정과목을 선택하세요</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-headline text-lg font-bold text-on-surface">{accountLabel}</h3>
          <p className="text-xs text-on-surface-variant font-label mt-0.5">
            할일 {tasks.length}건
          </p>
        </div>
        <button
          onClick={onAddTask}
          className="px-3.5 py-2 bg-gradient-to-r from-primary to-primary-container text-white text-xs font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1.5"
        >
          <span className="material-symbols-outlined text-[16px]">add</span>
          할일 추가
        </button>
      </div>

      {/* Task list */}
      <div className="space-y-3">
        {tasks.map((task) => {
          const st = STATUS_MAP[task.status];
          const pr = PRIORITY_MAP[task.priority];
          return (
            <div
              key={task.id}
              className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 hover:shadow-sm transition"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    {/* status badge */}
                    <button
                      onClick={() => onToggleStatus(task.id)}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-xl text-[11px] font-label font-semibold ${st.bg} ${st.text} hover:opacity-80 transition`}
                    >
                      {st.label}
                    </button>
                    {/* priority dot */}
                    <span className="flex items-center gap-1 text-[11px] font-label text-on-surface-variant">
                      <span className={`w-1.5 h-1.5 rounded-full ${pr.dot}`} />
                      {pr.label}
                    </span>
                  </div>
                  <p className="text-sm font-label font-semibold text-on-surface">{task.title}</p>
                  {task.memo && (
                    <p className="text-xs text-on-surface-variant font-body mt-1">{task.memo}</p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs font-label text-on-surface-variant">{task.assignee}</p>
                  <p className="text-[11px] text-outline font-label mt-0.5">{task.deadline}</p>
                </div>
              </div>
            </div>
          );
        })}

        {tasks.length === 0 && (
          <div className="text-center py-10 text-on-surface-variant text-sm font-body">
            할일이 없습니다
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Engagements Page
// ---------------------------------------------------------------------------

let nextId = 100;

export default function Engagements() {
  const [tree, setTree] = useState(initialTree);
  const [tasks, setTasks] = useState(initialTasks);
  const [selectedId, setSelectedId] = useState("hanbit-interim-ar");
  const [expanded, setExpanded] = useState({});

  const onToggle = (id) =>
    setExpanded((prev) => ({ ...prev, [id]: prev[id] === false ? true : false }));

  // -- find label for selected account --
  function findLabel(nodes) {
    for (const n of nodes) {
      if (n.id === selectedId) return n.label;
      if (n.children) {
        const found = findLabel(n.children);
        if (found) return found;
      }
    }
    return null;
  }

  // -- add account under a phase --
  const onAddAccount = (phaseId) => {
    const name = prompt("새 계정과목 이름:");
    if (!name) return;
    const newId = `account-${nextId++}`;
    const addChild = (nodes) =>
      nodes.map((n) => {
        if (n.id === phaseId) {
          return { ...n, children: [...(n.children || []), { id: newId, label: name, type: "account" }] };
        }
        if (n.children) return { ...n, children: addChild(n.children) };
        return n;
      });
    setTree(addChild(tree));
    setTasks((prev) => ({ ...prev, [newId]: [] }));
    setSelectedId(newId);
  };

  // -- delete account --
  const onDeleteAccount = (accountId) => {
    if (!confirm(`"${findLabelById(accountId)}" 계정과목을 삭제하시겠습니까?`)) return;
    const removeChild = (nodes) =>
      nodes
        .filter((n) => n.id !== accountId)
        .map((n) => (n.children ? { ...n, children: removeChild(n.children) } : n));
    setTree(removeChild(tree));
    setTasks((prev) => {
      const copy = { ...prev };
      delete copy[accountId];
      return copy;
    });
    if (selectedId === accountId) setSelectedId(null);
  };

  function findLabelById(id) {
    const search = (nodes) => {
      for (const n of nodes) {
        if (n.id === id) return n.label;
        if (n.children) {
          const f = search(n.children);
          if (f) return f;
        }
      }
      return null;
    };
    return search(tree);
  }

  // -- add task --
  const onAddTask = () => {
    const title = prompt("할일 제목:");
    if (!title) return;
    setTasks((prev) => ({
      ...prev,
      [selectedId]: [
        ...(prev[selectedId] || []),
        {
          id: nextId++,
          title,
          status: "todo",
          assignee: "미배정",
          deadline: "미정",
          priority: "mid",
          memo: "",
        },
      ],
    }));
  };

  // -- cycle status --
  const statusOrder = ["todo", "in_progress", "review", "done"];
  const onToggleStatus = (taskId) => {
    setTasks((prev) => {
      const list = prev[selectedId].map((t) => {
        if (t.id !== taskId) return t;
        const idx = statusOrder.indexOf(t.status);
        return { ...t, status: statusOrder[(idx + 1) % statusOrder.length] };
      });
      return { ...prev, [selectedId]: list };
    });
  };

  return (
    <div className="flex gap-5 h-[calc(100vh-7rem)]">
      {/* Left: Tree */}
      <div className="w-80 shrink-0 bg-surface-container-lowest rounded-xl border border-outline-variant p-3 overflow-y-auto">
        <div className="flex items-center justify-between px-2 mb-3">
          <h3 className="font-headline text-sm font-bold text-on-surface">감사업무 목록</h3>
        </div>
        {tree.map((node) => (
          <TreeNode
            key={node.id}
            node={{ ...node, depth: 0 }}
            selectedId={selectedId}
            onSelect={setSelectedId}
            expanded={expanded}
            onToggle={onToggle}
            onAddAccount={onAddAccount}
            onDeleteAccount={onDeleteAccount}
          />
        ))}
      </div>

      {/* Right: Task Panel */}
      <div className="flex-1 bg-surface-container-lowest rounded-xl border border-outline-variant p-5 overflow-y-auto">
        <TaskPanel
          accountId={selectedId}
          accountLabel={findLabel(tree)}
          tasks={tasks[selectedId] || []}
          onAddTask={onAddTask}
          onToggleStatus={onToggleStatus}
        />
      </div>
    </div>
  );
}
