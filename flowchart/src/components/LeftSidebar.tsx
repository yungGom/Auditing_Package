import { useState } from "react";
import { shellDesign, icfrColors } from "../design";
import { useFlow } from "../state/flowState";
import type { ControlData, RiskData } from "../types";
import { HeaderEditModal } from "./HeaderEditModal";
import { AddControlModal } from "./AddControlModal";
import { AddRiskModal } from "./AddRiskModal";

/**
 * 좌측 사이드바 — v6 신구조.
 *
 *   ┌─ 헤더 정보 (요약 카드 + [편집])
 *   ├─ 통제 목록 ([+] 추가)
 *   └─ 위험 목록 ([+] 추가)
 *
 * 통제 카드 클릭 → 해당 flowchartCode 로 활성 캔버스 전환.
 * 통제 카드 호버 시 ⋯ 메뉴 → 편집 / 복제 / 삭제(수기만).
 */
export function LeftSidebar() {
  const {
    headerInfo,
    controls,
    risks,
    setActiveCode,
    setHeaderInfo,
    flowcharts,
    activeCode,
    deleteControl,
    duplicateControl,
  } = useFlow();

  // 모달 상태
  const [headerOpen, setHeaderOpen] = useState(false);
  const [addControlOpen, setAddControlOpen] = useState(false);
  const [addRiskOpen, setAddRiskOpen] = useState(false);
  const [editControl, setEditControl] = useState<ControlData | null>(null);

  const onPickControl = (c: ControlData) => {
    // flowchart 가 있으면 그 코드로 전환
    const fc = flowcharts.find((f) => f.code === c.flowchartCode);
    if (fc) {
      setActiveCode(fc.code);
      setHeaderInfo({
        ...headerInfo,
        flowchartCode: fc.code,
        subProcessName: fc.name,
      });
    }
  };

  return (
    <aside
      className="flex shrink-0 flex-col border-r border-slate-200 bg-white"
      style={{ width: shellDesign.leftSidebarWidth }}
    >
      {/* ── 헤더 정보 요약 ── */}
      <section className="shrink-0 border-b border-slate-200 p-3">
        <div className="flex items-center justify-between">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            📋 헤더 정보
          </div>
          <button
            type="button"
            onClick={() => setHeaderOpen(true)}
            className="rounded border border-slate-300 px-2 py-0.5 text-[10px] text-slate-600 hover:bg-slate-100"
          >
            편집
          </button>
        </div>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-[11px]">
          <HeaderRow k="회사명" v={headerInfo.company} />
          <HeaderRow k="대분류" v={headerInfo.processName} />
          <HeaderRow k="중분류" v={headerInfo.middleCategory} />
          <HeaderRow k="작성자" v={headerInfo.author} />
          <HeaderRow k="날짜" v={headerInfo.lastChangeDate} />
        </dl>
      </section>

      {/* ── 통제 목록 ── */}
      <ListSection
        title="통제 (Control)"
        count={controls.length}
        onAdd={() => setAddControlOpen(true)}
        addLabel="통제 추가"
        emptyHint="엑셀을 업로드하거나 [+] 로 통제를 추가하세요."
      >
        {controls.map((c) => (
          <ControlCard
            key={c.id}
            control={c}
            active={c.flowchartCode === activeCode}
            onPick={() => onPickControl(c)}
            onEdit={() => setEditControl(c)}
            onDuplicate={() => duplicateControl(c.id)}
            onDelete={() => {
              if (c.source === "excel") return;
              if (
                confirm(
                  `통제 "${c.controlNo}" 와 관련된 flowchart 도 함께 삭제됩니다. 진행할까요?`,
                )
              ) {
                deleteControl(c.id);
              }
            }}
          />
        ))}
      </ListSection>

      {/* ── 위험 목록 ── */}
      <ListSection
        title="위험 (Risk)"
        count={risks.length}
        onAdd={() => setAddRiskOpen(true)}
        addLabel="위험 추가"
        emptyHint="RCM 의 위험 또는 [+] 로 추가한 위험이 표시됩니다."
      >
        {risks.map((r) => (
          <RiskCard key={r.id} risk={r} controls={controls} />
        ))}
      </ListSection>

      {/* ── 모달들 ── */}
      <HeaderEditModal
        open={headerOpen}
        onClose={() => setHeaderOpen(false)}
      />
      <AddControlModal
        open={addControlOpen}
        onClose={() => setAddControlOpen(false)}
        mode="add"
      />
      <AddControlModal
        open={editControl !== null}
        onClose={() => setEditControl(null)}
        mode="edit"
        editTarget={editControl ?? undefined}
      />
      <AddRiskModal
        open={addRiskOpen}
        onClose={() => setAddRiskOpen(false)}
      />
    </aside>
  );
}

/* ─────────────────────────────────────────────
 * 서브 컴포넌트
 * ───────────────────────────────────────────── */

function HeaderRow({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="text-slate-500">{k}</dt>
      <dd className="truncate text-slate-800" title={v}>
        {v || "—"}
      </dd>
    </>
  );
}

function ListSection({
  title,
  count,
  onAdd,
  addLabel,
  emptyHint,
  children,
}: {
  title: string;
  count: number;
  onAdd: () => void;
  addLabel: string;
  emptyHint: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            {title}
          </span>
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
            {count}개
          </span>
        </div>
        <button
          type="button"
          onClick={onAdd}
          title={addLabel}
          className="flex h-6 w-6 items-center justify-center rounded border border-slate-300 text-sm font-semibold text-slate-600 hover:bg-slate-100"
        >
          +
        </button>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-auto p-2">
        {count === 0 ? (
          <div className="flex flex-1 items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 p-3 text-center">
            <p className="text-[11px] leading-snug text-slate-500">
              {emptyHint}
            </p>
          </div>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

function ControlCard({
  control,
  active,
  onPick,
  onEdit,
  onDuplicate,
  onDelete,
}: {
  control: ControlData;
  active: boolean;
  onPick: () => void;
  onEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isManual = control.source === "manual";
  const ctColor =
    control.controlType === "A"
      ? icfrColors.ctrlA
      : control.controlType === "M"
        ? icfrColors.ctrlM
        : icfrColors.ctrlI;
  const ctFg = control.controlType === "I" ? "#0F172A" : "#FFFFFF";

  return (
    <div
      className={
        "group relative cursor-pointer rounded-md border px-2 py-1.5 transition " +
        (active
          ? "border-icfr-keyCtrl bg-icfr-headerCellBg"
          : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50")
      }
      onClick={onPick}
      title={control.controlName || control.controlNo}
    >
      <div className="flex items-center gap-1.5">
        <span className="text-[11px]" aria-hidden>
          {isManual ? "🔸" : "🔹"}
        </span>
        <span className="flex-1 truncate text-[11px] font-semibold text-slate-800">
          {control.flowchartCode || control.controlNo}
        </span>
        {/* Key / Non-Key 점 */}
        <span
          aria-label={control.isKeyControl ? "Key" : "Non-Key"}
          title={control.isKeyControl ? "Key Control" : "Non-Key Control"}
          style={{
            width: 8,
            height: 8,
            borderRadius: 4,
            backgroundColor: control.isKeyControl
              ? icfrColors.keyCtrl
              : icfrColors.nonkeyCtrl,
          }}
        />
        {/* 통제유형 칩 */}
        <span
          style={{
            backgroundColor: ctColor,
            color: ctFg,
            fontSize: 9,
            fontWeight: 700,
            padding: "1px 4px",
            borderRadius: 3,
            minWidth: 14,
            textAlign: "center",
          }}
        >
          {control.controlType}
        </span>
        {/* 호버 시 ⋯ 메뉴 */}
        <button
          type="button"
          aria-label="옵션"
          onClick={(e) => {
            e.stopPropagation();
            setMenuOpen((v) => !v);
          }}
          className="invisible flex h-5 w-5 items-center justify-center rounded text-slate-500 hover:bg-slate-200 group-hover:visible"
        >
          ⋯
        </button>
      </div>
      <div className="mt-0.5 flex items-center justify-between text-[10px] text-slate-500">
        <span className="truncate" title={control.controlNo}>
          {control.controlNo}
        </span>
        <span
          className={
            "shrink-0 rounded px-1 py-px text-[9px] " +
            (isManual
              ? "bg-amber-50 text-amber-700"
              : "bg-slate-100 text-slate-500")
          }
        >
          {isManual ? "수기 ✏" : "엑셀"}
        </span>
      </div>

      {menuOpen && (
        <div
          className="absolute right-1 top-7 z-10 flex flex-col rounded-md border border-slate-200 bg-white py-1 text-[11px] shadow-md"
          onClick={(e) => e.stopPropagation()}
        >
          <MenuItem onClick={() => { setMenuOpen(false); onEdit(); }}>
            📝 편집
          </MenuItem>
          <MenuItem onClick={() => { setMenuOpen(false); onDuplicate(); }}>
            📋 복제
          </MenuItem>
          <MenuItem
            onClick={() => { setMenuOpen(false); onDelete(); }}
            disabled={!isManual}
            disabledHint="엑셀 통제는 삭제 불가"
            danger
          >
            🗑 삭제
          </MenuItem>
        </div>
      )}
    </div>
  );
}

function MenuItem({
  children,
  onClick,
  disabled,
  disabledHint,
  danger,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  disabledHint?: string;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={disabled ? disabledHint : undefined}
      className={
        "px-3 py-1 text-left " +
        (disabled
          ? "cursor-not-allowed text-slate-300"
          : danger
            ? "text-rose-600 hover:bg-rose-50"
            : "text-slate-700 hover:bg-slate-100")
      }
    >
      {children}
    </button>
  );
}

function RiskCard({
  risk,
  controls,
}: {
  risk: RiskData;
  controls: ControlData[];
}) {
  const isManual = risk.source === "manual";
  const linked = risk.linkedControlId
    ? controls.find((c) => c.id === risk.linkedControlId)
    : null;
  return (
    <div
      className="rounded-md border border-slate-200 bg-white px-2 py-1.5"
      title={risk.riskDesc}
    >
      <div className="flex items-center gap-1.5">
        <span className="text-[11px]" aria-hidden>
          ⚠
        </span>
        <span className="flex-1 truncate text-[11px] font-semibold text-slate-800">
          {risk.riskNo}
        </span>
        <span
          className={
            "shrink-0 rounded px-1 py-px text-[9px] " +
            (isManual
              ? "bg-amber-50 text-amber-700"
              : "bg-slate-100 text-slate-500")
          }
        >
          {isManual ? "수기 ✏" : "엑셀"}
        </span>
      </div>
      {linked && (
        <div className="mt-0.5 truncate text-[10px] text-slate-500">
          ↳ {linked.controlNo}
        </div>
      )}
      {risk.riskDesc && (
        <div className="mt-0.5 line-clamp-2 text-[10px] text-slate-500">
          {risk.riskDesc}
        </div>
      )}
    </div>
  );
}
