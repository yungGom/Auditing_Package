# ICFR Flowchart Generator

내부회계관리제도(ICFR) 평가 시 작성하는 **표준 Flowchart** 를 RCM(Risk Control
Matrix) 엑셀에서 자동으로 만들어주는 브라우저용 도구입니다. 화면에서 도형을
드래그하고 화살표를 다시 그릴 수 있어, 리뷰 코멘트에 즉시 대응한 뒤 그대로
PPT 로 내려받을 수 있습니다.

> **보안 원칙**: 모든 처리는 브라우저 안에서 일어납니다.
> 외부 API/서버 통신이 일절 없으며, 인터넷 연결이 끊긴 상태에서도 동작합니다.
> 처리 대상이 고객사 감사 데이터이기 때문에 절대 외부로 나가지 않아야 합니다.

## 기술 스택

- Vite + React 18 + TypeScript
- [React Flow](https://reactflow.dev/) — 인터랙티브 캔버스
- Tailwind CSS — 스타일
- [SheetJS (xlsx)](https://sheetjs.com/) — 엑셀 파싱
- [pptxgenjs](https://gitbrent.github.io/PptxGenJS/) — PPT 생성

## 실행

```bash
cd flowchart
npm install
npm run dev
```

브라우저에서 `http://127.0.0.1:5173` 으로 접속하면 더미 활동 3개가 그려진
캔버스가 나옵니다. (실제 RCM 업로드 기능은 다음 단계에서 붙입니다.)

## 폴더 구조

```
flowchart/
├─ src/
│  ├─ components/
│  │  ├─ ActivityNode.tsx     # 활동 박스 (4분할 + 통제유형 원형)
│  │  └─ FlowCanvas.tsx        # React Flow 캔버스
│  ├─ types.ts                  # 데이터 모델 (HeaderInfo, RcmRow, Activity)
│  ├─ App.tsx
│  ├─ main.tsx
│  └─ index.css                 # Tailwind 진입점
├─ references/                  # Python 원본·예시 엑셀·예시 PPT (커밋됨)
│  ├─ flowchart_generator.py    # 색상/레이아웃/도형 규칙의 출처
│  ├─ FA21_RCM_매핑_예시_v3.xlsx
│  └─ Python_생성_예시.pptx
├─ index.html
├─ vite.config.ts
├─ tailwind.config.js
├─ tsconfig.json
└─ package.json
```

## 데이터 모델 요약

- **HeaderInfo** — PPT 상단 헤더 박스에 들어가는 회사명·분류·코드·작성자.
- **RcmRow** — RCM 시트의 한 행 (Process Narrative 단락 단위).
  Risk 와 Control 은 같은 행에 들어있을 수도, 없을 수도 있음.
- **Activity** — 매핑 시트의 한 행 = flowchart 캔버스의 활동 노드 하나.
  `rcmRow` 로 RCM 한 행을 참조하며, JOIN 후 `rcm` 필드가 채워진다.

자세한 비즈니스 로직(통제유형 분류, 핵심통제 여부 등)은
[`src/types.ts`](src/types.ts) 와 [`references/flowchart_generator.py`](references/flowchart_generator.py) 를 보세요.

## 시각 규칙

`flowchart_generator.py` 의 색상 정의를 그대로 가져와
[`tailwind.config.js`](tailwind.config.js) 의 `icfr.*` 색상 토큰으로 둡니다.

| 용도            | 색상      |
| --------------- | --------- |
| 헤더 / Key Ctrl | `#B4185C` |
| Non-Key Ctrl    | `#E27D9E` |
| Risk            | `#FFC000` |
| DB              | `#E0356A` |
| 문서            | `#D9D9D9` |
| START/END       | `#1F3A5F` |

## 로드맵

- **1단계 (진행 중)** 엑셀 파싱 → 자동 노드 배치 → 인라인 편집 → PPT 다운로드
- **2단계** 분기 노드, 자유 화살표, 활동 순서 변경, 매핑 시트 역(逆)export
- **3단계** localStorage 자동 저장, `.flow.json` 프로젝트 파일

## 라이선스

추후 LICENSE 파일 추가 예정 (MIT 검토 중).
