// 참조 구현의 공용 시각 요소 — 문구·토큰 그대로 (재디자인 금지)
import React from "react";

export const F_HEAD = "var(--al-font-headline)";
export const F_LABEL = "var(--al-font-label)";
export const MONO = "ui-monospace,Consolas,monospace";

export function Icon({ name, size = 17, color, fill, style }: {
  name: string; size?: number; color?: string; fill?: boolean;
  style?: React.CSSProperties;
}) {
  return (
    <span className="material-symbols-outlined" style={{
      fontSize: size, color,
      fontVariationSettings: fill ? "'FILL' 1" : undefined, ...style,
    }}>{name}</span>
  );
}

export function chip(fg: string, bg: string): React.CSSProperties {
  return {
    display: "inline-flex", alignItems: "center", gap: 4,
    font: `600 11px ${F_LABEL}`, color: fg, background: bg,
    borderRadius: 4, padding: "3px 8px", whiteSpace: "nowrap",
  };
}

export function Card({ children, style }: {
  children: React.ReactNode; style?: React.CSSProperties;
}) {
  return (
    <div style={{
      background: "#fff", border: "1px solid #c3c6d1", borderRadius: 8,
      padding: 16, ...style,
    }}>{children}</div>
  );
}

export function PrimaryBtn({ children, onClick, disabled }: {
  children: React.ReactNode; onClick?: () => void; disabled?: boolean;
}) {
  return (
    <button className="hoverable" onClick={onClick} disabled={disabled} style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      font: `600 13px ${F_LABEL}`, color: "#fff",
      background: disabled ? "#c3c6d1"
        : "linear-gradient(90deg,#001e40,#003366)",
      border: "none", borderRadius: 8, padding: "9px 18px",
      cursor: disabled ? "default" : "pointer",
    }}>{children}</button>
  );
}

export function GhostBtn({ children, onClick }: {
  children: React.ReactNode; onClick?: () => void;
}) {
  return (
    <button className="hoverable" onClick={onClick} style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      font: `600 13px ${F_LABEL}`, color: "#43474f", background: "#fff",
      border: "1px solid #c3c6d1", borderRadius: 8, padding: "9px 16px",
      cursor: "pointer",
    }}>{children}</button>
  );
}

export function ErrorBanner({ msg }: { msg: string }) {
  if (!msg) return null;
  return (
    <div style={{
      font: `500 12px ${F_LABEL}`, color: "#930010", background: "#ffdad6",
      borderRadius: 8, padding: "10px 12px", margin: "10px 0",
    }}>{msg}</div>
  );
}
