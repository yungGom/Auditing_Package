import { useState, useEffect, useRef, useCallback } from "react";

/**
 * useState that persists to sessionStorage.
 * Survives React Router navigation but clears on tab/window close.
 */
export function usePersistedState(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = sessionStorage.getItem(key);
      return stored !== null ? JSON.parse(stored) : initialValue;
    } catch {
      return initialValue;
    }
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch { /* quota exceeded – ignore */ }
  }, [key, value]);

  return [value, setValue];
}

/**
 * Save and restore scroll position for a ref element.
 * Returns a ref to attach to the scrollable container.
 */
export function usePersistedScroll(key) {
  const ref = useRef(null);

  // Restore on mount
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    try {
      const pos = sessionStorage.getItem(key);
      if (pos) el.scrollTop = Number(pos);
    } catch { /* ignore */ }
  }, [key]);

  // Save on scroll (throttled)
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let timer = null;
    const handler = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        try { sessionStorage.setItem(key, String(el.scrollTop)); } catch {}
      }, 150);
    };
    el.addEventListener("scroll", handler, { passive: true });
    return () => { el.removeEventListener("scroll", handler); if (timer) clearTimeout(timer); };
  }, [key]);

  return ref;
}
