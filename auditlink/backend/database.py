"""
SQLite database initialisation & helpers.
All tables are created on first run; seed data is inserted if the DB is empty.
"""
import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "auditlink.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS fiscal_years (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    is_active   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS clients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fy_id       INTEGER NOT NULL REFERENCES fiscal_years(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    industry    TEXT    NOT NULL DEFAULT '',
    report_date TEXT
);

CREATE TABLE IF NOT EXISTS phases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_id    INTEGER NOT NULL REFERENCES phases(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    title       TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'todo',
    assignee    TEXT    NOT NULL DEFAULT '',
    due_date    TEXT,
    priority    TEXT    NOT NULL DEFAULT 'mid',
    memo        TEXT    NOT NULL DEFAULT '',
    file_path   TEXT    NOT NULL DEFAULT '',
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS task_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    old_status  TEXT    NOT NULL,
    new_status  TEXT    NOT NULL,
    changed_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    industry        TEXT    NOT NULL DEFAULT '',
    accounts_json   TEXT    NOT NULL DEFAULT '[]',
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS icfr_tests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    client_name     TEXT    NOT NULL DEFAULT '',
    process         TEXT    NOT NULL DEFAULT '',
    control_name    TEXT    NOT NULL DEFAULT '',
    test_method     TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT '미실시',
    assignee        TEXT    NOT NULL DEFAULT '',
    note            TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS pbc_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    account_id      INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    name            TEXT    NOT NULL,
    request_date    TEXT,
    due_date        TEXT,
    status          TEXT    NOT NULL DEFAULT '미요청',
    auditor         TEXT    NOT NULL DEFAULT '',
    client_contact  TEXT    NOT NULL DEFAULT '',
    note            TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS template_checklists (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id     INTEGER NOT NULL,
    sheet_name      TEXT    NOT NULL DEFAULT '',
    row_index       INTEGER NOT NULL,
    is_completed    INTEGER NOT NULL DEFAULT 0,
    note            TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS pbc_excel_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id           INTEGER NOT NULL,
    file_name           TEXT    NOT NULL DEFAULT '',
    sheet_name          TEXT    NOT NULL DEFAULT '',
    row_index           INTEGER NOT NULL,
    is_received         INTEGER NOT NULL DEFAULT 0,
    received_date       TEXT,
    completion_status   TEXT    NOT NULL DEFAULT '',
    note                TEXT    NOT NULL DEFAULT ''
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    # Migrate: add file_path, updated_at columns if missing
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    if "file_path" not in cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN file_path TEXT NOT NULL DEFAULT ''")
    if "updated_at" not in cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN updated_at TEXT")
    # Seed only when fiscal_years is empty
    row = conn.execute("SELECT COUNT(*) c FROM fiscal_years").fetchone()
    if row["c"] == 0:
        _seed(conn)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Seed data (mirrors existing front-end mock data)
# ---------------------------------------------------------------------------

def _seed(conn: sqlite3.Connection):
    # -- FY --
    conn.execute("INSERT INTO fiscal_years (name, is_active) VALUES ('FY2025', 1)")
    fy_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # -- Clients --
    clients = [
        ("한빛제조", "제조업", "2025-12-31"),
        ("서현테크", "IT서비스", "2025-12-31"),
        ("동아리테일", "유통업", "2025-12-31"),
        ("미래에너지", "에너지", "2025-12-31"),
    ]
    client_ids = {}
    for name, industry, rd in clients:
        conn.execute(
            "INSERT INTO clients (fy_id, name, industry, report_date) VALUES (?,?,?,?)",
            (fy_id, name, industry, rd),
        )
        client_ids[name] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # -- Phases & Accounts & Tasks  (한빛제조) --
    hb = client_ids["한빛제조"]
    conn.execute("INSERT INTO phases (client_id, name, sort_order) VALUES (?,?,?)", (hb, "기중감사", 0))
    hb_interim = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO phases (client_id, name, sort_order) VALUES (?,?,?)", (hb, "기말감사", 1))
    hb_final = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # 기중감사 계정
    for sort, (acc_name, task_list) in enumerate([
        ("매출채권", [
            ("매출채권 확인서 발송", "in_progress", "김감사", "2025-03-26", "high", "거래처 30곳 대상"),
            ("대손충당금 적정성 검토", "todo", "이주임", "2025-03-28", "mid", ""),
            ("매출채권 회전율 분석", "done", "김감사", "2025-03-20", "low", "전기 대비 개선"),
        ]),
        ("재고자산", [
            ("재고실사 참관 일정 확정", "done", "박대리", "2025-03-15", "high", "본사 창고 + 외주 창고"),
            ("재고자산 평가 테스트", "in_progress", "이주임", "2025-04-01", "mid", ""),
        ]),
    ]):
        conn.execute("INSERT INTO accounts (phase_id, name, sort_order) VALUES (?,?,?)", (hb_interim, acc_name, sort))
        acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for title, status, assignee, due, prio, memo in task_list:
            conn.execute(
                "INSERT INTO tasks (account_id, title, status, assignee, due_date, priority, memo) VALUES (?,?,?,?,?,?,?)",
                (acc_id, title, status, assignee, due, prio, memo),
            )

    # 기말감사 계정
    for sort, (acc_name, task_list) in enumerate([
        ("유형자산", [
            ("유형자산 실사", "review", "박대리", "2025-04-10", "high", "공장 설비 중심"),
            ("감가상각비 재계산", "todo", "김감사", "2025-04-12", "mid", ""),
        ]),
        ("리스", [
            ("리스 계약 검토", "todo", "이주임", "2025-04-15", "mid", "IFRS 16 적용 확인"),
        ]),
    ]):
        conn.execute("INSERT INTO accounts (phase_id, name, sort_order) VALUES (?,?,?)", (hb_final, acc_name, sort))
        acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for title, status, assignee, due, prio, memo in task_list:
            conn.execute(
                "INSERT INTO tasks (account_id, title, status, assignee, due_date, priority, memo) VALUES (?,?,?,?,?,?,?)",
                (acc_id, title, status, assignee, due, prio, memo),
            )

    # -- Phases & Accounts & Tasks  (서현테크) --
    sh = client_ids["서현테크"]
    conn.execute("INSERT INTO phases (client_id, name, sort_order) VALUES (?,?,?)", (sh, "기중감사", 0))
    sh_interim = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO phases (client_id, name, sort_order) VALUES (?,?,?)", (sh, "기말감사", 1))
    sh_final = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    for sort, (acc_name, task_list) in enumerate([
        ("수익인식", [
            ("수익인식 기준 검토", "in_progress", "최선임", "2025-03-30", "high", "K-IFRS 1115"),
            ("계약 샘플링 테스트", "todo", "정사원", "2025-04-05", "mid", ""),
        ]),
        ("현금및현금성자산", [
            ("은행잔고 확인서 수취", "done", "정사원", "2025-03-18", "high", "5개 은행"),
        ]),
    ]):
        conn.execute("INSERT INTO accounts (phase_id, name, sort_order) VALUES (?,?,?)", (sh_interim, acc_name, sort))
        acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for title, status, assignee, due, prio, memo in task_list:
            conn.execute(
                "INSERT INTO tasks (account_id, title, status, assignee, due_date, priority, memo) VALUES (?,?,?,?,?,?,?)",
                (acc_id, title, status, assignee, due, prio, memo),
            )

    for sort, (acc_name, task_list) in enumerate([
        ("자본", [
            ("자본변동 내역 검토", "todo", "최선임", "2025-04-20", "low", ""),
        ]),
        ("충당부채", [
            ("소송충당부채 검토", "review", "최선임", "2025-04-18", "high", "법률의견서 수취 필요"),
            ("제품보증충당부채 계산 검증", "todo", "정사원", "2025-04-22", "mid", ""),
        ]),
    ]):
        conn.execute("INSERT INTO accounts (phase_id, name, sort_order) VALUES (?,?,?)", (sh_final, acc_name, sort))
        acc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for title, status, assignee, due, prio, memo in task_list:
            conn.execute(
                "INSERT INTO tasks (account_id, title, status, assignee, due_date, priority, memo) VALUES (?,?,?,?,?,?,?)",
                (acc_id, title, status, assignee, due, prio, memo),
            )

    # -- Templates --
    templates_data = [
        ("제조업 기본", "제조업", "2025-03-15", [
            {"name": "매출채권", "tasks": ["매출채권 확인서 발송", "대손충당금 적정성 검토", "매출채권 연령분석"]},
            {"name": "재고자산", "tasks": ["재고실사 참관", "재고자산 평가 검토", "저가법 적용 검토"]},
            {"name": "유형자산", "tasks": ["유형자산 실사", "감가상각비 재계산", "손상차손 검토"]},
            {"name": "매입채무", "tasks": ["매입채무 확인서 발송", "기말 미지급금 검토"]},
            {"name": "리스", "tasks": ["리스 계약 검토", "사용권자산/리스부채 재계산"]},
            {"name": "충당부채", "tasks": ["소송충당부채 검토", "제품보증충당부채 추정 검토"]},
        ]),
        ("IT서비스업", "IT서비스", "2025-03-10", [
            {"name": "매출채권", "tasks": ["매출채권 확인서 발송", "대손충당금 적정성 검토"]},
            {"name": "무형자산", "tasks": ["개발비 자본화 요건 검토", "무형자산 손상 검토", "내용연수 적정성 검토"]},
            {"name": "선수수익", "tasks": ["수익인식 기준 검토", "이연수익 적정성 검토"]},
            {"name": "전환사채", "tasks": ["전환사채 공정가치 평가", "파생상품 분리회계 검토"]},
            {"name": "스톡옵션", "tasks": ["주식보상비용 재계산", "공정가치 산정 검토"]},
        ]),
        ("유통업", "유통업", "2025-02-28", [
            {"name": "매출채권", "tasks": ["매출채권 확인서 발송", "대손충당금 적정성 검토"]},
            {"name": "재고자산", "tasks": ["재고실사 참관", "재고자산 평가 검토", "저가법 적용 검토"]},
            {"name": "매입채무", "tasks": ["매입채무 확인서 발송", "기말 미지급금 검토"]},
            {"name": "리스", "tasks": ["리스 계약 검토", "사용권자산/리스부채 재계산"]},
            {"name": "충성고객포인트", "tasks": ["포인트 부채 추정 검토", "사용률 분석 검토"]},
        ]),
    ]
    for name, industry, updated_at, accounts in templates_data:
        conn.execute(
            "INSERT INTO templates (name, industry, accounts_json, updated_at) VALUES (?,?,?,?)",
            (name, industry, json.dumps(accounts, ensure_ascii=False), updated_at),
        )

    # -- ICFR Tests --
    icfr_data = [
        ("한빛제조", "매출", "매출 거래 승인 통제", "검사", "완료", "김민수", ""),
        ("한빛제조", "매출", "수익인식 시점 적정성 통제", "재수행", "진행중", "김민수", "샘플 25건 중 15건 완료"),
        ("한빛제조", "매입", "구매요청서 승인 통제", "검사", "완료", "이서연", ""),
        ("한빛제조", "재고", "재고 실사 통제", "관찰", "이슈발견", "이서연", "일부 창고 실사 누락 발견"),
        ("한빛제조", "자금", "자금 집행 승인 통제", "질문", "미실시", "박준혁", ""),
        ("한빛제조", "급여", "급여 계산 및 지급 통제", "재수행", "완료", "박준혁", ""),
        ("서현테크", "매출", "계약 검토 및 승인 통제", "검사", "완료", "최유진", ""),
        ("서현테크", "매출", "프로젝트 진행률 산정 통제", "재수행", "이슈발견", "최유진", "진행률 산정 기준 불일치"),
        ("서현테크", "매입", "외주용역 검수 통제", "검사", "진행중", "정하은", "검수 보고서 수집 중"),
        ("서현테크", "자금", "일일 자금 시재 확인 통제", "관찰", "완료", "정하은", ""),
        ("서현테크", "급여", "인건비 배부 통제", "재수행", "미실시", "김민수", ""),
    ]
    for client_name, process, control, method, status, assignee, note in icfr_data:
        cid = client_ids.get(client_name)
        conn.execute(
            "INSERT INTO icfr_tests (client_id, client_name, process, control_name, test_method, status, assignee, note) VALUES (?,?,?,?,?,?,?,?)",
            (cid, client_name, process, control, method, status, assignee, note),
        )

    # -- Settings --
    default_settings = {
        "activeFY": "FY2025",
        "userName": "",
        "userTitle": "",
        "userFirm": "",
        "reportDeadlineDays": "90",
        "alertDays": json.dumps([7, 15, 30]),
    }
    for k, v in default_settings.items():
        conn.execute("INSERT INTO settings (key, value) VALUES (?,?)", (k, v))

    # -- PBC Items (한빛제조) --
    # We need account IDs – they were created starting from 1 in order
    pbc_data = [
        (hb, 1, "매출채권 잔액 확인서", "2025-03-10", "2025-03-25", "수령완료", "김감사", "재무팀 박과장", "30곳 중 28곳 회수"),
        (hb, 1, "매출채권 연령분석표", "2025-03-10", "2025-03-20", "수령완료", "김감사", "재무팀 박과장", ""),
        (hb, 2, "재고자산 실사 보고서", "2025-03-05", "2025-03-18", "수령완료", "이주임", "경영지원팀 김대리", ""),
        (hb, 2, "재고자산 평가 조서", "2025-03-12", "2025-04-01", "요청완료", "이주임", "경영지원팀 김대리", "저가법 적용 내역 포함"),
        (hb, 3, "유형자산 대장", "2025-03-20", "2025-04-08", "요청완료", "박대리", "재무팀 이차장", ""),
        (hb, 3, "감가상각 명세서", None, "2025-04-10", "미요청", "박대리", "재무팀 이차장", ""),
        (hb, 4, "리스 계약서 사본", None, "2025-04-12", "미요청", "이주임", "법무팀 정대리", "IFRS 16 관련"),
        (hb, 4, "리스료 지급 스케줄", "2025-03-25", "2025-04-12", "보완요청", "이주임", "법무팀 정대리", "일부 계약 누락"),
    ]
    for cid, acc_id, name, req_date, due, status, auditor, contact, note in pbc_data:
        conn.execute(
            "INSERT INTO pbc_items (client_id, account_id, name, request_date, due_date, status, auditor, client_contact, note) VALUES (?,?,?,?,?,?,?,?,?)",
            (cid, acc_id, name, req_date, due, status, auditor, contact, note),
        )
