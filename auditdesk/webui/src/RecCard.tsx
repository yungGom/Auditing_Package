// 추천 카드 — Design v2 RecCard 컴포넌트 스펙 그대로 (상태 4종)
// variant: recommend(추천 1순위) | confirmed(확정됨) | extension(확장 필요)
//          | standard(표준 사용 권장)
import React, { useState } from "react";
import { F_LABEL, Icon, MONO } from "./ui";

export type RecBadge = {
  label: string; kind: "corpus" | "sim" | "peer" | "ext";
};
export type RecAlt = { id: string; label: string; badge: string; rank?: number };

const VARIANTS: Record<string, {
  label: string; icon: string; fg: string; bg: string; border: string;
  cardBg?: string;
}> = {
  recommend: { label: "추천 1순위", icon: "auto_awesome", fg: "#001e40",
    bg: "#d5e3ff", border: "#c3c6d1" },
  confirmed: { label: "확정됨", icon: "check", fg: "#3a5a2e",
    bg: "#dcead2", border: "#c3c6d1", cardBg: "#fbfdfa" },
  extension: { label: "확장 필요", icon: "report", fg: "#930010",
    bg: "#ffdad6", border: "#c3c6d1" },
  standard: { label: "표준 사용 권장", icon: "warning", fg: "#7a4f00",
    bg: "#ffecc7", border: "#e0a100", cardBg: "#fffdf6" },
};

const BADGE_KINDS: Record<string, [string, string]> = {
  corpus: ["#001e40", "#d5e3ff"],
  sim: ["#43474f", "#edeeef"],
  peer: ["#4e6874", "#cbe7f5"],
  ext: ["#930010", "#ffdad6"],
};

export default function RecCard({
  variant, elementId, labelKo, badges, alts, note, confirmedBy, onConfirm, onSelect, selectionLabel,
}: {
  variant: string; elementId: string; labelKo: string;
  badges?: RecBadge[]; alts?: RecAlt[]; note?: string;
  confirmedBy?: string; onConfirm?: () => void;
  onSelect?: (elementId: string) => void;
  selectionLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const v = VARIANTS[variant] || VARIANTS.recommend;
  const confirmed = variant === "confirmed";
  return (
    <div style={{
      background: v.cardBg || "#fff", border: `1px solid ${v.border}`,
      borderRadius: 8, padding: "14px 16px",
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: MONO, fontSize: 12, color: "#001e40",
            fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}>{elementId}</div>
          <div style={{
            font: `600 14px ${F_LABEL}`, color: "#191c1d", marginTop: 3,
          }}>{labelKo}</div>
        </div>
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          font: `600 11px ${F_LABEL}`, color: v.fg, background: v.bg,
          borderRadius: 4, padding: "3px 8px", flex: "none",
        }}>
          <Icon name={v.icon} size={13} />{selectionLabel || v.label}
        </span>
      </div>

      <div style={{
        display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap",
        marginTop: 9,
      }}>
        {(badges || []).map((b, i) => {
          const [fg, bg] = BADGE_KINDS[b.kind] || BADGE_KINDS.sim;
          return (
            <span key={i} style={{
              font: `600 11px ${F_LABEL}`, color: fg, background: bg,
              borderRadius: 4, padding: "3px 8px",
              fontVariantNumeric: "tabular-nums",
            }}>{b.label}</span>
          );
        })}
      </div>

      {note && (
        <div style={{
          font: `500 11px ${F_LABEL}`, color: v.fg, background: v.bg,
          borderRadius: 8, padding: "8px 10px", marginTop: 10,
        }}>{note}</div>
      )}

      {(alts || []).length > 0 && (
        <>
          <div onClick={() => setOpen(!open)} style={{
            display: "inline-flex", alignItems: "center", gap: 4,
            font: `600 12px ${F_LABEL}`, color: "#43474f",
            cursor: "pointer", marginTop: 10,
          }}>
            <Icon name={open ? "expand_more" : "chevron_right"} size={16} />
            대안 {alts!.length}건 보기
          </div>
          {open && (
            <div style={{
              display: "flex", flexDirection: "column", marginTop: 6,
              borderTop: "1px solid rgba(195,198,209,0.5)",
            }}>
              {alts!.map((a, i) => (
                <div key={a.id}
                  role={onSelect && !confirmed ? "button" : undefined}
                  tabIndex={onSelect && !confirmed ? 0 : undefined}
                  aria-label={onSelect && !confirmed ? `${a.label} 선택` : undefined}
                  onClick={onSelect && !confirmed ? () => onSelect(a.id) : undefined}
                  onKeyDown={onSelect && !confirmed ? (e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault(); onSelect(a.id);
                    }
                  } : undefined}
                  style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "7px 2px",
                  borderBottom: "1px solid rgba(195,198,209,0.35)",
                }}>
                  <span style={{
                    font: `700 10px ${F_LABEL}`, color: "#737780",
                    width: 14, fontVariantNumeric: "tabular-nums",
                  }}>{a.rank ?? i + 2}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontFamily: MONO, fontSize: 11, color: "#43474f",
                      overflow: "hidden", textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}>{a.id}</div>
                    <div style={{
                      font: `500 11px ${F_LABEL}`, color: "#737780",
                    }}>{a.label}</div>
                  </div>
                  <span style={{
                    font: `600 10px ${F_LABEL}`, color: "#43474f",
                    background: "#edeeef", borderRadius: 4,
                    padding: "2px 7px",
                    fontVariantNumeric: "tabular-nums", flex: "none",
                  }}>{a.badge}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <div style={{
        display: "flex", alignItems: "center", gap: 10, marginTop: 12,
      }}>
        <div style={{ flex: 1 }} />
        {confirmed && (
          <span style={{
            font: `500 11px ${F_LABEL}`, color: "#737780",
            display: "inline-flex", alignItems: "center", gap: 4,
          }}>
            <Icon name="lock" size={14} color="#3a5a2e" />
            확정: {confirmedBy}
          </span>
        )}
        {!confirmed && onConfirm && (
          <button className="hoverable" onClick={onConfirm} style={{
            font: `600 12px ${F_LABEL}`, color: "#fff",
            background: "linear-gradient(90deg,#001e40,#003366)",
            border: "none", borderRadius: 8, padding: "7px 16px",
            cursor: "pointer", whiteSpace: "nowrap",
          }}>확정</button>
        )}
      </div>
    </div>
  );
}
