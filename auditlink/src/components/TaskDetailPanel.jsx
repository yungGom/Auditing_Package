import { useState, useEffect, useRef } from "react";
import api from "../api";

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

const STATUS_OPTIONS = ["todo", "in_progress", "review", "done"];
const PRIORITY_OPTIONS = ["high", "mid", "low"];

export default function TaskDetailPanel({ task, path, onClose, onSave, onDelete, useApi }) {
  const [form, setForm] = useState({
    title: "",
    status: "todo",
    priority: "mid",
    assignee: "",
    due_date: "",
    memo: "",
    file_path: "",
  });
  const [history, setHistory] = useState([]);
  const [editingTitle, setEditingTitle] = useState(false);
  const [dirty, setDirty] = useState(false);
  const titleRef = useRef(null);
  const memoRef = useRef(null);

  // Initialize form from task
  useEffect(() => {
    if (!task) return;
    setForm({
      title: task.title || "",
      status: task.status || "todo",
      priority: task.priority || "mid",
      assignee: task.assignee || "",
      due_date: task.due_date || task.deadline || "",
      memo: task.memo || "",
      file_path: task.file_path || "",
    });
    setDirty(false);
    setEditingTitle(false);

    // Load history from API
    if (useApi && task.id) {
      api.getTaskHistory(task.id).then(setHistory).catch(() => setHistory([]));
    } else {
      setHistory([]);
    }
  }, [task, useApi]);

  // Auto-resize memo textarea
  useEffect(() => {
    if (memoRef.current) {
      memoRef.current.style.height = "auto";
      memoRef.current.style.height = memoRef.current.scrollHeight + "px";
    }
  }, [form.memo]);

  // ESC to close
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  if (!task) return null;

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setDirty(true);
  };

  const handleSave = () => {
    onSave(task.id, {
      title: form.title,
      status: form.status,
      priority: form.priority,
      assignee: form.assignee,
      due_date: form.due_date || null,
      memo: form.memo,
      file_path: form.file_path,
    });
    setDirty(false);
  };

  const handleDelete = () => {
    if (confirm(`"${form.title}" 할일을 삭제하시겠습니까?`)) {
      onDelete(task.id);
    }
  };

  const taskPath = path || task.path || "";

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40" onClick={onClose} />

      {/* Slide-in panel */}
      <div className="fixed top-0 right-0 bottom-0 w-full max-w-[600px] bg-surface-container-lowest border-l border-outline-variant shadow-2xl z-50 flex flex-col animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-lg">edit_note</span>
            </div>
            <span className="text-sm font-label font-semibold text-on-surface-variant">할일 상세</span>
          </div>
          <button onClick={onClose} className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Title - inline edit */}
          <div>
            {editingTitle ? (
              <input
                ref={titleRef}
                type="text"
                value={form.title}
                onChange={(e) => updateField("title", e.target.value)}
                onBlur={() => setEditingTitle(false)}
                onKeyDown={(e) => { if (e.key === "Enter") setEditingTitle(false); }}
                autoFocus
                className="w-full text-xl font-headline font-bold text-on-surface border-b-2 border-primary bg-transparent focus:outline-none pb-1"
              />
            ) : (
              <h2
                onClick={() => { setEditingTitle(true); setTimeout(() => titleRef.current?.focus(), 50); }}
                className="text-xl font-headline font-bold text-on-surface cursor-text hover:text-primary transition pb-1 border-b-2 border-transparent hover:border-outline-variant"
              >
                {form.title || "제목 없음"}
              </h2>
            )}
          </div>

          {/* Properties */}
          <div className="bg-surface-container rounded-xl p-4 space-y-3.5">
            {/* Status */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-label font-semibold text-on-surface-variant w-16 shrink-0">상태</span>
              <div className="flex gap-1.5 flex-wrap">
                {STATUS_OPTIONS.map((s) => {
                  const st = STATUS_MAP[s];
                  return (
                    <button key={s}
                      onClick={() => updateField("status", s)}
                      className={`px-2.5 py-1 rounded-xl text-[11px] font-label font-bold transition ${form.status === s ? `${st.bg} ${st.text} ring-1 ring-current` : "bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-low"}`}>
                      {st.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Priority */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-label font-semibold text-on-surface-variant w-16 shrink-0">우선순위</span>
              <div className="flex gap-1.5">
                {PRIORITY_OPTIONS.map((p) => {
                  const pr = PRIORITY_MAP[p];
                  return (
                    <button key={p}
                      onClick={() => updateField("priority", p)}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-label font-bold transition ${form.priority === p ? "bg-surface-container-lowest ring-1 ring-on-surface-variant text-on-surface" : "text-on-surface-variant hover:bg-surface-container-low"}`}>
                      <span className={`w-2 h-2 rounded-full ${pr.dot}`} />
                      {pr.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Assignee */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-label font-semibold text-on-surface-variant w-16 shrink-0">담당자</span>
              <input type="text" value={form.assignee} onChange={(e) => updateField("assignee", e.target.value)}
                placeholder="담당자 이름"
                className="flex-1 px-3 py-1.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
            </div>

            {/* Due date */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-label font-semibold text-on-surface-variant w-16 shrink-0">마감일</span>
              <input type="date" value={form.due_date} onChange={(e) => updateField("due_date", e.target.value)}
                className="flex-1 px-3 py-1.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
            </div>

            {/* Path (read-only) */}
            {taskPath && (
              <div className="flex items-center gap-3">
                <span className="text-xs font-label font-semibold text-on-surface-variant w-16 shrink-0">소속</span>
                <div className="flex-1 px-3 py-1.5 rounded-xl bg-surface-container-low text-xs font-label text-on-surface-variant">
                  {taskPath}
                </div>
              </div>
            )}
          </div>

          {/* Memo */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-2 block">메모</label>
            <textarea ref={memoRef} value={form.memo} onChange={(e) => updateField("memo", e.target.value)}
              placeholder="메모를 입력하세요..."
              rows={3}
              className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition resize-none" />
          </div>

          {/* File path */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-2 block">
              <span className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px]">attach_file</span>
                참조 파일 경로
              </span>
            </label>
            <input type="text" value={form.file_path} onChange={(e) => updateField("file_path", e.target.value)}
              placeholder="예: C:\감사조서\한빛제조\매출채권.xlsx"
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
          </div>

          {/* History */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-2 block">
              <span className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px]">history</span>
                상태 변경 이력
              </span>
            </label>
            {history.length === 0 ? (
              <p className="text-xs text-outline font-body px-3 py-2">변경 이력이 없습니다</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {history.map((h) => (
                  <div key={h.id} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-surface-container-low">
                    <span className="text-[10px] text-outline font-label shrink-0 w-32">{formatDateTime(h.changed_at)}</span>
                    <span className={`inline-flex px-1.5 py-0.5 rounded-lg text-[10px] font-label font-bold ${(STATUS_MAP[h.old_status] || STATUS_MAP.todo).bg} ${(STATUS_MAP[h.old_status] || STATUS_MAP.todo).text}`}>
                      {(STATUS_MAP[h.old_status] || STATUS_MAP.todo).label}
                    </span>
                    <span className="material-symbols-outlined text-[12px] text-outline">arrow_forward</span>
                    <span className={`inline-flex px-1.5 py-0.5 rounded-lg text-[10px] font-label font-bold ${(STATUS_MAP[h.new_status] || STATUS_MAP.todo).bg} ${(STATUS_MAP[h.new_status] || STATUS_MAP.todo).text}`}>
                      {(STATUS_MAP[h.new_status] || STATUS_MAP.todo).label}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-outline-variant">
          <button onClick={handleDelete}
            className="px-3 py-2 rounded-xl text-xs font-label font-semibold text-error hover:bg-error/5 transition flex items-center gap-1.5">
            <span className="material-symbols-outlined text-sm">delete</span>
            삭제
          </button>
          <div className="flex items-center gap-2">
            <button onClick={onClose}
              className="px-4 py-2 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition">
              닫기
            </button>
            <button onClick={handleSave} disabled={!dirty}
              className={`px-5 py-2 rounded-xl text-xs font-label font-semibold text-white transition flex items-center gap-1.5 ${dirty ? "bg-primary hover:opacity-90" : "bg-outline cursor-not-allowed"}`}>
              <span className="material-symbols-outlined text-sm">save</span>
              저장
            </button>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
        .animate-slide-in { animation: slideIn 0.2s ease-out; }
      `}</style>
    </>
  );
}

function formatDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
