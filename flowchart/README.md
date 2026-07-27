# ICFR Flowchart Generator

내부회계관리제도(ICFR) 평가 시 작성하는 **표준 Flowchart** 를 RCM(Risk Control
Matrix) 엑셀에서 자동으로 만들어주는 도구입니다. 캔버스에서 도형을 드래그하고
화살표를 다시 그릴 수 있어, 리뷰 코멘트에 즉시 대응한 뒤 그대로 PPT 로
내려받을 수 있습니다. 브라우저에서 바로 쓰거나, Electron 포터블 EXE로
설치 없이 배포할 수 있습니다.

> **보안 원칙**: 모든 처리는 클라이언트 안에서 일어납니다. 백엔드가 없고
> 외부 API/서버 통신이 일절 없으며, 인터넷 연결이 끊긴 상태에서도 동작합니다.
> Electron 셸은 이를 코드로 강제합니다 — `sandbox` + `contextIsolation` 활성,
> devTools 비활성, `onBeforeRequest`로 `file:/blob:/data:` 외 모든 네트워크
> 요청 차단, 외부 URL 네비게이션·새 창 전면 차단.

## 구현 현황

**완료** — 엑셀 업로드부터 PPT 다운로드까지 전체 파이프라인이 연결되어 있습니다.

- RCM 엑셀 파싱: 컬럼 별칭 매칭, 병합셀 그룹헤더 처리, 엑셀 날짜 직렬값 보정, 경고 수집
- 파싱 결과 → 노드/엣지 자동 배치 (다중 flowchart 동시 생성 + 탭 전환)
- 캔버스 인라인 편집: 도형 팔레트 11종, 속성 편집 패널, Control/Risk 추가·복제 모달
- undo/redo, 복사/붙여넣기/복제/전체선택(Ctrl+C/V/D/A), 노드 잠금, 단축키 시스템(`?` 도움말)
- PPT 내보내기: 4:3(720×540pt) 슬라이드에 헤더 테이블·도형·연결선 렌더
- 디자인 프리뷰 뷰 (PPT 출력 미리보기)
- Electron 포터블 EXE 빌드

**미구현(로드맵)** — 매핑 시트 역(逆)export · localStorage 자동 저장 · `.flow.json` 프로젝트 파일

**갭** — 자동화 테스트가 없습니다. `xlsxParser`·`pptExport` 같은 변환 로직에
테스트를 붙이는 것이 우선 과제이며, 현재는 `npm run typecheck`와 수동 검증에 의존합니다.

## 기술 스택

- Vite + React 18 + TypeScript
- [React Flow](https://reactflow.dev/) — 인터랙티브 캔버스
- Tailwind CSS — 스타일
- [SheetJS (xlsx)](https://sheetjs.com/) — 엑셀 파싱
- [pptxgenjs](https://gitbrent.github.io/PptxGenJS/) — PPT 생성
- Electron + electron-builder — 포터블 EXE (win portable)

## 실행

```bash
cd flowchart
npm install
npm run dev              # http://127.0.0.1:5173
```

| 목적 | 명령 |
|---|---|
| 타입체크 | `npm run typecheck` |
| 웹 빌드 | `npm run build` |
| Electron 실행 | `npm run electron` |
| 포터블 EXE | `npm run electron:build` → `release/ICFR-Flowchart-Generator-portable.exe` |

첫 화면에는 부트스트랩 더미 flowchart가 그려져 있으며, 상단바에서 RCM 엑셀을
업로드하면 실제 flowchart가 생성됩니다.

## 폴더 구조

```
flowchart/
├─ src/
│  ├─ App.tsx                   # canvas/design 뷰 전환
│  ├─ types.ts                  # 데이터 모델 (HeaderInfo, RcmRow, Activity, Control, Risk)
│  ├─ shapes.ts                 # 도형 팔레트 11종 정의
│  ├─ design.ts                 # 색상/치수 토큰 (Python 원본 규칙 이식)
│  ├─ state/                    # 중앙 스토어(undo/redo)·단축키·복사붙여넣기·초기 flowchart
│  ├─ parsing/                  # xlsxParser(RCM 파싱) + buildFlowFromExcel(자동 배치)
│  ├─ export/pptExport.ts       # PPT 렌더링
│  └─ components/               # 캔버스·노드·상단바·사이드바·편집 패널·모달·디자인 프리뷰
├─ electron/main.cjs            # Electron 셸 (보안 하드닝)
├─ references/                  # Python 원본·예시 엑셀·예시 PPT (커밋됨)
│  └─ flowchart_generator.py    # 색상/레이아웃/도형 규칙의 출처
├─ index.html
├─ vite.config.ts
├─ tailwind.config.ts
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
[`tailwind.config.ts`](tailwind.config.ts) 의 `icfr.*` 색상 토큰으로 둡니다.

도형 팔레트: Link · Start/End · 활동 · DB · 분기점 · 문서 · I/F · Risk ·
Key 통제 · Non-Key 통제 · 통제구분(M/A/I) · 텍스트

| 용도            | 색상      |
| --------------- | --------- |
| 헤더 / Key Ctrl | `#B4185C` |
| Non-Key Ctrl    | `#E27D9E` |
| Risk            | `#FFC000` |
| DB              | `#E0356A` |
| 문서            | `#D9D9D9` |
| START/END       | `#1F3A5F` |

## 로드맵

- ~~**1단계** 엑셀 파싱 → 자동 노드 배치 → 인라인 편집 → PPT 다운로드~~ ✅ 완료
- ~~**2단계** 분기 노드, 자유 화살표, 활동 순서 변경~~ ✅ 완료 (매핑 시트 역(逆)export만 잔여)
- **3단계** localStorage 자동 저장, `.flow.json` 프로젝트 파일
- **품질** 파싱·PPT 렌더 로직 자동화 테스트

## 라이선스

추후 LICENSE 파일 추가 예정 (MIT 검토 중).
