// ---------------------------------------------------------------------------
// Settings – 설정 페이지
// ---------------------------------------------------------------------------
import { useState, useEffect, useCallback } from "react";
import api from "../api";

const STORAGE_KEY = "auditlink_settings";

const DEFAULT_SETTINGS = {
  fiscalYears: ["FY2025"],
  activeFY: "FY2025",
  userName: "",
  userTitle: "",
  userFirm: "",
  reportDeadlineDays: 90,
  alertDays: [7, 15, 30],
};

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : { ...DEFAULT_SETTINGS };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

// --- Sub-components ---------------------------------------------------------

function SectionCard({ icon, title, description, children }) {
  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
          <span className="material-symbols-outlined text-primary text-lg">{icon}</span>
        </div>
        <div>
          <h3 className="text-sm font-label font-bold text-on-surface">{title}</h3>
          {description && (
            <p className="text-xs text-on-surface-variant font-body mt-0.5">{description}</p>
          )}
        </div>
      </div>
      {children}
    </div>
  );
}

function InputField({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="block">
      <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition"
      />
    </label>
  );
}

// --- Main -------------------------------------------------------------------

export default function Settings() {
  const [settings, setSettings] = useState(load);
  const [saved, setSaved] = useState(false);
  const [newFY, setNewFY] = useState("");

  const update = useCallback((key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }, []);

  // Load from API on mount
  useEffect(() => {
    api.getSettings().then((apiSettings) => {
      if (apiSettings && Object.keys(apiSettings).length) {
        const parsed = { ...settings };
        for (const [k, v] of Object.entries(apiSettings)) {
          try { parsed[k] = JSON.parse(v); } catch { parsed[k] = v; }
        }
        setSettings((prev) => ({ ...prev, ...parsed }));
      }
    }).catch(() => {});
  }, []);

  const handleSave = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    // Also save to API
    api.updateSettings(settings).catch(() => {});
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  // --- FY helpers ---
  const addFY = () => {
    const fy = newFY.trim();
    if (!fy || settings.fiscalYears.includes(fy)) return;
    update("fiscalYears", [...settings.fiscalYears, fy]);
    setNewFY("");
  };

  const removeFY = (fy) => {
    if (settings.fiscalYears.length <= 1) return;
    const next = settings.fiscalYears.filter((f) => f !== fy);
    update("fiscalYears", next);
    if (settings.activeFY === fy) update("activeFY", next[0]);
  };

  const toggleAlert = (day) => {
    const current = settings.alertDays;
    const next = current.includes(day) ? current.filter((d) => d !== day) : [...current, day].sort((a, b) => a - b);
    update("alertDays", next);
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-headline text-2xl font-bold text-on-surface">설정</h2>
          <p className="mt-1 text-sm text-on-surface-variant font-body">
            앱 환경 및 기본값을 설정하세요
          </p>
        </div>
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-label font-semibold hover:bg-primary-container hover:text-white transition shadow-sm"
        >
          <span className="material-symbols-outlined text-lg">
            {saved ? "check_circle" : "save"}
          </span>
          {saved ? "저장 완료" : "저장"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-5">
        {/* ── 회계연도 관리 ────────────────────────────── */}
        <SectionCard icon="calendar_today" title="회계연도 관리" description="감사 대상 회계연도를 관리합니다">
          {/* 활성 FY */}
          <div className="mb-4">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">
              활성 회계연도
            </span>
            <select
              value={settings.activeFY}
              onChange={(e) => update("activeFY", e.target.value)}
              className="appearance-none w-full pl-3 pr-8 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface cursor-pointer focus:border-primary focus:outline-none transition"
            >
              {settings.fiscalYears.map((fy) => (
                <option key={fy} value={fy}>{fy}</option>
              ))}
            </select>
          </div>

          {/* FY 목록 */}
          <div className="space-y-2 mb-4">
            {settings.fiscalYears.map((fy) => (
              <div
                key={fy}
                className={`flex items-center justify-between px-3 py-2 rounded-xl border ${
                  fy === settings.activeFY
                    ? "border-primary/30 bg-primary/5"
                    : "border-outline-variant bg-surface-container-low"
                }`}
              >
                <div className="flex items-center gap-2">
                  {fy === settings.activeFY && (
                    <span className="w-2 h-2 rounded-full bg-primary" />
                  )}
                  <span className="text-sm font-label font-semibold text-on-surface">{fy}</span>
                  {fy === settings.activeFY && (
                    <span className="text-[11px] font-label text-primary font-semibold">활성</span>
                  )}
                </div>
                <button
                  onClick={() => removeFY(fy)}
                  disabled={settings.fiscalYears.length <= 1}
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-error/10 hover:text-error disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-on-surface-variant transition"
                >
                  <span className="material-symbols-outlined text-base">close</span>
                </button>
              </div>
            ))}
          </div>

          {/* FY 추가 */}
          <div className="flex gap-2">
            <input
              value={newFY}
              onChange={(e) => setNewFY(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addFY()}
              placeholder="예: FY2026"
              className="flex-1 px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition"
            />
            <button
              onClick={addFY}
              className="px-3 py-2 rounded-xl border border-outline-variant text-sm font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-base">add</span>
              추가
            </button>
          </div>
        </SectionCard>

        {/* ── 사용자 정보 ─────────────────────────────── */}
        <SectionCard icon="person" title="사용자 정보" description="감사 보고서에 표시될 사용자 정보입니다">
          <div className="space-y-4">
            <InputField
              label="이름"
              value={settings.userName}
              onChange={(v) => update("userName", v)}
              placeholder="홍길동"
            />
            <InputField
              label="직급"
              value={settings.userTitle}
              onChange={(v) => update("userTitle", v)}
              placeholder="시니어 / 매니저 / 파트너"
            />
            <InputField
              label="소속법인"
              value={settings.userFirm}
              onChange={(v) => update("userFirm", v)}
              placeholder="OO회계법인"
            />
          </div>
        </SectionCard>

        {/* ── 기본값 설정 ─────────────────────────────── */}
        <SectionCard icon="tune" title="기본값 설정" description="감사 일정 관련 기본값을 지정합니다">
          {/* 보고서 제출 기한 */}
          <div className="mb-5">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">
              감사보고서 제출 기한 (결산일 기준)
            </span>
            <div className="flex items-center gap-3">
              <span className="text-sm text-on-surface-variant font-body">결산일 +</span>
              <input
                type="number"
                min={1}
                max={365}
                value={settings.reportDeadlineDays}
                onChange={(e) => update("reportDeadlineDays", Number(e.target.value))}
                className="w-20 px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface text-center focus:border-primary focus:outline-none transition"
              />
              <span className="text-sm text-on-surface-variant font-body">일</span>
            </div>
          </div>

          {/* D-day 알림 기준일 */}
          <div>
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-2 block">
              D-day 알림 기준일
            </span>
            <div className="flex flex-wrap gap-2">
              {[3, 7, 15, 30, 60].map((day) => {
                const active = settings.alertDays.includes(day);
                return (
                  <button
                    key={day}
                    onClick={() => toggleAlert(day)}
                    className={`px-3.5 py-2 rounded-xl text-xs font-label font-semibold border transition ${
                      active
                        ? "bg-primary/10 text-primary border-primary/30"
                        : "bg-surface-container-low text-on-surface-variant border-outline-variant hover:border-primary/30"
                    }`}
                  >
                    D-{day}
                  </button>
                );
              })}
            </div>
          </div>
        </SectionCard>

        {/* ── 데이터 관리 ─────────────────────────────── */}
        <SectionCard icon="storage" title="데이터 관리" description="로컬 데이터 백업 및 복원">
          <div className="space-y-3">
            <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-outline-variant hover:bg-surface-container-low transition group">
              <div className="w-9 h-9 rounded-xl bg-secondary/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-secondary text-lg">download</span>
              </div>
              <div className="text-left">
                <p className="text-sm font-label font-semibold text-on-surface group-hover:text-primary transition">
                  데이터 백업
                </p>
                <p className="text-xs text-on-surface-variant font-body">
                  SQLite 데이터베이스 파일을 내보냅니다
                </p>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant ml-auto">chevron_right</span>
            </button>

            <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-outline-variant hover:bg-surface-container-low transition group">
              <div className="w-9 h-9 rounded-xl bg-on-tertiary-container/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-on-tertiary-container text-lg">upload</span>
              </div>
              <div className="text-left">
                <p className="text-sm font-label font-semibold text-on-surface group-hover:text-primary transition">
                  데이터 복원
                </p>
                <p className="text-xs text-on-surface-variant font-body">
                  백업 파일에서 데이터를 복원합니다
                </p>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant ml-auto">chevron_right</span>
            </button>

            <div className="mt-4 px-4 py-3 rounded-xl bg-error/5 border border-error/20">
              <button className="w-full flex items-center gap-3 group">
                <span className="material-symbols-outlined text-error text-lg">warning</span>
                <div className="text-left">
                  <p className="text-sm font-label font-semibold text-error">데이터 초기화</p>
                  <p className="text-xs text-on-surface-variant font-body">
                    모든 데이터를 삭제하고 초기 상태로 되돌립니다
                  </p>
                </div>
              </button>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
