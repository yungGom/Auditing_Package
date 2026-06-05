import { useRef, useState } from "react";
import * as XLSX from "xlsx";

import { shellDesign } from "../design";
import { useFlow } from "../state/flowState";
import type { FlowchartState, FlowNode } from "../state/flowState";
import { parseXlsx } from "../parsing/xlsxParser";
import { buildFlowFromExcel } from "../parsing/buildFlowFromExcel";
import { exportToPpt } from "../export/pptExport";
import { buildCatalogFromActivities } from "../types";

/**
 * 상단 툴바 — 제목, 액션 버튼 (엑셀 업로드 / 활성 flowchart / PPT 다운로드),
 * 뷰 토글, 도움말.
 */

export type AppView = "canvas" | "design";

interface TopbarProps {
  view: AppView;
  onChangeView: (v: AppView) => void;
  onOpenHelp?: () => void;
}

export function Topbar({ view, onChangeView, onOpenHelp }: TopbarProps) {
  const {
    loadFlowcharts,
    flowcharts,
    activeCode,
    setActiveCode,
    headerInfo,
    setHeaderInfo,
    undo,
    redo,
    canUndo,
    canRedo,
    nodes,
    setNodes,
  } = useFlow();

  // 전체 잠금 토글 — 현재 캔버스의 모든 노드 위치를 한 번에 고정/해제
  const allLocked =
    nodes.length > 0 &&
    nodes.every((n) => !!(n.data as { locked?: boolean })?.locked);
  function toggleLockAll() {
    const next = !allLocked;
    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        draggable: !next,
        data: { ...n.data, locked: next },
      })),
    );
  }
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<{
    kind: "idle" | "ok" | "err";
    msg: string;
  }>({ kind: "idle", msg: "" });

  async function handleFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    try {
      const buf = await file.arrayBuffer();
      const wb = XLSX.read(buf, { type: "array" });
      const parsed = parseXlsx(wb);
      const built = buildFlowFromExcel(parsed);

      const fcStates: FlowchartState[] = built.flowcharts.map((f) => ({
        code: f.code,
        name: f.name,
        nodes: f.nodes as FlowNode[],
        edges: f.edges,
      }));

      if (fcStates.length === 0) {
        setStatus({ kind: "err", msg: "표시할 flowchart 가 없습니다." });
        return;
      }

      // v8: 매핑 시트(CONTROL_NO) 우선 → 통제/위험 카탈로그.
      //   매핑 시트에 CONTROL_NO 없으면 RCM 자동 JOIN (v7 이하 호환).
      const catalog = buildCatalogFromActivities(parsed.activities, parsed.rcmByRow);

      // 진단 로그 — 사용자가 콘솔에서 통제번호가 비어있는지 즉시 확인 가능
      console.log(
        `[topbar] 카탈로그 빌드: 통제 ${catalog.controls.length}개 / 위험 ${catalog.risks.length}개`,
      );
      console.table(
        catalog.controls.map((c) => ({
          id: c.id,
          flowchart: c.flowchartCode,
          controlNo: c.controlNo || "(빈값 ⚠)",
          name: c.controlName.slice(0, 30),
          key: c.isKeyControl ? "Key" : "Non-Key",
          type: c.controlType,
        })),
      );

      loadFlowcharts({
        flowcharts: fcStates,
        headerInfo: built.headerInfo,
        controls: catalog.controls,
        risks: catalog.risks,
      });

      const codesStr = fcStates.map((f) => f.code).join(", ");
      setStatus({
        kind: "ok",
        msg: `${file.name} · flowchart ${fcStates.length}개 (${codesStr})`,
      });

      if (built.warnings.length > 0) {
        console.warn("[xlsx parsing warnings]", built.warnings);
      }
    } catch (err) {
      console.error(err);
      setStatus({
        kind: "err",
        msg: `엑셀 읽기 실패: ${(err as Error).message}`,
      });
    }
  }

  async function handleDownloadPpt() {
    // 모든 flowchart 를 한 파일에 묶어 출력. 1페이지는 가이드, 2~ 페이지는 각 flowchart.
    const targets = flowcharts.filter((f) => f.nodes.length > 0);
    if (targets.length === 0) {
      setStatus({
        kind: "err",
        msg: "캔버스가 비어있습니다. 엑셀 업로드 또는 도형 추가 후 다시 시도하세요.",
      });
      return;
    }
    try {
      await exportToPpt(
        headerInfo,
        targets.map((f) => ({
          code: f.code,
          name: f.name,
          nodes: f.nodes,
          edges: f.edges,
        })),
      );
      setStatus({
        kind: "ok",
        msg: `PPT 다운로드 시작: 가이드 + ${targets.length}개 flowchart`,
      });
    } catch (err) {
      console.error(err);
      setStatus({
        kind: "err",
        msg: `PPT 생성 실패: ${(err as Error).message}`,
      });
    }
  }

  // 활성 flowchart 가 바뀌면 헤더 표(Flowchart Code / 소분류) 도 자동 갱신
  function handleSwitch(code: string) {
    setActiveCode(code);
    const fc = flowcharts.find((f) => f.code === code);
    if (fc) {
      setHeaderInfo({
        ...headerInfo,
        flowchartCode: fc.code,
        subProcessName: fc.name,
      });
    }
  }

  return (
    <header
      className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4"
      style={{ height: shellDesign.topbarHeight }}
    >
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-base font-bold text-slate-900">
            ICFR Flowchart Generator
          </h1>
          <p className="text-[11px] leading-tight text-slate-500">
            내부회계관리제도 Flowchart 자동 생성 · 로컬 전용
          </p>
        </div>

        <nav className="flex items-center gap-1">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            hidden
            onChange={handleFileChosen}
          />
          <ToolbarButton
            label="엑셀 업로드"
            hint="RCM + 매핑 시트가 들어있는 .xlsx"
            onClick={() => fileInputRef.current?.click()}
          />
          <ToolbarButton
            label="PPT 다운로드"
            hint="현재 활성 flowchart 를 .pptx 로"
            onClick={handleDownloadPpt}
          />
          <ToolbarButton
            label="Export 매핑"
            hint="캔버스 상태를 매핑 시트로 (Ctrl+S 예정)"
            disabled
          />
          <ToolbarButton
            label={allLocked ? "🔒 전체 해제" : "🔓 전체 잠금"}
            hint="모든 노드 위치 고정/해제 (개별: 노드 선택 후 L)"
            onClick={toggleLockAll}
            disabled={nodes.length === 0}
          />

          {/* Undo / Redo — Ctrl+Z, Ctrl+Y (또는 Ctrl+Shift+Z) */}
          <div className="ml-1 flex items-center gap-0.5 border-l border-slate-200 pl-2">
            <IconButton
              label="↶"
              title="실행 취소 (Ctrl+Z)"
              onClick={undo}
              disabled={!canUndo}
            />
            <IconButton
              label="↷"
              title="다시 실행 (Ctrl+Y · Ctrl+Shift+Z)"
              onClick={redo}
              disabled={!canRedo}
            />
          </div>
        </nav>

        {/* 활성 flowchart 드롭다운 — 2개 이상일 때만 노출 */}
        {flowcharts.length > 1 && (
          <FlowchartPicker
            flowcharts={flowcharts}
            activeCode={activeCode}
            onChange={handleSwitch}
          />
        )}

        {status.kind !== "idle" && (
          <span
            className={
              "rounded px-2 py-0.5 text-[11px] " +
              (status.kind === "ok"
                ? "bg-emerald-50 text-emerald-700"
                : "bg-rose-50 text-rose-700")
            }
          >
            {status.msg}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <ViewToggle view={view} onChange={onChangeView} />
        <button
          type="button"
          onClick={onOpenHelp}
          aria-label="단축키 안내"
          title="단축키 안내 (?)"
          className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 bg-white text-sm font-semibold text-slate-600 hover:bg-slate-100"
        >
          ?
        </button>
        <div className="text-xs text-slate-400">v0.1.0</div>
      </div>
    </header>
  );
}

function FlowchartPicker({
  flowcharts,
  activeCode,
  onChange,
}: {
  flowcharts: FlowchartState[];
  activeCode: string;
  onChange: (code: string) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
        현재
      </span>
      <select
        value={activeCode}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 hover:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400"
      >
        {flowcharts.map((f) => (
          <option key={f.code} value={f.code}>
            {f.code} · {f.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function ToolbarButton({
  label,
  hint,
  disabled,
  onClick,
}: {
  label: string;
  hint?: string;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={hint}
      className={[
        "rounded-md px-3 py-1.5 text-sm transition",
        disabled
          ? "cursor-not-allowed text-slate-400"
          : "text-slate-700 hover:bg-slate-100",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function IconButton({
  label,
  title,
  onClick,
  disabled,
}: {
  label: string;
  title: string;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={[
        "flex h-7 w-7 items-center justify-center rounded text-lg leading-none transition",
        disabled
          ? "cursor-not-allowed text-slate-300"
          : "text-slate-700 hover:bg-slate-100",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function ViewToggle({
  view,
  onChange,
}: {
  view: AppView;
  onChange: (v: AppView) => void;
}) {
  return (
    <div className="inline-flex overflow-hidden rounded-md border border-slate-300 text-xs">
      <button
        type="button"
        onClick={() => onChange("canvas")}
        className={
          "px-3 py-1.5 transition " +
          (view === "canvas"
            ? "bg-slate-900 text-white"
            : "bg-white text-slate-700 hover:bg-slate-100")
        }
      >
        캔버스
      </button>
      <button
        type="button"
        onClick={() => onChange("design")}
        className={
          "border-l border-slate-300 px-3 py-1.5 transition " +
          (view === "design"
            ? "bg-slate-900 text-white"
            : "bg-white text-slate-700 hover:bg-slate-100")
        }
      >
        디자인 프리뷰
      </button>
    </div>
  );
}
