import { ReactNode, useEffect } from "react";

/**
 * 가벼운 모달 셸 — backdrop + 카드. ESC 로 닫힘.
 *
 * 디자인 토큰을 따로 두지 않고 Tailwind 유틸로 직접 표현.
 * 큰 폼이 들어갈 수 있어 max-h-[90vh] + overflow-auto.
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  width = 480,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: number;
}) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="flex max-h-[90vh] flex-col overflow-hidden rounded-lg bg-white shadow-xl"
        style={{ width }}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="flex h-7 w-7 items-center justify-center rounded text-slate-500 hover:bg-slate-100"
          >
            ×
          </button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-auto">
          {children}
        </div>
      </div>
    </div>
  );
}

/* ─── 폼 헬퍼 (모달 안에서 공통으로 쓰는 라벨/입력) ─── */

export function ModalField({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-medium text-slate-600">
        {label} {required && <span className="text-rose-500">*</span>}
      </span>
      {children}
      {hint && (
        <span className="text-[10px] text-slate-400">{hint}</span>
      )}
    </label>
  );
}

export function ModalSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3 border-b border-slate-100 px-4 py-3 last:border-b-0">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </div>
      <div className="flex flex-col gap-3">{children}</div>
    </section>
  );
}

export function ModalFooter({
  onCancel,
  onConfirm,
  confirmLabel = "저장",
  confirmDisabled,
}: {
  onCancel: () => void;
  onConfirm: () => void;
  confirmLabel?: string;
  confirmDisabled?: boolean;
}) {
  return (
    <div className="flex shrink-0 items-center justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3">
      <button
        type="button"
        onClick={onCancel}
        className="rounded-md px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-200"
      >
        취소
      </button>
      <button
        type="button"
        onClick={onConfirm}
        disabled={confirmDisabled}
        className={
          "rounded-md px-3 py-1.5 text-xs font-medium text-white transition " +
          (confirmDisabled
            ? "cursor-not-allowed bg-slate-300"
            : "bg-icfr-headerBg hover:bg-icfr-keyCtrl")
        }
      >
        {confirmLabel}
      </button>
    </div>
  );
}

/* ─── 기본 input 스타일 (Tailwind 유틸 묶음) ─── */

export const inputCls =
  "rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-800 outline-none focus:border-icfr-keyCtrl focus:ring-1 focus:ring-icfr-keyCtrl/40";
