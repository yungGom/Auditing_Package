# AuditLink v2 — Frontend (Vite + React + Tailwind)

Linear 스타일 회계감사 관리 앱 프론트엔드.

## 실행

```bash
cd frontend
npm install
npm run dev         # http://localhost:5173
```

백엔드(`backend/`) 서버도 함께 실행해야 합니다 (`http://localhost:8000`).

## 구조

```
src/
  api.js              # API 클라이언트 (fetch wrapper)
  constants.js        # STATUS, PRIORITY, ENG_TYPE, NAV 상수
  App.jsx             # 루트: 사이드바+탑바+페이지 라우팅
  components/
    Shell.jsx         # Sidebar, Topbar
    Tokens.jsx        # StatusDot, StatusPill, PriorityDot, DDay, Icon, Spinner
    CommandPalette.jsx # Ctrl+K 전역 검색
    QuickMemo.jsx     # 플로팅 메모 FAB (localStorage)
  pages/
    Dashboard.jsx     # 진척률 링, 마감일, 클라이언트 목록, 캘린더
    Engagements.jsx   # 트리(CRUD/컨텍스트메뉴) + 탭(할일/PBC/인터뷰)
    ICFR.jsx          # 통제활동 테이블 + RCM 상세 패널
    Templates.jsx     # 카드 그리드 + 신규 템플릿 모달
    Settings.jsx      # 회계연도, 사용자 정보, 알림 설정
```

## 디자인 토큰

| 변수 | 값 |
|---|---|
| `--lnac` | `#5b5bd6` (포인트 컬러, CSS variable) |
| `canvas` | `#f9f9fb` |
| `ink` | `#1a1a1a` |
| `sub` | `#6b7280` |
| `faint` | `#9ca3af` |
| `line` | `#e5e7eb` |
