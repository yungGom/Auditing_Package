# AuditLink - 회계감사 일정관리 데스크톱 앱

## 기술 스택

- **프론트엔드**: React 18 + Tailwind CSS + Material Symbols Icons
- **백엔드**: Python FastAPI + SQLite
- **데스크톱**: PyWebView로 래핑 → PyInstaller로 EXE 빌드
- **폰트**: Manrope(헤드라인), Inter(본문)

## 데이터 계층 구조

FY(회계연도) → Client(클라이언트) → Phase(기중/기말) → Account(계정과목, 자유추가) → Task(할일)

## 핵심 화면

1. **Dashboard** - 전체 진척률, 마감임박 항목, 활성 engagement 목록
2. **Engagements** - FY별 클라이언트 트리 네비게이션 + 할일 관리
3. **Templates** - 감사 템플릿 관리 (제조업, 서비스업 등)
4. **ICFR Tracking** - 내부회계관리제도 테스트 추적
5. **Settings** - 설정

## 디자인 원칙

- STITCH에서 생성한 디자인 시스템 준수 (컬러, 타이포, 간격)
- Primary: `#001e40`, Primary Container: `#003366`
- 네이비 기반 전문적 톤, 둥근 모서리(`rounded-xl`), 깔끔한 카드 레이아웃

## 개발 규칙

- 완전 오프라인 로컬 실행 (외부 API 호출 없음)
- 한국어 UI 지원
- 모든 데이터는 로컬 SQLite에 저장
