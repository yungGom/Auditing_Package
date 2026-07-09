# AuditLink v2

Linear 스타일 회계감사 관리 앱 — FastAPI + SQLite 백엔드, Vite + React + Tailwind 프론트엔드.

## 빠른 시작

### 백엔드

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000
```

데모 데이터 로드 (선택):
```bash
python seed.py
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

## 디렉터리 구조

```
backend/         FastAPI + SQLAlchemy + SQLite (pytest 29개)
frontend/        Vite + React + Tailwind CSS
project/         원본 HTML 프로토타입 (Linear 디자인)
chats/           디자인 이터레이션 기록
```

## 기능

- **대시보드**: 진척률 링, 주요 마감일, 클라이언트 목록, 캘린더
- **감사업무**: FY→Client→Engagement→Phase→Account 트리 (CRUD), 할일(리스트/칸반)/PBC/인터뷰 탭
- **내부회계**: ICFR 통제활동 테이블, RCM 상세 편집
- **템플릿**: 업종별 카드 그리드, 계정과목 일괄 추가
- **설정**: 회계연도 관리, 사용자 정보, 알림 설정
- **전역**: Ctrl+K 검색, 빠른 메모 FAB

## 버그 방지 규칙 (서버 강제)

1. 활성 FY는 항상 하나 — 활성화 시 다른 FY 자동 비활성화
2. 모든 write 응답이 저장된 객체 반환 — F5 없이 상태 갱신
3. 빈 DB로 시작 — mock 없는 실 API (`seed.py`로 별도 데모 로드)
4. `GET /api/engagement-tree` — 모든 FY 반환, `is_active` 플래그로 기본 펼침 제어
