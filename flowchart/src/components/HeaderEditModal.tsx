import { useEffect, useState } from "react";
import type { HeaderInfo } from "../types";
import { useFlow } from "../state/flowState";
import {
  Modal,
  ModalField,
  ModalFooter,
  ModalSection,
  inputCls,
} from "./Modal";

/**
 * 좌측 사이드바 상단 [편집] 버튼 → 전역 헤더 정보 편집.
 *
 *   - flowchartCode/subProcessName 은 통제별로 다르므로 여기서는 편집 X.
 *     (엑셀 통제는 RCM 에서 자동 추출, 수기 통제는 통제 추가 모달에서 입력)
 *   - 회사명·대분류·중분류·작성자·날짜만 전역으로 관리.
 */
export function HeaderEditModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { headerInfo, setHeaderInfo } = useFlow();
  const [draft, setDraft] = useState<HeaderInfo>(headerInfo);

  useEffect(() => {
    if (open) setDraft(headerInfo);
  }, [open, headerInfo]);

  const setField = <K extends keyof HeaderInfo>(k: K, v: HeaderInfo[K]) =>
    setDraft((d) => ({ ...d, [k]: v }));

  const onSave = () => {
    setHeaderInfo(draft);
    onClose();
  };

  // 회사명만 필수 — 나머지는 비워두면 PPT 에서 "—" 로 표시
  const confirmDisabled = !draft.company.trim();

  return (
    <Modal open={open} onClose={onClose} title="헤더 정보 편집" width={460}>
      <ModalSection title="필수 정보">
        <ModalField label="회사명" required>
          <input
            type="text"
            value={draft.company}
            onChange={(e) => setField("company", e.target.value)}
            className={inputCls}
            placeholder="예: ABC주식회사"
          />
        </ModalField>
      </ModalSection>

      <ModalSection title="프로세스 분류">
        <ModalField label="대분류">
          <input
            type="text"
            value={draft.processName}
            onChange={(e) => setField("processName", e.target.value)}
            className={inputCls}
            placeholder="예: 고정자산"
          />
        </ModalField>
        <ModalField label="중분류">
          <input
            type="text"
            value={draft.middleCategory}
            onChange={(e) => setField("middleCategory", e.target.value)}
            className={inputCls}
            placeholder="예: 자산관리"
          />
        </ModalField>
        <ModalField
          label="소분류 (기본값)"
          hint="수기 통제 추가 시 기본 소분류로 사용됨. 통제별 override 가능."
        >
          <input
            type="text"
            value={draft.subProcessName}
            onChange={(e) => setField("subProcessName", e.target.value)}
            className={inputCls}
            placeholder="예: 손상검토"
          />
        </ModalField>
      </ModalSection>

      <ModalSection title="작성 정보">
        <ModalField label="작성자">
          <input
            type="text"
            value={draft.author}
            onChange={(e) => setField("author", e.target.value)}
            className={inputCls}
            placeholder="예: 김감사"
          />
        </ModalField>
        <ModalField label="Last Change Date">
          <input
            type="text"
            value={draft.lastChangeDate}
            onChange={(e) => setField("lastChangeDate", e.target.value)}
            className={inputCls}
            placeholder="YYYY-MM-DD"
          />
        </ModalField>
      </ModalSection>

      <ModalFooter
        onCancel={onClose}
        onConfirm={onSave}
        confirmDisabled={confirmDisabled}
      />
    </Modal>
  );
}
