import { useEffect, useMemo, useState } from "react";
import { emptyManualRisk } from "../types";
import { useFlow } from "../state/flowState";
import {
  Modal,
  ModalField,
  ModalFooter,
  ModalSection,
  inputCls,
} from "./Modal";

/**
 * 위험 추가 모달 — 좌측 사이드바 위험 섹션의 [+] 버튼에서 호출.
 *
 *   - 위험번호·설명 입력
 *   - 옵션: 기존 통제와 연관시킴 (드롭다운에서 선택)
 */
export function AddRiskModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { addRisk, controls, risks } = useFlow();
  const [draft, setDraft] = useState(() => emptyManualRisk());
  const [linkMode, setLinkMode] = useState<"none" | "link">("none");

  useEffect(() => {
    if (open) {
      setDraft(emptyManualRisk());
      setLinkMode("none");
    }
  }, [open]);

  const setField = <K extends keyof typeof draft>(
    k: K,
    v: (typeof draft)[K],
  ) => setDraft((d) => ({ ...d, [k]: v }));

  const dupRiskNo = useMemo(
    () =>
      risks.some(
        (r) => r.riskNo.trim() && r.riskNo.trim() === draft.riskNo.trim(),
      ),
    [risks, draft.riskNo],
  );

  const confirmDisabled =
    !draft.riskNo.trim() ||
    dupRiskNo ||
    (linkMode === "link" && !draft.linkedControlId);

  const onSave = () => {
    if (confirmDisabled) return;
    addRisk({
      ...draft,
      linkedControlId:
        linkMode === "link" ? draft.linkedControlId : undefined,
    });
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="새 위험 추가" width={460}>
      <ModalSection title="기본 정보">
        <ModalField label="위험번호" required hint="예: R.CM.1-1">
          <input
            type="text"
            value={draft.riskNo}
            onChange={(e) => setField("riskNo", e.target.value)}
            className={inputCls}
            placeholder="R.CM.1-1"
          />
          {dupRiskNo && (
            <span className="text-[10px] text-rose-500">
              ⚠ 이미 사용 중인 위험번호입니다.
            </span>
          )}
        </ModalField>
        <ModalField label="위험 설명" required>
          <textarea
            value={draft.riskDesc}
            onChange={(e) => setField("riskDesc", e.target.value)}
            className={inputCls + " min-h-[60px] resize-y"}
            placeholder="위험 내용을 설명…"
          />
        </ModalField>
      </ModalSection>

      <ModalSection title="연관 통제 (선택)">
        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="radio"
              checked={linkMode === "none"}
              onChange={() => setLinkMode("none")}
            />
            새 위험만 추가
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="radio"
              checked={linkMode === "link"}
              onChange={() => setLinkMode("link")}
              disabled={controls.length === 0}
            />
            기존 통제와 연관:
            <select
              value={draft.linkedControlId ?? ""}
              onChange={(e) =>
                setField("linkedControlId", e.target.value || undefined)
              }
              disabled={linkMode !== "link" || controls.length === 0}
              className={inputCls + " ml-1"}
            >
              <option value="">통제 선택…</option>
              {controls.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.controlNo} · {c.controlName || c.flowchartCode}
                </option>
              ))}
            </select>
          </label>
        </div>
      </ModalSection>

      <ModalFooter
        onCancel={onClose}
        onConfirm={onSave}
        confirmLabel="위험 추가"
        confirmDisabled={confirmDisabled}
      />
    </Modal>
  );
}
