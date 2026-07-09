import { useState, useEffect, useRef, useMemo } from "react";
import { Icon } from "./Tokens.jsx";

const GROUP_ORDER = ["할일", "계정과목", "클라이언트", "내부회계", "템플릿", "이동"];

export function CommandPalette({ open, onClose, onNav, searchIndex }) {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    const index = searchIndex || [];
    const matched = term
      ? index.filter((it) => (it.label + (it.sub || "") + (it.group || "")).toLowerCase().includes(term))
      : index;
    const flat = [];
    GROUP_ORDER.forEach((g) => {
      const items = matched.filter((it) => it.group === g);
      if (items.length) {
        flat.push({ header: g });
        items.forEach((it) => flat.push({ ...it }));
      }
    });
    return flat;
  }, [q, searchIndex]);

  const selectable = results.filter((r) => !r.header);
  const activeItem = selectable[active];

  useEffect(() => { setActive(0); }, [q]);

  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, selectable.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); if (activeItem) { onNav(activeItem.nav); onClose(); } }
    else if (e.key === "Escape") { e.preventDefault(); onClose(); }
  };

  if (!open) return null;
  let selIdx = -1;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center pt-[12vh] px-4">
      <div className="absolute inset-0 bg-black/20 backdrop-blur-[1px]" onClick={onClose} />
      <div className="relative w-full max-w-xl bg-white rounded-xl border border-line shadow-2xl overflow-hidden">
        <div className="flex items-center gap-2.5 px-4 border-b border-line">
          <Icon name="search" className="text-[20px] text-faint" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKey}
            placeholder="클라이언트, 계정과목, 할일 검색…"
            className="flex-1 py-3.5 text-sm text-ink bg-transparent border-0 focus:ring-0 focus:outline-none placeholder:text-faint"
          />
          <span className="text-[10px] text-faint border border-line2 rounded px-1.5 py-0.5">Esc</span>
        </div>
        <div className="max-h-[52vh] overflow-y-auto py-2">
          {selectable.length === 0 && (
            <div className="px-4 py-10 text-center text-xs text-faint">검색 결과가 없습니다</div>
          )}
          {results.map((r, i) => {
            if (r.header) {
              return (
                <div key={"h" + i} className="px-4 pt-3 pb-1 text-[10px] font-semibold text-faint uppercase tracking-wide">
                  {r.header}
                </div>
              );
            }
            selIdx++;
            const isActive = selIdx === active;
            const myIdx = selIdx;
            return (
              <button
                key={i}
                onMouseEnter={() => setActive(myIdx)}
                onClick={() => { onNav(r.nav); onClose(); }}
                className={`w-full flex items-center gap-3 px-4 py-2 text-left transition ${isActive ? "bg-[#f4f4f5]" : ""}`}
              >
                <Icon name={r.icon || "search"} className={`text-[18px] ${isActive ? "text-[color:var(--lnac)]" : "text-faint"}`} />
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] text-ink truncate">{r.label}</span>
                  {r.sub && <span className="block text-[11px] text-faint truncate">{r.sub}</span>}
                </span>
                {isActive && <Icon name="subdirectory_arrow_left" className="text-[16px] text-faint" />}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-4 px-4 py-2 border-t border-line text-[10px] text-faint">
          <span className="flex items-center gap-1">
            <span className="border border-line2 rounded px-1">↑↓</span> 이동
          </span>
          <span className="flex items-center gap-1">
            <span className="border border-line2 rounded px-1">Enter</span> 선택
          </span>
          <span className="flex items-center gap-1">
            <span className="border border-line2 rounded px-1">Esc</span> 닫기
          </span>
        </div>
      </div>
    </div>
  );
}
