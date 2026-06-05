import { CSSProperties, ReactNode } from "react";
import { Edge } from "reactflow";

import { useFlow, FlowNode } from "../state/flowState";
import { SHAPES } from "../shapes";
import {
  canvasDesign as C,
  EdgeShape,
  EDGE_SHAPE_LABELS,
  activityNodeDesign,
  shapeNodeDesign,
} from "../design";
import type { ActivityNodeData } from "./ActivityNode";
import type { NonActivityShape, ShapeNodeData } from "./ShapeNode";
import type { Activity, ControlTypeSymbol } from "../types";
import { parseSubSteps } from "../types";

/**
 * 우측 편집 패널 — 선택 상태에 따라 4가지 모드를 보여준다.
 *
 *  - 선택 없음              → 안내
 *  - 활동(ActivityNode) 1개  → ActivityEditor
 *  - 도형(ShapeNode) 1개     → ShapeEditor
 *  - 엣지 1개                → EdgeEditor
 *  - 다중 선택               → 개수 안내 + 일괄 삭제
 *
 * 값 변경은 즉시 반영 (controlled inputs → useFlow().update*).
 */
export function EditPanel() {
  const { selectedNode, selectedEdge, selectedCount, deleteSelected } =
    useFlow();

  let body: ReactNode;
  if (selectedCount === 0) {
    body = <EmptyState />;
  } else if (selectedNode) {
    body =
      selectedNode.type === "activity" ? (
        <ActivityEditor node={selectedNode} />
      ) : (
        <ShapeEditor node={selectedNode} />
      );
  } else if (selectedEdge) {
    body = <EdgeEditor edge={selectedEdge} />;
  } else {
    body = <MultiSelectionState count={selectedCount} />;
  }

  return (
    <section className="flex flex-1 min-h-0 flex-col gap-3 overflow-auto p-3">
      <div className="flex items-center justify-between">
        <SectionLabel>편집</SectionLabel>
        {selectedCount > 0 && (
          <button
            type="button"
            onClick={deleteSelected}
            className="rounded border border-slate-300 px-2 py-0.5 text-[10px] font-medium text-slate-600 hover:border-rose-400 hover:bg-rose-50 hover:text-rose-700"
            title="Delete / Backspace"
          >
            삭제
          </button>
        )}
      </div>
      {body}
    </section>
  );
}

/* ─────────────────────────────────────────────
 * 빈 상태 / 다중 선택
 * ───────────────────────────────────────────── */

function EmptyState() {
  return (
    <div className="flex flex-1 items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-center">
      <div>
        <div className="text-xs font-medium text-slate-600">
          노드 또는 엣지를 선택하세요
        </div>
        <p className="mt-1 text-[11px] leading-snug text-slate-500">
          캔버스에서 클릭, Ctrl+클릭으로 다중 선택.
          <br />
          Del / Backspace 로 삭제.
        </p>
      </div>
    </div>
  );
}

function MultiSelectionState({ count }: { count: number }) {
  return (
    <div className="rounded-md border border-slate-300 bg-slate-50 p-3 text-center">
      <div className="text-xs font-medium text-slate-700">
        {count}개 선택됨
      </div>
      <p className="mt-1 text-[11px] leading-snug text-slate-500">
        단일 선택 시 상세 편집이 활성화됩니다.
        <br />
        다중 선택 상태에서도 "삭제" 와 그룹 드래그는 가능합니다.
      </p>
    </div>
  );
}

/* ─────────────────────────────────────────────
 * Activity 편집기
 * ───────────────────────────────────────────── */

function ActivityEditor({ node }: { node: FlowNode }) {
  const { updateActivityField } = useFlow();
  const data = node.data as ActivityNodeData;
  const a = data.activity;
  const update = (partial: Partial<Activity>) =>
    updateActivityField(node.id, partial);

  return (
    <div className="flex flex-col gap-3">
      <Badge tone="navy">활동 (Activity)</Badge>

      <BoxSizeEditor
        node={node}
        defaultWidth={activityNodeDesign.width}
        defaultHeight={88}
      />

      <Row>
        <Field label="활동번호" hint="A 칸에 표시">
          <input
            type="number"
            min={0}
            value={a.actNo}
            onChange={(e) => update({ actNo: Number(e.target.value) || 0 })}
            className={inputCls}
            style={{ width: 70 }}
          />
        </Field>
      </Row>

      <Field label="활동명" hint="C 칸 굵게 표시">
        <input
          type="text"
          value={a.actName}
          onChange={(e) => update({ actName: e.target.value })}
          className={inputCls}
        />
      </Field>

      <Field
        label="수행팀 (TEAM_OVERRIDE)"
        hint="비워두면 RCM의 controlOrg 사용"
      >
        <input
          type="text"
          value={a.teamOverride}
          onChange={(e) => update({ teamOverride: e.target.value })}
          placeholder={a.rcm?.controlOrg || ""}
          className={inputCls}
        />
      </Field>

      {/* v8 — 통제 정보 직접 입력 (매핑 시트 CONTROL_NO/CONTROL_TYPE/KEY_CA) */}
      <div className="mt-1 rounded-md border border-slate-200 bg-slate-50/60 p-2">
        <SectionLabel>통제 정보 (v8 — 매핑 시트 직접 입력)</SectionLabel>
        <div className="mt-2 flex flex-col gap-3">
          <Field
            label="통제번호 (CONTROL_NO)"
            hint="비우면 RCM의 통제번호 자동 사용"
          >
            <input
              type="text"
              value={a.controlNo ?? ""}
              onChange={(e) =>
                update({ controlNo: e.target.value || undefined })
              }
              placeholder={a.rcm?.controlNo || "C.FA.2.1-1"}
              className={inputCls}
            />
          </Field>
          <Field label="통제구분 (CONTROL_TYPE)" hint="통제 박스 우측 칩 색 (M=Manual · A=Auto · I=ITDM)">
            <div className="inline-flex overflow-hidden rounded border border-slate-300 text-xs">
              {(["M", "A", "I"] as ControlTypeSymbol[]).map((k) => {
                const cur = (a.controlTypeRaw ?? "").trim().toUpperCase();
                const isActive = cur === k;
                return (
                  <button
                    key={k}
                    type="button"
                    onClick={() => update({ controlTypeRaw: k })}
                    className={
                      "px-3 py-1 transition " +
                      (isActive
                        ? "bg-slate-900 text-white"
                        : "bg-white text-slate-700 hover:bg-slate-100")
                    }
                  >
                    {k === "M" ? "M · Manual" : k === "A" ? "A · Auto" : "I · ITDM"}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => update({ controlTypeRaw: "" })}
                className="border-l border-slate-300 bg-white px-2 py-1 text-slate-500 hover:bg-slate-100"
                title="값 지움 → RCM 의 통제유형 자동 사용"
              >
                지움
              </button>
            </div>
          </Field>
          <Field label="Key Control 여부 (KEY_CA)" hint="Y = Key, N = Non-Key">
            <div className="inline-flex overflow-hidden rounded border border-slate-300 text-xs">
              {(["Y", "N"] as const).map((k) => {
                const cur = (a.keyCaRaw ?? "").trim().toUpperCase();
                const isActive =
                  k === "Y"
                    ? cur === "Y" || cur === "YES" || cur === "TRUE" || cur === "KEY"
                    : cur === "N" || cur === "NO" || cur === "FALSE";
                return (
                  <button
                    key={k}
                    type="button"
                    onClick={() => update({ keyCaRaw: k })}
                    className={
                      "px-3 py-1 transition " +
                      (isActive
                        ? "bg-slate-900 text-white"
                        : "bg-white text-slate-700 hover:bg-slate-100")
                    }
                  >
                    {k === "Y" ? "Y · Key" : "N · Non-Key"}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => update({ keyCaRaw: "" })}
                className="border-l border-slate-300 bg-white px-2 py-1 text-slate-500 hover:bg-slate-100"
                title="값 지움 → RCM 의 Key 여부 자동 사용"
              >
                지움
              </button>
            </div>
          </Field>
        </div>
      </div>

      <Field
        label="SUB_STEPS (단계별로 줄바꿈으로 입력)"
        hint={
          parseSubSteps(a.subSteps).length > 0
            ? `${parseSubSteps(a.subSteps).length}개 단계 — 캔버스/PPT 에 ①②③… 자동 번호`
            : "한 줄에 한 단계씩. Enter 로 단계 추가"
        }
      >
        <textarea
          rows={6}
          value={a.subSteps}
          onChange={(e) => update({ subSteps: e.target.value })}
          placeholder={"단계 1\n단계 2\n단계 3"}
          className={inputCls}
        />
      </Field>

      <Field label="발생위치 / IT시스템" hint="D 칸 (비면 'Manual')">
        <input
          type="text"
          value={a.rcm?.itSystem ?? ""}
          onChange={(e) =>
            update({
              rcm: { ...(a.rcm ?? blankRcm(a.rcmRow)), itSystem: e.target.value },
            })
          }
          placeholder="Manual"
          className={inputCls}
        />
      </Field>

      <Field label="문서 (DOC_NAMES)" hint="쉼표로 구분">
        <input
          type="text"
          value={a.docNames}
          onChange={(e) => update({ docNames: e.target.value })}
          className={inputCls}
        />
      </Field>

      <Field label="비고 (NOTE)">
        <input
          type="text"
          value={a.note}
          onChange={(e) => update({ note: e.target.value })}
          className={inputCls}
        />
      </Field>
    </div>
  );
}

function blankRcm(rowNum: number) {
  return {
    rowNum,
    process: "",
    processName: "",
    subProcessNo: "",
    subProcessName: "",
    narrative: "",
    riskNo: "",
    riskDesc: "",
    controlNo: "",
    controlName: "",
    controlDesc: "",
    itSystem: "",
    controlOwner: "",
    controlOrg: "",
    keyCa: "",
    controlType: "",
  };
}

/* ─────────────────────────────────────────────
 * Shape 편집기 (8종 도형 공용)
 * ───────────────────────────────────────────── */

function ShapeEditor({ node }: { node: FlowNode }) {
  const { updateShapeField } = useFlow();
  const data = node.data as ShapeNodeData;
  const def = SHAPES.find((s) => s.key === data.shapeKey);
  const update = (partial: Partial<ShapeNodeData>) =>
    updateShapeField(node.id, partial);

  const baseDimsForVariant = shapeNodeDesign[data.shapeKey as NonActivityShape];

  // 통제구분만 라벨이 A/M/I 셋 중 하나이므로 라디오로 노출.
  if (data.shapeKey === "controlType") {
    const letter = (data.label || "M").toUpperCase().charAt(0) as
      | "A"
      | "M"
      | "I";
    return (
      <div className="flex flex-col gap-3">
        <Badge tone="pink">{def?.label ?? "도형"}</Badge>
        <BoxSizeEditor
          node={node}
          defaultWidth={baseDimsForVariant.width}
          defaultHeight={baseDimsForVariant.height}
        />
        <Field label="유형" hint="A=Auto · M=Manual · I=ITDM">
          <div className="inline-flex overflow-hidden rounded border border-slate-300 text-xs">
            {(["A", "M", "I"] as const).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => update({ label: k })}
                className={
                  "px-3 py-1 transition " +
                  (letter === k
                    ? "bg-slate-900 text-white"
                    : "bg-white text-slate-700 hover:bg-slate-100")
                }
              >
                {k}
              </button>
            ))}
          </div>
        </Field>
      </div>
    );
  }

  // Start/End 노드는 라벨이 사실상 START / END 둘 중 하나라서 토글로 노출.
  if (data.shapeKey === "startEnd") {
    const isEnd = data.label.toUpperCase() === "END";
    return (
      <div className="flex flex-col gap-3">
        <Badge tone="slate">{def?.label ?? "도형"}</Badge>
        <BoxSizeEditor
          node={node}
          defaultWidth={baseDimsForVariant.width}
          defaultHeight={baseDimsForVariant.height}
        />
        <Field label="종류" hint="프로세스의 시작 / 끝">
          <div className="inline-flex overflow-hidden rounded border border-slate-300 text-xs">
            <button
              type="button"
              onClick={() => update({ label: "START" })}
              className={
                "px-3 py-1 transition " +
                (!isEnd
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 hover:bg-slate-100")
              }
            >
              START
            </button>
            <button
              type="button"
              onClick={() => update({ label: "END" })}
              className={
                "border-l border-slate-300 px-3 py-1 transition " +
                (isEnd
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 hover:bg-slate-100")
              }
            >
              END
            </button>
          </div>
        </Field>
        <Field label="라벨 (직접 수정)" hint="START / END 외 텍스트도 입력 가능">
          <input
            type="text"
            value={data.label}
            onChange={(e) => update({ label: e.target.value })}
            className={inputCls}
          />
        </Field>
      </div>
    );
  }

  const baseDims = shapeNodeDesign[data.shapeKey as NonActivityShape];

  return (
    <div className="flex flex-col gap-3">
      <Badge tone="slate">{def?.label ?? "도형"}</Badge>

      <BoxSizeEditor
        node={node}
        defaultWidth={baseDims.width}
        defaultHeight={baseDims.height}
      />

      <Field label="라벨" hint="도형 본문에 표시되는 텍스트">
        <input
          type="text"
          value={data.label}
          onChange={(e) => update({ label: e.target.value })}
          className={inputCls}
        />
      </Field>

      <Field label="보조 라벨" hint="두 번째 줄 (선택 사항)">
        <input
          type="text"
          value={data.sublabel ?? ""}
          onChange={(e) =>
            update({ sublabel: e.target.value || undefined })
          }
          className={inputCls}
        />
      </Field>
    </div>
  );
}

/* ─────────────────────────────────────────────
 * Edge 편집기 — 모양 / 실선·점선
 * ───────────────────────────────────────────── */

function EdgeEditor({ edge }: { edge: Edge }) {
  const { updateEdge } = useFlow();
  const currentShape = (edge.type as EdgeShape) ?? "smoothstep";
  const isDashed = !!(edge.style as CSSProperties | undefined)?.strokeDasharray;
  const currentLabel =
    typeof edge.label === "string" ? edge.label : "";

  const setShape = (s: EdgeShape) => updateEdge(edge.id, { type: s });
  const setLabel = (v: string) =>
    updateEdge(edge.id, { label: v || undefined });
  const setDashed = (dashed: boolean) => {
    const baseStyle: CSSProperties = {
      stroke: C.edgeStroke,
      strokeWidth: C.edgeStrokeWidth,
    };
    updateEdge(edge.id, {
      style: dashed
        ? { ...baseStyle, strokeDasharray: C.edgeDashedPattern }
        : baseStyle,
    });
  };

  return (
    <div className="flex flex-col gap-3">
      <Badge tone="navy">엣지 (Edge)</Badge>

      <Field label="모양">
        <div className="inline-flex overflow-hidden rounded border border-slate-300 text-xs">
          {(["straight", "smoothstep", "default"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setShape(s)}
              className={
                "px-2 py-0.5 transition " +
                (currentShape === s
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-700 hover:bg-slate-100")
              }
            >
              {EDGE_SHAPE_LABELS[s]}
            </button>
          ))}
        </div>
      </Field>

      <Field label="선" hint="실선 = 프로세스 흐름 · 점선 = 데이터/정보 흐름">
        <div className="inline-flex overflow-hidden rounded border border-slate-300 text-xs">
          <button
            type="button"
            onClick={() => setDashed(false)}
            className={
              "px-3 py-0.5 transition " +
              (!isDashed
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-700 hover:bg-slate-100")
            }
          >
            실선
          </button>
          <button
            type="button"
            onClick={() => setDashed(true)}
            className={
              "border-l border-slate-300 px-3 py-0.5 transition " +
              (isDashed
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-700 hover:bg-slate-100")
            }
          >
            점선
          </button>
        </div>
      </Field>

      <Field
        label="라벨"
        hint='분기 화살표 위에 표시되는 텍스트 (예: "상각", "금융비용 자본화")'
      >
        <input
          type="text"
          value={currentLabel}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="비워두면 라벨 없음"
          className={inputCls}
        />
      </Field>

      <div className="text-[10px] leading-snug text-slate-500">
        엣지의 source · target 변경은 캔버스에서 핸들을 다시 끌어
        연결해주세요. 핸들 자석 반경 안에서 자동으로 잡힙니다.
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
 * 작은 UI 헬퍼
 * ───────────────────────────────────────────── */

const inputCls =
  "w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-900 outline-none focus:border-slate-500";

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] font-medium text-slate-700">{label}</label>
      {children}
      {hint && <div className="text-[10px] text-slate-400">{hint}</div>}
    </div>
  );
}

function Row({ children }: { children: ReactNode }) {
  return <div className="flex items-end gap-3">{children}</div>;
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
      {children}
    </div>
  );
}

/**
 * 도형 외곽 치수(customWidth/customHeight) 입력 — 활동/도형 공용.
 *  - node.data.customWidth / node.data.customHeight 를 갱신
 *  - 캔버스 NodeResizer 의 onResize 도 같은 필드를 갱신 → 단일 소스
 */
function BoxSizeEditor({
  node,
  defaultWidth,
  defaultHeight,
}: {
  node: FlowNode;
  defaultWidth: number;
  defaultHeight: number;
}) {
  const { setNodes } = useFlow();
  const data = node.data as { customWidth?: number; customHeight?: number };
  const w = Math.round(data.customWidth ?? defaultWidth);
  const h = Math.round(data.customHeight ?? defaultHeight);

  function update(partial: { customWidth?: number; customHeight?: number }) {
    setNodes((prev) =>
      prev.map((n) => {
        if (n.id !== node.id) return n;
        // 타입 안전: data shape 보존하면서 customWidth/Height 만 머지
        const merged = { ...(n.data as object), ...partial };
        return { ...n, data: merged as typeof n.data };
      }),
    );
  }

  return (
    <Field label="크기 (px)" hint="모서리 드래그로도 조절 가능">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 items-center gap-1">
          <span className="text-[10px] text-slate-500">W</span>
          <input
            type="number"
            min={20}
            value={w}
            onChange={(e) =>
              update({ customWidth: Number(e.target.value) || w })
            }
            className={inputCls + " text-right"}
          />
        </div>
        <div className="flex flex-1 items-center gap-1">
          <span className="text-[10px] text-slate-500">H</span>
          <input
            type="number"
            min={16}
            value={h}
            onChange={(e) =>
              update({ customHeight: Number(e.target.value) || h })
            }
            className={inputCls + " text-right"}
          />
        </div>
        <button
          type="button"
          onClick={() =>
            update({
              customWidth: defaultWidth,
              customHeight: defaultHeight,
            })
          }
          className="rounded border border-slate-300 px-2 py-1 text-[10px] text-slate-600 hover:border-slate-500"
          title="기본 크기로 재설정"
        >
          리셋
        </button>
      </div>
    </Field>
  );
}

function Badge({
  tone,
  children,
}: {
  tone: "navy" | "pink" | "slate";
  children: ReactNode;
}) {
  const cls =
    tone === "navy"
      ? "bg-slate-900 text-white"
      : tone === "pink"
        ? "bg-icfr-keyCtrl text-white"
        : "bg-slate-200 text-slate-700";
  return (
    <span
      className={
        "inline-flex w-fit items-center rounded px-2 py-0.5 text-[10px] font-semibold " +
        cls
      }
    >
      {children}
    </span>
  );
}
