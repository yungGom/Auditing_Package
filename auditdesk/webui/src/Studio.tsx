// XBRL Studio 5화면 — 택사노미 체크 · 매핑 확정 · 작성 워크시트 ·
// 차원 표 뷰어 · 트리 뷰 (참조 구현 v2 이식)
import React, { useEffect, useMemo, useState } from "react";
import { api, Job, openFile, pollJob } from "./api";
import RecCard, { RecAlt, RecBadge } from "./RecCard";
import {
  Card, chip, ErrorBanner, F_HEAD, F_LABEL, GhostBtn, Icon, MONO,
  PrimaryBtn,
} from "./ui";

// ---- 공용: job 실행 훅 — 서버가 진실 원천: 마운트 시 같은 종류의
// 최근 완료 job 결과를 복원 (새로고침·다른 브라우저에서도 동일 상태) ----
function useStudioJob(kind: string) {
  const [result, setResult] = useState<any>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api(`/api/jobs?kind=${kind}`).then((r) => {
      const last = (r.jobs || []).find((j: Job) =>
        j.state === "done" && j.result);
      if (last) setResult((cur: any) => cur ?? last.result);
    }).catch(() => {});
  }, [kind]);

  const run = async (path: string, body: any) => {
    setErr("");
    try {
      const r = await api(path, {
        method: "POST", body: JSON.stringify(body),
      });
      const done = await pollJob(r.job_id, setJob);
      setJob(null);
      if (done.state === "error") {
        setErr(done.error_detail?.detail || "작업 실패");
        return null;
      }
      setResult(done.result);
      return done.result;
    } catch (e: any) {
      setJob(null);
      setErr(e.message);
      return null;
    }
  };
  return { result, setResult, job, err, setErr, run };
}

function JobBar({ job }: { job: Job | null }) {
  if (!job) return null;
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10, padding: "10px 24px",
      background: "#d5e3ff", font: `600 12px ${F_LABEL}`, color: "#001e40",
    }}>
      <Icon name="progress_activity" size={16} />
      {job.kind} — {job.progress?.message || job.state}
    </div>
  );
}

function PathInput({ value, onChange, placeholder, width }: {
  value: string; onChange: (v: string) => void; placeholder: string;
  width?: number | string;
}) {
  return (
    <input value={value} onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder} style={{
        flex: width ? undefined : 1, width,
        font: `500 12px ${F_LABEL}`, padding: "8px 10px",
        border: "1px solid #c3c6d1", borderRadius: 8,
      }} />
  );
}

// 최근 수신 패키지 드롭다운 (explorer 캐시 목록 — 경로 복사 제거)
function PackagePicker({ onPick }: { onPick: (path: string) => void }) {
  const [pkgs, setPkgs] = useState<any[]>([]);
  useEffect(() => {
    api("/api/explorer/packages").then((r) =>
      setPkgs(r.packages)).catch(() => {});
  }, []);
  if (!pkgs.length) return null;
  return (
    <select defaultValue="" data-testid="pkg-picker"
      onChange={(e) => { if (e.target.value) onPick(e.target.value); }}
      style={{
        font: `500 12px ${F_LABEL}`, border: "1px solid #c3c6d1",
        borderRadius: 8, padding: "8px 10px", background: "#fff",
        maxWidth: 260,
      }}>
      <option value="">최근 수신 패키지…</option>
      {pkgs.map((p) => (
        <option key={p.path} value={p.path}>{p.name}</option>
      ))}
    </select>
  );
}

function fmtCell(v: any) {
  if (typeof v === "number") {
    const s = Math.abs(v).toLocaleString();
    return v < 0 ? `(${s})` : s;
  }
  return v == null ? "" : String(v);
}

const _td: React.CSSProperties = {
  font: `500 12px var(--al-font-label)`, color: "#191c1d",
  padding: "6px 10px", borderBottom: "1px solid rgba(195,198,209,0.4)",
  whiteSpace: "pre-wrap",
};

function GridTable({ rows }: { rows: any[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{
        borderCollapse: "collapse", background: "#fff",
        border: "1px solid #c3c6d1",
      }}>
        <tbody>
          {rows.map((r: any) => (
            <tr key={r.row}>
              {r.cells.map((v: any, ci: number) => (
                <td key={ci} style={{
                  ..._td,
                  textAlign: typeof v === "number" ? "right" : "left",
                  fontVariantNumeric: "tabular-nums",
                  color: typeof v === "number" && v < 0
                    ? "#ba1a1a" : "#191c1d",
                  maxWidth: ci === 0 ? 380 : 220,
                  overflow: "hidden", textOverflow: "ellipsis",
                }}>{fmtCell(v)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ==========================================================================
// 매핑 확정
// ==========================================================================
const MAP_STATE_META: Record<string, {
  label: string; dot: string; variant: string;
}> = {
  normal: { label: "추천", dot: "#001e40", variant: "recommend" },
  standard_recommended: { label: "표준 권장", dot: "#7a4f00",
    variant: "standard" },
  extension_needed: { label: "확장 필요", dot: "#930010",
    variant: "extension" },
  manual: { label: "수동 확인", dot: "#737780", variant: "extension" },
};

export function MappingScreen() {
  const { result: lastMap, job, err, setErr, run } =
    useStudioJob("mapping");
  const [mappingId, setMappingId] = useState<string | null>(null);
  useEffect(() => {
    if (lastMap?.mapping_id) setMappingId((c) => c ?? lastMap.mapping_id);
  }, [lastMap]);
  const [data, setData] = useState<any>(null);
  const [input, setInput] = useState("");
  const [filter, setFilter] = useState<"open" | "done" | "all">("open");
  const [sel, setSel] = useState(0);

  const reload = async (mid: string) => {
    try {
      setData(await api(`/api/studio/mapping/${mid}`));
    } catch (e: any) { setErr(e.message); }
  };
  useEffect(() => { if (mappingId) reload(mappingId); }, [mappingId]);

  const start = async () => {
    const accounts = input.split("\n").map((l) => l.trim()).filter(Boolean)
      .map((l) => {
        const [name, category] = l.split(",").map((x) => x.trim());
        return { name, category: category || undefined };
      });
    if (!accounts.length) { setErr("계정을 한 줄에 하나씩 입력하세요"); return; }
    const r = await run("/api/studio/mapping", { accounts });
    if (r?.mapping_id) setMappingId(r.mapping_id);
  };

  const items: any[] = data?.items || [];
  const nDone = items.filter((i) => i.decided).length;
  const pct = items.length ? Math.round(nDone / items.length * 100) : 0;
  const ringOff = 150.8 * (1 - (items.length ? nDone / items.length : 0));
  const shownIdx = items.map((it, i) => i).filter((i) =>
    filter === "all" || (filter === "done") === !!items[i].decided);
  const cur = items[sel];

  const confirm = async (idx: number, element: string) => {
    try {
      await api(`/api/studio/mapping/${mappingId}/decide`, {
        method: "PUT",
        body: JSON.stringify({ account_idx: idx, element }),
      });
      await reload(mappingId!);
    } catch (e: any) { setErr(e.message); }
  };

  return (
    <div style={{ display: "flex", height: "100%", minHeight: 0,
      flexDirection: "column" }}>
      <JobBar job={job} />
      <div style={{ padding: err ? "0 24px" : 0 }}>
        <ErrorBanner msg={err} /></div>
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{
          width: 360, flex: "none", background: "#fff",
          borderRight: "1px solid #c3c6d1", display: "flex",
          flexDirection: "column", minHeight: 0,
        }}>
          <div style={{
            flex: "none", display: "flex", alignItems: "center", gap: 14,
            padding: "16px 16px 12px",
            borderBottom: "1px solid rgba(195,198,209,0.5)",
          }}>
            <svg width="56" height="56" viewBox="0 0 56 56">
              <circle cx="28" cy="28" r="24" fill="none" stroke="#e1e3e4"
                strokeWidth="6" />
              <circle cx="28" cy="28" r="24" fill="none" stroke="#001e40"
                strokeWidth="6" strokeLinecap="round"
                strokeDasharray="150.8" strokeDashoffset={ringOff}
                transform="rotate(-90 28 28)" />
              <text x="28" y="32" textAnchor="middle"
                fontFamily="Manrope,sans-serif" fontWeight={700}
                fontSize={13} fill="#001e40">{pct}%</text>
            </svg>
            <div>
              <div style={{ font: `700 14px ${F_HEAD}`, color: "#191c1d" }}>
                매핑 확정 {nDone}/{items.length}</div>
              <div style={{
                font: `500 11px ${F_LABEL}`, color: "#737780", marginTop: 2,
              }}>공시 사례 데이터 · Top-4 적중 99.0%</div>
            </div>
          </div>
          <div style={{
            flex: "none", display: "flex", gap: 4, padding: "10px 12px",
            borderBottom: "1px solid rgba(195,198,209,0.5)",
          }}>
            {([["open", "미결"], ["done", "확정"], ["all", "전체"]] as const)
              .map(([k, lb]) => (
                <span key={k} onClick={() => setFilter(k)} style={{
                  font: `600 11px ${F_LABEL}`, padding: "4px 10px",
                  borderRadius: 8, cursor: "pointer",
                  color: filter === k ? "#001e40" : "#737780",
                  background: filter === k ? "#d5e3ff" : "#edeeef",
                }}>{lb}</span>
              ))}
          </div>
          <div style={{ flex: 1, overflow: "auto" }}>
            {!items.length && (
              <div style={{ padding: 14 }}>
                <div style={{
                  font: `600 12px ${F_LABEL}`, color: "#191c1d",
                  marginBottom: 6,
                }}>계정과목 입력 (한 줄당 "계정명[,구분]")</div>
                <textarea value={input} data-testid="map-input"
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={"현금및현금성자산,BS\n매출채권,BS\n…"}
                  style={{
                    width: "100%", height: 220,
                    font: `500 12px ${F_LABEL}`, padding: 8,
                    border: "1px solid #c3c6d1", borderRadius: 8,
                    resize: "vertical",
                  }} />
                <div style={{ marginTop: 8 }}>
                  <PrimaryBtn onClick={start}>
                    <Icon name="join_inner" size={15} />추천 생성
                  </PrimaryBtn>
                </div>
              </div>
            )}
            {shownIdx.map((i) => {
              const it = items[i];
              const meta = it.decided
                ? { label: "확정", dot: "#3a5a2e" }
                : MAP_STATE_META[it.state] || MAP_STATE_META.manual;
              return (
                <div key={i} className="hoverable" onClick={() => setSel(i)}
                  style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "10px 14px", cursor: "pointer",
                    borderBottom: "1px solid rgba(195,198,209,0.35)",
                    background: sel === i ? "#f3f4f5" : undefined,
                  }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: 9999,
                    background: meta.dot, flex: "none",
                  }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      font: `600 12px ${F_LABEL}`, color: "#191c1d",
                      overflow: "hidden", textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}>{it.account}</div>
                    <div style={{
                      font: `500 11px ${F_LABEL}`, color: "#737780",
                    }}>{it.category || "구분 미지정"}</div>
                  </div>
                  <span style={it.decided
                    ? chip("#3a5a2e", "#dcead2")
                    : chip("#43474f", "#edeeef")}>{meta.label}</span>
                </div>
              );
            })}
            {items.length > 0 && (
              <div style={{ padding: 12 }}>
                <GhostBtn onClick={() => {
                  setMappingId(null);
                  setData(null);
                }}>
                  <Icon name="add" size={15} />새 매핑 작업</GhostBtn>
              </div>
            )}
          </div>
        </div>

        <div style={{ flex: 1, overflow: "auto", padding: 24, maxWidth: 680 }}>
          {cur ? (
            <>
              <div style={{
                display: "flex", alignItems: "baseline", gap: 10,
                marginBottom: 4,
              }}>
                <h2 style={{
                  margin: 0, font: `700 16px ${F_HEAD}`, color: "#191c1d",
                }}>{cur.account}</h2>
                <span style={{
                  font: `500 12px ${F_LABEL}`, color: "#737780",
                }}>{cur.category || ""}</span>
              </div>
              <div style={{
                font: `500 12px ${F_LABEL}`, color: "#737780",
                marginBottom: 14,
              }}>추천은 실증·유사도 기반 후보입니다 — 최종 판단은
                회계사가 확정 버튼으로 기록합니다 (자동 확정 없음)</div>
              <MappingCard key={`${mappingId}:${sel}`} item={cur} onConfirm={(el) => confirm(sel, el)} />
            </>
          ) : (
            <div style={{ font: `500 13px ${F_LABEL}`, color: "#737780" }}>
              좌측에서 계정과목을 입력해 추천을 생성하세요.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function MappingCard({ item, onConfirm }: {
  item: any; onConfirm: (element: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const top = item.candidates?.find((c: any) => c.element.replace("_", ":") === selected)
    || item.candidates?.[0];
  const decided = item.decided;
  const meta = MAP_STATE_META[item.state] || MAP_STATE_META.manual;
  const badges: RecBadge[] = top ? [
    { label: `실증 ${top.firms.toLocaleString()}사`, kind: "corpus" },
    { label: `유사도 ${top.similarity.toFixed(2)}`, kind: "sim" },
    ...(top.industry_boost
      ? [{ label: `동업종 ${top.industry_boost}사`, kind: "peer" as const }]
      : []),
    ...(item.similar_extensions?.length
      ? [{ label: `유사 확장 ${item.similar_extensions[0].firms}사`,
           kind: "ext" as const }] : []),
  ] : [];
  const alts: RecAlt[] = (item.candidates || []).filter((c: any) => c !== top).map((c: any) => ({
    id: c.element.replace("_", ":"), label: c.label,
    rank: item.candidates.indexOf(c) + 1,
    badge: `score ${c.score.toFixed(2)}`,
  }));
  const note = item.state === "standard_recommended"
    ? "확장 실증과 고유사 표준이 동시에 존재 — 불필요 확장 억제를 위해 " +
      "표준 사용을 권장합니다"
    : item.state === "extension_needed"
      ? "적합 표준 없음 — 확장 element 정의 필요" +
        (item.similar_extensions?.length
          ? ` (유사 확장: '${item.similar_extensions[0].label}' ` +
            `${item.similar_extensions[0].firms}사)` : "")
      : item.state === "manual" ? "신호 없음 — 수동 확인 필요" : undefined;

  if (!top && !decided) {
    return (
      <RecCard variant="extension" elementId="[확장 필요]"
        labelKo={item.account} note={note}
        badges={(item.similar_extensions || []).map((e: any) => ({
          label: `유사 확장 '${e.label}' ${e.firms}사`, kind: "ext",
        }))}
        onConfirm={() => onConfirm("[확장]")} />
    );
  }
  return (
    <RecCard
      variant={decided ? "confirmed" : meta.variant}
      elementId={(decided?.element || top.element).replace("_", ":")}
      labelKo={decided ? item.account : top.label}
      badges={badges} alts={alts} note={decided ? undefined : note}
      confirmedBy={decided
        ? `${item.decided_by} ${item.decided_at?.slice(5, 16)}` : undefined}
      onSelect={decided ? undefined : setSelected}
      selectionLabel={!decided && top !== item.candidates?.[0] ? "선택한 대안" : undefined}
      onConfirm={decided ? undefined : () => onConfirm(top.element)} />
  );
}

// ==========================================================================
// 택사노미 체크 (D-4c)
// ==========================================================================
export function TaxoScreen() {
  const { result, job, err, setErr, run } = useStudioJob("taxcheck");
  const [pkg, setPkg] = useState("");
  const [against, setAgainst] = useState("");
  const [versions, setVersions] = useState<string[]>([]);

  useEffect(() => {
    api("/api/studio/taxonomies").then((r) => {
      setVersions(r.versions);
      if (r.versions.length) setAgainst(r.versions[r.versions.length - 1]);
    }).catch(() => {});
  }, []);

  return (
    <div style={{ height: "100%", overflow: "auto" }}>
      <JobBar job={job} />
      <div style={{ padding: 24, maxWidth: 960 }}>
        <ErrorBanner msg={err} />
        <div style={{
          display: "flex", gap: 8, alignItems: "center", marginBottom: 16,
        }}>
          <PathInput value={pkg} onChange={setPkg}
            placeholder="전기 XBRL 패키지 폴더 (dart_explorer 캐시 경로)" />
          <select value={against} onChange={(e) => setAgainst(e.target.value)}
            style={{
              font: `500 12px ${F_LABEL}`, border: "1px solid #c3c6d1",
              borderRadius: 8, padding: "8px 10px", background: "#fff",
            }}>
            {versions.map((v) => <option key={v}>{v}</option>)}
          </select>
          <PrimaryBtn onClick={() => run("/api/studio/taxcheck", {
            prior_package: pkg, against_version: against,
            skip_promotions: true,
          })}>
            <Icon name="fact_check" size={15} />대조 실행</PrimaryBtn>
          <GhostBtn onClick={() => run("/api/studio/taxcheck", {
            prior_package: pkg, against_version: against,
            skip_promotions: false,
          })}>
            <Icon name="trending_up" size={15} />+승격 감지 (수십 분)
          </GhostBtn>
        </div>

        {result && (
          <>
            <div style={{
              display: "flex", alignItems: "center", gap: 8,
              marginBottom: 16, flexWrap: "wrap",
            }}>
              <span style={chip("#3a5a2e", "#dcead2")}>
                녹색(그대로) {result.counts.green}</span>
              <span style={chip("#7a4f00", "#ffecc7")}>
                노랑(폐지) {result.counts.yellow}</span>
              <span style={chip("#4e6874", "#cbe7f5")}>
                파랑(라벨변경) {result.counts.blue}</span>
              <span style={chip("#43474f", "#edeeef")}>
                확장(회사고유) {result.counts.ext}</span>
              {result.promotions != null && (
                <span style={chip("#4e6874", "#cbe7f5")}>
                  승격 감지 {result.promotions}</span>
              )}
              {result.skip_promotions && (
                <span style={{
                  font: `500 11px ${F_LABEL}`, color: "#737780",
                }}>승격 감지 생략됨 — 별도 실행 버튼</span>
              )}
              <div style={{ flex: 1 }} />
              <GhostBtn onClick={() => openFile(result.xlsx_path)}>
                <Icon name="download" size={15} />
                착수 전 체크리스트 엑셀 내보내기</GhostBtn>
            </div>
            <div style={{
              font: `500 12px ${F_LABEL}`, color: "#43474f",
              marginBottom: 14,
            }}>전기 제출파일 대비 {against} 택소노미 대조 — 폐지된
              element에 대체 후보를 제시합니다</div>

            {result.yellow.map((tx: any, i: number) => (
              <Card key={i} style={{ marginBottom: 12 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  marginBottom: 10,
                }}>
                  <span style={chip("#930010", "#ffdad6")}>
                    <Icon name="block" size={13} />폐지</span>
                  <span style={{
                    fontFamily: MONO, fontSize: 12, color: "#930010",
                    textDecoration: "line-through",
                  }}>{tx.element.replace("_", ":")}</span>
                  <span style={{
                    font: `500 12px ${F_LABEL}`, color: "#737780",
                  }}>{tx.label}</span>
                </div>
                {tx.candidates?.length ? (
                  <RecCard variant="recommend"
                    elementId={tx.candidates[0].element.replace("_", ":")}
                    labelKo={tx.candidates[0].label}
                    badges={[{
                      label: `score ${tx.candidates[0].score}`,
                      kind: "sim" }]}
                    alts={tx.candidates.slice(1).map((c: any) => ({
                      id: c.element.replace("_", ":"), label: c.label,
                      badge: `score ${c.score}`,
                    }))} />
                ) : (
                  <div style={{
                    font: `500 12px ${F_LABEL}`, color: "#737780",
                  }}>대체 후보 없음 — 수동 확인</div>
                )}
              </Card>
            ))}
            {!result.yellow.length && (
              <Card><div style={{
                font: `500 13px ${F_LABEL}`, color: "#3a5a2e",
              }}>폐지 element 없음 — 전 element 신버전에서 사용 가능
                (라벨변경 {result.counts.blue}건은 값 영향 없음, 체크리스트
                엑셀에 전체 목록)</div></Card>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// 작성 워크시트 (F-1/F-2/F-3 전 모드)
// ==========================================================================
export function WorksheetScreen({ presetDsd }: {
  presetDsd?: string | null;
}) {
  const { result, job, err, setErr, run } =
    useStudioJob("worksheet");
  const [dsd, setDsd] = useState(presetDsd || "");
  const [report, setReport] = useState("annual");
  const [mode, setMode] = useState<"new" | "inherit">("new");
  const [inheritPkg, setInheritPkg] = useState("");
  const [notes, setNotes] = useState(false);
  const [sheet, setSheet] = useState<string>("");

  const grids: any[] = result?.grids || [];
  const curGrid = grids.find((g) => g.sheet === sheet) || grids[1] || grids[0];
  const sm = result?.summary;

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%", minHeight: 0,
    }}>
      <JobBar job={job} />
      <div style={{
        flex: "none", display: "flex", alignItems: "center", gap: 8,
        padding: "12px 24px", background: "#fff",
        borderBottom: "1px solid #c3c6d1", flexWrap: "wrap", rowGap: 8,
      }}>
        <PathInput value={dsd} onChange={setDsd} width={340}
          placeholder="회사 DSD 경로" />
        <select value={report} onChange={(e) => setReport(e.target.value)}
          style={{
            font: `500 12px ${F_LABEL}`, border: "1px solid #c3c6d1",
            borderRadius: 8, padding: "8px 10px", background: "#fff",
          }}>
          {["annual", "half", "q1", "q3"].map((r) => (
            <option key={r} value={r}>{
              { annual: "연간", half: "반기", q1: "1분기", q3: "3분기",
              }[r]}</option>
          ))}
        </select>
        <select value={mode} onChange={(e) =>
          setMode(e.target.value as any)} style={{
            font: `500 12px ${F_LABEL}`, border: "1px solid #c3c6d1",
            borderRadius: 8, padding: "8px 10px", background: "#fff",
          }}>
          <option value="new">신규 (공시 사례 추천)</option>
          <option value="inherit">승계 (기말 태깅 이어받기)</option>
        </select>
        {mode === "inherit" && (
          <PathInput value={inheritPkg} onChange={setInheritPkg} width={300}
            placeholder="자기 기말 XBRL 패키지 폴더" />
        )}
        <label style={{
          display: "inline-flex", alignItems: "center", gap: 5,
          font: `500 12px ${F_LABEL}`, color: "#43474f",
        }}>
          <input type="checkbox" checked={notes}
            onChange={(e) => setNotes(e.target.checked)}
            style={{ accentColor: "#001e40" }} />
          주석 포함 (수 분 소요)
        </label>
        <PrimaryBtn onClick={() => run("/api/studio/worksheet", {
          dsd_path: dsd, report, mode,
          inherit_package: mode === "inherit" ? inheritPkg : undefined,
          include_notes: notes,
        })}>
          <Icon name="edit_note" size={15} />전사 가이드 생성</PrimaryBtn>
      </div>

      <div style={{ padding: err ? "0 24px" : 0 }}>
        <ErrorBanner msg={err} /></div>

      {result && (
        <>
          <div style={{
            flex: "none", display: "flex", alignItems: "center", gap: 8,
            padding: "10px 24px", background: "#fff",
            borderBottom: "1px solid #c3c6d1", flexWrap: "wrap",
          }}>
            {grids.map((g) => (
              <span key={g.sheet} onClick={() => setSheet(g.sheet)} style={{
                font: `600 12px ${F_LABEL}`, padding: "5px 11px",
                borderRadius: 8, cursor: "pointer",
                color: curGrid?.sheet === g.sheet ? "#001e40" : "#737780",
                background: curGrid?.sheet === g.sheet
                  ? "#d5e3ff" : "transparent",
              }}>{g.sheet}</span>
            ))}
            <div style={{ flex: 1 }} />
            <span style={{
              font: `500 12px ${F_LABEL}`, color: "#43474f",
              fontVariantNumeric: "tabular-nums",
            }}>
              작성 개요: 항목 {sm.rows} · 매핑 {sm.mapped} · 확장 후보{" "}
              {sm.extension_candidates}
              {sm.mode === "inherit" && ` · 승계 ${sm.inherited} · ` +
                `신규 계정 ${sm.new_accounts} · 폐지 예정 ${sm.deprecated}`}
            </span>
            {sm.mode === "inherit" && (
              <span style={chip("#001e40", "#d5e3ff")}>승계 모드</span>
            )}
            <GhostBtn onClick={() => openFile(result.xlsx_path)}>
              <Icon name="download" size={15} />엑셀 열기</GhostBtn>
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "16px 24px" }}>
            {curGrid && <GridTable rows={curGrid.rows} />}
            <div style={{
              font: `500 11px ${F_LABEL}`, color: "#737780", marginTop: 10,
            }}>검색어를 복사해 DART 편집기 요소 검색창에 붙여넣으십시오 —
              확정 ☐ 전부 체크 전까지 미완성입니다. 화면은 산출 xlsx를
              그대로 표시합니다.</div>
          </div>
        </>
      )}
      {!result && !job && (
        <div style={{
          padding: 24, font: `500 13px ${F_LABEL}`, color: "#737780",
        }}>DSD와 보고서 유형·모드를 지정해 전사 가이드를
          생성하세요. 승계 모드는 자기 기말 인스턴스의 element·확장·role을
          그대로 잇고 신규 계정에만 공시 사례 추천이 작동합니다.</div>
      )}
    </div>
  );
}

// ==========================================================================
// 차원 표 뷰어 (D-2) — 화면 = 산출 xlsx
// ==========================================================================
export function DimScreen() {
  const { result, job, err, setErr, run } = useStudioJob("dimtable");
  const [pkg, setPkg] = useState("");
  const [role, setRole] = useState("");
  const [sheet, setSheet] = useState("");

  const grids: any[] = result?.grids || [];
  const cur = grids.find((g) => g.sheet === sheet) || grids[0];

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%", minHeight: 0,
    }}>
      <JobBar job={job} />
      <div style={{
        flex: "none", display: "flex", alignItems: "center", gap: 8,
        padding: "12px 24px", background: "#fff",
        borderBottom: "1px solid #c3c6d1",
      }}>
        <PackagePicker onPick={setPkg} />
        <PathInput value={pkg} onChange={setPkg}
          placeholder="XBRL 패키지 폴더 (dart_explorer 캐시)" />
        <PathInput value={role} onChange={setRole} width={160}
          placeholder="role 필터 (예: D310000)" />
        <PrimaryBtn onClick={() => run("/api/studio/dimtable", {
          package_path: pkg, role: role || undefined,
        })}>
          <Icon name="pivot_table_chart" size={15} />렌더</PrimaryBtn>
        <div style={{ flex: 1 }} />
        {result && (
          <>
            <span style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
              화면은 산출 엑셀 재독(값 동일 보장)</span>
            <GhostBtn onClick={() => openFile(result.xlsx_path)}>
              <Icon name="download" size={15} />엑셀 열기</GhostBtn>
          </>
        )}
      </div>
      <div style={{ padding: err ? "0 24px" : 0 }}>
        <ErrorBanner msg={err} /></div>
      {result && (
        <div style={{
          flex: "none", display: "flex", gap: 6, padding: "10px 24px",
          background: "#fff", borderBottom: "1px solid #c3c6d1",
          flexWrap: "wrap",
        }}>
          {grids.map((g) => (
            <span key={g.sheet} onClick={() => setSheet(g.sheet)} style={{
              font: `600 12px ${F_LABEL}`, padding: "5px 11px",
              borderRadius: 8, cursor: "pointer",
              color: cur?.sheet === g.sheet ? "#001e40" : "#737780",
              background: cur?.sheet === g.sheet ? "#d5e3ff" : "transparent",
            }}>{g.sheet}</span>
          ))}
        </div>
      )}
      <div style={{ flex: 1, overflow: "auto", padding: "16px 24px" }}>
        {cur ? <GridTable rows={cur.rows} /> : !job && (
          <div style={{ font: `500 13px ${F_LABEL}`, color: "#737780" }}>
            패키지 폴더를 지정해 Role별 차원 표를 렌더하세요.</div>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// 트리 뷰 (D-1)
// ==========================================================================
export function TreeScreen() {
  const { result, job, err, setErr, run } = useStudioJob("taxtree");
  const [pkg, setPkg] = useState("");
  const [role, setRole] = useState("");

  const roleWithRows = (result?.roles || []).find((r: any) => r.rows);
  const rows: any[] = roleWithRows?.rows || [];

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%", minHeight: 0,
    }}>
      <JobBar job={job} />
      <div style={{
        flex: "none", display: "flex", alignItems: "center", gap: 10,
        padding: "12px 24px", background: "#fff",
        borderBottom: "1px solid #c3c6d1",
      }}>
        <PackagePicker onPick={setPkg} />
        <PathInput value={pkg} onChange={setPkg}
          placeholder="XBRL 패키지 폴더 또는 taxonomies 버전 폴더" />
        <PathInput value={role} onChange={setRole} width={160}
          placeholder="role 필터 (예: D210000)" />
        <PrimaryBtn onClick={() => run("/api/studio/taxtree", {
          package_path: pkg, role: role || undefined,
        })}>
          <Icon name="account_tree" size={15} />트리 로드</PrimaryBtn>
        <div style={{ flex: 1 }} />
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 5,
          font: `500 11px ${F_LABEL}`, color: "#930010",
          background: "#ffdad6", borderRadius: 4, padding: "3px 8px",
        }}>빨간 표시 = 확장 element</span>
      </div>
      <div style={{ padding: err ? "0 24px" : 0 }}>
        <ErrorBanner msg={err} /></div>
      <div style={{ flex: 1, overflow: "auto", padding: "16px 24px" }}>
        {roleWithRows && (
          <div style={{
            font: `600 12px ${F_LABEL}`, color: "#43474f", marginBottom: 8,
          }}>{roleWithRows.definition}
            <span style={{ color: "#737780", fontWeight: 500 }}>
              {" "}— 아크 {result.arcs ?? "?"} · 확장 {result.extensions}
            </span></div>
        )}
        {rows.length > 0 ? (
          <div style={{
            background: "#fff", border: "1px solid #c3c6d1",
            borderRadius: 8, maxWidth: 860, padding: "8px 0",
          }}>
            {rows.map((t, i) => (
              <div key={i} className="hoverable" style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: `4px 14px 4px ${14 + t.depth * 22}px`,
              }}>
                <Icon size={15} color="#c3c6d1"
                  name={t.depth === 0 ? "account_tree"
                    : "subdirectory_arrow_right"} />
                <span style={{
                  font: `${t.depth <= 1 ? 600 : 500} 12px ${F_LABEL}`,
                  color: t.ext ? "#930010" : "#191c1d",
                }}>{t.ko}</span>
                <span style={{
                  fontFamily: MONO, fontSize: 10, color: "#737780",
                  overflow: "hidden", textOverflow: "ellipsis",
                  whiteSpace: "nowrap", flex: 1,
                }}>{t.prefix}:{t.id}</span>
                {t.ext && (
                  <span style={{
                    font: `600 9px ${F_LABEL}`, color: "#930010",
                    background: "#ffdad6", borderRadius: 4,
                    padding: "2px 6px", flex: "none",
                  }}>확장</span>
                )}
              </div>
            ))}
          </div>
        ) : !job && (
          <div style={{ font: `500 13px ${F_LABEL}`, color: "#737780" }}>
            패키지 폴더와 role 필터를 지정해 presentation 트리를
            로드하세요.</div>
        )}
      </div>
    </div>
  );
}
