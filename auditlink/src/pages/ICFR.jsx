// ---------------------------------------------------------------------------
// ICFR – 내부회계관리제도 테스트 추적 페이지
// ---------------------------------------------------------------------------
import { useState, useEffect, useMemo } from "react";
import api from "../api";
import { usePersistedState } from "../hooks/usePersistedState";

const STATUS = {
  미실시: { bg: "bg-outline/10", text: "text-outline", border: "border-outline/30" },
  진행중: { bg: "bg-secondary/10", text: "text-secondary", border: "border-secondary/30" },
  완료: { bg: "bg-[#2e7d32]/10", text: "text-[#2e7d32]", border: "border-[#2e7d32]/30" },
  이슈발견: { bg: "bg-error/10", text: "text-error", border: "border-error/30" },
};

const MOCK_DATA = [
  // 한빛제조
  { id: 1, client: "한빛제조", process: "매출", control: "매출 거래 승인 통제", method: "검사", status: "완료", assignee: "김민수", note: "" },
  { id: 2, client: "한빛제조", process: "매출", control: "수익인식 시점 적정성 통제", method: "재수행", status: "진행중", assignee: "김민수", note: "샘플 25건 중 15건 완료" },
  { id: 3, client: "한빛제조", process: "매입", control: "구매요청서 승인 통제", method: "검사", status: "완료", assignee: "이서연", note: "" },
  { id: 4, client: "한빛제조", process: "재고", control: "재고 실사 통제", method: "관찰", status: "이슈발견", assignee: "이서연", note: "일부 창고 실사 누락 발견" },
  { id: 5, client: "한빛제조", process: "자금", control: "자금 집행 승인 통제", method: "질문", status: "미실시", assignee: "박준혁", note: "" },
  { id: 6, client: "한빛제조", process: "급여", control: "급여 계산 및 지급 통제", method: "재수행", status: "완료", assignee: "박준혁", note: "" },
  // 서현테크
  { id: 7, client: "서현테크", process: "매출", control: "계약 검토 및 승인 통제", method: "검사", status: "완료", assignee: "최유진", note: "" },
  { id: 8, client: "서현테크", process: "매출", control: "프로젝트 진행률 산정 통제", method: "재수행", status: "이슈발견", assignee: "최유진", note: "진행률 산정 기준 불일치" },
  { id: 9, client: "서현테크", process: "매입", control: "외주용역 검수 통제", method: "검사", status: "진행중", assignee: "정하은", note: "검수 보고서 수집 중" },
  { id: 10, client: "서현테크", process: "자금", control: "일일 자금 시재 확인 통제", method: "관찰", status: "완료", assignee: "정하은", note: "" },
  { id: 11, client: "서현테크", process: "급여", control: "인건비 배부 통제", method: "재수행", status: "미실시", assignee: "김민수", note: "" },
];

const ALL_CLIENTS = ["전체", ...new Set(MOCK_DATA.map((d) => d.client))];
const ALL_STATUSES = ["전체", "미실시", "진행중", "완료", "이슈발견"];

const METHOD_ICON = {
  질문: "forum",
  관찰: "visibility",
  검사: "fact_check",
  재수행: "replay",
};

// --- Sub-components ---------------------------------------------------------

function SummaryBar({ filtered, total }) {
  const completed = filtered.filter((d) => d.status === "완료").length;
  const inProgress = filtered.filter((d) => d.status === "진행중").length;
  const issue = filtered.filter((d) => d.status === "이슈발견").length;
  const notStarted = filtered.filter((d) => d.status === "미실시").length;
  const pct = total === 0 ? 0 : Math.round((completed / total) * 100);

  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-label font-semibold text-on-surface-variant">
          전체 테스트 완료율
        </h3>
        <span className="text-sm font-label font-bold text-on-surface">
          {completed} / {total}건 완료
        </span>
      </div>

      {/* 프로그레스바 */}
      <div className="w-full h-3 bg-surface-container-highest rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-primary to-primary-container rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* 상태 요약 칩 */}
      <div className="flex items-center gap-4 mt-3">
        {[
          { label: "완료", value: completed, color: "text-[#2e7d32]" },
          { label: "진행중", value: inProgress, color: "text-secondary" },
          { label: "이슈발견", value: issue, color: "text-error" },
          { label: "미실시", value: notStarted, color: "text-outline" },
        ].map((s) => (
          <span key={s.label} className="flex items-center gap-1.5 text-xs font-label">
            <span className={`inline-block w-2 h-2 rounded-full ${s.color.replace("text-", "bg-")}`} />
            <span className="text-on-surface-variant">{s.label}</span>
            <strong className={`${s.color}`}>{s.value}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

function FilterDropdown({ label, icon, options, value, onChange }) {
  return (
    <div className="relative">
      <div className="flex items-center gap-1.5 text-xs font-label text-on-surface-variant mb-1">
        <span className="material-symbols-outlined text-sm">{icon}</span>
        {label}
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none w-full pl-3 pr-8 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface cursor-pointer hover:border-primary/40 focus:border-primary focus:outline-none transition"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
      <span className="material-symbols-outlined absolute right-2 bottom-2 text-base text-on-surface-variant pointer-events-none">
        expand_more
      </span>
    </div>
  );
}

function StatusBadge({ status }) {
  const s = STATUS[status] || STATUS["미실시"];
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-[11px] font-label font-bold border ${s.bg} ${s.text} ${s.border}`}>
      {status}
    </span>
  );
}

// --- Main -------------------------------------------------------------------

export default function ICFR() {
  const [data, setData] = useState([]);
  const [loadError, setLoadError] = useState(false);
  const [clientFilter, setClientFilter] = usePersistedState("icfr:clientFilter", "전체");
  const [statusFilter, setStatusFilter] = usePersistedState("icfr:statusFilter", "전체");
  const [editItem, setEditItem] = useState(null); // null or item object for edit modal

  const loadData = () => {
    api.getICFRTests().then((rows) => {
      setData((rows || []).map((r) => ({
        ...r,
        client: r.client_name,
        control: r.control_name,
        method: r.test_method,
      })));
      setLoadError(false);
    }).catch(() => { setLoadError(true); });
  };

  useEffect(() => { loadData(); }, []);

  const handleAdd = () => {
    setEditItem({ id: null, client_name: "", process: "", control_name: "", test_method: "검사", status: "미실시", assignee: "", note: "" });
  };

  const handleSave = async (item) => {
    const body = {
      client_name: item.client_name, process: item.process,
      control_name: item.control_name, test_method: item.test_method,
      status: item.status, assignee: item.assignee, note: item.note,
    };
    try {
      if (item.id) {
        const updated = await api.updateICFRTest(item.id, body);
        setData((prev) => prev.map((d) => d.id === item.id ? { ...d, ...updated, client: updated.client_name, control: updated.control_name, method: updated.test_method } : d));
      } else {
        const created = await api.createICFRTest(body);
        setData((prev) => [...prev, { ...created, client: created.client_name, control: created.control_name, method: created.test_method }]);
      }
    } catch { alert("저장에 실패했습니다."); }
    setEditItem(null);
  };

  const handleDelete = async (id) => {
    if (!confirm("이 ICFR 테스트를 삭제하시겠습니까?")) return;
    try {
      await api.deleteICFRTest(id);
      setData((prev) => prev.filter((d) => d.id !== id));
    } catch { alert("삭제에 실패했습니다."); }
    setEditItem(null);
  };

  const allClients = useMemo(() => ["전체", ...new Set(data.map((d) => d.client))], [data]);

  const filtered = useMemo(() => {
    return data.filter((d) => {
      if (clientFilter !== "전체" && d.client !== clientFilter) return false;
      if (statusFilter !== "전체" && d.status !== statusFilter) return false;
      return true;
    });
  }, [clientFilter, statusFilter, data]);

  return (
    <div className="space-y-6">
      {/* 상단 헤더 */}
      <div>
        <h2 className="font-headline text-2xl font-bold text-on-surface">내부회계관리제도</h2>
        <p className="mt-1 text-sm text-on-surface-variant font-body">
          ICFR 통제활동 테스트 현황을 추적하고 관리하세요
        </p>
      </div>

      {loadError && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-error/10 border border-error/20 text-xs font-label text-error">
          <span className="material-symbols-outlined text-sm">error</span>
          ICFR 데이터를 불러오지 못했습니다. 백엔드 서버를 확인해주세요.
        </div>
      )}

      {/* 요약 바 */}
      <SummaryBar filtered={filtered} total={data.length} />

      {/* 필터 + 테이블 */}
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant">
        {/* 필터 행 */}
        <div className="flex items-end gap-4 p-5 border-b border-outline-variant">
          <FilterDropdown
            label="클라이언트"
            icon="business"
            options={allClients}
            value={clientFilter}
            onChange={setClientFilter}
          />
          <FilterDropdown
            label="테스트 상태"
            icon="filter_list"
            options={ALL_STATUSES}
            value={statusFilter}
            onChange={setStatusFilter}
          />
          <div className="ml-auto flex items-center gap-3 self-end pb-2">
            <span className="text-xs font-label text-on-surface-variant">{filtered.length}건 표시 중</span>
            <button onClick={handleAdd}
              className="px-3 py-1.5 bg-primary text-white text-xs font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">add</span>추가
            </button>
          </div>
        </div>

        {/* 테이블 */}
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-outline-variant text-xs font-label text-on-surface-variant">
                <th className="px-5 py-3 font-semibold">클라이언트</th>
                <th className="px-5 py-3 font-semibold">프로세스</th>
                <th className="px-5 py-3 font-semibold">통제활동명</th>
                <th className="px-5 py-3 font-semibold">테스트 방법</th>
                <th className="px-5 py-3 font-semibold">상태</th>
                <th className="px-5 py-3 font-semibold">담당자</th>
                <th className="px-5 py-3 font-semibold">비고</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center">
                    <span className="material-symbols-outlined text-4xl text-outline/40 mb-2 block">search_off</span>
                    <p className="text-sm text-on-surface-variant font-label">해당 조건에 맞는 데이터가 없습니다</p>
                  </td>
                </tr>
              ) : (
                filtered.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => setEditItem({ ...row, client_name: row.client, control_name: row.control, test_method: row.method })}
                    className="border-b border-outline-variant/50 last:border-b-0 hover:bg-surface-container-low transition cursor-pointer"
                  >
                    <td className="px-5 py-3.5">
                      <span className="text-sm font-label font-semibold text-on-surface">{row.client}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-xs font-label text-on-surface-variant px-2 py-0.5 bg-surface-container rounded-xl">
                        {row.process}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-sm font-body text-on-surface">{row.control}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center gap-1 text-xs font-label text-on-surface-variant">
                        <span className="material-symbols-outlined text-sm">{METHOD_ICON[row.method] || "help"}</span>
                        {row.method}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-xs font-label text-on-surface-variant">{row.assignee}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-xs font-body text-on-surface-variant">{row.note || "—"}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit/Add Modal */}
      {editItem && (
        <ICFREditModal item={editItem} onClose={() => setEditItem(null)} onSave={handleSave} onDelete={handleDelete} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ICFR Edit Modal
// ---------------------------------------------------------------------------

const ALL_METHODS = ["질문", "관찰", "검사", "재수행"];
const ALL_ICFR_STATUSES = ["미실시", "진행중", "완료", "이슈발견"];

function ICFREditModal({ item, onClose, onSave, onDelete }) {
  const [form, setForm] = useState({ ...item });
  const update = (k, v) => setForm((p) => ({ ...p, [k]: v }));
  const isNew = !item.id;

  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-lg flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b border-outline-variant">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-lg">fact_check</span>
            </div>
            <h3 className="font-headline text-sm font-bold text-on-surface">{isNew ? "ICFR 테스트 추가" : "ICFR 테스트 수정"}</h3>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
            <span className="material-symbols-outlined text-on-surface-variant text-lg">close</span>
          </button>
        </div>

        <div className="p-5 space-y-3">
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">클라이언트명 *</span>
            <input type="text" value={form.client_name} onChange={(e) => update("client_name", e.target.value)} required
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">프로세스</span>
              <input type="text" value={form.process} onChange={(e) => update("process", e.target.value)} placeholder="매출/매입/재고/자금/급여"
                className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
            </label>
            <label className="block">
              <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">테스트 방법</span>
              <select value={form.test_method} onChange={(e) => update("test_method", e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface focus:border-primary focus:outline-none transition">
                {ALL_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </label>
          </div>
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">통제활동명 *</span>
            <input type="text" value={form.control_name} onChange={(e) => update("control_name", e.target.value)} required
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">상태</span>
              <select value={form.status} onChange={(e) => update("status", e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface focus:border-primary focus:outline-none transition">
                {ALL_ICFR_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">담당자</span>
              <input type="text" value={form.assignee} onChange={(e) => update("assignee", e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition" />
            </label>
          </div>
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">비고</span>
            <textarea value={form.note} onChange={(e) => update("note", e.target.value)} rows={2}
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition resize-none" />
          </label>
        </div>

        <div className="flex items-center justify-between p-5 border-t border-outline-variant">
          {!isNew ? (
            <button onClick={() => onDelete(item.id)} className="px-3 py-2 rounded-xl text-xs font-label font-semibold text-error hover:bg-error/5 transition flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">delete</span>삭제
            </button>
          ) : <div />}
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="px-4 py-2 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition">취소</button>
            <button onClick={() => onSave(form)} disabled={!form.client_name || !form.control_name}
              className={`px-5 py-2 rounded-xl text-xs font-label font-semibold text-white transition flex items-center gap-1 ${form.client_name && form.control_name ? "bg-primary hover:opacity-90" : "bg-outline cursor-not-allowed"}`}>
              <span className="material-symbols-outlined text-sm">{isNew ? "add" : "save"}</span>{isNew ? "추가" : "저장"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
