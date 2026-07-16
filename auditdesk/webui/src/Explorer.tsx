// DART Explorer 3화면 — 공시 검색 · XBRL 파이프라인 · 설정 (참조 구현 이식)
import React, { useEffect, useRef, useState } from "react";
import { api, Job, pollJob } from "./api";
import {
  Card, chip, ErrorBanner, F_HEAD, F_LABEL, GhostBtn, Icon, MONO,
  PrimaryBtn,
} from "./ui";

const REPORT_CHIPS: [string, string][] = [
  ["annual", "사업보고서"], ["half", "반기보고서"], ["q1", "분기(1Q)"],
  ["q3", "분기(3Q)"],
];

// ==========================================================================
// 공시 검색
// ==========================================================================
export function SearchScreen({ goXbrl }: {
  goXbrl: (corp: string, year: number, report: string) => void;
}) {
  const [q, setQ] = useState("");
  const [sug, setSug] = useState<any[]>([]);
  const [picked, setPicked] = useState<any>(null);
  const [type, setType] = useState<string | null>("annual");
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const debounce = useRef<any>(null);

  // 딥링크: #/search/<회사명> — 진입 시 자동 검색 (헤드리스 증빙 겸용)
  useEffect(() => {
    const seg = window.location.hash.replace(/^#\/?/, "").split("/");
    if (seg[0] === "search" && seg[1]) {
      const name = decodeURIComponent(seg[1]);
      setQ(name);
      (async () => {
        try {
          const r = await api(`/api/explorer/search?corp=${
            encodeURIComponent(name)}&type=annual`);
          setRes(r);
        } catch { /* 자동 검색 실패는 무시 */ }
      })();
    }
  }, []);

  // 자동완성 (corpCode 캐시)
  useEffect(() => {
    if (picked || q.trim().length < 2) { setSug([]); return; }
    clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      api(`/api/explorer/corps?q=${encodeURIComponent(q)}`)
        .then((r) => setSug(r.corps)).catch(() => {});
    }, 250);
  }, [q, picked]);

  const search = async () => {
    setErr("");
    setBusy(true);
    try {
      const corp = picked?.corp_code || q;
      const r = await api(`/api/explorer/search?corp=${
        encodeURIComponent(corp)}${type ? `&type=${type}` : ""}`);
      setRes(r);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 1080 }}>
      <Card style={{
        display: "flex", flexDirection: "column", gap: 12,
      }}>
        <div style={{ display: "flex", gap: 10, position: "relative" }}>
          <div style={{
            flex: 1, display: "flex", alignItems: "center", gap: 8,
            border: "1px solid #c3c6d1", borderRadius: 8,
            padding: "9px 12px", background: "#fff", position: "relative",
          }}>
            <Icon name="search" size={18} color="#737780" />
            <input value={q} data-testid="search-input"
              onChange={(e) => { setQ(e.target.value); setPicked(null); }}
              placeholder="회사명 또는 corp_code (8자리)"
              style={{
                flex: 1, border: "none", outline: "none",
                font: `500 13px ${F_LABEL}`, color: "#191c1d",
              }} />
            {picked && (
              <span style={{
                font: `500 11px ${F_LABEL}`, background: "#d5e3ff",
                borderRadius: 4, padding: "2px 6px", color: "#001e40",
              }}>corpCode 캐시 일치 · {picked.corp_code}</span>
            )}
            {sug.length > 0 && (
              <div style={{
                position: "absolute", top: "105%", left: 0, right: 0,
                background: "#fff", border: "1px solid #c3c6d1",
                borderRadius: 8, zIndex: 20, overflow: "hidden",
                boxShadow: "0 8px 20px rgba(0,0,0,0.08)",
              }}>
                {sug.map((c) => (
                  <div key={c.corp_code} className="hoverable"
                    onClick={() => {
                      setPicked(c); setQ(c.corp_name); setSug([]);
                    }} style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "8px 12px", cursor: "pointer",
                      font: `500 12px ${F_LABEL}`, color: "#191c1d",
                    }}>
                    <span style={{ flex: 1 }}>{c.corp_name}</span>
                    {c.stock_code && (
                      <span style={chip("#4e6874", "#cbe7f5")}>
                        상장 {c.stock_code}</span>
                    )}
                    <span style={{
                      fontFamily: MONO, fontSize: 11, color: "#737780",
                    }}>{c.corp_code}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <PrimaryBtn onClick={search} disabled={busy}>
            {busy ? "검색 중…" : "검색"}</PrimaryBtn>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{
            font: `600 11px ${F_LABEL}`, color: "#737780", marginRight: 2,
          }}>보고서 유형</span>
          {REPORT_CHIPS.map(([k, lb]) => (
            <span key={k} onClick={() => setType(type === k ? null : k)}
              style={{
                font: `600 11px ${F_LABEL}`, padding: "4px 10px",
                borderRadius: 8, cursor: "pointer",
                color: type === k ? "#001e40" : "#737780",
                background: type === k ? "#d5e3ff" : "#edeeef",
              }}>{lb}</span>
          ))}
          <div style={{ flex: 1 }} />
          {res?.induty && (
            <span style={{ font: `500 11px ${F_LABEL}`, color: "#737780" }}>
              업종코드: {res.induty}</span>
          )}
        </div>
      </Card>

      <ErrorBanner msg={err} />

      {res && (
        <table style={{
          width: "100%", borderCollapse: "collapse", marginTop: 16,
          background: "#fff", border: "1px solid #c3c6d1",
        }}>
          <thead><tr>
            {["회사", "보고서명", "접수일", "rcept_no", "액션"].map(
              (h, i) => (
                <th key={h} style={{
                  textAlign: i === 4 ? "right" : "left",
                  font: `700 11px ${F_LABEL}`, color: "#737780",
                  borderBottom: "1px solid #c3c6d1",
                  padding: i === 0 ? "9px 14px" : "9px 10px",
                }}>{h}</th>
              ))}
          </tr></thead>
          <tbody>
            {res.docs.map((d: any) => (
              <tr key={d.rcept_no}>
                <td style={{
                  font: `600 12px ${F_LABEL}`, color: "#191c1d",
                  padding: "9px 14px",
                  borderBottom: "1px solid rgba(195,198,209,0.4)",
                }}>{d.corp_name}</td>
                <td style={{
                  font: `500 12px ${F_LABEL}`, color: "#43474f",
                  padding: "9px 10px",
                  borderBottom: "1px solid rgba(195,198,209,0.4)",
                }}>
                  {d.report_nm}
                  {d.cached && (
                    <span data-testid="cache-badge" style={{
                      ...chip("#3a5a2e", "#dcead2"), marginLeft: 6,
                      fontSize: 10, padding: "2px 6px",
                    }}><Icon name="check" size={11} />캐시</span>
                  )}
                </td>
                <td style={{
                  font: `500 12px ${F_LABEL}`, color: "#43474f",
                  padding: "9px 10px",
                  borderBottom: "1px solid rgba(195,198,209,0.4)",
                  fontVariantNumeric: "tabular-nums",
                }}>{d.rcept_dt}</td>
                <td style={{
                  fontFamily: MONO, fontSize: 11, color: "#737780",
                  padding: "9px 10px",
                  borderBottom: "1px solid rgba(195,198,209,0.4)",
                }}>{d.rcept_no}</td>
                <td style={{
                  textAlign: "right", padding: "9px 14px",
                  borderBottom: "1px solid rgba(195,198,209,0.4)",
                }}>
                  <button className="hoverable" onClick={() => {
                    const m = (d.report_nm || "").match(/\((\d{4})\./);
                    const y = m ? Number(m[1]) : new Date().getFullYear();
                    const rep = d.report_nm?.includes("반기") ? "half"
                      : d.report_nm?.includes("분기") ? "q1" : "annual";
                    goXbrl(res.corp_code, y, rep);
                  }} style={{
                    font: `600 11px ${F_LABEL}`, color: "#001e40",
                    background: "#d5e3ff", border: "none", borderRadius: 8,
                    padding: "5px 10px", cursor: "pointer",
                  }}>XBRL 파이프라인</button>
                </td>
              </tr>
            ))}
            {!res.docs.length && (
              <tr><td colSpan={5} style={{
                font: `500 12px ${F_LABEL}`, color: "#737780",
                padding: "12px 14px",
              }}>검색 결과 없음</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ==========================================================================
// XBRL 파이프라인
// ==========================================================================
export function XbrlScreen({ preset }: {
  preset?: { corp: string; year: number; report: string } | null;
}) {
  const [corp, setCorp] = useState(preset?.corp || "");
  const [year, setYear] = useState(String(preset?.year ||
    new Date().getFullYear() - 1));
  const [report, setReport] = useState(preset?.report || "annual");
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState("");
  const [steps, setSteps] = useState<{ label: string; state: string }[]>([]);

  useEffect(() => {
    api("/api/jobs?kind=xbrl").then((r) => {
      const last = (r.jobs || []).find((j: Job) =>
        j.state === "done" && j.result);
      if (last) {
        setResult((c: any) => c ?? last.result);
        setSteps((c) => c.length ? c : [1, 2, 3, 4].map((i) => ({
          label: ["접수번호 검색", "XBRL 수신", "압축 해제",
            "팩트 추출 → 엑셀"][i - 1], state: "done",
        })));
      }
    }).catch(() => {});
  }, []);

  const run = async () => {
    setErr("");
    setResult(null);
    const labels = ["접수번호 검색", "XBRL 수신", "압축 해제",
      "팩트 추출 → 엑셀"];
    setSteps(labels.map((l) => ({ label: l, state: "todo" })));
    try {
      const r = await api("/api/explorer/xbrl", {
        method: "POST",
        body: JSON.stringify({ corp, year: Number(year), report }),
      });
      const done = await pollJob(r.job_id, (j) => {
        setJob(j);
        const cur = j.progress?.current || 0;
        setSteps(labels.map((l, i) => ({
          label: l,
          state: i + 1 < cur ? "done" : i + 1 === cur ? "run" : "todo",
        })));
      });
      setJob(null);
      if (done.state === "error") {
        setErr(done.error_detail?.detail || "실패");
        setSteps((s) => s.map((x) =>
          x.state === "run" ? { ...x, state: "fail" } : x));
      } else {
        setResult(done.result);
        setSteps(labels.map((l) => ({ label: l, state: "done" })));
      }
    } catch (e: any) {
      setJob(null);
      setErr(e.message);
    }
  };

  return (
    <div style={{
      padding: 24, maxWidth: 900, display: "flex",
      flexDirection: "column", gap: 16,
    }}>
      <Card style={{ padding: 20 }}>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{
              font: `600 11px ${F_LABEL}`, color: "#737780",
              marginBottom: 5,
            }}>회사 (이름 또는 corp_code)</div>
            <input value={corp} data-testid="xbrl-corp"
              onChange={(e) => setCorp(e.target.value)} style={{
                width: "100%", border: "1px solid #c3c6d1",
                borderRadius: 8, padding: "8px 12px",
                font: `500 13px ${F_LABEL}`, color: "#191c1d",
              }} />
          </div>
          <div style={{ width: 110 }}>
            <div style={{
              font: `600 11px ${F_LABEL}`, color: "#737780",
              marginBottom: 5,
            }}>사업연도</div>
            <input value={year} onChange={(e) => setYear(e.target.value)}
              style={{
                width: "100%", border: "1px solid #c3c6d1",
                borderRadius: 8, padding: "8px 12px",
                font: `500 13px ${F_LABEL}`,
                fontVariantNumeric: "tabular-nums",
              }} />
          </div>
          <div style={{ width: 140 }}>
            <div style={{
              font: `600 11px ${F_LABEL}`, color: "#737780",
              marginBottom: 5,
            }}>보고서</div>
            <select value={report}
              onChange={(e) => setReport(e.target.value)} style={{
                width: "100%", border: "1px solid #c3c6d1",
                borderRadius: 8, padding: "8px 10px",
                font: `500 13px ${F_LABEL}`, background: "#fff",
              }}>
              {REPORT_CHIPS.map(([k, lb]) => (
                <option key={k} value={k}>{lb}</option>
              ))}
            </select>
          </div>
          <PrimaryBtn onClick={run}>
            <Icon name="play_arrow" size={16} />실행</PrimaryBtn>
        </div>
      </Card>

      <ErrorBanner msg={err} />

      {steps.length > 0 && (
        <Card style={{ padding: 20 }}>
          <div style={{
            font: `700 13px ${F_HEAD}`, color: "#191c1d", marginBottom: 14,
          }}>실행 스텝 {job ? "— 진행 중" : ""}</div>
          {steps.map((x, i) => (
            <div key={x.label} style={{ display: "flex", gap: 12 }}>
              <div style={{
                display: "flex", flexDirection: "column",
                alignItems: "center", flex: "none", width: 22,
              }}>
                <div style={{
                  width: 20, height: 20, borderRadius: 9999,
                  display: "flex", alignItems: "center",
                  justifyContent: "center",
                  color: x.state === "todo" ? "#737780" : "#fff",
                  background: x.state === "done" ? "#001e40"
                    : x.state === "run"
                      ? "linear-gradient(90deg,#001e40,#003366)"
                      : x.state === "fail" ? "#ba1a1a" : "#e1e3e4",
                }}>
                  <Icon size={13} name={x.state === "done" ? "check"
                    : x.state === "run" ? "progress_activity"
                      : x.state === "fail" ? "close"
                        : "radio_button_unchecked"} />
                </div>
                {i < steps.length - 1 && (
                  <div style={{
                    width: 2, flex: 1, background: "#c3c6d1", minHeight: 14,
                  }} />
                )}
              </div>
              <div style={{ paddingBottom: 14 }}>
                <span style={{
                  font: `600 12px ${F_LABEL}`, color: "#191c1d",
                }}>{x.label}</span>
                {x.state === "run" && job?.progress?.message && (
                  <span style={{
                    font: `500 11px ${F_LABEL}`, color: "#737780",
                    marginLeft: 8,
                  }}>{job.progress.message}</span>
                )}
              </div>
            </div>
          ))}
        </Card>
      )}

      {result && (
        <Card style={{ padding: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
            <div>
              <div style={{
                font: `700 28px ${F_HEAD}`, color: "#001e40",
                fontVariantNumeric: "tabular-nums",
              }}>{result.facts?.toLocaleString()}</div>
              <div style={{
                font: `500 11px ${F_LABEL}`, color: "#737780", marginTop: 3,
              }}>추출 팩트</div>
            </div>
            <div style={{ width: 1, height: 36, background: "#c3c6d1" }} />
            <div style={{ minWidth: 0 }}>
              <div style={{
                font: `600 12px ${F_LABEL}`, color: "#191c1d",
              }}>{result.report_nm}</div>
              <div style={{
                fontFamily: MONO, fontSize: 11, color: "#737780",
                marginTop: 3,
              }}>rcept {result.rcept_no} · {result.corp_code}</div>
            </div>
            <div style={{ flex: 1 }} />
            <GhostBtn onClick={() => api("/api/fs/open", {
              method: "POST",
              body: JSON.stringify({ path: result.xlsx_path }),
            })}>
              <Icon name="table" size={15} />산출 엑셀 열기</GhostBtn>
          </div>
        </Card>
      )}
    </div>
  );
}

// ==========================================================================
// 설정 (+ 코퍼스 카드)
// ==========================================================================
export function SettingsScreen() {
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [job, setJob] = useState<Job | null>(null);

  const reload = () => {
    api("/api/explorer/settings").then(setS).catch((e) =>
      setErr(e.message));
  };
  useEffect(reload, []);

  const clearCache = async () => {
    if (!window.confirm(
      "공시 캐시를 전부 비웁니다. 재다운로드는 가능하지만 OpenDART 일 " +
      "요청 한도를 소모합니다. 계속할까요?")) return;
    try {
      const r = await api("/api/explorer/cache?confirm=DELETE", {
        method: "DELETE",
      });
      setMsg(`캐시 ${r.cleared}개 항목 삭제됨`);
      reload();
    } catch (e: any) { setErr(e.message); }
  };

  const buildCorpus = async () => {
    if (!window.confirm(
      "코퍼스 갱신은 상장사 전체를 순회하며 수 시간 + 일 요청 한도를 " +
      "대량 소모합니다. 재개(resume) 로직으로 이어서 실행됩니다. " +
      "시작할까요?")) return;
    setErr("");
    try {
      const r = await api("/api/explorer/corpus/build", {
        method: "POST", body: JSON.stringify({}),
      });
      const done = await pollJob(r.job_id, setJob);
      setJob(null);
      if (done.state === "error")
        setErr(done.error_detail?.detail || "실패");
      else setMsg(`코퍼스 빌드 완료: ${JSON.stringify(done.result)}`);
      reload();
    } catch (e: any) { setJob(null); setErr(e.message); }
  };

  if (!s) return <div style={{ padding: 24 }}><ErrorBanner msg={err} /></div>;

  const usagePct = s.daily_limit
    ? Math.min(100, Math.round((s.today_usage || 0) / s.daily_limit * 100))
    : 0;

  return (
    <div style={{
      padding: 24, maxWidth: 640, display: "flex",
      flexDirection: "column", gap: 12,
    }}>
      {job && (
        <div style={{
          display: "flex", gap: 10, padding: "10px 14px",
          background: "#d5e3ff", borderRadius: 8,
          font: `600 12px ${F_LABEL}`, color: "#001e40",
        }}>
          <Icon name="progress_activity" size={16} />
          코퍼스 빌드 — {job.progress?.message || job.state}
        </div>
      )}
      <ErrorBanner msg={err} />
      {msg && <div style={{
        font: `500 12px ${F_LABEL}`, color: "#3a5a2e",
        background: "#dcead2", borderRadius: 8, padding: "10px 12px",
      }}>{msg}</div>}

      <Card style={{
        padding: 18, display: "flex", alignItems: "center", gap: 12,
      }}>
        <Icon name="key" size={20}
          color={s.api_key_set ? "#3a5a2e" : "#930010"} />
        <div style={{ flex: 1 }}>
          <div style={{ font: `600 13px ${F_LABEL}`, color: "#191c1d" }}>
            OpenDART API 키</div>
          <div style={{
            font: `500 11px ${F_LABEL}`, color: "#737780", marginTop: 2,
          }}>{s.api_key_set
            ? ".env에서 감지됨 — 키 값은 표시하지 않습니다"
            : "미설정 — dart_explorer/.env에 OPENDART_API_KEY를 저장하세요"}
          </div>
        </div>
        <span style={s.api_key_set
          ? chip("#3a5a2e", "#dcead2") : chip("#930010", "#ffdad6")}>
          <Icon name={s.api_key_set ? "check" : "warning"} size={13} />
          {s.api_key_set ? "설정됨" : "미설정"}</span>
      </Card>

      <Card style={{
        padding: 18, display: "flex", alignItems: "center", gap: 12,
      }}>
        <Icon name="database" size={20} color="#48626e" />
        <div style={{ flex: 1 }}>
          <div style={{ font: `600 13px ${F_LABEL}`, color: "#191c1d" }}>
            공시 캐시</div>
          <div style={{
            font: `500 11px ${F_LABEL}`, color: "#737780", marginTop: 2,
            fontVariantNumeric: "tabular-nums",
          }}>{s.cache_files.toLocaleString()}파일 ·{" "}
            {(s.cache_size_mb / 1024).toFixed(2)} GB · {s.cache_path}</div>
        </div>
        <button className="hoverable" onClick={clearCache} style={{
          font: `600 12px ${F_LABEL}`, color: "#ba1a1a", background: "#fff",
          border: "1px solid #c3c6d1", borderRadius: 8, padding: "7px 12px",
          cursor: "pointer",
        }}>비우기</button>
      </Card>

      <Card style={{
        padding: 18, display: "flex", alignItems: "center", gap: 12,
      }}>
        <Icon name="speed" size={20} color="#48626e" />
        <div style={{ flex: 1 }}>
          <div style={{ font: `600 13px ${F_LABEL}`, color: "#191c1d" }}>
            일 사용량 (추정)</div>
          <div style={{
            font: `500 11px ${F_LABEL}`, color: "#737780", marginTop: 2,
            fontVariantNumeric: "tabular-nums",
          }}>{(s.today_usage ?? 0).toLocaleString()} /{" "}
            {(s.daily_limit ?? 20000).toLocaleString()} 요청</div>
        </div>
        <div style={{
          width: 160, height: 6, background: "#e1e3e4",
          borderRadius: 9999, overflow: "hidden",
        }}>
          <div style={{
            width: `${usagePct}%`, minWidth: 4, height: "100%",
            background: "linear-gradient(90deg,#001e40,#003366)",
          }} />
        </div>
      </Card>

      <Card style={{
        padding: 18, display: "flex", alignItems: "center", gap: 12,
      }}>
        <Icon name="sync" size={20} color="#48626e" />
        <div style={{ flex: 1 }}>
          <div style={{ font: `600 13px ${F_LABEL}`, color: "#191c1d" }}>
            벤치마크 코퍼스</div>
          <div style={{
            font: `500 11px ${F_LABEL}`, color: "#737780", marginTop: 2,
            fontVariantNumeric: "tabular-nums",
          }}>ok {(s.corpus?.ok ?? 0).toLocaleString()}사 · 처리{" "}
            {(s.corpus?.processed ?? 0).toLocaleString()}사 · D-3b Top-4
            홀드아웃 99.0%</div>
        </div>
        <GhostBtn onClick={buildCorpus}>
          <Icon name="sync" size={15} />갱신 실행 (재개)</GhostBtn>
      </Card>
    </div>
  );
}
