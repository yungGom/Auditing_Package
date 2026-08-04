// 상태 (E-0 승격) — 참조 구현의 요약 카드 + 실데이터 연결
import { useEffect, useState } from "react";
import { api } from "./api";
import { Card, chip, F_HEAD, F_LABEL } from "./ui";

export default function StatusPage() {
  const [ov, setOv] = useState<any>(null);

  useEffect(() => {
    api("/api/status/overview").then(setOv).catch(() => {});
  }, []);

  const gates = ov?.gates || [];

  return (
    <div style={{ padding: 24, maxWidth: 760 }}>
      <Card style={{
        padding: 18, display: "flex", flexDirection: "column", gap: 10,
      }}>
        <Row label="코퍼스"
          value={ov?.corpus
            ? JSON.stringify(ov.corpus).slice(0, 80)
            : "조회 중…"} first />
        <Row label="최근 XBRL 수신"
          value={`${ov?.recent_runs?.length ?? "—"}건`} />
        <Row label="반영 이력"
          value={`${ov?.history?.length ?? "—"}건`} />
        <Row label="편집기 버전 등재"
          value={`${ov?.known_versions?.length ?? "—"}종`} />
      </Card>

      <div style={{
        display: "flex", alignItems: "baseline", gap: 8,
        margin: "20px 0 10px",
      }}>
        <h2 style={{ margin: 0, font: `700 15px ${F_HEAD}`,
          color: "#191c1d" }}>품질 점검 현황</h2>
        <span style={{ font: `500 12px ${F_LABEL}`, color: "#737780" }}>
          GATES.json</span>
      </div>
      <Card style={{ padding: 0, overflow: "hidden" }}>
        {gates.map((g: any, i: number) => (
          <div key={g.patch} style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "10px 16px",
            borderTop: i ? "1px solid rgba(195,198,209,0.5)" : undefined,
          }}>
            <span style={{
              font: `700 11px ${F_LABEL}`, color: "#43474f", width: 44,
            }}>{g.patch}</span>
            <span style={{
              font: `500 12px ${F_LABEL}`, color: "#191c1d", flex: 1,
            }}>{g.title}</span>
            <span style={g.status === "통과"
              ? chip("#3a5a2e", "#dcead2") : chip("#7a4f00", "#ffecc7")}>
              {g.status}</span>
            <span style={{
              font: `500 11px ${F_LABEL}`, color: "#737780",
              fontVariantNumeric: "tabular-nums",
            }}>{g.date}</span>
          </div>
        ))}
      </Card>
    </div>
  );
}

function Row({ label, value, first }: {
  label: string; value: string; first?: boolean;
}) {
  return (
    <div style={{
      display: "flex", alignItems: "center",
      justifyContent: "space-between", font: `500 13px ${F_LABEL}`,
      color: "#43474f",
      borderTop: first ? undefined : "1px solid rgba(195,198,209,0.5)",
      paddingTop: first ? 0 : 10,
    }}>
      <span>{label}</span>
      <span style={{ fontVariantNumeric: "tabular-nums" }}>{value}</span>
    </div>
  );
}
