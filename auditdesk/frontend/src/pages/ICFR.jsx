import { useState, useEffect, useRef, useMemo } from "react";
import { api } from "../api.js";
import { STATUS } from "../constants.js";
import { StatusPill, Icon, Spinner } from "../components/Tokens.jsx";
import { RcmImportModal } from "./RcmImport.jsx";

// ============================================================
//  필드/컬럼 메타데이터
// ============================================================
// 상위(IcfrControl) 필드 / RCM 중첩 필드 구분 — 저장 시 분리에 사용
const TOP_FIELDS = ["code", "process", "description", "ctrl_type", "owner", "due", "status"];
const RCM_FIELDS = ["risk", "objective", "org", "nature", "frequency", "residual_risk",
  "mrc", "ipe", "accounts", "assertions", "test_types", "eval_result", "sample_size", "exception_note"];

const ARR_FIELDS = ["accounts", "assertions", "test_types"];
const BOOL_FIELDS = ["mrc", "ipe"];
const LONG_FIELDS = ["risk", "description", "objective", "exception_note"];

const FIELD_LABEL = {
  code: "통제활동번호", process: "프로세스", description: "통제활동명", ctrl_type: "평가유형",
  client: "클라이언트", owner: "담당자(책임자)", due: "완료일", status: "테스트상태",
  risk: "위험(Risk)", objective: "통제목적", org: "수행조직", nature: "예방/적발",
  frequency: "통제주기", residual_risk: "잔여위험", mrc: "핵심통제(Key/MRC)", ipe: "IPE",
  accounts: "계정과목", assertions: "경영자주장", test_types: "테스트유형",
  sample_size: "표본크기", eval_result: "평가결과", exception_note: "미비점/이슈",
};

// 상세 패널 섹션 (요청 순서)
const SECTIONS = [
  { key: "process",  label: "프로세스",   fields: ["process"] },
  { key: "risk",     label: "리스크",     fields: ["risk", "objective"] },
  { key: "control",  label: "통제활동",   fields: ["code", "description", "client", "ctrl_type"] },
  { key: "mrcipe",   label: "MRC·IPE",   fields: ["mrc", "ipe"] },
  { key: "org",      label: "통제조직",   fields: ["owner", "org"] },
  { key: "ctype",    label: "통제유형",   fields: ["nature", "frequency"] },
  { key: "accounts", label: "계정과목",   fields: ["accounts"] },
  { key: "assert",   label: "경영자주장", fields: ["assertions"] },
  { key: "residual", label: "잔여위험",   fields: ["residual_risk"] },
  { key: "test",     label: "테스트",     fields: ["status", "due", "test_types", "sample_size", "eval_result", "exception_note"] },
];

// 테이블 컬럼 (순서 = 표시 순서). core=기본 표시, required=항상 표시(끌 수 없음)
const COLUMNS = [
  { key: "code",          label: "통제활동번호", width: 124, filter: "text",   core: true, required: true, strong: true },
  { key: "process",       label: "프로세스",     width: 110, filter: "text",   core: true },
  { key: "description",   label: "통제활동명",   width: 360, filter: "text",   core: true, strong: true, grow: true },
  { key: "accounts",      label: "계정과목",     width: 160, filter: "text",   core: true },
  { key: "mrc",           label: "Key CA",       width: 78,  filter: "select", options: ["Y", "N"], core: true, center: true },
  { key: "nature",        label: "통제유형",     width: 96,  filter: "text",   core: true },
  { key: "owner",         label: "담당자",       width: 96,  filter: "text",   core: true },
  { key: "status",        label: "테스트상태",   width: 120, filter: "select", options: ["미착수", "진행중", "검토대기", "완료", "예외발견"], core: true },
  { key: "ctrl_type",     label: "평가유형",     width: 90,  filter: "select", options: ["설계", "운영"] },
  { key: "client",        label: "클라이언트",   width: 130, filter: "select" },
  { key: "due",           label: "마감",         width: 100, filter: "text" },
  { key: "risk",          label: "위험(Risk)",   width: 240, filter: "text" },
  { key: "objective",     label: "통제목적",     width: 180, filter: "text" },
  { key: "org",           label: "수행조직",     width: 130, filter: "text" },
  { key: "frequency",     label: "통제주기",     width: 96,  filter: "text" },
  { key: "residual_risk", label: "잔여위험",     width: 96,  filter: "text" },
  { key: "ipe",           label: "IPE",          width: 64,  filter: "select", options: ["Y", "N"], center: true },
  { key: "assertions",    label: "경영자주장",   width: 180, filter: "text" },
  { key: "test_types",    label: "테스트유형",   width: 160, filter: "text" },
  { key: "sample_size",   label: "표본크기",     width: 100, filter: "text" },
  { key: "eval_result",   label: "평가결과",     width: 120, filter: "text" },
  { key: "exception_note",label: "미비점/이슈",  width: 220, filter: "text" },
];
const CORE_KEYS = COLUMNS.filter((c) => c.core).map((c) => c.key);
const ALL_KEYS = COLUMNS.map((c) => c.key);

const LS_COLS = "ln_icfr_cols_v1";
const LS_PRESETS = "ln_icfr_presets_v1";
const LS_DENSITY = "ln_icfr_density_v1";

const pickTop = (ctrl) => Object.fromEntries(TOP_FIELDS.map((k) => [k, ctrl[k]]));

// 그리드 셀 표시용 문자열(필터 비교에도 사용)
function rawValue(key, ctrl, getClientName) {
  if (key === "client") return getClientName(ctrl);
  if (key === "ctrl_type") return ctrl.ctrl_type === "design" ? "설계" : "운영";
  if (key === "status") return (STATUS[ctrl.status] || STATUS.todo).label;
  if (TOP_FIELDS.includes(key)) return ctrl[key] || "";
  const v = ctrl.rcm?.[key];
  if (BOOL_FIELDS.includes(key)) return v ? "Y" : "N";
  if (Array.isArray(v)) return v.join(", ");
  return v || "";
}

// 상세 패널 표시용
function viewValue(field, ctrl, clientName) {
  if (field === "client") return clientName;
  if (field === "ctrl_type") return ctrl.ctrl_type === "design" ? "설계평가" : "운영평가";
  if (field === "status") return (STATUS[ctrl.status] || STATUS.todo).label;
  if (TOP_FIELDS.includes(field)) return ctrl[field] || "";
  const v = ctrl.rcm?.[field];
  if (BOOL_FIELDS.includes(field)) return v ? "예" : "아니오";
  if (Array.isArray(v)) return (v || []).join(" · ");
  return v || "";
}

function KeyBadge() {
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
      style={{ background: "color-mix(in srgb, var(--lnac) 12%, transparent)", color: "var(--lnac)" }}>
      Key
    </span>
  );
}

function renderCell(col, row, getClientName) {
  if (col.key === "status") return <StatusPill k={row.status} />;
  if (col.key === "mrc") return row.rcm?.mrc ? <KeyBadge /> : <span className="text-faint">—</span>;
  if (col.key === "ipe") return row.rcm?.ipe ? <span className="text-ink">Y</span> : <span className="text-faint">—</span>;
  const v = rawValue(col.key, row, getClientName);
  return v || <span className="text-faint">—</span>;
}

// ============================================================
//  상세 패널 (전체 RCM · 섹션 접기/펼치기)
// ============================================================
function FieldRow({ field, ctrl, clientName, editing, form, setForm }) {
  const label = FIELD_LABEL[field] || field;
  const set = (val) => setForm((f) => ({ ...f, [field]: val }));
  const inputCls = "w-full px-3 py-2 rounded-lg bg-[#fafafa] text-[13px] text-ink focus:bg-white transition";

  if (!editing) {
    const v = viewValue(field, ctrl, clientName);
    const empty = v === "" || v == null;
    return (
      <div className="flex gap-3 text-xs">
        <span className="text-faint w-24 shrink-0">{label}</span>
        <span className="text-ink flex-1 break-words whitespace-pre-wrap">
          {empty ? <span className="text-faint">—</span> : v}
        </span>
      </div>
    );
  }

  // --- edit mode (label 위 / 컨트롤 아래) ---
  const wrap = (children) => (
    <div><p className="text-[11px] text-faint mb-1">{label}</p>{children}</div>
  );

  if (field === "client") return wrap(<span className="text-[13px] text-faint">{clientName}</span>);
  if (field === "status")
    return wrap(
      <select value={form.status || "todo"} onChange={(e) => set(e.target.value)} className={inputCls}>
        {["todo", "in_progress", "review", "done", "exception"].map((k) => (
          <option key={k} value={k}>{STATUS[k].label}</option>
        ))}
      </select>
    );
  if (field === "ctrl_type")
    return wrap(
      <select value={form.ctrl_type || "operating"} onChange={(e) => set(e.target.value)} className={inputCls}>
        <option value="design">설계평가</option>
        <option value="operating">운영평가</option>
      </select>
    );
  if (BOOL_FIELDS.includes(field))
    return wrap(
      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={!!form[field]} onChange={(e) => set(e.target.checked)}
          className="w-4 h-4 rounded accent-[color:var(--lnac)]" />
        <span className="text-[13px] text-ink">{form[field] ? "예" : "아니오"}</span>
      </label>
    );
  if (ARR_FIELDS.includes(field))
    return wrap(
      <input value={(form[field] || []).join(", ")}
        onChange={(e) => set(e.target.value.split(/,\s*/).filter(Boolean))}
        placeholder="쉼표로 구분" className={inputCls} />
    );
  if (LONG_FIELDS.includes(field))
    return wrap(
      <textarea value={form[field] || ""} onChange={(e) => set(e.target.value)} rows={3}
        className={inputCls + " resize-none"} />
    );
  return wrap(<input value={form[field] || ""} onChange={(e) => set(e.target.value)} className={inputCls} />);
}

function Section({ sec, ctrl, clientName, editing, form, setForm, open, onToggle }) {
  return (
    <div className="border-b border-line">
      <button onClick={onToggle}
        className="w-full flex items-center justify-between px-6 py-2.5 hover:bg-[#fafafa] transition">
        <span className="text-[11px] font-semibold text-faint tracking-wide uppercase">{sec.label}</span>
        <Icon name="expand_more" className={`text-[18px] text-faint transition-transform ${open ? "" : "-rotate-90"}`} />
      </button>
      {open && (
        <div className="px-6 pb-3.5 flex flex-col gap-2.5">
          {sec.fields.map((f) => (
            <FieldRow key={f} field={f} ctrl={ctrl} clientName={clientName}
              editing={editing} form={form} setForm={setForm} />
          ))}
        </div>
      )}
    </div>
  );
}

function RcmDetail({ ctrl, clientName, onClose, onUpdated }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [openSec, setOpenSec] = useState(() => Object.fromEntries(SECTIONS.map((s) => [s.key, true])));

  useEffect(() => {
    if (ctrl) setForm({ ...pickTop(ctrl), ...ctrl.rcm });
    setEditing(false);
  }, [ctrl?.id]);

  if (!ctrl) return null;

  const save = async () => {
    setSaving(true);
    try {
      const top = {}; TOP_FIELDS.forEach((k) => { top[k] = form[k]; });
      const rcm = {}; RCM_FIELDS.forEach((k) => { rcm[k] = form[k]; });
      const updated = await api.updateIcfr(ctrl.id, { ...top, rcm });
      onUpdated(updated);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const cancel = () => { setForm({ ...pickTop(ctrl), ...ctrl.rcm }); setEditing(false); };

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative ml-auto w-[480px] bg-white border-l border-line flex flex-col h-full shadow-xl overflow-hidden">
        <div className="flex items-start justify-between px-6 py-4 border-b border-line">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-mono font-medium text-ink">{ctrl.code}</span>
              {ctrl.process && <span className="text-xs text-faint truncate">{ctrl.process}</span>}
            </div>
            <p className="text-[15px] font-semibold text-ink mt-1 leading-snug">{ctrl.description || "—"}</p>
            <div className="flex items-center gap-2 mt-2">
              <StatusPill k={ctrl.status} />
              <span className="text-xs text-faint">{ctrl.ctrl_type === "design" ? "설계평가" : "운영평가"}</span>
              {ctrl.rcm?.mrc && <KeyBadge />}
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {!editing && (
              <button onClick={() => setEditing(true)}
                className="px-2.5 py-1 rounded-lg text-xs font-medium text-sub hover:bg-[#f4f4f5] transition flex items-center gap-1">
                <Icon name="edit" className="text-[15px] text-faint" />편집
              </button>
            )}
            <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
              <Icon name="close" className="text-[18px]" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {SECTIONS.map((sec) => (
            <Section key={sec.key} sec={sec} ctrl={ctrl} clientName={clientName}
              editing={editing} form={form} setForm={setForm}
              open={openSec[sec.key]} onToggle={() => setOpenSec((o) => ({ ...o, [sec.key]: !o[sec.key] }))} />
          ))}
        </div>

        {editing && (
          <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-line">
            <button onClick={cancel} className="px-3 py-1.5 rounded-lg text-[13px] font-medium text-sub hover:bg-[#f4f4f5] transition">취소</button>
            <button onClick={save} disabled={saving}
              className="px-3.5 py-1.5 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition disabled:opacity-40"
              style={{ background: "var(--lnac)" }}>
              {saving ? "저장 중…" : "저장"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================
//  컬럼 표시 설정 (체크 토글 + 프리셋)
// ============================================================
function ColumnSettings({ visible, setVisible, presets, setPresets, onClose }) {
  const isOn = (key) => visible.includes(key);
  const toggle = (key) => {
    const col = COLUMNS.find((c) => c.key === key);
    if (col?.required) return;
    setVisible((v) => (v.includes(key) ? v.filter((k) => k !== key) : [...v, key]));
  };
  const savePreset = () => {
    const name = (window.prompt("프리셋 이름") || "").trim();
    if (!name) return;
    setPresets((p) => [...p.filter((x) => x.name !== name), { name, cols: visible }]);
  };
  const visibleCount = COLUMNS.filter((c) => isOn(c.key)).length;

  return (
    <>
      <div className="fixed inset-0 z-[55]" onClick={onClose} />
      <div className="absolute right-0 top-9 z-[56] w-72 bg-white rounded-xl border border-line shadow-xl flex flex-col max-h-[70vh]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <span className="text-xs font-semibold text-ink">표시 컬럼 <span className="text-faint font-normal">({visibleCount})</span></span>
          <div className="flex items-center gap-1">
            <button onClick={() => setVisible(CORE_KEYS)}
              className="text-[11px] text-sub hover:text-ink px-1.5 py-0.5 rounded hover:bg-[#f4f4f5] transition">핵심만</button>
            <button onClick={() => setVisible(ALL_KEYS)}
              className="text-[11px] text-sub hover:text-ink px-1.5 py-0.5 rounded hover:bg-[#f4f4f5] transition">전체</button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-2">
          {SECTIONS.map((sec) => {
            const keys = sec.fields.filter((f) => f !== "client" || true).filter((f) => COLUMNS.some((c) => c.key === f));
            if (keys.length === 0) return null;
            return (
              <div key={sec.key} className="mb-1.5">
                <p className="text-[10px] font-semibold text-faint uppercase tracking-wide px-2 pt-1.5 pb-1">{sec.label}</p>
                {keys.map((key) => {
                  const col = COLUMNS.find((c) => c.key === key);
                  if (!col) return null;
                  return (
                    <label key={key}
                      className={`flex items-center gap-2 px-2 py-1 rounded-lg text-xs transition ${col.required ? "opacity-50 cursor-default" : "cursor-pointer hover:bg-[#f4f4f5]"}`}>
                      <input type="checkbox" checked={isOn(key)} disabled={col.required} onChange={() => toggle(key)}
                        className="w-3.5 h-3.5 rounded accent-[color:var(--lnac)]" />
                      <span className="text-ink">{col.label}</span>
                      {col.required && <span className="text-[10px] text-faint ml-auto">고정</span>}
                    </label>
                  );
                })}
              </div>
            );
          })}
        </div>

        <div className="border-t border-line px-3 py-2.5">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-faint">프리셋</span>
            <button onClick={savePreset}
              className="text-[11px] text-[color:var(--lnac)] hover:opacity-80 transition flex items-center gap-0.5">
              <Icon name="bookmark_add" className="text-[14px]" />현재 저장
            </button>
          </div>
          {presets.length === 0 ? (
            <p className="text-[11px] text-faint py-1">저장된 프리셋이 없습니다</p>
          ) : (
            <div className="flex flex-col gap-0.5">
              {presets.map((p) => (
                <div key={p.name} className="group flex items-center gap-1 rounded-lg hover:bg-[#f4f4f5] transition">
                  <button onClick={() => setVisible(p.cols.includes("code") ? p.cols : ["code", ...p.cols])}
                    className="flex-1 text-left px-2 py-1 text-xs text-ink truncate">
                    {p.name} <span className="text-faint">({p.cols.length})</span>
                  </button>
                  <button onClick={() => setPresets((ps) => ps.filter((x) => x.name !== p.name))}
                    className="opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center text-faint hover:text-[#ef4444] transition shrink-0">
                    <Icon name="close" className="text-[14px]" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// ============================================================
//  ICFR 그리드 (핵심 컬럼 + 가변 표시 + code 좌측고정)
// ============================================================
function IcfrGrid({ rows, getClientName, clientNames, onOpen, visible, setVisible, presets, setPresets, density, setDensity }) {
  const [filters, setFilters] = useState({});
  const [showFilters, setShowFilters] = useState(false);
  const [colOpen, setColOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rowRef = useRef(null);
  const gridRef = useRef(null);

  const cols = useMemo(() => {
    const set = new Set(visible);
    return COLUMNS.filter((c) => c.required || set.has(c.key));
  }, [visible]);

  const colOptions = (col) => (col.key === "client" ? clientNames : col.options || []);

  const filtered = useMemo(() => {
    return rows.filter((row) =>
      cols.every((col) => {
        const f = filters[col.key];
        if (!f) return true;
        const v = String(rawValue(col.key, row, getClientName) ?? "");
        return col.filter === "select" ? v === f : v.toLowerCase().includes(f.toLowerCase());
      })
    );
  }, [rows, filters, cols, getClientName]);

  useEffect(() => { setActive((a) => Math.min(a, Math.max(0, filtered.length - 1))); }, [filtered.length]);
  useEffect(() => { rowRef.current?.scrollIntoView({ block: "nearest" }); }, [active]);

  const onKeyDown = (e) => {
    if (filtered.length === 0) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); if (filtered[active]) onOpen(filtered[active]); }
  };

  const GROW_MIN = 240; // 가변 컬럼(통제활동명)의 최소 폭 — 이 값으로 스크롤 발생 임계 계산
  const totalWidth = cols.reduce((s, c) => s + (c.grow ? GROW_MIN : c.width), 0);
  const hasFilter = Object.values(filters).some(Boolean);
  const rowPadY = density === "compact" ? "py-1" : "py-2";
  const cellText = density === "compact" ? "text-[11px]" : "text-xs";

  const btnSeg = (on) => `px-2 py-1 text-[11px] font-medium transition ${on ? "bg-[#f4f4f5] text-ink" : "text-faint hover:text-sub"}`;

  return (
    <div className="border-t border-line">
      {/* 그리드 툴바 */}
      <div className="flex items-center justify-between gap-2 px-4 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <button onClick={() => setShowFilters((s) => !s)}
            className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium transition ${showFilters || hasFilter ? "bg-[#f4f4f5] text-ink" : "text-faint hover:text-sub"}`}>
            <Icon name="filter_alt" className="text-[14px]" />필터
          </button>
          {hasFilter && (
            <button onClick={() => setFilters({})} className="text-[11px] text-faint hover:text-sub transition flex items-center gap-0.5">
              <Icon name="filter_alt_off" className="text-[14px]" />초기화
            </button>
          )}
          <span className="text-[11px] text-faint truncate hidden md:inline">행 클릭 → 상세 · 방향키 ↑↓ · Enter 상세</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex rounded-lg border border-line overflow-hidden">
            <button onClick={() => setDensity("default")} className={btnSeg(density !== "compact")}>기본</button>
            <button onClick={() => setDensity("compact")} className={btnSeg(density === "compact")}>조밀</button>
          </div>
          <div className="relative">
            <button onClick={() => setColOpen((o) => !o)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-line text-[11px] font-medium text-sub hover:bg-[#fafafa] transition">
              <Icon name="view_column" className="text-[14px] text-faint" />컬럼 설정
              <span className="text-faint">({cols.length})</span>
            </button>
            {colOpen && (
              <ColumnSettings visible={visible} setVisible={setVisible} presets={presets} setPresets={setPresets}
                onClose={() => setColOpen(false)} />
            )}
          </div>
        </div>
      </div>

      <div ref={gridRef} tabIndex={0} onKeyDown={onKeyDown}
        className="overflow-auto max-h-[calc(100vh-360px)] focus:outline-none border-t border-line"
        style={{ position: "relative" }}>
        <table className="w-full border-collapse text-left" style={{ tableLayout: "fixed", minWidth: totalWidth }}>
          <colgroup>
            {cols.map((col) => <col key={col.key} style={col.grow ? undefined : { width: col.width }} />)}
          </colgroup>
          <thead>
            <tr>
              {cols.map((col, ci) => (
                <th key={col.key}
                  className="bg-[#fafafa] border-b border-r border-line px-3 py-2 text-[11px] font-medium text-faint whitespace-nowrap"
                  style={{ position: "sticky", top: 0, zIndex: ci === 0 ? 40 : 30, textAlign: col.center ? "center" : "left",
                    ...(ci === 0 ? { left: 0, boxShadow: "2px 0 0 #e5e7eb" } : {}) }}>
                  {col.label}
                </th>
              ))}
            </tr>
            {showFilters && (
              <tr>
                {cols.map((col, ci) => (
                  <th key={col.key}
                    className="bg-white border-b border-r border-line px-1.5 py-1"
                    style={{ position: "sticky", top: 33, zIndex: ci === 0 ? 40 : 30,
                      ...(ci === 0 ? { left: 0, boxShadow: "2px 0 0 #e5e7eb" } : {}) }}>
                    {col.filter === "select" ? (
                      <select value={filters[col.key] || ""} onChange={(e) => setFilters((f) => ({ ...f, [col.key]: e.target.value }))}
                        className="w-full text-[11px] px-1 py-0.5 rounded border border-line text-sub bg-white focus:ring-0">
                        <option value="">전체</option>
                        {colOptions(col).map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : (
                      <input value={filters[col.key] || ""} onChange={(e) => setFilters((f) => ({ ...f, [col.key]: e.target.value }))}
                        placeholder="필터" className="w-full text-[11px] px-1.5 py-0.5 rounded border border-line text-ink bg-white" />
                    )}
                  </th>
                ))}
              </tr>
            )}
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={cols.length} className="px-4 py-10 text-center text-xs text-faint border-b border-line">조건에 맞는 통제활동이 없습니다</td>
              </tr>
            )}
            {filtered.map((row, ri) => {
              const isActive = ri === active;
              const zebra = ri % 2 === 1;
              const rowBg = isActive ? "#f4f6ff" : zebra ? "#fafafb" : "#ffffff";
              return (
                <tr key={row.id} ref={isActive ? rowRef : null}
                  onClick={() => setActive(ri)} onDoubleClick={() => onOpen(row)}
                  className={`cursor-pointer ${isActive ? "bg-[#f4f6ff]" : zebra ? "bg-[#fafafb] hover:bg-[#f4f6ff]" : "bg-white hover:bg-[#f4f6ff]"}`}>
                  {cols.map((col, ci) => (
                    <td key={col.key}
                      title={col.key === "description" ? (rawValue(col.key, row, getClientName) || undefined) : undefined}
                      className={`border-b border-r border-line px-3 ${rowPadY} ${cellText} whitespace-nowrap overflow-hidden text-ellipsis ${col.strong ? "text-ink" : "text-sub"}`}
                      style={{ ...(col.grow ? {} : { maxWidth: col.width }), textAlign: col.center ? "center" : "left",
                        ...(ci === 0 ? { position: "sticky", left: 0, zIndex: 20, background: rowBg, boxShadow: "2px 0 0 #e5e7eb" } : {}) }}>
                      {renderCell(col, row, getClientName)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
//  통제활동 추가 모달
// ============================================================
function NewCtrlModal({ open, clients, onClose, onCreated }) {
  const [form, setForm] = useState({ client_id: "", code: "", process: "", description: "", ctrl_type: "operating", status: "todo" });
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const submit = async () => {
    if (!form.client_id || !form.code) return;
    setSaving(true);
    try {
      const created = await api.createIcfr({ ...form, client_id: Number(form.client_id) });
      onCreated(created);
      onClose();
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative bg-white rounded-xl border border-line shadow-xl w-full max-w-md flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 pt-6 pb-2">
          <h3 className="text-base font-semibold text-ink">통제활동 추가</h3>
          <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center text-faint hover:bg-[#f4f4f5] transition">
            <Icon name="close" className="text-[18px]" />
          </button>
        </div>
        <div className="px-6 py-4 flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs text-sub mb-1.5 block">번호 *</span>
              <input type="text" placeholder="예: RV-01" value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
            </label>
            <label className="block">
              <span className="text-xs text-sub mb-1.5 block">프로세스</span>
              <input type="text" placeholder="예: 수익" value={form.process} onChange={(e) => setForm((f) => ({ ...f, process: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
            </label>
          </div>
          <label className="block">
            <span className="text-xs text-sub mb-1.5 block">통제 설명</span>
            <input type="text" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink" />
          </label>
          <label className="block">
            <span className="text-xs text-sub mb-1.5 block">클라이언트 *</span>
            <select value={form.client_id} onChange={(e) => setForm((f) => ({ ...f, client_id: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink">
              <option value="">선택</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs text-sub mb-1.5 block">평가유형</span>
              <select value={form.ctrl_type} onChange={(e) => setForm((f) => ({ ...f, ctrl_type: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink">
                <option value="design">설계평가</option>
                <option value="operating">운영평가</option>
              </select>
            </label>
            <label className="block">
              <span className="text-xs text-sub mb-1.5 block">상태</span>
              <select value={form.status} onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-white text-[13px] text-ink">
                {["todo", "in_progress", "done", "exception"].map((k) => (
                  <option key={k} value={k}>{STATUS[k].label}</option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-line">
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-[13px] font-medium text-sub hover:bg-[#f4f4f5] transition">취소</button>
          <button onClick={submit} disabled={saving || !form.client_id || !form.code}
            className="px-3.5 py-1.5 rounded-lg text-white text-[13px] font-medium hover:opacity-90 transition disabled:opacity-40"
            style={{ background: "var(--lnac)" }}>
            {saving ? "추가 중…" : "추가"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
//  ICFR 페이지
// ============================================================
export function ICFR() {
  const [controls, setControls] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [clientFilter, setClientFilter] = useState("all");
  const [openCtrl, setOpenCtrl] = useState(null);
  const [newOpen, setNewOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  // 컬럼 표시 / 프리셋 / 밀도 (localStorage 영속)
  const [visible, setVisible] = useState(() => {
    try { const r = JSON.parse(localStorage.getItem(LS_COLS)); if (Array.isArray(r) && r.length) return r; } catch (e) {}
    return CORE_KEYS;
  });
  const [presets, setPresets] = useState(() => {
    try { const r = JSON.parse(localStorage.getItem(LS_PRESETS)); if (Array.isArray(r)) return r; } catch (e) {}
    return [];
  });
  const [density, setDensity] = useState(() => {
    try { return localStorage.getItem(LS_DENSITY) || "default"; } catch (e) { return "default"; }
  });
  useEffect(() => { try { localStorage.setItem(LS_COLS, JSON.stringify(visible)); } catch (e) {} }, [visible]);
  useEffect(() => { try { localStorage.setItem(LS_PRESETS, JSON.stringify(presets)); } catch (e) {} }, [presets]);
  useEffect(() => { try { localStorage.setItem(LS_DENSITY, density); } catch (e) {} }, [density]);

  const load = async () => {
    const [cs_raw, fys] = await Promise.all([api.getAllIcfr(), api.getFYs()]);
    setControls(cs_raw);
    const cs = [];
    for (const fy of fys) {
      const fyCs = await api.getClients(fy.id);
      cs.push(...fyCs);
    }
    setClients(cs);
  };

  useEffect(() => {
    load().catch(() => {}).finally(() => setLoading(false));
  }, []);

  const getClientName = (c) => {
    const cl = clients.find((cl) => cl.id === c.client_id);
    return cl?.name || `Client ${c.client_id}`;
  };

  const clientNames = [...new Set(controls.map((c) => getClientName(c)))];

  const counts = controls.reduce((a, c) => { a[c.status] = (a[c.status] || 0) + 1; return a; }, {});
  const pct = controls.length ? Math.round((counts.done || 0) / controls.length * 100) : 0;
  const FILTERS = ["todo", "in_progress", "exception", "done"];

  const rows = controls
    .filter((c) => statusFilter === "all" || c.status === statusFilter)
    .filter((c) => clientFilter === "all" || getClientName(c) === clientFilter);

  if (loading) return <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>;

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-ink">내부회계</h2>
          <p className="mt-1 text-sm text-sub">ICFR 통제활동 테스트 현황</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setImportOpen(true)}
            className="px-3 py-1.5 rounded-lg border border-line2 text-[13px] font-medium text-sub hover:bg-[#fafafa] transition flex items-center gap-1.5">
            <Icon name="upload_file" className="text-[16px] text-faint" />
            RCM 엑셀 업로드
          </button>
          <button onClick={() => setNewOpen(true)}
            className="px-3 py-1.5 text-white text-[13px] font-medium rounded-lg hover:opacity-90 transition flex items-center gap-1"
            style={{ background: "var(--lnac)" }}>
            <Icon name="add" className="text-[16px]" style={{ fontVariationSettings: '"wght" 400' }} />
            통제활동
          </button>
        </div>
      </div>

      {controls.length > 0 && (
        <div className="bg-white rounded-lg border border-line p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-baseline gap-3">
              <span className="text-2xl font-semibold text-ink tabular-nums">{pct}%</span>
              <span className="text-xs text-faint">완료 {counts.done || 0} / 전체 {controls.length}</span>
            </div>
            <div className="flex items-center gap-4">
              {FILTERS.map((k) => (
                <span key={k} className="flex items-center gap-1.5 text-xs text-sub">
                  <span className="w-[7px] h-[7px] rounded-full" style={{ background: STATUS[k].color }} />
                  {STATUS[k].label} <span className="text-ink font-medium tabular-nums">{counts[k] || 0}</span>
                </span>
              ))}
            </div>
          </div>
          <div className="w-full h-1.5 bg-line rounded-full overflow-hidden flex">
            {FILTERS.filter((k) => counts[k]).map((k) => (
              <div key={k} className="h-full transition-all duration-700"
                style={{ width: `${(counts[k] / controls.length) * 100}%`, background: STATUS[k].color, opacity: k === "todo" ? 0.45 : 1 }} />
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border border-line">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-1 flex-wrap">
            <button onClick={() => setStatusFilter("all")}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${statusFilter === "all" ? "bg-[#f4f4f5] text-ink" : "text-faint hover:text-sub"}`}>
              전체 {controls.length}
            </button>
            {FILTERS.map((k) => (
              <button key={k} onClick={() => setStatusFilter(k)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition ${statusFilter === k ? "bg-[#f4f4f5] text-ink" : "text-faint hover:text-sub"}`}>
                <span className="w-[6px] h-[6px] rounded-full" style={{ background: STATUS[k].color }} />
                {STATUS[k].label} {counts[k] || 0}
              </button>
            ))}
          </div>
          <select value={clientFilter} onChange={(e) => setClientFilter(e.target.value)}
            className="pl-2.5 pr-7 py-1.5 rounded-lg bg-white text-xs text-sub focus:ring-0">
            <option value="all">전체 클라이언트</option>
            {clientNames.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {controls.length === 0 ? (
          <div className="border-t border-line p-10 text-center text-xs text-faint">통제활동이 없습니다</div>
        ) : (
          <IcfrGrid rows={rows} getClientName={getClientName} clientNames={clientNames} onOpen={setOpenCtrl}
            visible={visible} setVisible={setVisible} presets={presets} setPresets={setPresets}
            density={density} setDensity={setDensity} />
        )}
      </div>

      {openCtrl && (
        <RcmDetail ctrl={openCtrl} clientName={getClientName(openCtrl)} onClose={() => setOpenCtrl(null)}
          onUpdated={(updated) => {
            setControls((cs) => cs.map((c) => c.id === updated.id ? updated : c));
            setOpenCtrl(updated);
          }} />
      )}

      <NewCtrlModal open={newOpen} clients={clients} onClose={() => setNewOpen(false)}
        onCreated={(c) => setControls((cs) => [...cs, c])} />

      <RcmImportModal open={importOpen} clients={clients} onClose={() => setImportOpen(false)}
        onImported={(created) => setControls((cs) => [...cs, ...created])} />
    </div>
  );
}
