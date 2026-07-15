import { useState, useEffect, useRef } from "react";
import { Icon } from "./Tokens.jsx";

const KEY = "ln_quick_memos_v1";
const DRAFT_KEY = "ln_quick_memo_draft_v1";

function load() {
  try { const r = localStorage.getItem(KEY); if (r) return JSON.parse(r); } catch (e) {}
  return [];
}
function fmt(iso) {
  const d = new Date(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getMonth() + 1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function QuickMemo() {
  const [open, setOpen] = useState(false);
  const [memos, setMemos] = useState(load);
  const [draft, setDraft] = useState(() => { try { return localStorage.getItem(DRAFT_KEY) || ""; } catch (e) { return ""; } });
  const [savedFlash, setSavedFlash] = useState(false);
  const flashTimer = useRef(null);

  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(memos)); } catch (e) {} }, [memos]);
  useEffect(() => {
    try { localStorage.setItem(DRAFT_KEY, draft); } catch (e) {}
    if (draft) {
      setSavedFlash(true);
      clearTimeout(flashTimer.current);
      flashTimer.current = setTimeout(() => setSavedFlash(false), 1200);
    }
  }, [draft]);

  const commit = () => {
    const text = draft.trim();
    if (text) setMemos((ms) => [{ id: Date.now(), text, createdAt: new Date().toISOString() }, ...ms]);
    setDraft("");
  };
  const remove = (id) => setMemos((ms) => ms.filter((m) => m.id !== id));

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        title="빠른 메모"
        className="fixed bottom-6 right-6 z-40 w-11 h-11 rounded-full bg-white border border-line2 shadow-md flex items-center justify-center text-sub hover:text-ink hover:shadow-lg transition"
      >
        <Icon name={open ? "close" : "edit_note"} className="text-[20px]" />
      </button>

      {open && (
        <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
      )}

      <div
        className={`fixed top-0 right-0 bottom-0 z-30 w-[340px] bg-white border-l border-line flex flex-col transition-transform duration-300 ${
          open ? "translate-x-0 shadow-xl" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <h3 className="text-sm font-semibold text-ink">빠른 메모</h3>
          <button
            onClick={commit}
            className="px-2.5 py-1 rounded-lg text-xs font-medium text-sub hover:bg-[#f4f4f5] transition flex items-center gap-1"
          >
            <Icon name="add" className="text-[16px] text-faint" />
            저장
          </button>
        </div>

        <div className="px-5">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) commit(); }}
            placeholder="메모를 입력하세요… (⌘Enter로 저장)"
            className="w-full h-28 px-3 py-2.5 rounded-lg bg-[#fafafa] text-[13px] text-ink leading-relaxed resize-none focus:bg-white transition"
          />
          <div className="flex items-center justify-between mt-1.5 mb-3">
            <span className="text-[10px] text-faint tabular-nums">{fmt(new Date().toISOString())}</span>
            <span className={`text-[10px] text-faint transition-opacity duration-300 ${savedFlash ? "opacity-100" : "opacity-0"}`}>
              자동 저장됨
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-5">
          <p className="text-[11px] font-medium text-faint mb-2">최근 메모</p>
          {memos.length === 0 && (
            <p className="text-xs text-faint py-6 text-center">저장된 메모가 없습니다</p>
          )}
          <div className="flex flex-col gap-2">
            {memos.map((m) => (
              <div key={m.id} className="relative rounded-lg border border-line p-3.5 hover:border-line2 transition group">
                <p className="text-[13px] text-ink leading-snug line-clamp-3">{m.text}</p>
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-[10px] text-faint tabular-nums">{fmt(m.createdAt)}</span>
                  <span className="ml-auto opacity-0 group-hover:opacity-100 transition">
                    <button
                      onClick={() => remove(m.id)}
                      className="w-5 h-5 rounded flex items-center justify-center text-faint hover:text-[#ef4444] hover:bg-[#f4f4f5] transition"
                    >
                      <Icon name="delete" className="text-[13px]" />
                    </button>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
