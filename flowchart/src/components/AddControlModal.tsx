import { useEffect, useMemo, useState } from "react";
import type { ControlData, ControlTypeSymbol } from "../types";
import { emptyManualControl, emptyManualRisk } from "../types";
import { useFlow } from "../state/flowState";
import {
  Modal,
  ModalField,
  ModalFooter,
  ModalSection,
  inputCls,
} from "./Modal";

/**
 * 통제 추가/편집 모달.
 *
 *   mode="add"  : 빈 폼에서 시작. 저장 시 addControl + (옵션) addRisk
 *                 → 빈 flowchart 자동 생성 + 캔버스 전환
 *   mode="edit" : 기존 통제(엑셀·수기 무관) 의 일부 필드 수정.
 *                 엑셀 통제는 controlNo / flowchartCode 같은 키는 readonly.
 */
export function AddControlModal({
  open,
  onClose,
  mode,
  editTarget,
}: {
  open: boolean;
  onClose: () => void;
  mode: "add" | "edit";
  /** edit 모드일 때만 필수 */
  editTarget?: ControlData;
}) {
  const {
    addControl,
    updateControl,
    addRisk,
    controls,
    headerInfo,
  } = useFlow();

  const [draft, setDraft] = useState<Omit<ControlData, "id" | "source">>(
    () => emptyManualControl(),
  );
  const [addRiskToo, setAddRiskToo] = useState(false);
  const [riskDraft, setRiskDraft] = useState(() => emptyManualRisk());

  // open 시점에 폼 초기화 — add 면 빈값(소분류는 전역 기본값), edit 면 대상 값
  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && editTarget) {
      const { id: _id, source: _source, ...rest } = editTarget;
      void _id;
      void _source;
      setDraft(rest);
    } else {
      const empty = emptyManualControl();
      setDraft({
        ...empty,
        subProcessName: headerInfo.subProcessName || empty.subProcessName,
      });
    }
    setAddRiskToo(false);
    setRiskDraft(emptyManualRisk());
  }, [open, mode, editTarget, headerInfo.subProcessName]);

  const setField = <K extends keyof typeof draft>(
    k: K,
    v: (typeof draft)[K],
  ) => setDraft((d) => ({ ...d, [k]: v }));

  const isEdit = mode === "edit";
  const readonlyKeys = isEdit && editTarget?.source === "excel";

  // 검증 — 중복 통제번호 / flowchartCode 체크 (자기 자신 제외)
  const dupControlNo = useMemo(
    () =>
      controls.some(
        (c) =>
          c.id !== editTarget?.id &&
          c.controlNo.trim() &&
          c.controlNo.trim() === draft.controlNo.trim(),
      ),
    [controls, draft.controlNo, editTarget?.id],
  );
  const dupFlowchartCode = useMemo(
    () =>
      !isEdit &&
      controls.some(
        (c) =>
          c.flowchartCode.trim() &&
          c.flowchartCode.trim() === draft.flowchartCode.trim(),
      ),
    [controls, draft.flowchartCode, isEdit],
  );

  const requiredOk =
    draft.controlNo.trim().length > 0 &&
    draft.controlName.trim().length > 0 &&
    draft.flowchartCode.trim().length > 0 &&
    draft.subProcessName.trim().length > 0;

  const confirmDisabled =
    !requiredOk ||
    dupControlNo ||
    dupFlowchartCode ||
    (addRiskToo && !riskDraft.riskNo.trim());

  const onSave = () => {
    if (confirmDisabled) return;
    if (isEdit && editTarget) {
      updateControl(editTarget.id, draft);
    } else {
      const newControlId = addControl(draft);
      if (addRiskToo && riskDraft.riskNo.trim()) {
        addRisk({ ...riskDraft, linkedControlId: newControlId });
      }
    }
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "통제 편집" : "새 통제 추가"}
      width={520}
    >
      <ModalSection title="기본 정보">
        <ModalField label="통제번호" required hint="예: CM01, C.CM.1-1">
          <input
            type="text"
            value={draft.controlNo}
            onChange={(e) => setField("controlNo", e.target.value)}
            className={inputCls}
            disabled={readonlyKeys}
            placeholder="CM01"
          />
          {dupControlNo && (
            <span className="text-[10px] text-rose-500">
              ⚠ 이미 사용 중인 통제번호입니다.
            </span>
          )}
        </ModalField>
        <ModalField label="통제명" required>
          <input
            type="text"
            value={draft.controlName}
            onChange={(e) => setField("controlName", e.target.value)}
            className={inputCls}
            placeholder="예: 자산 감독·검토"
          />
        </ModalField>
        <div className="grid grid-cols-2 gap-3">
          <ModalField
            label="Flowchart 코드"
            required
            hint="이 통제의 flowchart 식별자"
          >
            <input
              type="text"
              value={draft.flowchartCode}
              onChange={(e) => setField("flowchartCode", e.target.value)}
              className={inputCls}
              disabled={readonlyKeys}
              placeholder="CM01"
            />
            {dupFlowchartCode && (
              <span className="text-[10px] text-rose-500">
                ⚠ 이미 사용 중입니다.
              </span>
            )}
          </ModalField>
          <ModalField label="소분류" required hint="flowchart 제목">
            <input
              type="text"
              value={draft.subProcessName}
              onChange={(e) => setField("subProcessName", e.target.value)}
              className={inputCls}
              placeholder="예: 감독·검토"
            />
          </ModalField>
        </div>
      </ModalSection>

      <ModalSection title="통제 분류">
        <div className="flex flex-col gap-2">
          <span className="text-[11px] font-medium text-slate-600">
            Key / Non-Key
          </span>
          <div className="flex gap-3 text-xs text-slate-700">
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                checked={draft.isKeyControl}
                onChange={() => setField("isKeyControl", true)}
              />
              Key Control
            </label>
            <label className="flex items-center gap-1.5">
              <input
                type="radio"
                checked={!draft.isKeyControl}
                onChange={() => setField("isKeyControl", false)}
              />
              Non-Key Control
            </label>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <span className="text-[11px] font-medium text-slate-600">
            통제유형
          </span>
          <div className="flex gap-3 text-xs text-slate-700">
            {(["M", "A", "I"] as ControlTypeSymbol[]).map((t) => (
              <label key={t} className="flex items-center gap-1.5">
                <input
                  type="radio"
                  checked={draft.controlType === t}
                  onChange={() => setField("controlType", t)}
                />
                {t === "M"
                  ? "Manual"
                  : t === "A"
                    ? "Automated"
                    : "ITDM"}
              </label>
            ))}
          </div>
        </div>
      </ModalSection>

      <ModalSection title="운영 정보">
        <ModalField label="통제 수행팀">
          <input
            type="text"
            value={draft.controlOrg}
            onChange={(e) => setField("controlOrg", e.target.value)}
            className={inputCls}
            placeholder="예: 자산관리팀"
          />
        </ModalField>
        <ModalField label="IT 시스템 / 발생위치">
          <input
            type="text"
            value={draft.itSystem}
            onChange={(e) => setField("itSystem", e.target.value)}
            className={inputCls}
            placeholder="예: SAP / Manual"
          />
        </ModalField>
        <ModalField label="통제 설명">
          <textarea
            value={draft.controlDesc}
            onChange={(e) => setField("controlDesc", e.target.value)}
            className={inputCls + " min-h-[60px] resize-y"}
            placeholder="통제 운영 방식을 설명…"
          />
        </ModalField>
      </ModalSection>

      {!isEdit && (
        <ModalSection title="연관 위험 (선택)">
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={addRiskToo}
              onChange={(e) => setAddRiskToo(e.target.checked)}
            />
            이 통제와 연관된 위험을 함께 추가
          </label>
          {addRiskToo && (
            <div className="flex flex-col gap-3 rounded-md border border-slate-200 bg-slate-50 p-3">
              <ModalField label="위험번호" required>
                <input
                  type="text"
                  value={riskDraft.riskNo}
                  onChange={(e) =>
                    setRiskDraft({ ...riskDraft, riskNo: e.target.value })
                  }
                  className={inputCls}
                  placeholder="R.CM.1-1"
                />
              </ModalField>
              <ModalField label="위험 설명">
                <textarea
                  value={riskDraft.riskDesc}
                  onChange={(e) =>
                    setRiskDraft({ ...riskDraft, riskDesc: e.target.value })
                  }
                  className={inputCls + " min-h-[50px] resize-y"}
                  placeholder="위험 내용을 설명…"
                />
              </ModalField>
            </div>
          )}
        </ModalSection>
      )}

      <ModalFooter
        onCancel={onClose}
        onConfirm={onSave}
        confirmLabel={isEdit ? "저장" : "통제 추가"}
        confirmDisabled={confirmDisabled}
      />
    </Modal>
  );
}
