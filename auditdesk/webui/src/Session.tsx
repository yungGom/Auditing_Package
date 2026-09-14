// 세션 상세 — 개요(파이프라인)·시트 뷰·수정 확인(반영 전 확인)·이력 + 반영 완료 모달
// (UI-7: 화면 용어는 GLOSSARY 기준 — API 경로·reason 코드는 계약 불변)
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, Job, openFile, pollJob } from "./api";
import {
  Card, chip, ErrorBanner, F_HEAD, F_LABEL, GhostBtn, Icon, MONO,
  PrimaryBtn,
} from "./ui";

type Change = {
  id: number; sheet: string; cell: string; before: string; after: string;
  reason: "edit" | "clean-cr" | "note-dedup";
};

const GROUPS: [string, string, [string, string]][] = [
  ["edit", "값 수정", ["#001e40", "#d5e3ff"]],
  ["clean-cr", "표기 자동 보정", ["#7a4f00", "#ffecc7"]],
  ["note-dedup", "표기 자동 보정", ["#4e6874", "#cbe7f5"]],
];

// 작업 종류 표시명 (내부 작업 코드 → 화면 용어)
const JOB_LABEL: Record<string, string> = {
  extract: "추출", diff: "수정 확인", repack: "DSD에 반영",
  foot: "합계검증", recon: "전기대사", "xbrl-recon": "제출파일 대사",
};

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

  const runJob = async (path: string, body?: any, method = "POST") => {
    setErr("");
    try {
      const r = await api(path, {
        method, body: JSON.stringify(body || {}),
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
    "반영완료": chip("#3a5a2e", "#dcead2"),
  };
  const stateLabel = s.state;   // 구버전 값은 서버가 읽기 시 정규화
  const diffCounts = s.diff?.counts;
  const footBad = s.foot
    ? (s.foot.summary.mismatch + s.foot.summary.rounding +
       s.foot.summary.cross)
    : undefined;
  const tabs = [
    { key: "overview", label: "개요" },
    { key: "sheets", label: "시트 뷰" },
    // 검증 배지: 합계 불일치·단수차·크로스 미발견 건수 — DSD 반영을
    // 차단하지 않으므로 중립색 (UI-7 ③)
    { key: "footing", label: "검증",
      count: footBad !== undefined ? String(footBad) : undefined,
      countBad: false,
      countTitle: "합계 불일치·단수차·크로스 미발견 건수 — " +
        "DSD 반영을 차단하지 않습니다 (확인용)" },
    { key: "change", label: "수정 확인",
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
            {meta.display_name || meta.file}</span>
          <span style={{ font: `500 12px ${F_LABEL}`, color: "#737780" }}>
            {meta.company}</span>
          <span style={stateChip[stateLabel] || stateChip["생성됨"]}>
            {stateLabel}</span>
          <div style={{ flex: 1 }} />
          <span title="반영 후 무결성 대조용"
            style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
            원본 지문 <code style={{
              fontFamily: MONO, fontSize: 11, background: "#edeeef",
              borderRadius: 4, padding: "1px 6px",
            }}>{meta.sha1?.slice(0, 4)}…{meta.sha1?.slice(-4)}</code>
          </span>
        </div>
        <div style={{ display: "flex", gap: 2 }}>
          {tabs.map((t) => {
            const active = tab === t.key ||
              (t.key === "footing" &&
               (tab === "prior" || tab === "xrecon"));
            return (
            <div key={t.key} data-testid={`tab-${t.key}`}
              onClick={() => setTab(t.key)} style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "9px 14px", cursor: "pointer",
                font: `600 13px ${F_LABEL}`,
                borderBottom: `2px solid ${
                  active ? "#001e40" : "transparent"}`,
                color: active ? "#001e40" : "#737780",
              }}>
              <span>{t.label}</span>
              {t.count && <span title={(t as any).countTitle} style={{
                font: `700 10px ${F_LABEL}`,
                color: (t as any).countBad ? "#930010" : "#001e40",
                background: (t as any).countBad ? "#ffdad6" : "#d5e3ff",
                borderRadius: 9999,
                padding: "1px 7px", fontVariantNumeric: "tabular-nums",
              }}>{t.count}</span>}
            </div>
            );
          })}
        </div>
      </div>

      {job && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "10px 24px", background: "#d5e3ff",
          font: `600 12px ${F_LABEL}`, color: "#001e40",
        }}>
          <Icon name="progress_activity" size={16} />
          {JOB_LABEL[job.kind] || job.kind} — {
            job.progress?.message || job.state}
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
      {(tab === "footing" || tab === "prior" || tab === "xrecon") && (
        <FootingTab sessionId={sessionId} s={s} runJob={runJob}
          setErr={setErr}
          initialSub={tab === "prior" ? "prior"
            : tab === "xrecon" ? "xrecon" : "foot"} />
      )}
      {tab === "change" && (
        <ChangeReview sessionId={sessionId} s={s} setErr={setErr}
          reload={reload}
          onRepack={async (approvedIds) => {
            const done = await runJob(
              `/api/workbench/sessions/${sessionId}/repack`,
              { approved_change_ids: approvedIds,
                reviewed_xlsx_sha256: s.diff?.xlsx_sha256 });
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
  const [vcheck, setVcheck] = useState<any>(null);
  const runVersionCheck = async () => {
    setVcheck({ running: true });
    try {
      const r = await api(`/api/workbench/version-check?dsd_path=${
        encodeURIComponent(s.dsd_path)}`);
      setVcheck(r);
    } catch (e: any) {
      setVcheck({ error: e.message });
    }
  };
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
              <GhostBtn onClick={() => openFile(s.xlsx_path)}>
                <Icon name="open_in_new" size={17} />엑셀: {s.xlsx_path
                  .split("\\").pop()}
              </GhostBtn>
              <PrimaryBtn onClick={goChange}>
                <Icon name="rule" size={17} />수정 완료 — 수정 확인
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
            <span style={{ color: "#737780" }}>원본 지문
              (반영 후 무결성 대조용)</span>
            <span style={{
              color: "#191c1d", fontFamily: MONO, fontSize: 11,
              wordBreak: "break-all",
            }}>{meta.sha1}</span>
            <span style={{ color: "#737780" }}>편집기 버전</span>
            <span style={{
              color: "#191c1d", display: "flex", alignItems: "center",
              gap: 6, flexWrap: "wrap",
            }}>
              {/* UI-9: 상태 3분리 — a.검증됨 b.미등재 c.버전 없음
                  (수신물/비수신물). 수신물 판정 = 추출 산출의 열람용
                  표식(소스 식별 자산), 추출 전엔 수신물 파일명 규약
                  (접수번호 14자리)으로 잠정 판정 */}
              {(() => {
                const wrapped = meta.viewonly ??
                  /^\d{14}/.test(String(meta.file || ""));
                if (meta.editver && meta.editver_known) return (
                  <span title="클릭 → 편집기 버전 확인 즉석 실행 (왕복 점검 포함)"
                    onClick={runVersionCheck}
                    style={{ ...chip("#3a5a2e", "#dcead2"),
                      cursor: "pointer" }}>
                    <Icon name="check" size={12} />
                    검증된 편집기 {meta.editver}
                  </span>
                );
                if (meta.editver) return (
                  <span title="클릭 → 편집기 버전 확인 즉석 실행"
                    onClick={runVersionCheck}
                    style={{ ...chip("#7a4f00", "#ffecc7"),
                      cursor: "pointer" }}>
                    <Icon name="schedule" size={12} />
                    {`편집기 버전 ${meta.editver} — 아직 검증 목록에 없음. 무수정 반영 1회로 지문 일치 확인 시 등록됩니다`}
                  </span>
                );
                if (wrapped) return (
                  <span style={chip("#43474f", "#edeeef")}>
                    <Icon name="visibility" size={12} />
                    공시 수신물 — 열람용 (편집기 버전 정보 없음이 정상)
                  </span>
                );
                return (
                  <span style={chip("#7a4f00", "#ffecc7")}>
                    <Icon name="warning" size={12} />
                    버전 정보 없는 파일 — 반영 전 무결성 확인 권장
                  </span>
                );
              })()}
              {vcheck && (
                <span style={vcheck.running
                  ? chip("#43474f", "#edeeef")
                  : vcheck.error || vcheck.g2_smoke === "fail"
                    ? chip("#930010", "#ffdad6")
                    : chip("#3a5a2e", "#dcead2")}>
                  {vcheck.running ? "버전 확인 중… (왕복 점검)"
                    : vcheck.error ? vcheck.error
                      : `버전 확인: ${vcheck.known ? "등재" : "미등재"}
                         · 왕복 점검 ${vcheck.g2_smoke.toUpperCase()}`}
                </span>
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
            <span style={{ color: "#737780" }}>줄바꿈 표기만 있는 빈 셀</span>
            <span style={{
              color: "#191c1d", fontVariantNumeric: "tabular-nums",
            }}>{meta.cr_only ?? "—"}</span>
          </div>
        </Card>
        <Card style={{ padding: 20 }}>
          <div style={{
            font: `700 13px ${F_HEAD}`, color: "#191c1d", marginBottom: 14,
          }}>반영 옵션</div>
          <div style={{
            display: "flex", flexDirection: "column", gap: 12,
            font: `500 12px ${F_LABEL}`,
          }}>
            {/* UI-7 확장 ④: 해당 0건 옵션은 접힘 — 평문 안내만 */}
            {(meta.cr_only ?? 0) > 0 && (
              <div>
                <div style={{ font: `600 12px ${F_LABEL}`,
                  color: "#191c1d" }}>
                  줄바꿈 표기 정리 — 기본 켜짐</div>
                <div style={{ color: "#737780" }}>
                  줄바꿈 표기만 있는 빈 셀 {meta.cr_only}개를 빈 셀로
                  정리합니다. 수정 확인 화면에서 함께 보여드립니다.</div>
              </div>
            )}
            {(meta.deduped_notes ?? 0) > 0 && (
              <div>
                <div style={{ font: `600 12px ${F_LABEL}`,
                  color: "#191c1d" }}>
                  주석 번호 정리 — 추출 때 결정</div>
                <div style={{ color: "#737780" }}>
                  중복 번호 {meta.deduped_notes}건은 추출 때 정리되어
                  DSD에 반영할 때 함께 적용됩니다.</div>
              </div>
            )}
            {!(meta.cr_only ?? 0) && !(meta.deduped_notes ?? 0) && (
              <div style={{ color: "#737780" }}>
                {meta.cells == null
                  ? "추출 후 자동 보정 대상이 표시됩니다."
                  : "자동 보정 대상이 없습니다 — 값 수정만 반영됩니다."}
              </div>
            )}
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

// ======== TAB: Footing (A-4 합계검증·주석대사 + A-5b 전기대사) ========
const _V_COLORS: Record<string, [string, string]> = {
  "일치": ["#3a5a2e", "#dcead2"],
  "단수차": ["#7a4f00", "#ffecc7"],
  "불일치": ["#930010", "#ffdad6"],
  "미매칭": ["#930010", "#ffdad6"],
};

function fmtNum(v: any) {
  if (typeof v === "number") {
    const s = Math.abs(v).toLocaleString();
    return v < 0 ? `(${s})` : s;
  }
  return v == null ? "" : String(v);
}

function FootingTab({ sessionId, s, runJob, setErr, initialSub }: {
  sessionId: string; s: any; setErr: (m: string) => void;
  runJob: (path: string, body?: any, method?: string) => Promise<any>;
  initialSub?: "foot" | "prior" | "xrecon";
}) {
  const [sub, setSub] = useState<"foot" | "prior" | "xrecon">(
    initialSub || "foot");
  const [filter, setFilter] = useState("문제만");
  const [sel, setSel] = useState<number | null>(null);
  const [levelEdits, setLevelEdits] = useState<Record<string, number>>({});
  const [priorPath, setPriorPath] = useState("");
  const foot = s.foot;
  const recon = s.recon;

  const subTab = (key: "foot" | "prior" | "xrecon", label: string) => (
    <span key={key} onClick={() => setSub(key)} style={{
      font: `600 12px ${F_LABEL}`, padding: "6px 12px", borderRadius: 8,
      cursor: "pointer",
      color: sub === key ? "#001e40" : "#737780",
      background: sub === key ? "#d5e3ff" : "transparent",
    }}>{label}</span>
  );

  // ---- 헤더 바 (서브탭 + 요약 뱃지 + 액션) ----
  const summary = foot?.summary;
  const badges = summary ? [
    ["일치", summary.match, "#3a5a2e", "#dcead2"],
    ["단수차", summary.rounding, "#7a4f00", "#ffecc7"],
    ["불일치", summary.mismatch, "#930010", "#ffdad6"],
    ["주석 미매칭", summary.cross, "#930010", "#ffdad6"],
  ] as [string, number, string, string][] : [];

  const overridesToApply = Object.entries(levelEdits);

  return (
    <div style={{
      display: "flex", flexDirection: "column", flex: 1, minHeight: 0,
    }}>
      <div style={{
        flex: "none", display: "flex", alignItems: "center", flexWrap: "wrap",
        rowGap: 8, gap: 8, padding: "12px 24px", background: "#fff",
        borderBottom: "1px solid #c3c6d1",
      }}>
        {subTab("foot", "합계검증·주석대사")}
        {subTab("prior", "전기와 일치합니까?")}
        {subTab("xrecon", "XBRL 태깅 대사")}
        <div style={{ width: 1, height: 22, background: "#c3c6d1",
          margin: "0 4px" }} />
        {sub === "foot" && badges.map(([lb, n, fg, bg]) => (
          <span key={lb} style={chip(fg, n ? bg : "#edeeef")}>
            {lb} {n}</span>
        ))}
        {sub === "foot" && summary?.manual_overrides > 0 && (
          <span style={chip("#001e40", "#d5e3ff")}>
            수동 레벨 {summary.manual_overrides}</span>
        )}
        <div style={{ flex: 1 }} />
        {sub === "foot" && (
          <>
            <GhostBtn onClick={() => runJob(
              `/api/workbench/sessions/${sessionId}/foot`,
              { excel: true }).then((d) => {
                const p = d?.result?.ai_excel_path;
                if (p) openFile(p);
              })}>
              <Icon name="download" size={15} />AI_Footing 엑셀 내보내기
            </GhostBtn>
            <PrimaryBtn onClick={async () => {
              if (overridesToApply.length) {
                await runJob(
                  `/api/workbench/sessions/${sessionId}/foot/levels`,
                  { overrides: overridesToApply.map(([k, level]) => {
                    const [sheet, row] = k.split("|");
                    return { sheet, row: Number(row), level };
                  }) }, "PUT");
                setLevelEdits({});
              } else {
                await runJob(`/api/workbench/sessions/${sessionId}/foot`);
              }
            }}>
              <Icon name="refresh" size={15} />
              {foot ? (overridesToApply.length
                ? `재검증 (레벨 ${overridesToApply.length}건 반영)` : "재검증")
                : "합계 검증 실행"}
            </PrimaryBtn>
          </>
        )}
      </div>

      {sub === "foot" && !foot && (
        <div style={{
          padding: 24, font: `500 13px ${F_LABEL}`, color: "#737780",
        }}>Footing 검증을 실행하면 합계검증·주석대사 findings와 레벨
          오버라이드가 여기 표시됩니다.</div>
      )}

      {sub === "foot" && foot && (
        <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
          {/* findings 리스트 */}
          <div style={{
            width: 340, flex: "none", background: "#fff",
            borderRight: "1px solid #c3c6d1", display: "flex",
            flexDirection: "column", minHeight: 0,
          }}>
            <div style={{
              flex: "none", display: "flex", gap: 4, padding: "10px 12px",
              borderBottom: "1px solid rgba(195,198,209,0.5)",
              flexWrap: "wrap",
            }}>
              {["문제만", "전체", "일치", "단수차", "불일치", "미매칭"].map(
                (f) => (
                  <span key={f} onClick={() => setFilter(f)} style={{
                    font: `600 11px ${F_LABEL}`, padding: "4px 9px",
                    borderRadius: 8, cursor: "pointer",
                    color: filter === f ? "#001e40" : "#737780",
                    background: filter === f ? "#d5e3ff" : "#edeeef",
                  }}>{f}</span>
                ))}
            </div>
            <div style={{ flex: 1, overflow: "auto" }}>
              {(foot.findings as any[])
                .map((r, i) => ({ ...r, _i: i, _kind: "foot" }))
                .concat((foot.notes as any[])
                  .filter((n) => !n.found)
                  .map((n, i) => ({
                    _i: 10000 + i, _kind: "note", sheet: n.sheet,
                    label: n.label, loc: `R${n.row}`, verdict: "미매칭",
                    expected: n.value, actual: null, diff: null,
                    refs: n.refs, period: n.period,
                  })))
                .filter((r) => filter === "전체"
                  || (filter === "문제만" && r.verdict !== "일치")
                  || r.verdict === filter)
                .map((r) => {
                  const [fg, bg] = _V_COLORS[r.verdict] ||
                    ["#43474f", "#edeeef"];
                  return (
                    <div key={r._i} className="hoverable"
                      onClick={() => setSel(r._i)} style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "10px 12px", cursor: "pointer",
                        borderBottom: "1px solid rgba(195,198,209,0.35)",
                        background: sel === r._i ? "#f3f4f5" : undefined,
                      }}>
                      <span style={{
                        width: 4, alignSelf: "stretch", borderRadius: 2,
                        background: fg, flex: "none",
                      }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          font: `600 12px ${F_LABEL}`, color: "#191c1d",
                          overflow: "hidden", textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}>{r.label}</div>
                        <div style={{
                          font: `500 11px ${F_LABEL}`, color: "#737780",
                          marginTop: 2,
                        }}>[{r.sheet}] {r.loc}
                          {r._kind === "foot" &&
                            ` · ${r.scope}/${r.direction}`}
                          {r._kind === "note" && ` · 주석 ${r.refs}`}
                        </div>
                      </div>
                      <span style={chip(fg, bg)}>{r.verdict}</span>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* 상세 + 레벨 오버라이드 */}
          <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
            <FindingDetail foot={foot} sel={sel} />
            <div style={{
              display: "flex", alignItems: "baseline", gap: 10,
              margin: "18px 0 8px",
            }}>
              <h2 style={{
                margin: 0, font: `700 15px ${F_HEAD}`, color: "#191c1d",
              }}>추론 레벨 (계층 오버라이드)</h2>
              <span style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
                수정 후 재검증 — 수동 지정 행은 뱃지로 구분</span>
            </div>
            <div style={{ overflowX: "auto", maxWidth: 760 }}>
              <table style={{
                width: "100%", borderCollapse: "collapse",
                background: "#fff", border: "1px solid #c3c6d1",
              }}>
                <thead><tr>
                  {["시트", "행", "라벨", "자동", "수동"].map((h, i) => (
                    <th key={h} style={{
                      textAlign: i >= 3 ? "center" : "left",
                      font: `700 11px ${F_LABEL}`, color: "#737780",
                      borderBottom: "1px solid #c3c6d1", padding: "7px 10px",
                      background: "#f3f4f5",
                    }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {(foot.levels as any[]).map((lv) => {
                    const key = `${lv.sheet}|${lv.row}`;
                    const cur = levelEdits[key] ?? lv.manual ?? "";
                    return (
                      <tr key={key}>
                        <td style={_tdL}>{lv.sheet}</td>
                        <td style={{ ..._tdL, fontFamily: MONO,
                          fontSize: 11 }}>R{lv.row}</td>
                        <td style={_tdL}>{lv.label}</td>
                        <td style={{ ..._tdL, textAlign: "center",
                          fontVariantNumeric: "tabular-nums" }}>
                          L{lv.auto}</td>
                        <td style={{ ..._tdL, textAlign: "center" }}>
                          <span style={{
                            display: "inline-flex", alignItems: "center",
                            gap: 5,
                          }}>
                            {(lv.manual || levelEdits[key] != null) && (
                              <span style={{
                                font: `600 9px ${F_LABEL}`,
                                color: "#001e40", background: "#d5e3ff",
                                borderRadius: 4, padding: "2px 5px",
                              }}>수동</span>
                            )}
                            <select value={cur} onChange={(e) =>
                              setLevelEdits({
                                ...levelEdits,
                                [key]: Number(e.target.value),
                              })} style={{
                                font: `600 11px ${F_LABEL}`,
                                color: "#43474f",
                                border: "1px solid #c3c6d1",
                                borderRadius: 4, padding: "2px 4px",
                                background: "#fff", cursor: "pointer",
                              }}>
                              <option value="">자동</option>
                              {[1, 2, 3, 4].map((n) => (
                                <option key={n} value={n}>L{n}</option>
                              ))}
                            </select>
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {sub === "prior" && (
        <PriorSub sessionId={sessionId} recon={recon} runJob={runJob}
          priorPath={priorPath} setPriorPath={setPriorPath} />
      )}
      {sub === "xrecon" && (
        <XbrlReconSub key={sessionId} sessionId={sessionId} runJob={runJob} />
      )}
    </div>
  );
}

// ---- XBRL 대사 서브탭 (V-1) — DSD ↔ 인스턴스 태깅 검증 ----
function XbrlReconSub({ sessionId, runJob }: {
  sessionId: string;
  runJob: (path: string, body?: any) => Promise<any>;
}) {
  const [pkg, setPkg] = useState("");
  const [tol, setTol] = useState("");
  const [storedResult, setResult] = useState<any>(null);
  const result = storedResult?.session_id === sessionId ? storedResult : null;
  const [falseOnly, setFalseOnly] = useState(true);
  const [pkgs, setPkgs] = useState<any[]>([]);

  useEffect(() => {
    api("/api/explorer/packages").then((r) =>
      setPkgs(r.packages)).catch(() => {});
  }, []);

  useEffect(() => {
    let active = true;
    setResult(null);
    api(`/api/workbench/sessions/${sessionId}`).then((s) => {
      if (active && s.xbrl_recon?.session_id === sessionId)
        setResult((current: any) => current ?? s.xbrl_recon);
    }).catch(() => {});
    return () => { active = false; };
  }, [sessionId]);

  const run = async () => {
    const done = await runJob("/api/studio/xbrl-recon", {
      session_id: sessionId, package_dir: pkg,
      tolerance: tol ? Number(tol) : undefined,
    });
    if (done?.state === "done" && done.result?.session_id === sessionId)
      setResult(done.result);
  };

  const c = result?.counts || {};
  const allRows: any[] = result
    ? Object.entries(result.rows || {}).flatMap(([sheet, rows]: any) =>
        rows.map((r: any) => ({ ...r, sheet })))
    : [];
  const shown = allRows.filter((r) => !falseOnly || r.true === false);
  const undecided = Math.max(
    allRows.filter((r) => r.true !== true && r.true !== false).length,
    Number(c["매핑 없음"] || 0),
    Number(result?.total || 0) - Number(result?.matched || 0));
  const complete = result?.total > 0 && undecided === 0
    && allRows.length === result.total
    && allRows.every((r) => r.true === true) && result.false === 0;

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
      <div style={{
        display: "flex", gap: 8, alignItems: "center", marginBottom: 14,
        maxWidth: 1100, flexWrap: "wrap",
      }}>
        {pkgs.length > 0 && (
          <select defaultValue="" onChange={(e) => {
            if (e.target.value) setPkg(e.target.value);
          }} style={{
            font: `500 12px ${F_LABEL}`, border: "1px solid #c3c6d1",
            borderRadius: 8, padding: "8px 10px", background: "#fff",
            maxWidth: 240,
          }}>
            <option value="">최근 수신 XBRL 자료…</option>
            {pkgs.map((p) => (
              <option key={p.path} value={p.path}>{p.name}</option>
            ))}
          </select>
        )}
        <input value={pkg} onChange={(e) => setPkg(e.target.value)}
          placeholder="XBRL 자료 폴더 (같은 회사 제출파일)"
          style={{
            flex: 1, minWidth: 280, font: `500 12px ${F_LABEL}`,
            padding: "8px 10px", border: "1px solid #c3c6d1",
            borderRadius: 8,
          }} />
        <input value={tol} onChange={(e) => setTol(e.target.value)}
          placeholder="오차(원, 비우면 자동)" style={{
            width: 150, font: `500 12px ${F_LABEL}`, padding: "8px 10px",
            border: "1px solid #c3c6d1", borderRadius: 8,
            fontVariantNumeric: "tabular-nums",
          }} />
        <PrimaryBtn onClick={run}>
          <Icon name="rule" size={15} />
          {result ? "재실행" : "태깅 대사 실행"}</PrimaryBtn>
      </div>

      {!result && (
        <div style={{ font: `500 13px ${F_LABEL}`, color: "#737780" }}>
          같은 회사의 XBRL 제출파일과 DSD 본문 값을 대조합니다 —
          태깅이 공시 본문과 일치하는지 제출 직전 최종 검증 (매핑은
          계정 매핑 확정 기록 → 기말 태깅 승계 순 재사용, 신규 추론 없음).</div>
      )}

      {result && (
        <>
          {result.source_warning && (
            <div style={{
              font: `500 12px ${F_LABEL}`, color: "#7a4f00",
              background: "#ffecc7", borderRadius: 8, padding: "9px 12px",
              marginBottom: 10, maxWidth: 1100,
            }}>{result.source_warning}</div>
          )}
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            flexWrap: "wrap",
            background: complete ? "#dcead2" : "#ffdad6",
            color: complete ? "#3a5a2e" : "#930010",
            borderRadius: 8, padding: "12px 16px", maxWidth: 1100,
          }}>
            <Icon name={complete ? "check_circle" : "error"}
              size={20} />
            <span style={{ font: `700 14px ${F_HEAD}` }}>
              대조율 {result.matched}/{result.total} (
              {((result.match_rate || 0) * 100).toFixed(1)}%)</span>
            <span style={chip("#3a5a2e", "#dcead2")}>
              일치 {c["일치"]}</span>
            <span style={chip("#930010", "#ffdad6")}>
              값 상이 {c["값 상이"]}</span>
            <span style={chip("#930010", "#ffdad6")}>
              태깅 누락 {c["태깅 누락"]}</span>
            <span style={chip("#4e6874", "#cbe7f5")}>
              제출파일에만 {result.only_instance}</span>
            <span style={chip("#43474f", "#edeeef")}>
              매핑 없음 {c["매핑 없음"]} · 미판정 {undecided}</span>
            <div style={{ flex: 1 }} />
            <span style={{ font: `500 11px ${F_LABEL}`, opacity: 0.85 }}>
              허용오차 {result.tolerance}</span>
            {result.out_path && (
              <GhostBtn onClick={() => openFile(result.out_path)}>
                <Icon name="download" size={15} />엑셀 다운로드</GhostBtn>
            )}
          </div>

          <div style={{
            display: "flex", gap: 6, margin: "12px 0 8px",
            alignItems: "center",
          }}>
            <span onClick={() => setFalseOnly(!falseOnly)} style={{
              font: `600 11px ${F_LABEL}`, padding: "4px 10px",
              borderRadius: 8, cursor: "pointer",
              color: falseOnly ? "#930010" : "#737780",
              background: falseOnly ? "#ffdad6" : "#edeeef",
            }}>FALSE만 {falseOnly ? "표시 중" : "보기"}</span>
            <span style={{
              font: `500 11px ${F_LABEL}`, color: "#737780",
            }}>{shown.length}건 표시 · 스코프 본문(BS/PL/CF — CE 제외)
            </span>
          </div>

          <div style={{ overflowX: "auto", maxWidth: 1250 }}>
            <table style={{
              width: "100%", minWidth: 900, borderCollapse: "collapse",
              background: "#fff", border: "1px solid #c3c6d1",
            }}>
              <thead><tr>
                {[["시트", "left"], ["행 라벨", "left"],
                  ["DSD 값(원)", "right"], ["element", "left"],
                  ["근거", "left"], ["제출파일 값", "right"],
                  ["차이", "right"], ["판정", "center"]].map(([h, a]) => (
                  <th key={String(h)} style={{
                    textAlign: a as any, font: `700 11px ${F_LABEL}`,
                    color: "#737780", borderBottom: "1px solid #c3c6d1",
                    padding: "8px 12px", background: "#f3f4f5",
                    whiteSpace: "nowrap",
                  }}>{String(h)}</th>
                ))}
              </tr></thead>
              <tbody>
                {shown.slice(0, 300).map((r, i) => (
                  <tr key={i} style={{
                    background: r.true === false
                      ? "rgba(255,218,214,0.35)" : undefined,
                  }}>
                    <td style={{ ..._tdL, color: "#737780" }}>
                      {r.sheet}</td>
                    <td style={{ ..._tdL, whiteSpace: "nowrap",
                      maxWidth: 260, overflow: "hidden",
                      textOverflow: "ellipsis" }}>{r.label}</td>
                    <td style={{ ..._tdL, textAlign: "right",
                      fontVariantNumeric: "tabular-nums" }}>
                      {fmtNum(r.won)}</td>
                    <td style={{ ..._tdL, fontFamily: MONO, fontSize: 11,
                      maxWidth: 280, overflow: "hidden",
                      textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {(r.element || "").replace("_", ":")}</td>
                    <td style={{ ..._tdL, color: "#737780" }}>
                      {r.map_src}</td>
                    <td style={{ ..._tdL, textAlign: "right",
                      fontVariantNumeric: "tabular-nums" }}>
                      {fmtNum(r.fact)}</td>
                    <td style={{ ..._tdL, textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      color: r.true === false ? "#ba1a1a" : "#191c1d" }}>
                      {fmtNum(r.diff)}</td>
                    <td style={{ ..._tdL, textAlign: "center" }}>
                      <span style={r.true === true
                        ? chip("#3a5a2e", "#dcead2")
                        : r.true === false
                          ? chip("#930010", "#ffdad6")
                          : chip("#43474f", "#edeeef")}>
                        {r.verdict}</span></td>
                  </tr>
                ))}
                {!shown.length && (
                  <tr><td colSpan={8} style={{
                    ..._tdL, color: "#737780",
                  }}>{falseOnly
                    ? (complete ? "FALSE 없음 — 태깅·본문 전수 일치"
                      : `FALSE 없음 — 검증 미완료 (미매핑/미판정 ${undecided}건)`)
                    : "행 없음"}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

const _tdL: React.CSSProperties = {
  font: `500 12px var(--al-font-label)`, color: "#191c1d",
  padding: "6px 10px", borderBottom: "1px solid rgba(195,198,209,0.4)",
};

function FindingDetail({ foot, sel }: { foot: any; sel: number | null }) {
  if (sel == null) return null;
  const r = sel < 10000 ? foot.findings[sel]
    : foot.notes.filter((n: any) => !n.found)[sel - 10000];
  if (!r) return null;
  const isNote = sel >= 10000;
  const diff = isNote ? null : r.diff;
  return (
    <div style={{ maxWidth: 560 }}>
      <h2 style={{
        margin: "0 0 12px", font: `700 15px ${F_HEAD}`, color: "#191c1d",
      }}>{r.label} <span style={{
        font: `500 12px ${F_LABEL}`, color: "#737780",
      }}>[{r.sheet}] {isNote ? `R${r.row}` : r.loc}</span></h2>
      <Card style={{
        padding: 20, display: "flex", flexDirection: "column", gap: 12,
      }}>
        {isNote ? (
          <>
            <Row2 k={`주석 ${r.refs} (${r.period})`} v={fmtNum(r.value)} />
            <div style={{
              background: "#ffdad6", borderRadius: 8, padding: "10px 12px",
              font: `600 12px ${F_LABEL}`, color: "#930010",
            }}>본문 값을 주석 {r.refs}에서 찾지 못했습니다 — 주석 시트에서
              수동 확인</div>
          </>
        ) : (
          <>
            <Row2 k={`Σ자식 (${r.n_children}개)`} v={fmtNum(r.expected)} />
            <Row2 k="기재값" v={fmtNum(r.actual)} top />
            <div style={{
              display: "flex", alignItems: "center",
              justifyContent: "space-between",
              background: r.verdict === "일치" ? "#dcead2" : "#ffdad6",
              borderRadius: 8, padding: "10px 12px",
            }}>
              <span style={{
                font: `600 12px ${F_LABEL}`,
                color: r.verdict === "일치" ? "#3a5a2e" : "#930010",
              }}>차이 ({r.verdict})</span>
              <span style={{
                font: `700 13px ${F_LABEL}`,
                color: r.verdict === "일치" ? "#3a5a2e" : "#930010",
                fontVariantNumeric: "tabular-nums",
              }}>{fmtNum(diff)}</span>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

function Row2({ k, v, top }: { k: string; v: string; top?: boolean }) {
  return (
    <div style={{
      display: "flex", alignItems: "center",
      justifyContent: "space-between", font: `500 13px ${F_LABEL}`,
      color: "#43474f",
      borderTop: top ? "1px solid rgba(195,198,209,0.5)" : undefined,
      paddingTop: top ? 12 : 0,
    }}>
      <span>{k}</span>
      <span style={{
        fontVariantNumeric: "tabular-nums", fontWeight: 600,
        color: "#191c1d",
      }}>{v}</span>
    </div>
  );
}

// ---- 전기대사 서브탭 (A-5b) ----
function PriorSub({ sessionId, recon, runJob, priorPath, setPriorPath }: {
  sessionId: string; recon: any; priorPath: string;
  setPriorPath: (v: string) => void;
  runJob: (path: string, body?: any) => Promise<any>;
}) {
  const [showNotes, setShowNotes] = useState(false);
  const [falseOnly, setFalseOnly] = useState(true);

  const run = () => runJob(`/api/workbench/sessions/${sessionId}/recon`,
    { prior_path: priorPath || recon?.prior_path });

  const pick = async () => {
    const r = await api("/api/fs/pick", { method: "POST" });
    if (r.path) setPriorPath(r.path);
  };

  const verdict = recon?.verdict;
  const rows: any[] = recon
    ? (showNotes ? recon.notes : recon.body) : [];
  const shown = rows.filter((r) => !falseOnly || !r.true);
  const otherFalse = recon
    ? (showNotes ? recon.body : recon.notes)
        .filter((r: any) => !r.true).length
    : 0;
  const emptyMsg = !falseOnly ? "행 없음"
    : otherFalse > 0
      ? `${showNotes ? "주석" : "본문"} 대사에는 FALSE 없음 — ` +
        `${showNotes ? "본문" : "주석"} 대사에 FALSE ${otherFalse}건`
      : "FALSE 없음 — 전수 일치";

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "20px 24px" }}>
      <div style={{
        display: "flex", gap: 8, alignItems: "center", marginBottom: 14,
        maxWidth: 960,
      }}>
        <input value={priorPath} onChange={(e) =>
          setPriorPath(e.target.value)}
          placeholder={recon?.prior_path ||
            "전기 .dsd/.xlsx 경로 (초도감사는 dart_explorer 캐시 파일)"}
          style={{
            flex: 1, font: `500 12px ${F_LABEL}`, padding: "8px 10px",
            border: "1px solid #c3c6d1", borderRadius: 8,
          }} />
        <GhostBtn onClick={pick}>
          <Icon name="folder_open" size={15} />찾기</GhostBtn>
        <PrimaryBtn onClick={run}>
          <Icon name="play_arrow" size={15} />
          {recon ? "전기대사 재실행" : "전기대사 실행"}</PrimaryBtn>
      </div>

      {!recon && (
        <div style={{ font: `500 13px ${F_LABEL}`, color: "#737780" }}>
          전기 보고서 파일을 지정하고 실행하세요 — 당기 파일의 전기값과
          전기 파일의 당기값을 전수 대조합니다.</div>
      )}

      {recon && (
        <>
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            background: verdict ? "#dcead2" : "#ffdad6",
            color: verdict ? "#3a5a2e" : "#930010",
            borderRadius: 8, padding: "12px 16px", maxWidth: 960,
          }}>
            <Icon name={verdict ? "check_circle" : "error"} size={22} />
            <span style={{ font: `700 15px ${F_HEAD}` }}>
              {verdict ? "TRUE — 전기대사 전수 일치" : "FALSE 존재"}</span>
            <span style={{ font: `500 12px ${F_LABEL}`, opacity: 0.9 }}>
              본문 {recon.stmt.true}/{recon.stmt.n} TRUE · 주석{" "}
              {recon.notes_summary.true}/{recon.notes_summary.n} TRUE ·
              제목 매칭 {recon.note_matched}/{recon.note_total}
            </span>
            <div style={{ flex: 1 }} />
            <span style={recon.source === "opendart-cache"
              ? chip("#4e6874", "#cbe7f5") : chip("#001e40", "#d5e3ff")}>
              <Icon name={recon.source === "opendart-cache"
                ? "cloud_done" : "computer"} size={13} />
              {recon.source === "opendart-cache"
                ? "전기 소스: OpenDART 캐시" : "전기 소스: 로컬 파일"}
            </span>
            <GhostBtn onClick={() => openFile(recon.excel_path)}>
              <Icon name="download" size={15} />엑셀 내보내기</GhostBtn>
          </div>
          <div style={{
            font: `500 12px ${F_LABEL}`, color: "#43474f",
            margin: "10px 2px 14px",
          }}>{recon.guide}</div>

          <div style={{
            display: "flex", gap: 6, marginBottom: 8, alignItems: "center",
          }}>
            {[["본문", false], ["주석", true]].map(([lb, isNotes]) => (
              <span key={String(lb)}
                onClick={() => setShowNotes(isNotes as boolean)} style={{
                  font: `600 11px ${F_LABEL}`, padding: "4px 10px",
                  borderRadius: 8, cursor: "pointer",
                  color: showNotes === isNotes ? "#001e40" : "#737780",
                  background: showNotes === isNotes ? "#d5e3ff" : "#edeeef",
                }}>{String(lb)} 대사
                {" "}{isNotes ? recon.notes.length : recon.body.length}건
              </span>
            ))}
            <span onClick={() => setFalseOnly(!falseOnly)} style={{
              font: `600 11px ${F_LABEL}`, padding: "4px 10px",
              borderRadius: 8, cursor: "pointer",
              color: falseOnly ? "#930010" : "#737780",
              background: falseOnly ? "#ffdad6" : "#edeeef",
            }}>FALSE만 {falseOnly ? "표시 중" : "보기"}</span>
            <span style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
              {shown.length}건 표시</span>
          </div>

          <div style={{ overflowX: "auto", maxWidth: 1100 }}>
            <table style={{
              width: "100%", minWidth: 760, borderCollapse: "collapse",
              background: "#fff", border: "1px solid #c3c6d1",
            }}>
              <thead><tr>
                {[["시트", "left"], ["계정과목/행", "left"],
                  ["당기보고서 전기값", "right"],
                  ["전기보고서 당기값", "right"], ["판정", "center"],
                  ["비고", "left"]].map(([h, a]) => (
                  <th key={String(h)} style={{
                    textAlign: a as any, font: `700 11px ${F_LABEL}`,
                    color: "#737780", borderBottom: "1px solid #c3c6d1",
                    padding: "8px 12px", background: "#f3f4f5",
                    whiteSpace: "nowrap",
                  }}>{String(h)}</th>
                ))}
              </tr></thead>
              <tbody>
                {shown.slice(0, 300).map((r, i) => (
                  <tr key={i} style={{
                    background: r.true ? undefined
                      : "rgba(255,218,214,0.35)",
                  }}>
                    <td style={{ ..._tdL, color: "#737780" }}>
                      {r.sheet}{r.table ? ` 표${r.table}` : ""}</td>
                    <td style={{ ..._tdL, whiteSpace: "nowrap",
                      maxWidth: 300, overflow: "hidden",
                      textOverflow: "ellipsis" }}>{r.label}</td>
                    <td style={{ ..._tdL, textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      color: typeof r.cur === "number" && r.cur < 0
                        ? "#ba1a1a" : "#191c1d" }}>{fmtNum(r.cur)}</td>
                    <td style={{ ..._tdL, textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      color: typeof r.pri === "number" && r.pri < 0
                        ? "#ba1a1a" : "#191c1d" }}>{fmtNum(r.pri)}</td>
                    <td style={{ ..._tdL, textAlign: "center" }}>
                      <span style={r.true
                        ? chip("#3a5a2e", "#dcead2")
                        : chip("#930010", "#ffdad6")}>
                        {r.true ? "TRUE" : "FALSE"}</span></td>
                    <td style={{ ..._tdL, color: "#737780" }}>{r.note}</td>
                  </tr>
                ))}
                {shown.length > 300 && (
                  <tr><td colSpan={6} style={{
                    ..._tdL, color: "#737780",
                  }}>외 {shown.length - 300}건 — 엑셀에서 전체 확인</td></tr>
                )}
                {!shown.length && (
                  <tr><td colSpan={6} style={{
                    ..._tdL, color: "#737780",
                  }}>{emptyMsg}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ======== TAB: 수정 확인 (반영 전 확인) ========
function ChangeReview({ sessionId, s, onRepack, setErr, reload }: {
  sessionId: string; s: any; setErr: (m: string) => void;
  reload: () => void;
  onRepack: (approvedIds: number[] | "all") => Promise<void>;
}) {
  const [open, setOpen] = useState<Record<string, boolean>>({ edit: true });
  const [excluded, setExcluded] = useState<Record<number, boolean>>({});
  const [running, setRunning] = useState(false);
  const [diffFailed, setDiffFailed] = useState(false);
  const diffPending = useRef(false);
  const diff = s.diff;

  const runDiff = async () => {
    if (diffPending.current) return;
    diffPending.current = true;
    setDiffFailed(false);
    setErr("");
    try {
      await api(`/api/workbench/sessions/${sessionId}/diff`, {
        method: "POST",
        body: JSON.stringify({ options: { clean_cr: true } }),
      });
      reload();
    } catch (e: any) {
      setErr(e.message);
      setDiffFailed(true);
    } finally {
      diffPending.current = false;
    }
  };

  const changes: Change[] = diff?.changes || [];
  const selCount = changes.filter((c) => !excluded[c.id]).length;

  // 최초 자동 실행은 한 번만. 실패 시 같은 화면에서 명시적으로 재시도.
  useEffect(() => {
    if (!diff && s.xlsx_path) runDiff();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!diff) {
    return (
      <div style={{ padding: 24, maxWidth: 720 }}>
        <Card style={{ padding: 20 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
          }}>
            <Icon name="progress_activity" size={18} color="#43474f" />
            <span style={{ font: `600 13px ${F_LABEL}`, color: "#191c1d" }}>
              {diffFailed ? "수정 내용 점검에 실패했습니다." : "수정 내용을 점검하고 있습니다…"}</span>
          </div>
          <div style={{
            font: `500 12px ${F_LABEL}`, color: "#737780", marginTop: 8,
          }}>
            엑셀에서 바뀐 내용을 자동으로 찾습니다. 원본은 그대로
            둡니다.
          </div>
          {diffFailed && <GhostBtn onClick={runDiff}>다시 비교</GhostBtn>}
        </Card>
      </div>
    );
  }

  const counts = diff.counts;
  // UI-7 확장 ⑤: 3단 과업 흐름 — 수정한 엑셀 → 바뀐 내용(자동) →
  // DSD에 반영
  const steps: [string, boolean][] = [
    ["1. 수정한 엑셀", true],
    [`2. 바뀐 내용 ${changes.length}건 (자동 점검)`, true],
    ["3. DSD에 반영", false],
  ];
  return (
    <div style={{
      display: "flex", flexDirection: "column", flex: 1, minHeight: 0,
    }}>
      <div style={{
        flex: "none", display: "flex", alignItems: "center", gap: 8,
        padding: "10px 24px 0", background: "#fff", flexWrap: "wrap",
      }}>
        {steps.map(([label, done], i) => (
          <React.Fragment key={label}>
            <span style={{
              display: "inline-flex", alignItems: "center", gap: 4,
              font: `600 11px ${F_LABEL}`, borderRadius: 8,
              padding: "4px 10px", whiteSpace: "nowrap",
              color: done ? "#3a5a2e" : "#43474f",
              background: done ? "#dcead2" : "#edeeef",
            }}>
              {done && <Icon name="check" size={12} />}{label}
            </span>
            {i < steps.length - 1 &&
              <Icon name="chevron_right" size={14} color="#c3c6d1" />}
          </React.Fragment>
        ))}
      </div>
      <div style={{
        flex: "none", display: "flex", alignItems: "center", gap: 10,
        padding: "12px 24px", background: "#fff",
        borderBottom: "1px solid #c3c6d1",
      }}>
        <Icon name="rule" size={18} color="#43474f" />
        <span style={{ font: `600 13px ${F_LABEL}`, color: "#191c1d" }}>
          반영 전 확인</span>
        <span title={`줄바꿈 표기 정리 ${counts.clean_cr}건 · 주석 번호 정리 ${
            counts.note_dedup}건 — 상세는 목록·이력 참조`}
          style={{ font: `500 12px ${F_LABEL}`, color: "#737780" }}>
          값 수정 {counts.edit}건 · 표기 자동 보정{" "}
          {counts.clean_cr + counts.note_dedup}건 — 적용 전 점검 결과
          ({diff.ts})
        </span>
        <div style={{ flex: 1 }} />
        <GhostBtn onClick={runDiff}>
          <Icon name="refresh" size={15} />다시 비교
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
                    ? "줄바꿈 표기만 있는 빈 셀 정리" : "주석 번호 중복 정리"}</span>
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
          }}>수정 0건 — 엑셀에서 값을 수정·저장한 뒤 [수정 확인]을 다시
            실행하세요. 지금 반영하면 원본과 동일한 사본이 만들어집니다.
          </div>
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
          {" "}— 원본은 그대로 둡니다
        </span>
        <div style={{ flex: 1 }} />
        {!changes.length ? (
          <GhostBtn onClick={() => onRepack("all")}>
            <Icon name="content_copy" size={15} />원본 사본 만들기
          </GhostBtn>
        ) : null}
        <PrimaryBtn disabled={running || !changes.length}
          onClick={async () => {
            setRunning(true);
            const ids = changes.filter((c) => !excluded[c.id])
              .map((c) => c.id);
            await onRepack(ids.length === changes.length ? "all" : ids);
            setRunning(false);
          }}>
          <Icon name="play_arrow" size={17} />
          선택한 {selCount}건 DSD에 반영
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
          이 DSD에 대한 반영 이력이 없습니다.</div>
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
            <span style={chip("#001e40", "#d5e3ff")}>DSD에 반영</span>
            <span style={{
              font: `600 12px ${F_LABEL}`, color: "#191c1d",
              fontVariantNumeric: "tabular-nums",
            }}>{h.ts}</span>
            <span title={`줄바꿈 표기 정리 ${h.cleans}건 · 주석 번호 정리 ${
                h.dedups}건`}
              style={{ font: `500 12px ${F_LABEL}`, color: "#43474f" }}>
              값 수정 {h.edits}건 · 표기 자동 보정 {h.cleans + h.dedups}건
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
              }}>옵션: {h.clean_cr ? "기본(줄바꿈 표기 정리)" : "원문 유지"} ·
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

// ======== MODAL: DSD에 반영 완료 ========
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
            color: "#191c1d" }}>DSD에 반영 완료</h2>
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
