import { useState, useEffect, useRef } from "react";
import { api } from "../api.js";
import { STATUS, PRIORITY, ENG_TYPE } from "../constants.js";
import { StatusDot, StatusPill, PriorityDot, Icon, Spinner } from "../components/Tokens.jsx";

// ---- Context Menu ----
// 업무유형에 따라 리프 항목 명칭 결정: 감사/검토 → "계정과목", 기타 → "항목"
function leafTerm(engType) {
  return engType === "etc" ? "항목" : "계정과목";
}

function ctxItems(node) {
  const term = leafTerm(node.engType);
  switch (node.type) {
    case "fy":
      return [["add-client", "클라이언트 추가", "add_business"]];
    case "client":
      return [["add-eng-audit", "감사 업무 추가", "add"], ["add-eng-review", "검토 업무 추가", "add"], ["add-eng-etc", "기타 업무 추가", "add"], ["rename", "이름 변경", "edit"], ["delete", "삭제", "delete"]];
    case "engagement":
      return [["add-phase", "단계 추가", "layers"], ["rename", "이름 변경", "edit"], ["delete", "삭제", "delete"]];
    case "phase":
      return [["add-account", `${term} 추가`, "add"], ["add-bulk", `${term} 일괄 추가`, "library_add"], ["rename", "이름 변경", "edit"], ["delete", "삭제", "delete"]];
    case "account":
      return [["rename", "이름 변경", "edit"], ["delete", "삭제", "delete"]];
    default:
      return [];
  }
}

function ContextMenu({ menu, onClose, onAction }) {
  if (!menu) return null;
  const items = ctxItems(menu.node);
  return (
    <div>
      <div className="fixed inset-0 z-[55]" onClick={onClose} onContextMenu={(e) => { e.preventDefault(); onClose(); }} />
      <div className="fixed z-[56] w-44 bg-white rounded-lg border border-line shadow-xl py-1" style={{ left: menu.x, top: menu.y }}>
        {items.map(([act, label, icon]) => (
          <button key={act} onClick={() => { onAction(act, menu.node); onClose(); }}
            className={`w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-left transition hover:bg-[#f4f4f5] ${act === "delete" ? "text-[#ef4444]" : "text-ink"}`}>
            <Icon name={icon} className={`text-[16px] ${act === "delete" ? "text-[#ef4444]" : "text-faint"}`} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---- Tree Node ----
function TreeNode({ node, depth, selected, onSelect, open, toggleOpen, onCtx, renaming, renameVal, setRenameVal, commitRename }) {
  const hasKids = (node.children || []).length > 0;
  const isOpen = open;
  const isSelected = selected === node.id;
  const isAccount = node.type === "account";

  return (
    <div>
      <div
        onClick={() => {
          if (hasKids) toggleOpen(node.id);
          if (isAccount || node.type === "client") onSelect(node);
        }}
        onContextMenu={(e) => { e.preventDefault(); onCtx(e, node); }}
        className={`group flex items-center gap-1.5 pr-1.5 py-[5px] rounded-lg cursor-pointer text-[13px] transition-colors min-w-0 ${
          isSelected ? "text-[color:var(--lnac)] font-medium" : "text-sub hover:bg-[#f4f4f5] hover:text-ink"
        }`}
        style={{ paddingLeft: `${depth * 14 + 6}px`, ...(isSelected ? { background: "color-mix(in srgb, var(--lnac) 8%, transparent)" } : {}) }}
      >
        {hasKids
          ? <Icon name="chevron_right" className={`text-[16px] text-faint transition-transform shrink-0 ${isOpen ? "rotate-90" : ""}`} />
          : <span className="w-4 shrink-0" />}

        {renaming === node.id ? (
          <input autoFocus value={renameVal} onChange={(e) => setRenameVal(e.target.value)}
            onBlur={commitRename} onKeyDown={(e) => { if (e.key === "Enter") commitRename(); if (e.key === "Escape") commitRename(true); }}
            onClick={(e) => e.stopPropagation()}
            className="flex-1 min-w-0 px-1 py-0 text-[13px] rounded bg-white text-ink focus:ring-0 focus:outline-none" style={{ border: "1px solid var(--lnac)" }} />
        ) : (
          <span className="flex-1 min-w-0 truncate">{node.label}</span>
        )}

        {node.type === "engagement" && renaming !== node.id && (
          <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full shrink-0"
            style={{ background: `${(ENG_TYPE[node.engType] || ENG_TYPE.etc).color}1a`, color: (ENG_TYPE[node.engType] || ENG_TYPE.etc).color }}>
            {(ENG_TYPE[node.engType] || ENG_TYPE.etc).label}
          </span>
        )}
        {isAccount && node.taskCount > 0 && renaming !== node.id && (
          <span className="text-[10px] text-faint tabular-nums shrink-0">{node.taskCount}</span>
        )}

        <button onClick={(e) => { e.stopPropagation(); onCtx(e, node, true); }}
          className="opacity-0 group-hover:opacity-100 w-4 h-4 flex items-center justify-center rounded hover:bg-line2/50 transition shrink-0">
          <Icon name="more_horiz" className="text-[14px] text-faint" />
        </button>
      </div>

      {hasKids && isOpen && node.children.map((c) => (
        <ChildNode key={c.id} node={c} depth={depth + 1} selected={selected} onSelect={onSelect}
          onCtx={onCtx} renaming={renaming} renameVal={renameVal} setRenameVal={setRenameVal} commitRename={commitRename} />
      ))}
    </div>
  );
}

// Recursive child node with its own open state
function ChildNode({ node, depth, selected, onSelect, onCtx, renaming, renameVal, setRenameVal, commitRename }) {
  const [open, setOpen] = useState(node.type === "fy");
  const toggle = () => setOpen((o) => !o);
  return (
    <TreeNode node={node} depth={depth} selected={selected} onSelect={onSelect}
      open={open} toggleOpen={toggle} onCtx={onCtx}
      renaming={renaming} renameVal={renameVal} setRenameVal={setRenameVal} commitRename={commitRename} />
  );
}

// ---- Status Dropdown ----
function StatusDropdown({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const s = STATUS[value] || STATUS.todo;
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium hover:opacity-80 transition"
        style={{ background: `${s.color}14`, color: s.color }}>
        <span className="w-[6px] h-[6px] rounded-full" style={{ background: s.color }} />
        {s.label}
        <Icon name="expand_more" className="text-[13px]" />
      </button>
      {open && (
        <div>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-7 z-20 w-32 bg-white rounded-lg border border-line shadow-lg py-1">
            {["todo", "in_progress", "review", "done"].map((k) => (
              <button key={k} onClick={() => { onChange(k); setOpen(false); }}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-ink hover:bg-[#f4f4f5] transition text-left">
                <span className="w-[7px] h-[7px] rounded-full" style={{ background: STATUS[k].color }} />
                {STATUS[k].label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---- Task Detail Panel ----
function TaskDetail({ task, onPatch, onDelete }) {
  if (!task) return <div className="text-center py-16 text-faint text-xs">할일을 선택하세요</div>;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <StatusDropdown value={task.status} onChange={(k) => onPatch({ status: k })} />
        <button onClick={onDelete} className="w-6 h-6 rounded flex items-center justify-center text-faint hover:text-[#ef4444] hover:bg-[#f4f4f5] transition">
          <Icon name="delete" className="text-[15px]" />
        </button>
      </div>
      <input
        value={task.title} onChange={(e) => onPatch({ title: e.target.value })}
        className="text-[15px] font-semibold text-ink leading-snug bg-transparent border-0 px-0 focus:ring-0 focus:outline-none"
      />
      <div className="flex flex-col gap-2.5 pt-3 border-t border-line">
        <div className="flex items-center justify-between text-xs">
          <span className="text-faint">담당자</span>
          <input
            value={task.assignee || ""} onChange={(e) => onPatch({ assignee: e.target.value })}
            className="text-ink font-medium bg-transparent border-0 focus:ring-0 focus:outline-none text-right w-24 text-xs"
          />
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-faint">마감일</span>
          <input
            type="date" value={task.deadline || ""} onChange={(e) => onPatch({ deadline: e.target.value })}
            className="text-ink font-medium tabular-nums bg-transparent border-0 focus:ring-0 focus:outline-none text-xs"
          />
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-faint">우선순위</span>
          <select value={task.priority || "mid"} onChange={(e) => onPatch({ priority: e.target.value })}
            className="bg-transparent border-0 focus:ring-0 focus:outline-none text-xs text-ink">
            <option value="high">상</option>
            <option value="mid">중</option>
            <option value="low">하</option>
          </select>
        </div>
      </div>
      <div className="pt-3 border-t border-line">
        <p className="text-xs text-faint mb-2">메모</p>
        <textarea value={task.memo || ""} onChange={(e) => onPatch({ memo: e.target.value })} rows="3"
          placeholder="메모"
          className="w-full text-xs text-sub bg-[#fafafa] rounded-lg p-3 leading-relaxed resize-none focus:bg-white transition" />
      </div>
      {task.history && task.history.length > 0 && (
        <div className="pt-3 border-t border-line">
          <p className="text-xs text-faint mb-2">상태 변경 이력</p>
          <div className="flex flex-col gap-1.5">
            {[...task.history].reverse().map((h, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <span className="w-[6px] h-[6px] rounded-full shrink-0" style={{ background: (STATUS[h.status] || STATUS.todo).color }} />
                <span className="text-sub">{(STATUS[h.status] || STATUS.todo).label}</span>
                <span className="ml-auto text-faint tabular-nums">{h.at}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---- Tasks Tab ----
function TasksTab({ accountId, parentLabel }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState("list");
  const [openId, setOpenId] = useState(null);

  useEffect(() => {
    if (!accountId) return;
    setLoading(true);
    api.getTasks(accountId).then((ts) => {
      setTasks(ts);
      if (ts.length > 0) setOpenId(ts[0].id);
    }).finally(() => setLoading(false));
  }, [accountId]);

  const openTask = tasks.find((t) => t.id === openId) || null;

  const patchTask = async (id, patch) => {
    const updated = await api.updateTask(id, patch);
    setTasks((ts) => ts.map((t) => t.id === id ? updated : t));
  };

  const addTask = async () => {
    const today = new Date().toISOString().slice(0, 10);
    const nt = await api.createTask({ account_id: accountId, title: "새 할일", status: "todo", deadline: today, priority: "mid" });
    setTasks((ts) => [nt, ...ts]);
    setOpenId(nt.id);
  };

  const delTask = async (id) => {
    await api.deleteTask(id);
    setTasks((ts) => ts.filter((t) => t.id !== id));
    setOpenId(null);
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const cols = ["todo", "in_progress", "review", "done"];

  return (
    <div>
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-baseline gap-2.5 min-w-0">
          <h3 className="text-[15px] font-semibold text-ink">{parentLabel || "계정과목"}</h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex bg-[#f4f4f5] rounded-lg p-0.5">
            {[["list", "리스트"], ["kanban", "칸반"]].map(([k, l]) => (
              <button key={k} onClick={() => setView(k)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-md whitespace-nowrap transition ${view === k ? "bg-white text-ink shadow-sm" : "text-faint hover:text-sub"}`}>
                {l}
              </button>
            ))}
          </div>
          <button onClick={addTask}
            className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-sub hover:bg-[#f4f4f5] transition flex items-center gap-1">
            <Icon name="add" className="text-[16px] text-faint" />할일
          </button>
        </div>
      </div>

      {view === "list" ? (
        <div className="flex border-t border-line">
          <div className="flex-1 min-w-0 px-2 py-2">
            {tasks.length === 0
              ? <div className="p-10 text-center text-xs text-faint">할일이 없습니다</div>
              : tasks.map((t) => (
                <div key={t.id} onClick={() => setOpenId(t.id)}
                  className={`flex items-center gap-3 px-4 py-2.5 rounded-lg cursor-pointer transition ${openId === t.id ? "bg-[#f4f4f5]" : "hover:bg-[#fafafa]"}`}>
                  <span className="w-[7px] h-[7px] rounded-full shrink-0" style={{ background: (STATUS[t.status] || STATUS.todo).color }} />
                  <span className={`flex-1 min-w-0 text-[13px] truncate ${t.status === "done" ? "text-faint line-through" : "text-ink"}`}>{t.title}</span>
                  <PriorityDot p={t.priority} />
                  <span className="text-xs text-faint w-12 shrink-0 truncate">{t.assignee || ""}</span>
                  <span className="text-xs text-faint tabular-nums w-20 text-right shrink-0">{t.deadline || ""}</span>
                </div>
              ))}
          </div>
          <div className="w-[260px] xl:w-72 shrink-0 border-l border-line p-6 overflow-y-auto">
            <TaskDetail task={openTask} onPatch={(p) => patchTask(openId, p)} onDelete={() => delTask(openId)} />
          </div>
        </div>
      ) : (
        <>
        <div className="grid grid-cols-4 gap-4 px-6 pb-6 pt-2 border-t border-line bg-[#fafafa]/60">
          {cols.map((col) => {
            const s = STATUS[col];
            const colTasks = tasks.filter((t) => t.status === col);
            return (
              <div key={col} className="flex flex-col gap-2 min-w-0 pt-4"
                onDragOver={(e) => e.preventDefault()}
                onDrop={async () => {
                  const id = window.__kanbanDrag;
                  if (id != null) {
                    await patchTask(id, { status: col });
                    window.__kanbanDrag = null;
                  }
                }}>
                <div className="flex items-center gap-2 px-1">
                  <span className="w-[7px] h-[7px] rounded-full" style={{ background: s.color }} />
                  <span className="text-xs font-medium text-sub">{s.label}</span>
                  <span className="text-[11px] text-faint tabular-nums">{colTasks.length}</span>
                </div>
                {colTasks.map((t) => (
                  <div key={t.id} draggable onDragStart={() => { window.__kanbanDrag = t.id; }} onClick={() => setOpenId(t.id)}
                    className={`bg-white rounded-lg border p-3.5 cursor-pointer transition hover:border-line2 ${openId === t.id ? "border-[color:var(--lnac)]" : "border-line"}`}>
                    <p className="text-[13px] text-ink leading-snug">{t.title}</p>
                    <div className="mt-2.5 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <span className="w-4 h-4 rounded-full bg-[#f4f4f5] flex items-center justify-center text-[8px] font-semibold text-sub">
                          {(t.assignee || "?").slice(0, 1)}
                        </span>
                        <PriorityDot p={t.priority} />
                      </span>
                      <span className="text-[11px] text-faint tabular-nums">{t.deadline || ""}</span>
                    </div>
                  </div>
                ))}
                {colTasks.length === 0 && (
                  <div className="rounded-lg border border-dashed border-line2 py-5 text-center text-[11px] text-faint">없음</div>
                )}
              </div>
            );
          })}
        </div>
        {openTask && (
          <div>
            <div className="fixed inset-0 z-30 bg-black/10" onClick={() => setOpenId(null)} />
            <div className="fixed inset-y-0 right-0 z-40 w-[min(380px,92vw)] bg-white border-l border-line shadow-xl flex flex-col">
              <div className="flex items-center justify-between px-5 py-3 border-b border-line">
                <span className="text-xs font-medium text-faint">할일 편집</span>
                <button onClick={() => setOpenId(null)} className="w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
                  <Icon name="close" className="text-[18px]" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-6">
                <TaskDetail task={openTask} onPatch={(p) => patchTask(openId, p)} onDelete={() => delTask(openId)} />
              </div>
            </div>
          </div>
        )}
        </>
      )}
    </div>
  );
}

// ---- PBC constants ----
const PBC_STATUS = {
  draft:     { label: "요청전",   color: "#9ca3af" },
  requested: { label: "요청중",   color: "#3b82f6" },
  received:  { label: "수령완료", color: "#10b981" },
  overdue:   { label: "지연",     color: "#ef4444" },
};
const PBC_DONE = {
  full:    { mark: "○", color: "#10b981", label: "완전" },
  partial: { mark: "△", color: "#f59e0b", label: "부분" },
  none:    { mark: "×", color: "#9ca3af", label: "미수령" },
};

function DoneCycle({ value, onChange }) {
  const order = ["none", "partial", "full"];
  const d = PBC_DONE[value] || PBC_DONE.none;
  return (
    <button onClick={(e) => { e.stopPropagation(); onChange(order[(order.indexOf(value) + 1) % 3]); }}
      title={`완성도: ${d.label} (클릭하여 변경)`}
      className="w-6 h-6 rounded-md flex items-center justify-center text-sm font-bold hover:bg-[#f4f4f5] transition"
      style={{ color: d.color }}>{d.mark}</button>
  );
}

// ---- PBC Tab ----  accounts: [{ id, label }] (1개=계정 / 여러 개=클라이언트 집계)
function PbcTab({ accounts }) {
  const isAggregate = accounts.length !== 1;
  const accLabel = (id) => accounts.find((a) => a.id === id)?.label || "";
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");
  const [sel, setSel] = useState(new Set());
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", dept: "", due: "", account_id: accounts[0]?.id });

  const accKey = accounts.map((a) => a.id).join(",");
  useEffect(() => {
    setLoading(true);
    setSel(new Set());
    Promise.all(accounts.map((a) => api.getPbc(a.id)))
      .then((lists) => setItems(lists.flat()))
      .finally(() => setLoading(false));
    setForm((f) => ({ ...f, account_id: accounts[0]?.id }));
  }, [accKey]);

  const counts = items.reduce((a, i) => { a[i.status] = (a[i.status] || 0) + 1; return a; }, {});
  const shown = filter === "all" ? items : items.filter((i) => i.status === filter);
  const allChecked = shown.length > 0 && shown.every((i) => sel.has(i.id));

  const toggle = (id) => setSel((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleAll = () => setSel(() => (allChecked ? new Set() : new Set(shown.map((i) => i.id))));

  const patch = async (id, p) => {
    const updated = await api.updatePbc(id, p);
    setItems((list) => list.map((i) => (i.id === id ? updated : i)));
  };
  const bulkStatus = async (st) => {
    const ids = [...sel];
    const extra = st === "received" ? { done: "full" } : {};
    const updates = await Promise.all(ids.map((id) => api.updatePbc(id, { status: st, ...extra })));
    setItems((list) => list.map((i) => updates.find((u) => u.id === i.id) || i));
    setSel(new Set());
  };
  const bulkDelete = async () => {
    const ids = [...sel];
    await Promise.all(ids.map((id) => api.deletePbc(id)));
    setItems((list) => list.filter((i) => !ids.includes(i.id)));
    setSel(new Set());
  };
  const del = async (id) => { await api.deletePbc(id); setItems((list) => list.filter((i) => i.id !== id)); };

  const addItem = async () => {
    if (!form.name.trim() || !form.account_id) return;
    const created = await api.createPbc({
      account_id: form.account_id, name: form.name.trim(), dept: form.dept, due: form.due, status: "draft", done: "none",
    });
    setItems((its) => [created, ...its]);
    setForm({ name: "", dept: "", due: "", account_id: accounts[0]?.id });
    setAdding(false);
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const gridCols = isAggregate
    ? "28px 110px 1fr 130px 70px 64px 56px 92px"
    : "28px 1fr 130px 70px 64px 56px 92px";

  return (
    <div>
      <div className="flex items-center justify-between px-6 py-4 flex-wrap gap-2">
        <div className="flex items-center gap-1 flex-wrap">
          <button onClick={() => setFilter("all")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${filter === "all" ? "bg-[#f4f4f5] text-ink" : "text-faint hover:text-sub"}`}>전체 {items.length}</button>
          {Object.entries(PBC_STATUS).map(([k, v]) => (
            <button key={k} onClick={() => setFilter(k)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition ${filter === k ? "bg-[#f4f4f5] text-ink" : "text-faint hover:text-sub"}`}>
              <span className="w-[6px] h-[6px] rounded-full" style={{ background: v.color }} />{v.label} {counts[k] || 0}
            </button>
          ))}
        </div>
        <button onClick={() => setAdding((o) => !o)}
          className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-sub hover:bg-[#f4f4f5] transition flex items-center gap-1">
          <Icon name="add" className="text-[16px] text-faint" />요청자료
        </button>
      </div>

      {adding && (
        <div className="mx-6 mb-3 p-4 bg-[#fafafa] rounded-lg border border-line flex flex-col gap-3">
          {isAggregate && (
            <select value={form.account_id} onChange={(e) => setForm((f) => ({ ...f, account_id: Number(e.target.value) }))}
              className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink">
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
            </select>
          )}
          <input placeholder="자료명 *" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
          <div className="grid grid-cols-2 gap-2">
            <input placeholder="담당부서·담당자" value={form.dept} onChange={(e) => setForm((f) => ({ ...f, dept: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
            <input type="date" value={form.due} onChange={(e) => setForm((f) => ({ ...f, due: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setAdding(false)} className="px-3 py-1.5 text-xs text-sub hover:bg-[#f0f0f0] rounded-lg transition">취소</button>
            <button onClick={addItem} className="px-3.5 py-1.5 rounded-lg text-white text-xs font-medium hover:opacity-90 transition" style={{ background: "var(--lnac)" }}>추가</button>
          </div>
        </div>
      )}

      {sel.size > 0 && (
        <div className="flex items-center gap-3 mx-6 mb-2 px-3 py-2 rounded-lg bg-[#f4f4f5] flex-wrap">
          <span className="text-xs font-medium text-ink">{sel.size}개 선택</span>
          <span className="text-xs text-faint">일괄 상태 변경:</span>
          {Object.entries(PBC_STATUS).map(([k, v]) => (
            <button key={k} onClick={() => bulkStatus(k)}
              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium hover:opacity-80 transition" style={{ background: `${v.color}14`, color: v.color }}>
              <span className="w-[6px] h-[6px] rounded-full" style={{ background: v.color }} />{v.label}
            </button>
          ))}
          <button onClick={bulkDelete} className="ml-auto text-[11px] font-medium text-[#ef4444] hover:bg-[#ef4444]/5 px-2 py-1 rounded transition">삭제</button>
          <button onClick={() => setSel(new Set())} className="text-[11px] text-faint hover:text-sub transition">취소</button>
        </div>
      )}

      <div className="border-t border-line px-2 py-2 overflow-x-auto">
        <div className="grid gap-3 items-center px-4 py-2 text-[11px] text-faint min-w-[620px]" style={{ gridTemplateColumns: gridCols }}>
          <span><input type="checkbox" checked={allChecked} onChange={toggleAll} className="w-3.5 h-3.5 rounded" style={{ accentColor: "var(--lnac)" }} /></span>
          {isAggregate && <span>계정</span>}
          <span>자료명</span><span>담당</span><span>수령기한</span><span>수령일</span><span className="text-center">완성도</span><span className="text-right">상태</span>
        </div>
        {shown.length === 0 && <div className="px-6 py-10 text-center text-xs text-faint">요청자료가 없습니다</div>}
        {shown.map((it) => {
          const s = PBC_STATUS[it.status] || PBC_STATUS.draft;
          const checked = sel.has(it.id);
          return (
            <div key={it.id} className={`grid gap-3 items-center px-4 py-2.5 rounded-lg transition group min-w-[620px] ${checked ? "bg-[#f4f4f5]" : "hover:bg-[#fafafa]"}`} style={{ gridTemplateColumns: gridCols }}>
              <span><input type="checkbox" checked={checked} onChange={() => toggle(it.id)} className="w-3.5 h-3.5 rounded" style={{ accentColor: "var(--lnac)" }} /></span>
              {isAggregate && <span className="text-[11px] text-faint truncate">{accLabel(it.account_id)}</span>}
              <span className="text-[13px] text-ink truncate">{it.name}</span>
              <span className="text-xs text-sub truncate">{it.dept || "—"}</span>
              <span className={`text-xs tabular-nums ${it.status === "overdue" ? "text-[#ef4444] font-medium" : "text-faint"}`}>{it.due || "—"}</span>
              <span className="text-xs text-faint tabular-nums">{it.recv_date || "—"}</span>
              <span className="flex justify-center"><DoneCycle value={it.done} onChange={(d) => patch(it.id, { done: d })} /></span>
              <span className="flex justify-end items-center gap-1">
                <select value={it.status} onChange={(e) => patch(it.id, { status: e.target.value, ...(e.target.value === "received" ? { done: "full" } : {}) })}
                  className="text-[11px] rounded-full pl-2 pr-5 py-0.5 border-0 font-medium" style={{ color: s.color, background: `${s.color}14` }}>
                  {Object.entries(PBC_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </select>
                <button onClick={() => del(it.id)} className="opacity-0 group-hover:opacity-100 w-5 h-5 flex items-center justify-center text-faint hover:text-[#ef4444] transition">
                  <Icon name="delete" className="text-[13px]" />
                </button>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---- Interview export helpers ----
function downloadFile(name, content, mime) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([content], { type: mime }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
function ivToText(iv) {
  const L = [];
  L.push("[감사조서] 인터뷰 기록");
  L.push("=".repeat(40));
  L.push(`일자: ${iv.date || ""}`);
  L.push(`대상자: ${iv.person || ""} ${iv.title || ""} (${iv.dept || ""})`);
  L.push(`장소: ${iv.place || ""}`);
  L.push(`참석자(감사팀): ${iv.attendees || ""}`);
  L.push(`주제/목적: ${iv.topic || ""}`);
  L.push(`상태: ${iv.status === "done" ? "완료" : "진행중"}`);
  L.push("");
  (iv.questions || []).forEach((q, i) => {
    L.push(`Q${i + 1}. ${q.q || ""}`);
    L.push(`A${i + 1}. ${q.a || "(답변 미기록)"}${q.answerer ? ` — ${q.answerer}` : ""}`);
    if (q.follow_up) L.push(`  [후속조치] ${q.follow_up_note || "(내용 미기록)"}`);
    L.push("");
  });
  L.push("총평/특이사항:");
  L.push(iv.memo || "(없음)");
  return L.join("\n");
}
function ivToWordHtml(iv) {
  const esc = (s) => String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const qRows = (iv.questions || []).map((q, i) => `
    <p style="margin:14px 0 4px"><b>Q${i + 1}. ${esc(q.q)}</b></p>
    <p style="margin:0 0 2px">A${i + 1}. ${esc(q.a) || "(답변 미기록)"}${q.answerer ? ` — ${esc(q.answerer)}` : ""}</p>
    ${q.follow_up ? `<p style="margin:2px 0;color:#b45309">[후속조치] ${esc(q.follow_up_note) || "(내용 미기록)"}</p>` : ""}
  `).join("");
  return `<html><head><meta charset="utf-8"><title>인터뷰 기록</title></head>
  <body style="font-family:'맑은 고딕',sans-serif;font-size:11pt;line-height:1.5">
    <h2 style="margin-bottom:4px">[감사조서] 인터뷰 기록</h2>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;font-size:10pt;width:100%">
      <tr><td width="110"><b>일자</b></td><td>${esc(iv.date)}</td><td width="110"><b>상태</b></td><td>${iv.status === "done" ? "완료" : "진행중"}</td></tr>
      <tr><td><b>대상자</b></td><td>${esc(iv.person)} ${esc(iv.title)} (${esc(iv.dept)})</td><td><b>장소</b></td><td>${esc(iv.place)}</td></tr>
      <tr><td><b>참석자(감사팀)</b></td><td>${esc(iv.attendees)}</td><td><b>주제/목적</b></td><td>${esc(iv.topic)}</td></tr>
    </table>
    ${qRows}
    <p style="margin-top:18px"><b>총평/특이사항</b></p>
    <p>${esc(iv.memo) || "(없음)"}</p>
  </body></html>`;
}

const IV_FIELD = "w-full px-2.5 py-1.5 rounded-lg border-0 bg-[#f7f7f8] text-[13px] text-ink focus:bg-white transition";
const IV_TA = IV_FIELD + " resize-none leading-relaxed";

// ---- Interview slide-in detail ----
function InterviewDetail({ iv, onSaved, onDelete, onClose }) {
  const [draft, setDraft] = useState(iv);
  const dragIdx = useRef(null);
  useEffect(() => { setDraft(iv); }, [iv.id]);

  const persist = async (next) => {
    const payload = {
      date: next.date, person: next.person, title: next.title, dept: next.dept,
      place: next.place, attendees: next.attendees, topic: next.topic,
      status: next.status, memo: next.memo,
      questions: (next.questions || []).map((q) => ({
        q: q.q || "", a: q.a || "", answerer: q.answerer || "",
        follow_up: !!q.follow_up, follow_up_note: q.follow_up_note || "",
      })),
    };
    const updated = await api.updateInterview(iv.id, payload);
    onSaved(updated);
  };

  const setField = (k, v) => setDraft((d) => ({ ...d, [k]: v }));
  const patchQ = (i, p) => setDraft((d) => ({ ...d, questions: d.questions.map((q, j) => (j === i ? { ...q, ...p } : q)) }));
  const addQ = () => { const next = { ...draft, questions: [...(draft.questions || []), { q: "", a: "", answerer: "", follow_up: false, follow_up_note: "" }] }; setDraft(next); persist(next); };
  const removeQ = (i) => { const next = { ...draft, questions: draft.questions.filter((_, j) => j !== i) }; setDraft(next); persist(next); };
  const dropQ = (to) => {
    const from = dragIdx.current;
    if (from === null || from === to) return;
    const qs = [...draft.questions]; const [m] = qs.splice(from, 1); qs.splice(to, 0, m);
    dragIdx.current = null;
    const next = { ...draft, questions: qs }; setDraft(next); persist(next);
  };
  const setStatus = (k) => { const next = { ...draft, status: k }; setDraft(next); persist(next); };
  const fuCount = (draft.questions || []).filter((q) => q.follow_up).length;

  return (
    <div>
      <div className="fixed inset-0 z-30 bg-black/10" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 z-40 w-[min(500px,92vw)] bg-white border-l border-line shadow-xl flex flex-col">
        <div className="flex items-center gap-2 px-6 pt-5 pb-4">
          <div className="flex bg-[#f4f4f5] rounded-lg p-0.5">
            {[["in_progress", "진행중"], ["done", "완료"]].map(([k, l]) => (
              <button key={k} onClick={() => setStatus(k)}
                className={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium rounded-md whitespace-nowrap transition ${draft.status === k ? "bg-white text-ink shadow-sm" : "text-faint hover:text-sub"}`}>
                <span className="w-[6px] h-[6px] rounded-full" style={{ background: STATUS[k === "done" ? "done" : "in_progress"].color }} />{l}
              </button>
            ))}
          </div>
          {fuCount > 0 && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium" style={{ background: "#f59e0b14", color: "#f59e0b" }}>
              <span className="w-[6px] h-[6px] rounded-full bg-[#f59e0b]" />후속조치 {fuCount}
            </span>
          )}
          <button onClick={onDelete} className="ml-auto w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:text-[#ef4444] hover:bg-[#f4f4f5] transition">
            <Icon name="delete" className="text-[16px]" />
          </button>
          <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
            <Icon name="close" className="text-[18px]" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 pb-6">
          <input type="text" value={draft.topic || ""} onChange={(e) => setField("topic", e.target.value)} onBlur={() => persist(draft)}
            placeholder="주제/목적" className="w-full px-0 py-0 border-0 bg-transparent text-base font-semibold text-ink focus:ring-0 mb-4" />
          <div className="grid grid-cols-2 gap-x-3 gap-y-3 mb-6">
            <div>
              <p className="text-[10px] text-faint mb-1">인터뷰 날짜</p>
              <input type="date" value={draft.date || ""} onChange={(e) => setField("date", e.target.value)} onBlur={() => persist(draft)} className={IV_FIELD} />
            </div>
            <div>
              <p className="text-[10px] text-faint mb-1">장소</p>
              <input type="text" value={draft.place || ""} onChange={(e) => setField("place", e.target.value)} onBlur={() => persist(draft)} className={IV_FIELD} />
            </div>
            <div>
              <p className="text-[10px] text-faint mb-1">대상자</p>
              <div className="flex gap-2">
                <input type="text" value={draft.person || ""} onChange={(e) => setField("person", e.target.value)} onBlur={() => persist(draft)} placeholder="이름" className={IV_FIELD} />
                <input type="text" value={draft.title || ""} onChange={(e) => setField("title", e.target.value)} onBlur={() => persist(draft)} placeholder="직책" className={IV_FIELD + " !w-20 shrink-0"} />
              </div>
            </div>
            <div>
              <p className="text-[10px] text-faint mb-1">부서</p>
              <input type="text" value={draft.dept || ""} onChange={(e) => setField("dept", e.target.value)} onBlur={() => persist(draft)} className={IV_FIELD} />
            </div>
            <div className="col-span-2">
              <p className="text-[10px] text-faint mb-1">참석자 (감사팀)</p>
              <input type="text" value={draft.attendees || ""} onChange={(e) => setField("attendees", e.target.value)} onBlur={() => persist(draft)} className={IV_FIELD} />
            </div>
          </div>

          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-ink">질의응답 <span className="text-faint font-normal tabular-nums">{(draft.questions || []).length}</span></p>
            <button onClick={addQ} className="px-2 py-1 rounded-lg text-[11px] font-medium text-sub hover:bg-[#f4f4f5] transition flex items-center gap-1">
              <Icon name="add" className="text-[14px] text-faint" />질의 추가
            </button>
          </div>
          <div className="flex flex-col gap-3">
            {(draft.questions || []).map((q, i) => (
              <div key={i} className="rounded-lg border border-line p-4 bg-white" onDragOver={(e) => e.preventDefault()} onDrop={() => dropQ(i)}>
                <div className="flex items-center gap-2 mb-2.5">
                  <span draggable onDragStart={() => { dragIdx.current = i; }}
                    className="material-symbols-outlined text-[16px] text-line2 cursor-grab active:cursor-grabbing hover:text-faint" title="드래그로 순서 변경">drag_indicator</span>
                  <span className="text-xs font-semibold text-sub tabular-nums">Q{i + 1}</span>
                  {q.follow_up && <span className="w-[6px] h-[6px] rounded-full bg-[#f59e0b]" title="후속조치 필요" />}
                  <button onClick={() => removeQ(i)} className="ml-auto w-5 h-5 rounded flex items-center justify-center text-line2 hover:text-[#ef4444] transition">
                    <Icon name="close" className="text-[14px]" />
                  </button>
                </div>
                <div className="flex flex-col gap-2.5">
                  <div>
                    <p className="text-[10px] text-faint mb-1">질의사항</p>
                    <textarea rows="2" value={q.q || ""} onChange={(e) => patchQ(i, { q: e.target.value })} onBlur={() => persist(draft)} placeholder="질의 내용" className={IV_TA} />
                  </div>
                  <div>
                    <p className="text-[10px] text-faint mb-1">답변사항</p>
                    <textarea rows="2" value={q.a || ""} onChange={(e) => patchQ(i, { a: e.target.value })} onBlur={() => persist(draft)} placeholder="답변 내용" className={IV_TA} />
                  </div>
                  <div className="flex items-center gap-3">
                    <input type="text" value={q.answerer || ""} onChange={(e) => patchQ(i, { answerer: e.target.value })} onBlur={() => persist(draft)} placeholder="답변자" className={IV_FIELD + " !w-32"} />
                    <label className="flex items-center gap-1.5 text-xs text-sub cursor-pointer select-none">
                      <input type="checkbox" checked={!!q.follow_up} onChange={(e) => { patchQ(i, { follow_up: e.target.checked }); }}
                        onBlur={() => persist(draft)} className="w-3.5 h-3.5 rounded" style={{ accentColor: "var(--lnac)" }} />
                      후속조치 필요
                    </label>
                  </div>
                  {q.follow_up && (
                    <div>
                      <p className="text-[10px] mb-1" style={{ color: "#f59e0b" }}>후속조치 내용</p>
                      <textarea rows="2" value={q.follow_up_note || ""} onChange={(e) => patchQ(i, { follow_up_note: e.target.value })} onBlur={() => persist(draft)} placeholder="후속으로 확인/요청할 사항" className={IV_TA} />
                    </div>
                  )}
                </div>
              </div>
            ))}
            {(draft.questions || []).length === 0 && (
              <div className="rounded-lg border border-dashed border-line2 py-8 text-center text-xs text-faint">질의를 추가하세요</div>
            )}
          </div>

          <div className="mt-6">
            <p className="text-xs font-semibold text-ink mb-2">전체 메모 <span className="text-faint font-normal">— 총평/특이사항</span></p>
            <textarea rows="3" value={draft.memo || ""} onChange={(e) => setField("memo", e.target.value)} onBlur={() => persist(draft)}
              placeholder="인터뷰 총평, 특이사항, 감사 시사점" className={IV_TA} />
          </div>
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-line">
          <span className="text-[10px] text-faint">워킹페이퍼 형식으로 내보내기</span>
          <div className="flex gap-2">
            <button onClick={() => downloadFile(`인터뷰_${draft.date || ""}_${draft.person || ""}.doc`, ivToWordHtml(draft), "application/msword")}
              className="px-3 py-1.5 rounded-lg border border-line2 text-xs font-medium text-sub hover:bg-[#fafafa] transition flex items-center gap-1.5">
              <Icon name="description" className="text-[15px] text-faint" />워드 (.doc)
            </button>
            <button onClick={() => downloadFile(`인터뷰_${draft.date || ""}_${draft.person || ""}.txt`, ivToText(draft), "text/plain;charset=utf-8")}
              className="px-3 py-1.5 rounded-lg border border-line2 text-xs font-medium text-sub hover:bg-[#fafafa] transition flex items-center gap-1.5">
              <Icon name="article" className="text-[15px] text-faint" />텍스트 (.txt)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Interview Tab ----  accounts: [{ id, label }]
function InterviewTab({ accounts }) {
  const isAggregate = accounts.length !== 1;
  const accLabel = (id) => accounts.find((a) => a.id === id)?.label || "";
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [openId, setOpenId] = useState(null);

  const accKey = accounts.map((a) => a.id).join(",");
  useEffect(() => {
    setLoading(true);
    Promise.all(accounts.map((a) => api.getInterviews(a.id)))
      .then((lists) => setInterviews(lists.flat()))
      .finally(() => setLoading(false));
  }, [accKey]);

  const addInterview = async () => {
    const accId = accounts[0]?.id;
    if (!accId) return;
    const created = await api.createInterview({
      account_id: accId, date: new Date().toISOString().slice(0, 10),
      person: "", title: "", dept: "", place: "", attendees: "",
      topic: "새 인터뷰", status: "in_progress", memo: "",
      questions: [{ q: "", a: "", answerer: "", follow_up: false, follow_up_note: "" }],
    });
    setInterviews((ivs) => [created, ...ivs]);
    setOpenId(created.id);
  };

  const onSaved = (updated) => setInterviews((ivs) => ivs.map((i) => (i.id === updated.id ? updated : i)));
  const del = async (id) => { await api.deleteInterview(id); setInterviews((ivs) => ivs.filter((i) => i.id !== id)); setOpenId(null); };

  const sorted = [...interviews].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  const doneN = interviews.filter((i) => i.status === "done").length;
  const openIv = interviews.find((i) => i.id === openId) || null;

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div>
      <div className="flex items-center justify-between px-6 py-4">
        <span className="text-xs text-faint">완료 {doneN} · 진행중 {interviews.length - doneN}</span>
        <button onClick={addInterview}
          className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-sub hover:bg-[#f4f4f5] transition flex items-center gap-1">
          <Icon name="add" className="text-[16px] text-faint" />인터뷰 추가
        </button>
      </div>
      <div className="border-t border-line px-6 py-5 flex flex-col gap-2.5">
        {sorted.length === 0 && <div className="py-10 text-center text-xs text-faint">기록된 인터뷰가 없습니다</div>}
        {sorted.map((iv) => {
          const fuCount = (iv.questions || []).filter((q) => q.follow_up).length;
          return (
            <div key={iv.id} onClick={() => setOpenId(iv.id)}
              className={`rounded-lg border p-4 cursor-pointer transition ${openId === iv.id ? "border-[color:var(--lnac)]" : "border-line hover:border-line2"}`}>
              <div className="flex items-center gap-4">
                <span className="shrink-0 w-[72px] text-xs text-faint tabular-nums">{(iv.date || "").slice(5).replace("-", "/")}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="w-[7px] h-[7px] rounded-full shrink-0" style={{ background: STATUS[iv.status === "done" ? "done" : "in_progress"].color }} />
                    <p className="text-[13px] font-medium text-ink truncate">{iv.topic || "제목 없음"}</p>
                    {fuCount > 0 && <span className="w-[7px] h-[7px] rounded-full bg-[#f59e0b] shrink-0" title={`후속조치 ${fuCount}건`} />}
                  </div>
                  <p className="text-xs text-faint mt-0.5 truncate">
                    {iv.person ? `${iv.person} ${iv.title || ""}` : "대상자 미지정"} · {iv.dept || "—"}
                    {isAggregate && ` · ${accLabel(iv.account_id)}`}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-faint tabular-nums">질의 {(iv.questions || []).length}건</span>
                <Icon name="chevron_right" className="text-[16px] text-line2 shrink-0" />
              </div>
            </div>
          );
        })}
      </div>
      {openIv && <InterviewDetail iv={openIv} onSaved={onSaved} onDelete={() => del(openIv.id)} onClose={() => setOpenId(null)} />}
    </div>
  );
}

// ---- Client Summary Tab ----
function Donut({ segments, size = 128, stroke = 16 }) {
  const r = (size - stroke) / 2, c = 2 * Math.PI * r;
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  let offset = 0;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f0f0f0" strokeWidth={stroke} />
        {segments.filter((s) => s.value > 0).map((s, i) => {
          const len = (s.value / total) * c;
          const el = <circle key={i} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={s.color} strokeWidth={stroke}
            strokeDasharray={`${len} ${c - len}`} strokeDashoffset={-offset} className="transition-all duration-700" />;
          offset += len;
          return el;
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold text-ink tabular-nums">{Math.round((segments.find((s) => s.key === "done")?.value || 0) / total * 100)}%</span>
        <span className="text-[10px] text-faint">완료율</span>
      </div>
    </div>
  );
}

function ClientSummaryTab({ accounts, clientLabel, industry }) {
  const [tasksByAcc, setTasksByAcc] = useState({});
  const [loading, setLoading] = useState(false);
  const accKey = accounts.map((a) => a.id).join(",");
  useEffect(() => {
    setLoading(true);
    Promise.all(accounts.map((a) => api.getTasks(a.id).then((ts) => [a.id, ts])))
      .then((pairs) => setTasksByAcc(Object.fromEntries(pairs)))
      .finally(() => setLoading(false));
  }, [accKey]);

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const allTasks = accounts.flatMap((a) => (tasksByAcc[a.id] || []).map((t) => ({ ...t, _acc: a.label })));
  const total = allTasks.length;
  const byStatus = ["todo", "in_progress", "review", "done"].map((k) => ({
    key: k, label: STATUS[k].label, color: STATUS[k].color, value: allTasks.filter((t) => t.status === k).length,
  }));
  const assignees = [...new Set(allTasks.map((t) => t.assignee).filter(Boolean))].map((name) => {
    const list = allTasks.filter((t) => t.assignee === name);
    return { name, total: list.length, done: list.filter((t) => t.status === "done").length };
  }).sort((a, b) => b.total - a.total);
  const maxA = Math.max(1, ...assignees.map((a) => a.total));

  const exportCsv = () => {
    const statusKo = { todo: "미착수", in_progress: "진행중", review: "검토대기", done: "완료" };
    const prioKo = { high: "상", mid: "중", low: "하" };
    const head = ["계정과목", "할일", "담당자", "상태", "우선순위", "마감일"];
    const rows = allTasks.map((t) => [t._acc, t.title, t.assignee || "", statusKo[t.status] || t.status, prioKo[t.priority] || "", t.deadline || ""]);
    const csv = [head, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\r\n");
    downloadFile(`${clientLabel}_요약.csv`, "﻿" + csv, "text/csv;charset=utf-8");
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5 min-w-0">
          <h3 className="text-[15px] font-semibold text-ink">{clientLabel}</h3>
          {industry && <span className="text-[11px] font-medium text-sub px-2 py-0.5 rounded-full bg-[#f4f4f5]">{industry}</span>}
          <span className="text-xs text-faint">요약</span>
        </div>
        <button onClick={exportCsv}
          className="px-2.5 py-1.5 rounded-lg border border-line2 text-xs font-medium text-sub hover:bg-[#fafafa] transition flex items-center gap-1.5">
          <Icon name="download" className="text-[15px] text-faint" />엑셀 내보내기
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-lg border border-line p-5">
          <p className="text-xs font-semibold text-ink mb-4">상태 분포</p>
          <div className="flex items-center gap-5">
            <Donut segments={byStatus} />
            <div className="flex-1 flex flex-col gap-2">
              {byStatus.map((s) => (
                <div key={s.key} className="flex items-center gap-2">
                  <span className="w-[8px] h-[8px] rounded-full shrink-0" style={{ background: s.color }} />
                  <span className="text-xs text-sub flex-1">{s.label}</span>
                  <span className="text-xs text-ink font-medium tabular-nums">{s.value}</span>
                </div>
              ))}
              <div className="flex items-center gap-2 pt-2 mt-1 border-t border-line">
                <span className="text-xs text-faint flex-1">전체</span>
                <span className="text-xs text-ink font-semibold tabular-nums">{total}건</span>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-line p-5">
          <p className="text-xs font-semibold text-ink mb-4">담당자별 분배</p>
          <div className="flex flex-col gap-3">
            {assignees.length === 0 && <p className="text-xs text-faint py-4 text-center">담당자가 지정된 할일이 없습니다</p>}
            {assignees.map((a) => (
              <div key={a.name}>
                <div className="flex items-center justify-between mb-1">
                  <span className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-[#f4f4f5] flex items-center justify-center text-[9px] font-semibold text-sub">{a.name.slice(0, 1)}</span>
                    <span className="text-xs text-ink">{a.name}</span>
                  </span>
                  <span className="text-[11px] text-faint tabular-nums">{a.done}/{a.total} 완료</span>
                </div>
                <div className="w-full h-1.5 bg-line rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-700" style={{ width: `${(a.total / maxA) * 100}%`, background: "var(--lnac)" }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-line p-5 mt-4">
        <p className="text-xs font-semibold text-ink mb-3">계정과목별 진행 <span className="text-faint font-normal">{accounts.length}</span></p>
        {accounts.length === 0 && <p className="text-xs text-faint py-4 text-center">계정과목이 없습니다</p>}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2.5">
          {accounts.map((ac) => {
            const list = (tasksByAcc[ac.id] || []);
            const d = list.filter((t) => t.status === "done").length;
            const p = list.length ? Math.round((d / list.length) * 100) : 0;
            return (
              <div key={ac.id} className="flex items-center gap-3">
                <span className="text-xs text-ink flex-1 truncate">{ac.label}</span>
                <div className="w-24 h-1.5 bg-line rounded-full overflow-hidden shrink-0">
                  <div className="h-full rounded-full transition-all duration-700" style={{ width: `${p}%`, background: p >= 100 ? "#10b981" : "var(--lnac)" }} />
                </div>
                <span className="text-[11px] text-faint tabular-nums w-9 text-right shrink-0">{p}%</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ---- Bulk Add Modal ----
function BulkModal({ open, parentId, term = "계정과목", onClose, onAdded }) {
  const [text, setText] = useState("");
  if (!open) return null;
  const names = text.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);

  const submit = async () => {
    if (names.length === 0) return;
    const created = await api.bulkAccounts({ phase_id: parentId, names });
    onAdded(created);
    onClose();
    setText("");
  };

  return (
    <div className="fixed inset-0 z-[57] flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative bg-white rounded-xl border border-line shadow-xl w-full max-w-sm overflow-hidden">
        <div className="px-6 pt-6 pb-2">
          <h3 className="text-base font-semibold text-ink">{term} 일괄 추가</h3>
          <p className="mt-0.5 text-xs text-faint">한 줄에 하나씩 입력하세요</p>
        </div>
        <div className="px-6 py-4">
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows="6" autoFocus
            placeholder={"매출채권\n재고자산\n유형자산"}
            className="w-full px-3 py-2.5 rounded-lg bg-[#fafafa] text-[13px] text-ink leading-relaxed resize-none focus:bg-white transition" />
          <p className="mt-1.5 text-[11px] text-faint">{names.length}개 {term}</p>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-line">
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-[13px] font-medium text-sub hover:bg-[#f4f4f5] transition">취소</button>
          <button onClick={submit} disabled={names.length === 0}
            className="px-3.5 py-1.5 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition disabled:opacity-40"
            style={{ background: "var(--lnac)" }}>
            추가
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- New Engagement Modal ----
function NewEngModal({ open, clients, fys, onClose, onCreated }) {
  const [fyId, setFyId] = useState("");
  const [clientId, setClientId] = useState("");
  const [newClientName, setNewClientName] = useState("");
  const [newClientIndustry, setNewClientIndustry] = useState("");
  const [engName, setEngName] = useState("");
  const [engType, setEngType] = useState("audit");
  const [creating, setCreating] = useState(false);

  const activeFy = fys.find((f) => f.is_active);
  useEffect(() => {
    if (activeFy && !fyId) setFyId(String(activeFy.id));
  }, [activeFy, fyId]);

  if (!open) return null;

  const fyClients = clients.filter((c) => String(c.fy_id) === fyId);

  const submit = async () => {
    if (!fyId) return;
    setCreating(true);
    try {
      let cid = clientId;
      if (!cid && newClientName.trim()) {
        const nc = await api.createClient({ fy_id: Number(fyId), name: newClientName.trim(), industry: newClientIndustry.trim() });
        cid = String(nc.id);
      }
      if (!cid) return;
      const eng = await api.createEngagement({ client_id: Number(cid), name: engName.trim() || `${ENG_TYPE[engType].label} FY${new Date().getFullYear()}`, eng_type: engType });
      onCreated(eng, Number(cid));
      onClose();
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative bg-white rounded-xl border border-line shadow-xl w-full max-w-md flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 pt-6 pb-2">
          <h3 className="text-base font-semibold text-ink">새 감사업무</h3>
          <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
            <Icon name="close" className="text-[18px]" />
          </button>
        </div>
        <div className="px-6 py-4 flex flex-col gap-4">
          <label className="block">
            <span className="text-xs text-sub mb-1.5 block">회계연도 *</span>
            <select value={fyId} onChange={(e) => setFyId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink">
              {fys.map((f) => <option key={f.id} value={f.id}>{f.label}{f.is_active ? " (활성)" : ""}</option>)}
            </select>
          </label>
          {fyClients.length > 0 ? (
            <label className="block">
              <span className="text-xs text-sub mb-1.5 block">클라이언트</span>
              <select value={clientId} onChange={(e) => setClientId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink">
                <option value="">— 신규 클라이언트 —</option>
                {fyClients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
          ) : null}
          {!clientId && (
            <>
              <label className="block">
                <span className="text-xs text-sub mb-1.5 block">클라이언트명 *</span>
                <input type="text" value={newClientName} onChange={(e) => setNewClientName(e.target.value)}
                  placeholder="예: 한빛제조" className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
              </label>
              <label className="block">
                <span className="text-xs text-sub mb-1.5 block">업종</span>
                <input type="text" value={newClientIndustry} onChange={(e) => setNewClientIndustry(e.target.value)}
                  placeholder="예: 제조업" className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
              </label>
            </>
          )}
          <label className="block">
            <span className="text-xs text-sub mb-1.5 block">업무유형 *</span>
            <div className="flex gap-2">
              {Object.entries(ENG_TYPE).map(([k, v]) => (
                <button key={k} onClick={() => setEngType(k)}
                  className={`flex-1 py-2 rounded-lg text-xs font-medium transition ${engType === k ? "text-white" : "bg-[#f4f4f5] text-sub"}`}
                  style={engType === k ? { background: v.color } : undefined}>
                  {v.label}
                </button>
              ))}
            </div>
          </label>
          <label className="block">
            <span className="text-xs text-sub mb-1.5 block">업무명</span>
            <input type="text" value={engName} onChange={(e) => setEngName(e.target.value)}
              placeholder={`예: ${ENG_TYPE[engType].label} FY${new Date().getFullYear()}`}
              className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
          </label>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-line">
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-[13px] font-medium text-sub hover:bg-[#f4f4f5] transition">취소</button>
          <button onClick={submit} disabled={creating || (!clientId && !newClientName.trim())}
            className="px-3.5 py-1.5 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition disabled:opacity-40"
            style={{ background: "var(--lnac)" }}>
            {creating ? "생성 중…" : "생성"}
          </button>
        </div>
      </div>
    </div>
  );
}

// Collect all descendant account nodes from a (client) subtree
function collectAccounts(node) {
  const out = [];
  const walk = (n) => {
    if (n.type === "account") out.push({ id: n.refId, label: n.label });
    (n.children || []).forEach(walk);
  };
  (node.children || []).forEach(walk);
  return out;
}

// ---- Main Engagements Page ----
export function Engagements({ modalOpen = false, onModalOpenChange }) {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null); // { id, type, label, refId, parentLabel }
  const [tab, setTab] = useState("tasks");
  const [ctxMenu, setCtxMenu] = useState(null);
  const [renaming, setRenaming] = useState(null);
  const [renameVal, setRenameVal] = useState("");
  const [bulk, setBulk] = useState(null); // { parentId, parentType }
  const [openNodes, setOpenNodes] = useState({});
  const [fys, setFys] = useState([]);
  const [clients, setClients] = useState([]);
  const setNewEngOpen = (v) => onModalOpenChange?.(v);

  const normalize = (nodes, inheritedEngType = null) => nodes.map((n) => {
    const engType = n.eng_type || inheritedEngType;
    return {
      ...n,
      refId: n.ref_id,
      engType,
      taskCount: n.task_count,
      parentLabel: n.parent_label,
      children: n.children ? normalize(n.children, engType) : [],
    };
  });

  const loadTree = async () => {
    const [t, fs] = await Promise.all([api.getTree(), api.getFYs()]);
    setTree(normalize(t));
    setFys(fs);
    const cs = [];
    for (const fy of fs) {
      const fyClients = await api.getClients(fy.id);
      cs.push(...fyClients);
    }
    setClients(cs);
    const defaultOpen = {};
    t.forEach((n) => { if (n.is_active) defaultOpen[n.id] = true; });
    setOpenNodes((prev) => ({ ...defaultOpen, ...prev }));
  };

  useEffect(() => {
    loadTree().catch(() => {}).finally(() => setLoading(false));
  }, []);

  const toggleOpen = (id) => setOpenNodes((o) => ({ ...o, [id]: !o[id] }));

  const onCtx = (e, node, fromBtn = false) => {
    const x = fromBtn ? e.currentTarget.getBoundingClientRect().right : e.clientX;
    const y = fromBtn ? e.currentTarget.getBoundingClientRect().bottom : e.clientY;
    setCtxMenu({ x, y, node });
  };

  const commitRename = async (cancel = false) => {
    if (!cancel && renameVal.trim() && renaming) {
      const node = findNode(tree, renaming);
      if (!node) return;
      if (node.type === "client") await api.updateClient(node.refId, { name: renameVal.trim() });
      else if (node.type === "engagement") await api.updateEngagement(node.refId, { name: renameVal.trim() });
      else if (node.type === "phase") await api.updatePhase(node.refId, { name: renameVal.trim() });
      else if (node.type === "account") await api.updateAccount(node.refId, { name: renameVal.trim() });
      await loadTree();
    }
    setRenaming(null);
    setRenameVal("");
  };

  const findNode = (nodes, id) => {
    for (const n of nodes) {
      if (n.id === id) return n;
      if (n.children) {
        const found = findNode(n.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const doAction = async (act, node) => {
    if (act === "rename") { setRenaming(node.id); setRenameVal(node.label); return; }
    if (act === "delete") {
      if (!window.confirm(`"${node.label}"을(를) 삭제하시겠습니까?`)) return;
      if (node.type === "client") await api.deleteClient(node.refId);
      else if (node.type === "engagement") await api.deleteEngagement(node.refId);
      else if (node.type === "phase") await api.deletePhase(node.refId);
      else if (node.type === "account") await api.deleteAccount(node.refId);
      await loadTree();
      if (selected?.id === node.id) setSelected(null);
      return;
    }
    if (act === "add-client") {
      const name = window.prompt("클라이언트명:");
      if (!name) return;
      await api.createClient({ fy_id: node.refId, name: name.trim() });
      await loadTree();
      return;
    }
    if (act.startsWith("add-eng-")) {
      const type = act.replace("add-eng-", "");
      const name = window.prompt("업무명 (비워두면 자동):", "");
      const body = { client_id: node.refId, eng_type: type };
      if (name?.trim()) body.name = name.trim();
      await api.createEngagement(body);
      await loadTree();
      return;
    }
    if (act === "add-phase") {
      const name = window.prompt("단계명:");
      if (!name) return;
      await api.createPhase({ engagement_id: node.refId, name: name.trim(), kind: "phase" });
      await loadTree();
      return;
    }
    if (act === "add-account") {
      const term = leafTerm(node.engType);
      const name = window.prompt(`${term}명:`);
      if (!name) return;
      await api.createAccount({ phase_id: node.refId, name: name.trim() });
      await loadTree();
      return;
    }
    if (act === "add-bulk") {
      setBulk({ parentId: node.refId, term: leafTerm(node.engType) });
      return;
    }
  };

  if (loading) return <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>;

  return (
    <div className="flex gap-0 h-[calc(100vh-48px)] overflow-hidden">
      {/* Left Tree */}
      <div className="w-60 shrink-0 border-r border-line bg-canvas overflow-y-auto overflow-x-hidden py-4 px-2">
        {tree.length === 0 && (
          <div className="px-4 py-8 text-center">
            <p className="text-xs text-faint mb-3">감사업무가 없습니다</p>
            <button onClick={() => setNewEngOpen(true)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-white hover:opacity-90 transition flex items-center gap-1 mx-auto"
              style={{ background: "var(--lnac)" }}>
              <Icon name="add" className="text-[16px]" />새 감사업무
            </button>
          </div>
        )}
        {tree.map((node) => {
          const isOpen = openNodes[node.id] ?? node.is_active;
          return (
            <TreeNode key={node.id} node={node} depth={0}
              selected={selected?.id} onSelect={(n) => { setSelected(n); setTab(n.type === "client" ? "summary" : "tasks"); }}
              open={isOpen} toggleOpen={toggleOpen}
              onCtx={onCtx} renaming={renaming} renameVal={renameVal}
              setRenameVal={setRenameVal} commitRename={commitRename} />
          );
        })}
      </div>

      {/* Right Content */}
      <div className="flex-1 min-w-0 flex flex-col">
        {!selected ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-3">
            <Icon name="account_balance" className="text-[48px] text-line2" />
            <p className="text-sm text-sub">계정과목을 선택하면 할일·요청자료·인터뷰를 관리할 수 있습니다</p>
          </div>
        ) : selected.type === "client" ? (
          (() => {
            const accs = collectAccounts(selected);
            const curTab = ["summary", "pbc", "interview"].includes(tab) ? tab : "summary";
            return (
              <>
                <div className="flex items-center border-b border-line px-6 bg-white">
                  {[["summary", "요약"], ["pbc", "요청자료"], ["interview", "인터뷰"]].map(([k, l]) => (
                    <button key={k} onClick={() => setTab(k)}
                      className={`px-4 py-3 text-[13px] font-medium border-b-2 transition ${curTab === k ? "border-[color:var(--lnac)] text-[color:var(--lnac)]" : "border-transparent text-sub hover:text-ink"}`}>
                      {l}
                    </button>
                  ))}
                </div>
                <div className="flex-1 bg-white overflow-y-auto">
                  {accs.length === 0 ? (
                    <div className="p-10 text-center text-xs text-faint">계정과목을 추가하면 요약·요청자료·인터뷰가 표시됩니다</div>
                  ) : curTab === "summary" ? (
                    <ClientSummaryTab accounts={accs} clientLabel={selected.label} industry={selected.industry} />
                  ) : curTab === "pbc" ? (
                    <PbcTab key={"c-pbc-" + selected.id} accounts={accs} />
                  ) : (
                    <InterviewTab key={"c-iv-" + selected.id} accounts={accs} />
                  )}
                </div>
              </>
            );
          })()
        ) : (
          (() => {
            const accs = [{ id: selected.refId, label: selected.label }];
            const curTab = ["tasks", "pbc", "interview"].includes(tab) ? tab : "tasks";
            return (
              <>
                <div className="flex items-center border-b border-line px-6 bg-white">
                  {[["tasks", "할일"], ["pbc", "요청자료"], ["interview", "인터뷰"]].map(([k, l]) => (
                    <button key={k} onClick={() => setTab(k)}
                      className={`px-4 py-3 text-[13px] font-medium border-b-2 transition ${curTab === k ? "border-[color:var(--lnac)] text-[color:var(--lnac)]" : "border-transparent text-sub hover:text-ink"}`}>
                      {l}
                    </button>
                  ))}
                </div>
                <div className="flex-1 bg-white overflow-y-auto">
                  {curTab === "tasks" && <TasksTab accountId={selected.refId} parentLabel={selected.label} />}
                  {curTab === "pbc" && <PbcTab key={"a-pbc-" + selected.id} accounts={accs} />}
                  {curTab === "interview" && <InterviewTab key={"a-iv-" + selected.id} accounts={accs} />}
                </div>
              </>
            );
          })()
        )}
      </div>

      <ContextMenu menu={ctxMenu} onClose={() => setCtxMenu(null)} onAction={doAction} />

      {bulk && (
        <BulkModal open={!!bulk} parentId={bulk.parentId} term={bulk.term}
          onClose={() => setBulk(null)}
          onAdded={async () => { await loadTree(); setBulk(null); }} />
      )}

      <NewEngModal open={modalOpen} fys={fys} clients={clients}
        onClose={() => setNewEngOpen(false)}
        onCreated={async () => { await loadTree(); setNewEngOpen(false); }} />
    </div>
  );
}
