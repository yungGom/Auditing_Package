# Claude Code 핸드오프 패키지 (v4 — 통제 N개 통합 RCM)

## 변경 사항 (v3 → v4)

- 단일 통제 → 통제 N개 통합 RCM
- 매핑 시트에 `FLOWCHART_CODE` 컬럼 추가
- 도구가 FLOWCHART_CODE별로 자동 그룹핑해 N개의 PPT 생성
- UI에 "현재 작업 중인 Flowchart" 드롭다운 추가
- 단일/전체 ZIP 다운로드 지원

## 사용 방법

### 1단계: 로컬 환경 준비

```bash
cd ~/Auditing_Package
git pull origin main
mkdir -p flowchart/references
```

### 2단계: 참고 파일 복사

이 폴더의 `references/` 안 파일들을 `~/Auditing_Package/flowchart/references/`로 복사:

| 파일 | 용도 |
|---|---|
| `flowchart_generator.py` | Python 버전 (참고용, React로 포팅) |
| **`FA_고정자산_RCM_매핑_예시_v4.xlsx`** | **메인 입력 양식 예시** (통제 7개, 활동 33개) |
| `Python_생성_예시.pptx` | Python 버전 출력 예시 |
| `구성정보_캡쳐.png` | 회사 표준 도형 9종 가이드 |

### 3단계: Claude Code 세션 시작

`~/Auditing_Package` 폴더에서 Claude Code 열고, `CLAUDE_CODE_PROMPT.md` 내용을 그대로 붙여넣으면 시작됩니다.

### 4단계: 첫 메시지 가이드

Claude Code가 초기 분석을 시작하면 다음을 시켜보세요:

```
references/FA_고정자산_RCM_매핑_예시_v4.xlsx를 먼저 SheetJS로 파싱해서 데이터 구조 확인해줘. 통제 7개와 활동 33개가 잘 인식되는지 확인 후, 1단계 부트스트랩 시작해줘.
```

## 진행 중 막힐 때

다음 사안은 다시 본 대화로 돌아와서 의논:

- **사양 결정**: 분기점·swim lane·자동 배치 알고리즘 등
- **다른 사이클 매핑**: 매출/구매/결산 사이클 매핑 시트 만들 때
- **포트폴리오용 README 작성** — 도메인 설명 포함
- **버그·UX 이슈가 설계 차원의 결정 필요할 때**

순수 코딩·디버깅·환경 설정은 Claude Code에서 끝까지 처리.

## 진행 체크리스트

### MVP (1단계) 완성 기준
- [ ] FA_고정자산_RCM_매핑_예시_v4.xlsx 업로드 → 통제 7개 자동 인식
- [ ] Flowchart 드롭다운에 FA11~FA51 7개 옵션 표시
- [ ] FA21 선택 시 활동 5개 + 통제 1개가 캔버스에 표시됨
- [ ] FA41 선택 시 활동 8개가 깨지지 않고 표시됨 (한 줄 또는 두 줄)
- [ ] 활동 박스를 마우스로 드래그해서 위치 변경 가능
- [ ] 활동 클릭하면 우측 패널에서 편집 가능
- [ ] 현재 flowchart PPT 다운로드 → Python 버전과 동등한 품질

### 2단계 완성 기준
- [ ] 빈 캔버스에서 활동 노드 추가/삭제 가능
- [ ] 노드끼리 마우스 드래그로 화살표 연결 가능
- [ ] 분기점 노드 추가 가능
- [ ] 단축키 동작 (`A`+클릭, `Del`, `Ctrl+→` 등)
- [ ] 전체 flowchart 7개를 ZIP으로 일괄 다운로드
- [ ] 변경사항을 매핑 시트(.xlsx)로 export

### 포트폴리오 준비
- [ ] README에 스크린샷 + 도메인 설명 + 기술 스택 + 실행 방법
- [ ] LICENSE 파일
- [ ] .gitignore에 회사 데이터 패턴 추가
- [ ] 커밋 메시지 정돈 (Conventional Commits)
- [ ] 익명화된 샘플 데이터만 커밋

## 다음 대화로 가져올 만한 토픽

도구가 어느 정도 동작하기 시작하면:

1. **매핑 시트의 다른 시나리오 추가**: 매출 사이클(SR11~), 구매 사이클(PR11~) 등 다른 도메인 예시
2. **분기 처리 방식 결정**: 단순히 BRANCH_INFO 텍스트로 표시 vs 실제 다이아몬드 노드 + 분기 화살표
3. **검증 강화**: RCM과 매핑 시트 정합성 자동 체크 (활동 수가 일반 범위 벗어남, 같은 RCM 행을 여러 flowchart가 참조 등)
4. **포트폴리오용 README 한국어/영문 듀얼** — 국내·해외 활용
