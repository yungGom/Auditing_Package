import { useFlow } from "../state/flowState";
import { icfrColors } from "../design";

/**
 * 캔버스 상단 작은 헤더 표 — 회사 산출물 PPT 의 상단 표와 동일 정보를
 * 캔버스에서도 항상 보이도록 띠로 깔아둔다.
 *
 * 표시 항목: 회사명 / 대분류 / 중분류 · 소분류 / Flowchart Code / Last Change Date
 *  - 라벨 셀: 진분홍 배경 (#B4185C), 흰 글자
 *  - 값 셀: 흰 배경, 검정 글자
 *  - 비어있으면 "—" 로 표시
 *
 * 캔버스 위 floating overlay (React Flow 와 분리). PPT 생성 시점에는
 * pptxgenjs 가 동일 데이터를 가지고 다시 그린다.
 */
export function CanvasHeaderTable() {
  const { headerInfo } = useFlow();

  const middleSub = [headerInfo.middleCategory, headerInfo.subProcessName]
    .filter(Boolean)
    .join(" / ");

  const cells: Array<{ label: string; value: string }> = [
    { label: "회사명", value: headerInfo.company || "—" },
    { label: "대분류", value: headerInfo.processName || "—" },
    { label: "중/소분류", value: middleSub || "—" },
    { label: "Flowchart\nCode", value: headerInfo.flowchartCode || "—" },
    { label: "Last Change\nDate", value: headerInfo.lastChangeDate || "—" },
  ];

  return (
    <div className="pointer-events-none absolute left-0 right-0 top-0 z-10 px-3 pt-2">
      <div className="pointer-events-auto mx-auto flex max-w-[1100px] items-stretch overflow-hidden rounded-md border border-slate-300 bg-white text-[10px] shadow-sm">
        {cells.map((c, i) => (
          <div key={i} className="flex shrink-0 items-stretch">
            <div
              className="flex items-center justify-center whitespace-pre-line px-2 py-1 font-semibold leading-tight text-white"
              style={{
                backgroundColor: icfrColors.headerBg,
                minWidth: 56,
              }}
            >
              {c.label}
            </div>
            <div
              className="flex items-center px-2 py-1 leading-tight text-slate-900"
              style={{ minWidth: 90 }}
            >
              <span className="truncate">{c.value}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
