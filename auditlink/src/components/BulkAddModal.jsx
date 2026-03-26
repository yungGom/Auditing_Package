import { useState, useEffect, useMemo } from "react";

/**
 * BulkAddModal – 계정과목 또는 할일 일괄 추가 모달
 *
 * Props:
 *  mode: "account" | "task"
 *  onClose: () => void
 *  onSubmit: (parsed[]) => void   // parsed items to create
 */
export default function BulkAddModal({ mode, onClose, onSubmit }) {
  const [text, setText] = useState("");

  const isTask = mode === "task";
  const title = isTask ? "할일 일괄 추가" : "계정과목 일괄 추가";
  const icon = isTask ? "add_task" : "account_balance";
  const placeholder = isTask
    ? "한 줄에 하나씩 할일 제목을 입력하세요.\n탭으로 구분하면 담당자, 마감일도 입력 가능:\n\n확인서 발송\t김감사\t2025-03-30\n대손충당금 검토\t박회계\t2025-04-05\n기말잔액 검증"
    : "한 줄에 하나씩 계정과목명을 입력하세요:\n\n매출채권\n재고자산\n유형자산\n매입채무\n리스";

  // Parse input
  const parsed = useMemo(() => {
    if (!text.trim()) return [];
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    const seen = new Set();
    const result = [];

    for (const line of lines) {
      if (isTask) {
        const parts = line.split("\t");
        const taskTitle = parts[0]?.trim();
        if (!taskTitle) continue;
        const key = taskTitle.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        result.push({
          title: taskTitle,
          assignee: parts[1]?.trim() || "",
          deadline: parts[2]?.trim() || "",
        });
      } else {
        const name = line.trim();
        if (!name) continue;
        const key = name.toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        result.push({ name });
      }
    }
    return result;
  }, [text, isTask]);

  // ESC to close
  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  const handleSubmit = () => {
    if (parsed.length === 0) return;
    onSubmit(parsed);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-lg flex flex-col overflow-hidden max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-outline-variant shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-xl">{icon}</span>
            </div>
            <h3 className="font-headline text-base font-bold text-on-surface">{title}</h3>
          </div>
          <button onClick={onClose} className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 flex-1 overflow-y-auto">
          {/* Input */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">
              {isTask ? "할일 목록 (한 줄에 하나씩)" : "계정과목명 (한 줄에 하나씩)"}
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={placeholder}
              rows={8}
              autoFocus
              className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition resize-none font-mono"
            />
            <p className="text-[10px] text-on-surface-variant font-label mt-1">
              {isTask
                ? "탭(Tab)으로 구분: 제목 → 담당자 → 마감일. 엑셀에서 복사 붙여넣기 가능."
                : "엑셀이나 메모장에서 복사한 텍스트를 그대로 붙여넣기 가능. 빈 줄/중복 자동 제거."}
            </p>
          </div>

          {/* Preview */}
          {parsed.length > 0 && (
            <div>
              <p className="text-xs font-label font-semibold text-on-surface-variant mb-2">
                미리보기 ({parsed.length}건)
              </p>
              <div className="rounded-xl border border-outline-variant overflow-hidden max-h-48 overflow-y-auto">
                <table className="w-full text-xs font-label">
                  <thead>
                    <tr className="bg-surface-container-low">
                      <th className="text-center px-2 py-2 font-semibold text-on-surface-variant w-8">#</th>
                      <th className="text-left px-3 py-2 font-semibold text-on-surface-variant">
                        {isTask ? "제목" : "계정과목명"}
                      </th>
                      {isTask && (
                        <>
                          <th className="text-left px-3 py-2 font-semibold text-on-surface-variant w-20">담당자</th>
                          <th className="text-left px-3 py-2 font-semibold text-on-surface-variant w-24">마감일</th>
                        </>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {parsed.map((item, i) => (
                      <tr key={i} className="border-t border-outline-variant/50">
                        <td className="text-center px-2 py-1.5 text-outline">{i + 1}</td>
                        <td className="px-3 py-1.5 text-on-surface font-semibold">
                          {isTask ? item.title : item.name}
                        </td>
                        {isTask && (
                          <>
                            <td className="px-3 py-1.5 text-on-surface-variant">{item.assignee || "-"}</td>
                            <td className="px-3 py-1.5 text-on-surface-variant">{item.deadline || "-"}</td>
                          </>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-5 border-t border-outline-variant shrink-0">
          <span className="text-[11px] font-label text-on-surface-variant">
            {parsed.length > 0 ? `${parsed.length}건 추가 예정` : "텍스트를 입력하세요"}
          </span>
          <div className="flex items-center gap-2">
            <button onClick={onClose}
              className="px-4 py-2 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition">
              취소
            </button>
            <button onClick={handleSubmit} disabled={parsed.length === 0}
              className={`px-5 py-2 rounded-xl text-xs font-label font-semibold text-white transition flex items-center gap-1.5 ${parsed.length > 0 ? "bg-primary hover:opacity-90" : "bg-outline cursor-not-allowed"}`}>
              <span className="material-symbols-outlined text-sm">add</span>
              {parsed.length}건 추가
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
