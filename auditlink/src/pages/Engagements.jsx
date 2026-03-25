import { useState, useEffect, useCallback } from "react";
import api from "../api";

// ---------------------------------------------------------------------------
// Fallback Mock Data
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

const fallbackTree = [
  {
    id: "fy2025", label: "FY2025", type: "fy", children: [
      {
        id: "hanbit", label: "한빛제조", type: "client", children: [
          { id: "hanbit-interim", label: "기중감사", type: "phase", children: [
            { id: "hanbit-interim-ar", label: "매출채권", type: "account" },
            { id: "hanbit-interim-inv", label: "재고자산", type: "account" },
          ]},
          { id: "hanbit-final", label: "기말감사", type: "phase", children: [
            { id: "hanbit-final-ppe", label: "유형자산", type: "account" },
            { id: "hanbit-final-lease", label: "리스", type: "account" },
          ]},
        ],
      },
      {
        id: "seohyun", label: "서현테크", type: "client", children: [
          { id: "seohyun-interim", label: "기중감사", type: "phase", children: [
            { id: "seohyun-interim-rev", label: "수익인식", type: "account" },
            { id: "seohyun-interim-cash", label: "현금및현금성자산", type: "account" },
          ]},
          { id: "seohyun-final", label: "기말감사", type: "phase", children: [
            { id: "seohyun-final-equity", label: "자본", type: "account" },
            { id: "seohyun-final-provision", label: "충당부채", type: "account" },
          ]},
        ],
      },
    ],
  },
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
  const isExpanded = expanded[node.id] !== false;
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

        {isPhase && (
          <button
            onClick={(e) => { e.stopPropagation(); onAddAccount(node); }}
            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-surface-container-highest transition"
            title="계정과목 추가"
          >
            <span className="material-symbols-outlined text-[14px] text-outline">add</span>
          </button>
        )}

        {isAccount && (
          <button
            onClick={(e) => { e.stopPropagation(); onDeleteAccount(node); }}
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

      <div className="space-y-3">
        {tasks.map((task) => {
          const st = STATUS_MAP[task.status] || STATUS_MAP.todo;
          const pr = PRIORITY_MAP[task.priority] || PRIORITY_MAP.mid;
          return (
            <div
              key={task.id}
              className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 hover:shadow-sm transition"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <button
                      onClick={() => onToggleStatus(task.id)}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-xl text-[11px] font-label font-semibold ${st.bg} ${st.text} hover:opacity-80 transition`}
                    >
                      {st.label}
                    </button>
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
                  <p className="text-[11px] text-outline font-label mt-0.5">{task.deadline || task.due_date}</p>
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
  const [tree, setTree] = useState(fallbackTree);
  const [tasks, setTasks] = useState(fallbackTasks);
  const [selectedId, setSelectedId] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [useApi, setUseApi] = useState(false);

  // Load tree from API
  useEffect(() => {
    api.getEngagementTree().then((apiTree) => {
      if (apiTree?.length) {
        setTree(apiTree);
        setUseApi(true);
        // select first account
        const firstAccount = findFirstAccount(apiTree);
        if (firstAccount) setSelectedId(firstAccount.id);
      }
    }).catch(() => {
      setSelectedId("hanbit-interim-ar");
    });
  }, []);

  function findFirstAccount(nodes) {
    for (const n of nodes) {
      if (n.type === "account") return n;
      if (n.children) {
        const found = findFirstAccount(n.children);
        if (found) return found;
      }
    }
    return null;
  }

  // Load tasks when account selected
  useEffect(() => {
    if (!selectedId || !useApi) return;
    const dbId = extractDbId(selectedId);
    if (!dbId) return;
    api.getTasks(dbId).then((apiTasks) => {
      setTasks((prev) => ({
        ...prev,
        [selectedId]: apiTasks.map((t) => ({
          ...t, deadline: t.due_date,
        })),
      }));
    }).catch(() => {});
  }, [selectedId, useApi]);

  function extractDbId(nodeId) {
    const m = nodeId.match(/^account-(\d+)$/);
    return m ? parseInt(m[1]) : null;
  }

  const onToggle = (id) =>
    setExpanded((prev) => ({ ...prev, [id]: prev[id] === false ? true : false }));

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

  const onAddAccount = (phaseNode) => {
    const name = prompt("새 계정과목 이름:");
    if (!name) return;

    const dbId = phaseNode.dbId;
    if (useApi && dbId) {
      api.createAccount({ phase_id: dbId, name, sort_order: (phaseNode.children?.length || 0) })
        .then((created) => {
          const newId = `account-${created.id}`;
          const addChild = (nodes) =>
            nodes.map((n) => {
              if (n.id === phaseNode.id) {
                return { ...n, children: [...(n.children || []), { id: newId, label: name, type: "account", dbId: created.id }] };
              }
              if (n.children) return { ...n, children: addChild(n.children) };
              return n;
            });
          setTree(addChild(tree));
          setTasks((prev) => ({ ...prev, [newId]: [] }));
          setSelectedId(newId);
        });
    } else {
      const newId = `account-${nextId++}`;
      const addChild = (nodes) =>
        nodes.map((n) => {
          if (n.id === phaseNode.id) {
            return { ...n, children: [...(n.children || []), { id: newId, label: name, type: "account" }] };
          }
          if (n.children) return { ...n, children: addChild(n.children) };
          return n;
        });
      setTree(addChild(tree));
      setTasks((prev) => ({ ...prev, [newId]: [] }));
      setSelectedId(newId);
    }
  };

  const onDeleteAccount = (accountNode) => {
    if (!confirm(`"${accountNode.label}" 계정과목을 삭제하시겠습니까?`)) return;

    if (useApi && accountNode.dbId) {
      api.deleteAccount(accountNode.dbId).catch(() => {});
    }

    const removeChild = (nodes) =>
      nodes
        .filter((n) => n.id !== accountNode.id)
        .map((n) => (n.children ? { ...n, children: removeChild(n.children) } : n));
    setTree(removeChild(tree));
    setTasks((prev) => {
      const copy = { ...prev };
      delete copy[accountNode.id];
      return copy;
    });
    if (selectedId === accountNode.id) setSelectedId(null);
  };

  const onAddTask = () => {
    const title = prompt("할일 제목:");
    if (!title) return;

    const dbId = extractDbId(selectedId);
    if (useApi && dbId) {
      api.createTask({ account_id: dbId, title, status: "todo", assignee: "미배정", priority: "mid", memo: "" })
        .then((created) => {
          setTasks((prev) => ({
            ...prev,
            [selectedId]: [...(prev[selectedId] || []), { ...created, deadline: created.due_date }],
          }));
        });
    } else {
      setTasks((prev) => ({
        ...prev,
        [selectedId]: [
          ...(prev[selectedId] || []),
          { id: nextId++, title, status: "todo", assignee: "미배정", deadline: "미정", priority: "mid", memo: "" },
        ],
      }));
    }
  };

  const statusOrder = ["todo", "in_progress", "review", "done"];
  const onToggleStatus = (taskId) => {
    const list = tasks[selectedId] || [];
    const task = list.find((t) => t.id === taskId);
    if (!task) return;
    const idx = statusOrder.indexOf(task.status);
    const newStatus = statusOrder[(idx + 1) % statusOrder.length];

    if (useApi) {
      api.updateTask(taskId, { status: newStatus }).catch(() => {});
    }

    setTasks((prev) => ({
      ...prev,
      [selectedId]: prev[selectedId].map((t) =>
        t.id === taskId ? { ...t, status: newStatus } : t
      ),
    }));
  };

  return (
    <div className="flex gap-5 h-[calc(100vh-7rem)]">
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
