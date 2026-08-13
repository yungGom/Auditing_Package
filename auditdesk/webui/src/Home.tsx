// 홈 (시즌 여정) — 참조 구현 그대로: 여정 카드 + 상태 요약 + 드롭존 + 최근 작업 파일
import React, { useEffect, useState } from "react";
import { api } from "./api";
import { Card, chip, ErrorBanner, F_HEAD, F_LABEL, Icon } from "./ui";

type SessionRow = {
  session_id: string; dsd_path: string; created: string;
  state: string; meta: any; xlsx_path: string | null;
};

function StepChip({ label, state }: { label: string; state: string }) {
  const style: React.CSSProperties = {
    display: "inline-flex", alignItems: "center", gap: 4,
    font: `600 11px ${F_LABEL}`, whiteSpace: "nowrap", borderRadius: 8,
    padding: "5px 10px",
    ...(state === "done"
      ? { color: "#3a5a2e", background: "#dcead2" }
      : state === "cur"
        ? { color: "#fff",
            background: "linear-gradient(90deg,#001e40,#003366)" }
        : { color: "#737780", background: "#edeeef" }),
  };
  return (
    <span style={style}>
      {state === "done" && <Icon name="check" size={13} />}
      {label}
    </span>
  );
}

function Journey({ tag, tagFg, tagBg, title, cta, steps, onGo }: {
  tag: string; tagFg: string; tagBg: string; title: string; cta: string;
  steps: [string, string][]; onGo?: () => void;
}) {
  return (
    <Card>
      <div style={{
        display: "flex", alignItems: "center", gap: 8, marginBottom: 12,
      }}>
        <span style={chip(tagFg, tagBg)}>{tag}</span>
        <span style={{ font: `700 13px ${F_HEAD}`, color: "#191c1d" }}>
          {title}</span>
        <div style={{ flex: 1 }} />
        <button className="hoverable" onClick={onGo} style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          font: `600 12px ${F_LABEL}`, color: "#001e40",
          background: "#d5e3ff", border: "none", borderRadius: 8,
          padding: "6px 12px", cursor: "pointer", whiteSpace: "nowrap",
          flex: "none",
        }}>{cta}<Icon name="arrow_forward" size={15} /></button>
      </div>
      <div style={{
        display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap",
      }}>
        {steps.map(([label, st], i) => (
          <React.Fragment key={label}>
            <StepChip label={label} state={st} />
            {i < steps.length - 1 &&
              <Icon name="chevron_right" size={14} color="#c3c6d1" />}
          </React.Fragment>
        ))}
      </div>
    </Card>
  );
}

export default function Home({ openSession }: {
  openSession: (id: string, label?: string, tab?: string) => void;
}) {
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [overview, setOverview] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [pathInput, setPathInput] = useState("");
  // UI-8: 목록 정리 — 접기/펼침·숨김 보기·30일 자동 숨김(기본 꺼짐)
  const [expanded, setExpanded] = useState(false);
  const [showHidden, setShowHidden] = useState(false);
  const [autoHide, setAutoHide] = useState(
    localStorage.getItem("ui8_auto_hide_30d") === "1");
  const setFlag = async (sid: string, body: any) => {
    await api(`/api/workbench/sessions/${sid}/flags`, {
      method: "POST", body: JSON.stringify(body),
    });
    reload();
  };

  const reload = () => {
    api("/api/workbench/sessions").then(setSessions).catch(() => {});
    api("/api/status/overview").then(setOverview).catch(() => {});
  };
  useEffect(reload, []);

  const createSession = async (dsdPath: string) => {
    setErr("");
    setBusy(true);
    try {
      const r = await api("/api/workbench/sessions", {
        method: "POST", body: JSON.stringify({ dsd_path: dsdPath }),
      });
      openSession(r.session_id, r.meta.display_name || r.meta.file);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const pick = async () => {
    setErr("");
    const r = await api("/api/fs/pick", { method: "POST" });
    if (r.path) await createSession(r.path);
  };

  const stChip: Record<string, React.CSSProperties> = {
    "추출됨": chip("#001e40", "#d5e3ff"),
    "수정중": chip("#7a4f00", "#ffecc7"),
    "반영완료": chip("#3a5a2e", "#dcead2"),
    "생성됨": chip("#43474f", "#edeeef"),
  };
  const stLabel = (v: string) => v;   // 구버전 값은 서버가 정규화

  const corpus = overview?.corpus;
  const gates = overview?.gates || [];
  const passed = gates.filter((g: any) => g.status === "통과").length;

  return (
    <div style={{ padding: 24, maxWidth: 1120 }}>
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 300px", gap: 16,
        alignItems: "start",
      }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Journey tag="결산" tagFg="#001e40" tagBg="#d5e3ff"
            title="DSD 결산 작업" cta="작업 파일 열기" onGo={pick}
            steps={[["엑셀 변환", "cur"], ["엑셀 편집", "todo"],
              ["검증", "todo"], ["수정 확인", "todo"],
              ["DSD 반영", "todo"], ["DART 확인", "todo"]]} />
          <Journey tag="시즌 착수" tagFg="#3a5a2e" tagBg="#dcead2"
            title="2026 택소노미 착수 준비" cta="전사 가이드 작성"
            steps={[["택소노미 버전 점검", "todo"], ["전사 가이드 작성", "todo"],
              ["편집기 전사", "todo"]]} />
          <Journey tag="수시" tagFg="#4e6874" tagBg="#cbe7f5"
            title="벤치마크 · 조회 도구" cta="공시 검색"
            steps={[["벤치마크 검색", "todo"], ["XBRL 표 조회", "todo"],
              ["코퍼스 갱신", "todo"]]} />
        </div>

        <Card>
          <div style={{
            font: `700 13px ${F_HEAD}`, color: "#191c1d", marginBottom: 12,
          }}>상태 요약</div>
          <div style={{
            display: "flex", flexDirection: "column", gap: 10,
          }}>
            {[
              { icon: "sync", color: "#3a5a2e", title: "코퍼스",
                detail: corpus?.available
                  ? `ok ${(corpus.by_status?.ok ?? 0).toLocaleString()}사 / `
                    + `처리 ${(corpus.processed ?? 0).toLocaleString()}사`
                  : corpus ? "코퍼스 없음" : "조회 중…" },
              { icon: "verified", color: "#001e40", title: "품질 점검 현황",
                detail: gates.length
                  ? `${passed}/${gates.length} 통과` : "조회 중…" },
              { icon: "check_circle", color: "#3a5a2e", title: "편집기 버전",
                detail: overview?.known_versions?.length
                  ? `등재 ${overview.known_versions.length}종` : "—" },
            ].map((ss) => (
              <div key={ss.title} style={{
                display: "flex", alignItems: "flex-start", gap: 9,
              }}>
                <Icon name={ss.icon} size={17} color={ss.color}
                  style={{ marginTop: 1 }} />
                <div style={{ flex: 1 }}>
                  <div style={{
                    font: `600 12px ${F_LABEL}`, color: "#191c1d",
                  }}>{ss.title}</div>
                  <div style={{
                    font: `500 11px ${F_LABEL}`, color: "#737780",
                    marginTop: 1, fontVariantNumeric: "tabular-nums",
                  }}>{ss.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <ErrorBanner msg={err} />

      <div className="hoverable" onClick={pick} style={{
        border: "2px dashed #c3c6d1", borderRadius: 12, background: "#fff",
        padding: 24, display: "flex", alignItems: "center",
        justifyContent: "center", gap: 12, cursor: "pointer", marginTop: 16,
      }}>
        <Icon name="upload_file" size={26} color="#737780" />
        <div>
          <div style={{ font: `600 14px ${F_LABEL}`, color: "#191c1d" }}>
            {busy ? "작업 파일 생성 중…" : "DSD 파일을 선택 (클릭 → OS 대화상자)"}
          </div>
          <div style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
            .dsd / .xml — 파일은 이 PC를 벗어나지 않습니다</div>
        </div>
      </div>
      <div style={{
        display: "flex", gap: 8, marginTop: 8, alignItems: "center",
      }}>
        {/* N-2: 폴더(스캔)·파일 경로 이중 수용 */}
        <input value={pathInput} data-testid="path-input"
          onChange={(e) => setPathInput(e.target.value)}
          placeholder="또는 폴더 또는 파일 경로 직접 입력 (폴더는 자동 탐색)"
          style={{
            flex: 1, font: `500 12px ${F_LABEL}`, padding: "8px 10px",
            border: "1px solid #c3c6d1", borderRadius: 8,
          }} />
        <button className="hoverable" data-testid="path-open"
          onClick={() => pathInput && createSession(pathInput)} style={{
            font: `600 12px ${F_LABEL}`, color: "#001e40",
            background: "#d5e3ff", border: "none", borderRadius: 8,
            padding: "8px 14px", cursor: "pointer",
          }}>열기</button>
      </div>

      {(() => {
        // UI-8: 핀 우선 정렬·숨김 분리·30일 자동 숨김(핀 제외)
        const now = Date.now();
        const auto = (s: SessionRow & any) => autoHide && !s.pinned &&
          now - new Date(s.created).getTime() > 30 * 864e5;
        const rows = sessions as any[];
        const hiddenRows = rows.filter((s) => s.hidden || auto(s));
        const shown = rows.filter((s) => !s.hidden && !auto(s))
          .sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
        const list = showHidden ? hiddenRows
          : expanded ? shown : shown.slice(0, 5);
        const groups: [string, any[]][] = [];
        if (expanded && !showHidden) {
          const m = new Map<string, any[]>();
          list.forEach((s) => {
            const k = s.meta?.company || "기타";
            if (!m.has(k)) m.set(k, []);
            m.get(k)!.push(s);
          });
          m.forEach((v, k) => groups.push([k, v]));
        } else {
          groups.push(["", list]);
        }
        const Row = ({ s }: { s: any }) => (
          <div key={s.session_id} className="hoverable"
            onClick={() => openSession(s.session_id,
              s.meta?.display_name || s.meta?.file)}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              background: "#fff", border: "1px solid #c3c6d1",
              borderRadius: 8, padding: "8px 12px", cursor: "pointer",
              marginBottom: 6, opacity: showHidden ? 0.75 : 1,
            }}>
            <Icon name={s.pinned ? "keep" : "description"} size={17}
              color={s.pinned ? "#7a4f00" : "#48626e"} />
            <span style={{
              font: `600 12px ${F_LABEL}`, color: "#191c1d", minWidth: 0,
              flex: 1, overflow: "hidden", textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>{s.meta?.display_name || s.meta?.file}</span>
            <span style={{
              ...(stChip[stLabel(s.state)] || stChip["생성됨"]),
              flex: "none",
            }}>{stLabel(s.state)}</span>
            <span style={{
              font: `500 11px ${F_LABEL}`, color: "#737780",
              flex: "none", fontVariantNumeric: "tabular-nums",
            }}>{s.created?.slice(5, 16).replace("T", " ")}</span>
            {showHidden ? (
              <button className="hoverable" title="목록에 다시 표시"
                onClick={(e) => {
                  e.stopPropagation();
                  setFlag(s.session_id, { hidden: false });
                }} style={{
                  font: `600 11px ${F_LABEL}`, color: "#001e40",
                  background: "#d5e3ff", border: "none", borderRadius: 6,
                  padding: "4px 8px", cursor: "pointer",
                }}>숨김 해제</button>
            ) : (
              <>
                <span title={s.pinned ? "핀 해제" : "핀 고정 (맨 위)"}
                  onClick={(e) => {
                    e.stopPropagation();
                    setFlag(s.session_id, { pinned: !s.pinned });
                  }} style={{ cursor: "pointer", display: "inline-flex" }}>
                  <Icon name={s.pinned ? "keep_off" : "keep"} size={16}
                    color="#737780" /></span>
                <span title="목록에서 숨김 — 원본 파일·작업 기록은 보존"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFlag(s.session_id, { hidden: true });
                  }} style={{ cursor: "pointer", display: "inline-flex" }}>
                  <Icon name="visibility_off" size={16}
                    color="#737780" /></span>
              </>
            )}
            <Icon name="chevron_right" size={15} color="#737780" />
          </div>
        );
        return (
          <>
            <div style={{
              display: "flex", alignItems: "baseline", gap: 10,
              margin: "24px 0 12px", flexWrap: "wrap",
            }}>
              <h2 style={{ margin: 0, font: `700 15px ${F_HEAD}`,
                color: "#191c1d" }}>최근 작업 파일</h2>
              <span style={{ font: `500 12px ${F_LABEL}`,
                color: "#737780" }}>
                {shown.length}건{hiddenRows.length
                  ? ` · 숨김 ${hiddenRows.length}건 (원본 파일은 보존)`
                  : ""}</span>
              <div style={{ flex: 1 }} />
              <label style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                font: `500 11px ${F_LABEL}`, color: "#737780",
              }}>
                <input type="checkbox" checked={autoHide}
                  onChange={(e) => {
                    setAutoHide(e.target.checked);
                    localStorage.setItem("ui8_auto_hide_30d",
                      e.target.checked ? "1" : "0");
                  }} style={{ accentColor: "#001e40" }} />
                30일 지난 파일 자동 숨김 (핀 제외)
              </label>
              {hiddenRows.length > 0 && (
                <button className="hoverable" data-testid="toggle-hidden"
                  onClick={() => setShowHidden(!showHidden)} style={{
                    font: `600 11px ${F_LABEL}`, color: "#43474f",
                    background: "#edeeef", border: "none",
                    borderRadius: 6, padding: "4px 10px",
                    cursor: "pointer",
                  }}>{showHidden ? "목록으로" : "숨김 보기"}</button>
              )}
            </div>
            {groups.map(([g, arr]) => (
              <div key={g || "flat"}>
                {g && <div style={{
                  font: `700 11px ${F_LABEL}`, color: "#737780",
                  letterSpacing: "0.05em", margin: "10px 0 6px",
                }}>{g} · {arr.length}건</div>}
                {arr.map((s) => <Row key={s.session_id} s={s} />)}
              </div>
            ))}
            {!showHidden && shown.length > 5 && (
              <button className="hoverable" data-testid="toggle-expand"
                onClick={() => setExpanded(!expanded)} style={{
                  font: `600 12px ${F_LABEL}`, color: "#001e40",
                  background: "#d5e3ff", border: "none", borderRadius: 8,
                  padding: "7px 14px", cursor: "pointer", marginTop: 4,
                }}>{expanded ? "접기 — 최근 5건만"
                  : `전체 보기 (${shown.length}건 · 회사별)`}</button>
            )}
          </>
        );
      })()}
    </div>
  );
}
