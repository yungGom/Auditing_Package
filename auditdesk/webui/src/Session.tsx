// 세션 상세 — 개요(파이프라인)·시트 뷰·변경검토(승인 게이트)·이력 + repack 모달
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api, Job, pollJob } from "./api";
import {
  Card, chip, ErrorBanner, F_HEAD, F_LABEL, GhostBtn, Icon, MONO,
  PrimaryBtn,
} from "./ui";

type Change = {
  id: number; sheet: string; cell: string; before: string; after: string;
  reason: "edit" | "clean-cr" | "note-dedup";
};

const GROUPS: [string, string, [string, string]][] = [
  ["edit", "수정", ["#001e40", "#d5e3ff"]],
  ["clean-cr", "&cr; 정리", ["#7a4f00", "#ffecc7"]],
  ["note-dedup", "번호 정리", ["#4e6874", "#cbe7f5"]],
];

export default function Session({ sessionId, initialTab }: {
  sessionId: string; initialTab?: string;
}) {
  const [s, setS] = useState<any>(null);
  const [tab, setTab] = useState(initialTab || "overview");
  const [err, setErr] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [modal, setModal] = useState<any>(null);

  const reload = useCallback(() => {
    api(`/api/workbench/sessions/${sessionId}`).then(setS)
      .catch((e) => setErr(e.message));
  }, [sessionId]);
  useEffect(reload, [reload]);

  const runJob = async (path: string, body?: any) => {
    setErr("");
    try {
      const r = await api(path, {
        method: "POST", body: JSON.stringify(body || {}),
      });
      const done = await pollJob(r.job_id, setJob);
      setJob(null);
      if (done.state === "error")
        setErr(done.error_detail?.detail || "작업 실패");
      reload();
      return done;
    } catch (e: any) {
      setJob(null);
      setErr(e.message);
      reload();
      return null;
    }
  };

  if (!s) return <div style={{ padding: 24 }}><ErrorBanner msg={err} /></div>;

  const meta = s.meta || {};
  const stateChip: Record<string, React.CSSProperties> = {
    "생성됨": chip("#43474f", "#edeeef"),
    "추출됨": chip("#001e40", "#d5e3ff"),
    "수정중": chip("#7a4f00", "#ffecc7"),
    "repack완료": chip("#3a5a2e", "#dcead2"),
  };
  const diffCounts = s.diff?.counts;
  const tabs = [
    { key: "overview", label: "개요" },
    { key: "sheets", label: "시트 뷰" },
    { key: "footing", label: "Footing", chip: "UI-2" },
    { key: "change", label: "변경검토",
      count: diffCounts ? String(diffCounts.total) : undefined },
    { key: "history", label: "이력" },
  ];

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
    }}>
      <div style={{
        flex: "none", background: "#fff", borderBottom: "1px solid #c3c6d1",
        padding: "14px 24px 0",
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 10, marginBottom: 12,
        }}>
          <Icon name="description" size={20} color="#48626e" />
          <span style={{ font: `700 15px ${F_HEAD}`, color: "#191c1d" }}>
            {meta.file}</span>
          <span style={{ font: `500 12px ${F_LABEL}`, color: "#737780" }}>
            {meta.company}</span>
          <span style={stateChip[s.state] || stateChip["생성됨"]}>
            {s.state}</span>
          <div style={{ flex: 1 }} />
          <span style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
            SHA1 <code style={{
              fontFamily: MONO, fontSize: 11, background: "#edeeef",
              borderRadius: 4, padding: "1px 6px",
            }}>{meta.sha1?.slice(0, 4)}…{meta.sha1?.slice(-4)}</code>
          </span>
        </div>
        <div style={{ display: "flex", gap: 2 }}>
          {tabs.map((t) => (
            <div key={t.key} data-testid={`tab-${t.key}`}
              onClick={() => setTab(t.key)} style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "9px 14px", cursor: "pointer",
                font: `600 13px ${F_LABEL}`,
                borderBottom: `2px solid ${
                  tab === t.key ? "#001e40" : "transparent"}`,
                color: tab === t.key ? "#001e40" : "#737780",
              }}>
              <span>{t.label}</span>
              {t.count && <span style={{
                font: `700 10px ${F_LABEL}`, color: "#001e40",
                background: "#d5e3ff", borderRadius: 9999,
                padding: "1px 7px", fontVariantNumeric: "tabular-nums",
              }}>{t.count}</span>}
              {t.chip && <span style={{
                font: `600 9px ${F_LABEL}`, color: "#737780",
                background: "#e1e3e4", borderRadius: 4, padding: "1px 6px",
              }}>{t.chip}</span>}
            </div>
          ))}
        </div>
      </div>

      {job && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "10px 24px", background: "#d5e3ff",
          font: `600 12px ${F_LABEL}`, color: "#001e40",
        }}>
          <Icon name="progress_activity" size={16} />
          {job.kind} — {job.progress?.message || job.state}
        </div>
      )}
      <div style={{ padding: err ? "0 24px" : 0 }}>
        <ErrorBanner msg={err} />
      </div>

      {tab === "overview" && (
        <Overview s={s} onExtract={() =>
          runJob(`/api/workbench/sessions/${sessionId}/extract`)}
          goChange={() => setTab("change")} />
      )}
      {tab === "sheets" && <Sheets sessionId={sessionId} s={s} />}
      {tab === "footing" && (
        <div style={{
          padding: 24, font: `500 13px ${F_LABEL}`, color: "#737780",
        }}>Footing 탭은 UI-2에서 구현됩니다 — CLI: <code
          style={{ fontFamily: MONO }}>python -m dsd_tool foot</code></div>
      )}
      {tab === "change" && (
        <ChangeReview sessionId={sessionId} s={s} setErr={setErr}
          reload={reload}
          onRepack={async (approvedIds) => {
            const done = await runJob(
              `/api/workbench/sessions/${sessionId}/repack`,
              { approved_change_ids: approvedIds });
            if (done?.state === "done") setModal(done.result);
          }} />
      )}
      {tab === "history" && <History sessionId={sessionId} />}

      {modal && <RepackModal result={modal} onClose={() => setModal(null)} />}
    </div>
  );
}

// ======== TAB: 개요 ========
function Overview({ s, onExtract, goChange }: {
  s: any; onExtract: () => void; goChange: () => void;
}) {
  const meta = s.meta || {};
  const pipeline = s.pipeline || [];
  const curIdx = pipeline.findIndex((p: any) => !p.done);
  return (
    <div style={{
      padding: 24, maxWidth: 1080, display: "flex",
      flexDirection: "column", gap: 16,
    }}>
      <Card style={{ padding: 20 }}>
        <div style={{
          font: `700 13px ${F_HEAD}`, color: "#191c1d", marginBottom: 16,
        }}>작업 파이프라인</div>
        <div style={{ display: "flex", alignItems: "center" }}>
          {pipeline.map((p: any, i: number) => {
            const done = p.done, active = i === curIdx;
            return (
              <div key={p.key} style={{
                display: "flex", alignItems: "center", flex: 1, minWidth: 0,
              }}>
                <div style={{
                  display: "flex", flexDirection: "column",
                  alignItems: "center", gap: 6, flex: "none",
                }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: 9999,
                    display: "flex", alignItems: "center",
                    justifyContent: "center",
                    color: done || active ? "#fff" : "#737780",
                    background: done ? "#001e40" : active
                      ? "linear-gradient(90deg,#001e40,#003366)" : "#e1e3e4",
                  }}>
                    <Icon size={16} name={done ? "check" : active
                      ? "radio_button_checked" : "radio_button_unchecked"} />
                  </div>
                  <span style={{
                    font: `${active ? 700 : 500} 11px ${F_LABEL}`,
                    color: active ? "#001e40"
                      : done ? "#43474f" : "#737780",
                    whiteSpace: "nowrap",
                  }}>{p.label}</span>
                </div>
                {i < pipeline.length - 1 && (
                  <div style={{
                    flex: 1, height: 2, margin: "0 8px 22px",
                    background: done ? "#001e40" : "#e1e3e4",
                  }} />
                )}
              </div>
            );
          })}
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
          {!s.xlsx_path ? (
            <PrimaryBtn onClick={onExtract}>
              <Icon name="play_arrow" size={17} />DSD → Excel 추출
            </PrimaryBtn>
          ) : (
            <>
              <GhostBtn onClick={() => api("/api/fs/open", {
                method: "POST",
                body: JSON.stringify({ path: s.xlsx_path }),
              })}>
                <Icon name="open_in_new" size={17} />엑셀: {s.xlsx_path
                  .split("\\").pop()}
              </GhostBtn>
              <PrimaryBtn onClick={goChange}>
                <Icon name="rule" size={17} />편집 완료 — 변경 검토
              </PrimaryBtn>
            </>
          )}
        </div>
      </Card>

      <div style={{
        display: "grid", gridTemplateColumns: "1fr 320px", gap: 16,
      }}>
        <Card style={{ padding: 20 }}>
          <div style={{
            font: `700 13px ${F_HEAD}`, color: "#191c1d", marginBottom: 14,
          }}>파일 메타</div>
          <div style={{
            display: "grid", gridTemplateColumns: "110px 1fr", rowGap: 10,
            font: `500 12px ${F_LABEL}`,
          }}>
            <span style={{ color: "#737780" }}>원본 경로</span>
            <span style={{
              color: "#191c1d", fontFamily: MONO, fontSize: 11,
              wordBreak: "break-all",
            }}>{s.dsd_path}</span>
            <span style={{ color: "#737780" }}>SHA1</span>
            <span style={{
              color: "#191c1d", fontFamily: MONO, fontSize: 11,
              wordBreak: "break-all",
            }}>{meta.sha1}</span>
            <span style={{ color: "#737780" }}>editver</span>
            <span style={{
              color: "#191c1d", display: "flex", alignItems: "center",
              gap: 6,
            }}>
              {meta.editver || "(없음)"}
              {meta.editver_known ? (
                <span style={chip("#3a5a2e", "#dcead2")}>
                  <Icon name="check" size={12} />검증됨</span>
              ) : (
                <span style={chip("#930010", "#ffdad6")}>
                  <Icon name="warning" size={12} />미검증</span>
              )}
            </span>
            <span style={{ color: "#737780" }}>셀 수</span>
            <span style={{
              color: "#191c1d", fontVariantNumeric: "tabular-nums",
            }}>{meta.cells != null
              ? meta.cells.toLocaleString() : "추출 후 표시"}</span>
            <span style={{ color: "#737780" }}>주석 수</span>
            <span style={{
              color: "#191c1d", fontVariantNumeric: "tabular-nums",
            }}>{meta.notes ?? "—"}</span>
            <span style={{ color: "#737780" }}>&cr;-only 셀</span>
            <span style={{
              color: "#191c1d", fontVariantNumeric: "tabular-nums",
            }}>{meta.cr_only ?? "—"}</span>
          </div>
        </Card>
        <Card style={{ padding: 20 }}>
          <div style={{
            font: `700 13px ${F_HEAD}`, color: "#191c1d", marginBottom: 14,
          }}>repack 옵션</div>
          <div style={{
            display: "flex", flexDirection: "column", gap: 12,
            font: `500 12px ${F_LABEL}`,
          }}>
            <div>
              <div style={{ font: `600 12px ${F_LABEL}`, color: "#191c1d" }}>
                &cr; 정리 — 기본 켜짐</div>
              <div style={{ color: "#737780" }}>
                &cr;만 남은 셀 {meta.cr_only ?? "?"}개를 빈 셀로 정리.
                변경검토 화면에서 옵션과 함께 dry-run 됩니다.</div>
            </div>
            <div>
              <div style={{ font: `600 12px ${F_LABEL}`, color: "#191c1d" }}>
                주석번호 정리 — extract 시 결정</div>
              <div style={{ color: "#737780" }}>
                중복 번호 {meta.deduped_notes ?? "?"}건은 추출 시 정리되어
                repack에 반영됩니다.</div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ======== TAB: 시트 뷰 ========
function Sheets({ sessionId, s }: { sessionId: string; s: any }) {
  const [names, setNames] = useState<string[]>([]);
  const [sel, setSel] = useState<string>("");
  const [grid, setGrid] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api(`/api/workbench/sessions/${sessionId}/sheets`)
      .then((r) => {
        setNames(r.sheets);
        setSel((cur) => cur || r.sheets.find((n: string) => n === "BS")
          || r.sheets[0]);
      })
      .catch((e) => setErr(e.message));
  }, [sessionId]);
  useEffect(() => {
    if (!sel) return;
    api(`/api/workbench/sessions/${sessionId}/sheets/${
      encodeURIComponent(sel)}`).then(setGrid).catch((e) => setErr(e.message));
  }, [sel, sessionId]);

  const fmt = (v: any) => {
    if (typeof v === "number") {
      const s = Math.abs(v).toLocaleString();
      return v < 0 ? `(${s})` : s;
    }
    return v == null ? "" : String(v);
  };

  return (
    <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
      <div style={{
        width: 180, flex: "none", background: "#fff",
        borderRight: "1px solid #c3c6d1", overflow: "auto",
        padding: "12px 8px",
      }}>
        <div style={{
          font: `700 10px ${F_LABEL}`, letterSpacing: "0.06em",
          color: "#737780", padding: "0 8px 8px",
        }}>시트</div>
        {names.map((n) => (
          <div key={n} className="navitem" onClick={() => setSel(n)} style={{
            padding: "7px 12px", borderRadius: 8,
            font: `${sel === n ? 600 : 500} 12px ${F_LABEL}`,
            color: sel === n ? "#001e40" : "#43474f", cursor: "pointer",
            marginBottom: 1, background: sel === n ? "#d5e3ff" : undefined,
          }}>{n}</div>
        ))}
      </div>
      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
        <ErrorBanner msg={err} />
        <div style={{
          display: "flex", alignItems: "baseline", gap: 10, marginBottom: 4,
        }}>
          <h2 style={{ margin: 0, font: `700 15px ${F_HEAD}`,
            color: "#191c1d" }}>{sel}</h2>
          <div style={{ flex: 1 }} />
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 5,
            font: `500 11px ${F_LABEL}`, color: "#43474f",
            background: "#edeeef", borderRadius: 4, padding: "3px 8px",
          }}>
            <Icon name="visibility" size={13} />읽기 전용 — 편집은 엑셀에서
          </span>
        </div>
        {grid && (
          <div style={{ overflowX: "auto", marginTop: 10 }}>
            <table style={{
              borderCollapse: "collapse", background: "#fff",
              border: "1px solid #c3c6d1",
            }}>
              <tbody>
                {grid.rows.map((r: any) => (
                  <tr key={r.row}>
                    {r.cells.map((v: any, ci: number) => (
                      <td key={ci} style={{
                        font: typeof v === "number"
                          ? `500 12px ${F_LABEL}` : `500 12px ${F_LABEL}`,
                        color: typeof v === "number" && v < 0
                          ? "#ba1a1a" : "#191c1d",
                        textAlign: typeof v === "number" ? "right" : "left",
                        fontVariantNumeric: "tabular-nums",
                        padding: "5px 10px",
                        borderBottom: "1px solid rgba(195,198,209,0.4)",
                        whiteSpace: "nowrap", maxWidth: 380,
                        overflow: "hidden", textOverflow: "ellipsis",
                      }}>{fmt(v)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {grid.truncated && (
              <div style={{
                font: `500 11px ${F_LABEL}`, color: "#737780",
                padding: "8px 2px",
              }}>… 400행까지 표시 — 전체는 엑셀에서 확인</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ======== TAB: 변경검토 (repack 승인 게이트) ========
function ChangeReview({ sessionId, s, onRepack, setErr, reload }: {
  sessionId: string; s: any; setErr: (m: string) => void;
  reload: () => void;
  onRepack: (approvedIds: number[] | "all") => Promise<void>;
}) {
  const [open, setOpen] = useState<Record<string, boolean>>({ edit: true });
  const [excluded, setExcluded] = useState<Record<number, boolean>>({});
  const [running, setRunning] = useState(false);
  const diff = s.diff;

  const runDiff = async () => {
    setErr("");
    try {
      await api(`/api/workbench/sessions/${sessionId}/diff`, {
        method: "POST",
        body: JSON.stringify({ options: { clean_cr: true } }),
      });
      reload();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  const changes: Change[] = diff?.changes || [];
  const selCount = changes.filter((c) => !excluded[c.id]).length;

  if (!diff) {
    return (
      <div style={{ padding: 24, maxWidth: 720 }}>
        <Card style={{ padding: 20 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            marginBottom: 8,
          }}>
            <Icon name="rule" size={18} color="#43474f" />
            <span style={{ font: `600 13px ${F_LABEL}`, color: "#191c1d" }}>
              repack 전 승인 게이트</span>
          </div>
          <div style={{
            font: `500 12px ${F_LABEL}`, color: "#737780", marginBottom: 14,
          }}>
            변경검토(dry-run)를 실행해 편집 내용을 확인·승인해야 repack이
            가능합니다. 서버가 이 순서를 강제합니다 (미실행 시 409).
          </div>
          <PrimaryBtn onClick={runDiff}>
            <Icon name="play_arrow" size={17} />변경검토 실행 (dry-run)
          </PrimaryBtn>
        </Card>
      </div>
    );
  }

  const counts = diff.counts;
  return (
    <div style={{
      display: "flex", flexDirection: "column", flex: 1, minHeight: 0,
    }}>
      <div style={{
        flex: "none", display: "flex", alignItems: "center", gap: 10,
        padding: "12px 24px", background: "#fff",
        borderBottom: "1px solid #c3c6d1",
      }}>
        <Icon name="rule" size={18} color="#43474f" />
        <span style={{ font: `600 13px ${F_LABEL}`, color: "#191c1d" }}>
          repack 전 승인 게이트</span>
        <span style={{ font: `500 12px ${F_LABEL}`, color: "#737780" }}>
          수정 {counts.edit} · &cr; 정리 {counts.clean_cr} · 번호 정리{" "}
          {counts.note_dedup} — dry-run 결과 ({diff.ts})
        </span>
        <div style={{ flex: 1 }} />
        <GhostBtn onClick={runDiff}>
          <Icon name="refresh" size={15} />다시 diff
        </GhostBtn>
        <span style={{
          font: `500 12px ${F_LABEL}`, color: "#43474f",
          fontVariantNumeric: "tabular-nums",
        }}>{selCount}/{changes.length}건 선택</span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "16px 24px 90px" }}>
        {GROUPS.map(([reason, label, [fg, bg]]) => {
          const rows = changes.filter((c) => c.reason === reason);
          if (!rows.length) return null;
          const isOpen = !!open[reason];
          const allChecked = rows.every((r) => !excluded[r.id]);
          return (
            <div key={reason} style={{
              background: "#fff", border: "1px solid #c3c6d1",
              borderRadius: 8, marginBottom: 12, overflow: "hidden",
            }}>
              <div className="hoverable" style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "12px 16px", cursor: "pointer",
                background: "#f3f4f5",
              }} onClick={() => setOpen({ ...open, [reason]: !isOpen })}>
                <Icon size={18} color="#737780"
                  name={isOpen ? "expand_more" : "chevron_right"} />
                <input type="checkbox" checked={allChecked}
                  onClick={(e) => e.stopPropagation()}
                  onChange={() => {
                    const next = { ...excluded };
                    rows.forEach((r) => { next[r.id] = allChecked; });
                    setExcluded(next);
                  }}
                  style={{
                    width: 15, height: 15, accentColor: "#001e40",
                    cursor: "pointer",
                  }} />
                <span style={chip(fg, bg)}>{label}</span>
                <span style={{
                  font: `600 13px ${F_LABEL}`, color: "#191c1d",
                }}>{reason === "edit" ? "사용자 수정 셀"
                  : reason === "clean-cr"
                    ? "&cr;만 남은 셀 정리" : "주석 번호 중복 정리"}</span>
                <span style={{
                  font: `500 12px ${F_LABEL}`, color: "#737780",
                  fontVariantNumeric: "tabular-nums",
                }}>{rows.length}건</span>
              </div>
              {isOpen && (
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {["", "시트", "셀", "변경 전", "", "변경 후"].map(
                        (h, i) => (
                          <th key={i} style={{
                            textAlign: i >= 3 ? "right" : "left",
                            font: `700 11px ${F_LABEL}`, color: "#737780",
                            borderBottom: "1px solid #c3c6d1",
                            padding: i === 0 ? "6px 8px 6px 16px" : "6px 8px",
                            width: i === 0 ? 36 : i === 1 ? 90
                              : i === 2 ? 70 : i === 4 ? 34 : undefined,
                          }}>{h}</th>
                        ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.slice(0, 100).map((r) => (
                      <tr key={r.id}>
                        <td style={{
                          padding: "6px 8px 6px 16px",
                          borderBottom: "1px solid rgba(195,198,209,0.4)",
                        }}>
                          <input type="checkbox" checked={!excluded[r.id]}
                            onChange={() => setExcluded({
                              ...excluded, [r.id]: !excluded[r.id],
                            })}
                            style={{
                              width: 14, height: 14,
                              accentColor: "#001e40", cursor: "pointer",
                            }} />
                        </td>
                        <td style={{
                          font: `500 12px ${F_LABEL}`, color: "#43474f",
                          padding: "6px 8px",
                          borderBottom: "1px solid rgba(195,198,209,0.4)",
                        }}>{r.sheet}</td>
                        <td style={{
                          fontFamily: MONO, fontSize: 11, color: "#43474f",
                          padding: "6px 8px",
                          borderBottom: "1px solid rgba(195,198,209,0.4)",
                        }}>{r.cell}</td>
                        <td style={{
                          font: `500 12px ${F_LABEL}`, color: "#930010",
                          textAlign: "right", padding: "6px 8px",
                          borderBottom: "1px solid rgba(195,198,209,0.4)",
                          fontVariantNumeric: "tabular-nums", maxWidth: 260,
                          overflow: "hidden", textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}>{JSON.stringify(r.before ?? "")}</td>
                        <td style={{
                          textAlign: "center",
                          borderBottom: "1px solid rgba(195,198,209,0.4)",
                        }}><Icon name="arrow_forward" size={14}
                          color="#737780" /></td>
                        <td style={{
                          font: `600 12px ${F_LABEL}`, color: "#191c1d",
                          textAlign: "right", padding: "6px 16px 6px 8px",
                          borderBottom: "1px solid rgba(195,198,209,0.4)",
                          fontVariantNumeric: "tabular-nums", maxWidth: 260,
                          overflow: "hidden", textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}>{JSON.stringify(r.after ?? "")}</td>
                      </tr>
                    ))}
                    {rows.length > 100 && (
                      <tr><td colSpan={6} style={{
                        font: `500 11px ${F_LABEL}`, color: "#737780",
                        padding: "8px 16px",
                      }}>외 {rows.length - 100}건 — 전체 목록은 이력·엑셀에서
                        확인</td></tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          );
        })}
        {!changes.length && (
          <div style={{
            font: `500 13px ${F_LABEL}`, color: "#737780", padding: 8,
          }}>변경 없음 — repack 시 원본 바이트 그대로 복사됩니다 (G2).</div>
        )}
      </div>

      <div style={{
        flex: "none", position: "sticky", bottom: 0, display: "flex",
        alignItems: "center", gap: 12, padding: "12px 24px",
        background: "rgba(255,255,255,0.92)", backdropFilter: "blur(8px)",
        borderTop: "1px solid #c3c6d1",
      }}>
        <span style={{ font: `500 12px ${F_LABEL}`, color: "#737780" }}>
          출력: <code style={{
            fontFamily: MONO, fontSize: 11, background: "#edeeef",
            borderRadius: 4, padding: "1px 6px",
          }}>{s.meta?.file?.replace(/\.dsd$/i, "") + "_수정.dsd"}</code>
        </span>
        <div style={{ flex: 1 }} />
        <PrimaryBtn disabled={running} onClick={async () => {
          setRunning(true);
          const ids = changes.filter((c) => !excluded[c.id]).map((c) => c.id);
          await onRepack(ids.length === changes.length ? "all" : ids);
          setRunning(false);
        }}>
          <Icon name="play_arrow" size={17} />
          repack 실행 ({selCount}건)
        </PrimaryBtn>
      </div>
    </div>
  );
}

// ======== TAB: 이력 ========
function History({ sessionId }: { sessionId: string }) {
  const [runs, setRuns] = useState<any[]>([]);
  const [open, setOpen] = useState<Record<number, boolean>>({});

  useEffect(() => {
    api(`/api/workbench/sessions/${sessionId}/history?changes=true`)
      .then((r) => setRuns(r.runs)).catch(() => {});
  }, [sessionId]);

  return (
    <div style={{ padding: 24, maxWidth: 900 }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 8, marginBottom: 14,
      }}>
        <span style={{ font: `500 12px ${F_LABEL}`, color: "#737780" }}>
          history.sqlite — 감사조서 증빙용 실행 기록</span>
      </div>
      {!runs.length && (
        <div style={{ font: `500 13px ${F_LABEL}`, color: "#737780" }}>
          이 DSD에 대한 repack 이력이 없습니다.</div>
      )}
      {runs.map((h) => (
        <div key={h.id} style={{
          background: "#fff", border: "1px solid #c3c6d1", borderRadius: 8,
          marginBottom: 10, overflow: "hidden",
        }}>
          <div className="hoverable" style={{
            display: "flex", alignItems: "center", gap: 12,
            padding: "14px 16px", cursor: "pointer",
          }} onClick={() => setOpen({ ...open, [h.id]: !open[h.id] })}>
            <Icon size={18} color="#737780"
              name={open[h.id] ? "expand_more" : "chevron_right"} />
            <span style={chip("#001e40", "#d5e3ff")}>repack</span>
            <span style={{
              font: `600 12px ${F_LABEL}`, color: "#191c1d",
              fontVariantNumeric: "tabular-nums",
            }}>{h.ts}</span>
            <span style={{ font: `500 12px ${F_LABEL}`, color: "#43474f" }}>
              수정 {h.edits} · &cr; 정리 {h.cleans} · 번호 정리 {h.dedups}
            </span>
            <div style={{ flex: 1 }} />
            <span style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
              SHA1 <span style={{ fontFamily: MONO }}>
                {h.dsd_sha1?.slice(0, 12)}…</span></span>
          </div>
          {open[h.id] && (
            <div style={{
              borderTop: "1px solid rgba(195,198,209,0.5)",
              padding: "12px 16px 14px 46px",
            }}>
              <div style={{
                font: `500 11px ${F_LABEL}`, color: "#737780",
                marginBottom: 8,
              }}>옵션: {h.clean_cr ? "기본(&cr; 정리)" : "keep-cr"} ·
                출력 {h.out_path}</div>
              {(h.changes || []).slice(0, 30).map((c: any, i: number) => (
                <div key={i} style={{
                  display: "flex", gap: 12, font: `500 11px ${F_LABEL}`,
                  color: "#43474f", padding: "3px 0",
                  fontVariantNumeric: "tabular-nums",
                }}>
                  <span style={{ width: 70, color: "#737780" }}>
                    {c.sheet}</span>
                  <span style={{ width: 70, fontFamily: MONO }}>
                    R{c.row}C{c.col}</span>
                  <span style={{
                    overflow: "hidden", textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}>{JSON.stringify(c.old)} → {JSON.stringify(c.new)}
                    {" "}({c.reason})</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ======== MODAL: repack 완료 ========
function RepackModal({ result, onClose }: {
  result: any; onClose: () => void;
}) {
  return (
    <div onClick={onClose} style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 50,
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: 480, background: "#fff", borderRadius: 16,
        boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)", padding: 24,
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 10, marginBottom: 6,
        }}>
          <Icon name="check_circle" size={24} color="#3a5a2e" />
          <h2 style={{ margin: 0, font: `700 17px ${F_HEAD}`,
            color: "#191c1d" }}>repack 완료</h2>
        </div>
        <p style={{
          margin: "0 0 14px", font: `500 12px ${F_LABEL}`, color: "#737780",
        }}>{result.n_changes}건 반영 · 이력에 기록됨</p>
        <div style={{
          background: "#f3f4f5", borderRadius: 8, padding: "10px 12px",
          marginBottom: 14,
        }}>
          <div style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
            출력 파일</div>
          <div data-testid="repack-out" style={{
            fontFamily: MONO, fontSize: 11, color: "#191c1d", marginTop: 3,
            wordBreak: "break-all",
          }}>{result.output_path}</div>
          <div style={{
            font: `500 11px ${F_LABEL}`, color: "#737780", marginTop: 4,
          }}>SHA1 <span data-testid="repack-sha"
            style={{ fontFamily: MONO }}>{result.sha1}</span></div>
        </div>
        <div style={{
          font: `700 11px ${F_LABEL}`, letterSpacing: "0.05em",
          color: "#737780", marginBottom: 8,
        }}>DART 편집기 확인 체크리스트</div>
        <div style={{
          display: "flex", flexDirection: "column", gap: 8,
          marginBottom: 18,
        }}>
          {(result.checklist || []).map((c: string) => (
            <label key={c} style={{
              display: "flex", alignItems: "center", gap: 9,
              font: `500 12px ${F_LABEL}`, color: "#43474f",
              cursor: "pointer",
            }}>
              <input type="checkbox" style={{
                width: 14, height: 14, accentColor: "#001e40",
              }} />{c}</label>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <GhostBtn onClick={onClose}>닫기</GhostBtn>
        </div>
      </div>
    </div>
  );
}
