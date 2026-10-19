import * as XLSX from "xlsx";

/**
 * 작성 템플릿(.xlsx) 생성·다운로드 — 브라우저 안에서 SheetJS 로 만든다.
 *
 *   시트 구성
 *     1. Flowchart   : 한 행 = 박스 1개. 예시 1개 flowchart (유형자산 유지보수, ABC주식회사 가상 데이터)
 *     2. 헤더정보    : 회사명·작성자·Last Change Date (선택)
 *     3. 작성가이드  : 열 설명과 규칙
 *
 *   열 이름 끝의 * 는 필수 열. 파서는 * · 공백 · 괄호를 무시하고 매칭한다.
 */

const COLUMNS: Array<{ name: string; width: number; guide: string }> = [
  { name: "Flowchart Code*", width: 14, guide: "flowchart 구분 코드. 같은 코드끼리 한 장으로 그려집니다. (필수)" },
  { name: "대분류 코드", width: 10, guide: "선택. 예: FA" },
  { name: "대분류", width: 12, guide: "헤더 표 '대분류'. 예: 고정자산" },
  { name: "중분류 코드", width: 10, guide: "선택" },
  { name: "중분류", width: 12, guide: "헤더 표 '중분류'. 예: 자산관리" },
  { name: "소분류 코드", width: 10, guide: "선택" },
  { name: "소분류", width: 12, guide: "헤더 표 '소분류'. 비우면 중분류 또는 Code 를 사용" },
  { name: "ID*", width: 6, guide: "같은 Code 안에서 겹치지 않는 번호. 활동은 1, 2, 3… 분기는 D1, Link 는 L1 처럼 (필수)" },
  { name: "유형", width: 8, guide: "비움 = 활동 / 분기 = 마름모 / Link = 다른 프로세스 연결" },
  { name: "활동명*", width: 20, guide: "박스에 표시할 이름 (필수)" },
  { name: "Next ID", width: 14, guide: "다음 박스 ID. 비우면 아래 행으로 이어짐. 분기는 3(Y), L1(N) 처럼 라벨을 괄호로. 마지막은 END" },
  { name: "업무기술(Narrative)", width: 44, guide: "PPT 의 Narrative 표에 들어갈 설명" },
  { name: "담당부서", width: 12, guide: "박스 상단 수행팀. 스윔레인 배치에서는 레인 이름" },
  { name: "시스템", width: 10, guide: "박스 하단 발생 위치. 예: 전사 ERP, Manual" },
  { name: "문서", width: 18, guide: "박스 아래 문서 도형. 여러 개는 쉼표로" },
  { name: "DB", width: 8, guide: "박스 아래 DB 도형 (저장되는 테이블·전표). 예: BKPF" },
  { name: "위험번호", width: 12, guide: "박스 위 노란 위험 뱃지" },
  { name: "위험내용", width: 34, guide: "Narrative 표에 표시" },
  { name: "통제번호", width: 12, guide: "박스 위 통제 뱃지" },
  { name: "통제명", width: 18, guide: "Narrative 표에 표시" },
  { name: "통제내용", width: 40, guide: "Narrative 표에 표시" },
  { name: "Key 여부(Y/N)", width: 10, guide: "Y = Key, N = Non-Key, 비우면 미지정(회색)" },
  { name: "통제유형(A/M/I)", width: 12, guide: "A = Automated, M = Manual, I = IT Dependent Manual" },
  { name: "세부단계", width: 24, guide: "선택. 박스 안에 ①②③ 로 표시할 단계 (셀 안 줄바꿈으로 구분)" },
  { name: "레인 순서", width: 8, guide: "선택. 스윔레인에서 레인을 위에서부터 놓을 순서 (숫자)" },
];

// 예시 — ABC주식회사 가상 데이터 (분기 2개, 합류, Link, DB, 문서, 통제 포함)
const H = ["FA21", "FA", "고정자산", "2", "자산관리", "1", "유지보수"];
const SAMPLE: Array<Array<string>> = [
  [...H, "1", "", "유지보수 요청", "2",
    "현업부서는 설비 이상을 확인하고 작업지시서를 작성하여 유지보수를 요청한다.",
    "현업부서", "Manual", "작업지시서", "", "", "", "", "", "", "", "", "", "1"],
  [...H, "2", "", "견적 접수 및 기안", "D1",
    "설비지원팀은 외부 업체 견적을 받아 유지보수 기안을 작성하고 결재를 받는다.",
    "설비지원팀", "Manual", "견적서, 기안서", "", "", "", "", "", "", "", "", "", "2"],
  [...H, "D1", "분기", "자본적 지출?", "3(Y), 4(N)",
    "내용연수 연장·가치 증가 여부로 자본적 지출 해당 여부를 판단한다.",
    "회계팀", "", "", "", "", "", "", "", "", "", "", "", "3"],
  [...H, "3", "", "자산 원가 가산", "5",
    "회계팀은 자본적 지출 해당분을 자산 원가에 가산하여 등록한다.",
    "회계팀", "전사 ERP", "", "ANLA",
    "R.FA.2.1-1", "수선비와 자본적 지출의 구분 오류로 자산·비용이 왜곡될 위험",
    "C.FA.2.1-1", "자본적 지출 구분 검토",
    "회계팀장은 기안서·견적서를 근거로 자본적 지출 해당 여부를 검토하고 승인한다.",
    "Y", "M", "", "3"],
  [...H, "4", "", "수선비 비용 처리", "5",
    "회계팀은 자본적 지출이 아닌 건을 수선유지비로 비용 처리한다.",
    "회계팀", "전사 ERP", "수선유지비 전표", "", "", "", "", "", "", "", "", "", "3"],
  [...H, "5", "", "작업 완료 확인", "D2",
    "현업부서는 유지보수 작업 완료를 확인하고 완료보고서를 작성한다.",
    "현업부서", "Manual", "완료보고서", "", "", "", "", "", "", "", "", "", "1"],
  [...H, "D2", "분기", "작업 결과 적정?", "6(Y), L1(N)",
    "작업 결과가 요청 내역과 일치하면 대금 지급을 진행하고, 아니면 하자 보수 프로세스로 이관한다.",
    "현업부서", "", "", "", "", "", "", "", "", "", "", "", "1"],
  [...H, "L1", "Link", "하자 보수 요청 (FA22)", "",
    "하자 건은 하자 보수 프로세스(FA22)에서 처리한다.",
    "현업부서", "", "", "", "", "", "", "", "", "", "", "", "1"],
  [...H, "6", "", "대금 지급 전표 승인", "END",
    "회계팀장은 거래명세서와 완료보고서를 대조하여 지급 전표를 승인한다.",
    "회계팀", "전사 ERP", "거래명세서", "BKPF",
    "R.FA.2.1-2", "승인되지 않은 유지보수 대금이 지급될 위험",
    "C.FA.2.1-2", "지급 전표 승인",
    "회계팀장은 지급 전표를 거래명세서·완료보고서와 대조하여 승인한다.",
    "Y", "M", "", "3"],
];

const GUIDE: string[][] = [
  ["Flowchart 작성 가이드"],
  [""],
  ["1. 'Flowchart' 시트에 한 행 = 박스 1개로 입력합니다. 엑셀 행 순서대로 배치됩니다."],
  ["2. 화살표는 'Next ID' 로 연결합니다. 비워 두면 바로 아래 행으로 이어지고, 마지막 행은 END 로 이어집니다."],
  ["3. 분기(유형 = 분기)는 'Next ID' 에 3(Y), L1(N) 처럼 갈래를 쉼표로 적습니다. 괄호 안 글자가 화살표 라벨이 됩니다 (승인/반려 등 한글 가능)."],
  ["4. Link(유형 = Link)는 다른 프로세스로 넘어가는 연결입니다. 분기에서만 들어오고 Next ID 가 비어 있으면 분기 바로 아래에 붙습니다."],
  ["5. '헤더정보' 시트의 회사명·작성자·Last Change Date 는 PPT 상단 표에 들어갑니다 (선택)."],
  ["6. 열 이름 끝의 * 는 필수 열입니다. 열 순서는 바꿔도 되고, 필요 없는 선택 열은 지워도 됩니다."],
  ["7. 업로드 후 화면 상단에서 '스네이크 / 스윔레인' 배치를 고를 수 있습니다."],
  [""],
  ["열", "설명"],
  ...COLUMNS.map((c) => [c.name, c.guide]),
];

export function downloadTemplate(fileName = "Flowchart_작성템플릿.xlsx") {
  const wb = XLSX.utils.book_new();

  const main = XLSX.utils.aoa_to_sheet([COLUMNS.map((c) => c.name), ...SAMPLE]);
  main["!cols"] = COLUMNS.map((c) => ({ wch: c.width }));
  main["!freeze"] = { xSplit: 0, ySplit: 1 };
  XLSX.utils.book_append_sheet(wb, main, "Flowchart");

  const header = XLSX.utils.aoa_to_sheet([
    ["항목", "값"],
    ["회사명", "ABC주식회사"],
    ["작성자", ""],
    ["Last Change Date", new Date().toISOString().slice(0, 10)],
  ]);
  header["!cols"] = [{ wch: 18 }, { wch: 24 }];
  XLSX.utils.book_append_sheet(wb, header, "헤더정보");

  const guide = XLSX.utils.aoa_to_sheet(GUIDE);
  guide["!cols"] = [{ wch: 22 }, { wch: 90 }];
  XLSX.utils.book_append_sheet(wb, guide, "작성가이드");

  XLSX.writeFile(wb, fileName);
}
