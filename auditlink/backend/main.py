"""
AuditLink FastAPI backend – CRUD for all tables.
Run: uvicorn backend.main:app --reload --port 8000
"""
import json
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from .database import init_db, get_connection


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

def _get_dist_dir():
    """Locate the React build output (dist/) directory."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "dist")
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="AuditLink API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve React static build if dist/ exists
_dist = _get_dist_dir()
if os.path.isdir(_dist):
    # Mount assets sub-folder for JS/CSS
    _assets = os.path.join(_dist, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class SPAMiddleware(BaseHTTPMiddleware):
        """Serve index.html for non-API, non-static routes (SPA fallback)."""
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            path = request.url.path
            if response.status_code == 404 and not path.startswith("/api/") and not path.startswith("/assets/"):
                return FileResponse(os.path.join(_dist, "index.html"))
            return response

    app.add_middleware(SPAMiddleware)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def _db():
    return get_connection()


# ═══════════════════════════════════════════════════════════════════════════
# Fiscal Years
# ═══════════════════════════════════════════════════════════════════════════

class FYCreate(BaseModel):
    name: str
    is_active: bool = False

class FYUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

@app.get("/api/fiscal-years")
def list_fiscal_years():
    conn = _db()
    rows = conn.execute("SELECT * FROM fiscal_years ORDER BY id").fetchall()
    conn.close()
    return rows_to_list(rows)

@app.post("/api/fiscal-years", status_code=201)
def create_fiscal_year(body: FYCreate):
    conn = _db()
    try:
        conn.execute("INSERT INTO fiscal_years (name, is_active) VALUES (?,?)", (body.name, int(body.is_active)))
        rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return {"id": rid, "name": body.name, "is_active": int(body.is_active)}

@app.put("/api/fiscal-years/{fy_id}")
def update_fiscal_year(fy_id: int, body: FYUpdate):
    conn = _db()
    existing = conn.execute("SELECT * FROM fiscal_years WHERE id=?", (fy_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(404)
    if body.is_active:
        conn.execute("UPDATE fiscal_years SET is_active=0")
    sets, vals = [], []
    if body.name is not None:
        sets.append("name=?"); vals.append(body.name)
    if body.is_active is not None:
        sets.append("is_active=?"); vals.append(int(body.is_active))
    if sets:
        vals.append(fy_id)
        conn.execute(f"UPDATE fiscal_years SET {','.join(sets)} WHERE id=?", vals)
        conn.commit()
    row = conn.execute("SELECT * FROM fiscal_years WHERE id=?", (fy_id,)).fetchone()
    conn.close()
    return row_to_dict(row)

@app.delete("/api/fiscal-years/{fy_id}")
def delete_fiscal_year(fy_id: int):
    conn = _db()
    conn.execute("DELETE FROM fiscal_years WHERE id=?", (fy_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Clients
# ═══════════════════════════════════════════════════════════════════════════

class ClientCreate(BaseModel):
    fy_id: int
    name: str
    industry: str = ""
    report_date: Optional[str] = None

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    report_date: Optional[str] = None

@app.get("/api/clients")
def list_clients(fy_id: Optional[int] = None):
    conn = _db()
    if fy_id:
        rows = conn.execute("SELECT * FROM clients WHERE fy_id=? ORDER BY id", (fy_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM clients ORDER BY id").fetchall()
    conn.close()
    return rows_to_list(rows)

@app.get("/api/clients/{client_id}")
def get_client(client_id: int):
    conn = _db()
    row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    return row_to_dict(row)

@app.post("/api/clients", status_code=201)
def create_client(body: ClientCreate):
    conn = _db()
    conn.execute(
        "INSERT INTO clients (fy_id, name, industry, report_date) VALUES (?,?,?,?)",
        (body.fy_id, body.name, body.industry, body.report_date),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"id": rid, **body.model_dump()}

@app.put("/api/clients/{client_id}")
def update_client(client_id: int, body: ClientUpdate):
    conn = _db()
    sets, vals = [], []
    for field in ["name", "industry", "report_date"]:
        v = getattr(body, field)
        if v is not None:
            sets.append(f"{field}=?"); vals.append(v)
    if sets:
        vals.append(client_id)
        conn.execute(f"UPDATE clients SET {','.join(sets)} WHERE id=?", vals)
        conn.commit()
    row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    return row_to_dict(row)

@app.delete("/api/clients/{client_id}")
def delete_client(client_id: int):
    conn = _db()
    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Phases
# ═══════════════════════════════════════════════════════════════════════════

class PhaseCreate(BaseModel):
    client_id: int
    name: str
    sort_order: int = 0

class PhaseUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None

@app.get("/api/phases")
def list_phases(client_id: Optional[int] = None):
    conn = _db()
    if client_id:
        rows = conn.execute("SELECT * FROM phases WHERE client_id=? ORDER BY sort_order", (client_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM phases ORDER BY sort_order").fetchall()
    conn.close()
    return rows_to_list(rows)

@app.post("/api/phases", status_code=201)
def create_phase(body: PhaseCreate):
    conn = _db()
    conn.execute("INSERT INTO phases (client_id, name, sort_order) VALUES (?,?,?)", (body.client_id, body.name, body.sort_order))
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"id": rid, **body.model_dump()}

@app.put("/api/phases/{phase_id}")
def update_phase(phase_id: int, body: PhaseUpdate):
    conn = _db()
    sets, vals = [], []
    if body.name is not None:
        sets.append("name=?"); vals.append(body.name)
    if body.sort_order is not None:
        sets.append("sort_order=?"); vals.append(body.sort_order)
    if sets:
        vals.append(phase_id)
        conn.execute(f"UPDATE phases SET {','.join(sets)} WHERE id=?", vals)
        conn.commit()
    row = conn.execute("SELECT * FROM phases WHERE id=?", (phase_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    return row_to_dict(row)

@app.delete("/api/phases/{phase_id}")
def delete_phase(phase_id: int):
    conn = _db()
    conn.execute("DELETE FROM phases WHERE id=?", (phase_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Accounts
# ═══════════════════════════════════════════════════════════════════════════

class AccountCreate(BaseModel):
    phase_id: int
    name: str
    sort_order: int = 0

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None

@app.get("/api/accounts")
def list_accounts(phase_id: Optional[int] = None):
    conn = _db()
    if phase_id:
        rows = conn.execute("SELECT * FROM accounts WHERE phase_id=? ORDER BY sort_order", (phase_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM accounts ORDER BY sort_order").fetchall()
    conn.close()
    return rows_to_list(rows)

@app.post("/api/accounts", status_code=201)
def create_account(body: AccountCreate):
    conn = _db()
    conn.execute("INSERT INTO accounts (phase_id, name, sort_order) VALUES (?,?,?)", (body.phase_id, body.name, body.sort_order))
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"id": rid, **body.model_dump()}

@app.put("/api/accounts/{account_id}")
def update_account(account_id: int, body: AccountUpdate):
    conn = _db()
    sets, vals = [], []
    if body.name is not None:
        sets.append("name=?"); vals.append(body.name)
    if body.sort_order is not None:
        sets.append("sort_order=?"); vals.append(body.sort_order)
    if sets:
        vals.append(account_id)
        conn.execute(f"UPDATE accounts SET {','.join(sets)} WHERE id=?", vals)
        conn.commit()
    row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    return row_to_dict(row)

@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int):
    conn = _db()
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════════════════════

class TaskCreate(BaseModel):
    account_id: int
    title: str
    status: str = "todo"
    assignee: str = ""
    due_date: Optional[str] = None
    priority: str = "mid"
    memo: str = ""
    file_path: str = ""

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    memo: Optional[str] = None
    file_path: Optional[str] = None

@app.get("/api/tasks")
def list_tasks(account_id: Optional[int] = None):
    conn = _db()
    if account_id:
        rows = conn.execute("SELECT * FROM tasks WHERE account_id=? ORDER BY id", (account_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    conn.close()
    return rows_to_list(rows)

@app.post("/api/tasks", status_code=201)
def create_task(body: TaskCreate):
    from datetime import datetime
    conn = _db()
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO tasks (account_id, title, status, assignee, due_date, priority, memo, file_path, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (body.account_id, body.title, body.status, body.assignee, body.due_date, body.priority, body.memo, body.file_path, now),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"id": rid, **body.model_dump(), "updated_at": now}

@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate):
    from datetime import datetime
    conn = _db()
    existing = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(404)
    # Record status change history
    if body.status is not None and body.status != existing["status"]:
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO task_history (task_id, old_status, new_status, changed_at) VALUES (?,?,?,?)",
            (task_id, existing["status"], body.status, now),
        )
    sets, vals = [], []
    for field in ["title", "status", "assignee", "due_date", "priority", "memo", "file_path"]:
        v = getattr(body, field)
        if v is not None:
            sets.append(f"{field}=?"); vals.append(v)
    if sets:
        now = datetime.now().isoformat(timespec="seconds")
        sets.append("updated_at=?"); vals.append(now)
        vals.append(task_id)
        conn.execute(f"UPDATE tasks SET {','.join(sets)} WHERE id=?", vals)
        conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    return row_to_dict(row)

@app.get("/api/tasks/{task_id}")
def get_task(task_id: int):
    """Return a single task with its breadcrumb path."""
    conn = _db()
    row = conn.execute("""
        SELECT t.*, a.name AS account_name, p.name AS phase_name,
               c.name AS client_name, fy.name AS fy_name
        FROM tasks t
        JOIN accounts a ON a.id = t.account_id
        JOIN phases p ON p.id = a.phase_id
        JOIN clients c ON c.id = p.client_id
        JOIN fiscal_years fy ON fy.id = c.fy_id
        WHERE t.id = ?
    """, (task_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    d = dict(row)
    d["path"] = f"{d.pop('fy_name')} > {d.pop('client_name')} > {d.pop('phase_name')} > {d.pop('account_name')}"
    return d

@app.get("/api/tasks/{task_id}/history")
def get_task_history(task_id: int):
    conn = _db()
    rows = conn.execute(
        "SELECT * FROM task_history WHERE task_id=? ORDER BY changed_at DESC", (task_id,)
    ).fetchall()
    conn.close()
    return rows_to_list(rows)

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    conn = _db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Templates
# ═══════════════════════════════════════════════════════════════════════════

class TemplateCreate(BaseModel):
    name: str
    industry: str = ""
    accounts_json: str = "[]"
    updated_at: Optional[str] = None

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    accounts_json: Optional[str] = None
    updated_at: Optional[str] = None

@app.get("/api/templates")
def list_templates():
    conn = _db()
    rows = conn.execute("SELECT * FROM templates ORDER BY id").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["accounts"] = json.loads(d.pop("accounts_json", "[]"))
        result.append(d)
    return result

@app.get("/api/templates/{template_id}")
def get_template(template_id: int):
    conn = _db()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (template_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    d = dict(row)
    d["accounts"] = json.loads(d.pop("accounts_json", "[]"))
    return d

@app.post("/api/templates", status_code=201)
def create_template(body: TemplateCreate):
    conn = _db()
    conn.execute(
        "INSERT INTO templates (name, industry, accounts_json, updated_at) VALUES (?,?,?,?)",
        (body.name, body.industry, body.accounts_json, body.updated_at),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"id": rid, **body.model_dump()}

@app.put("/api/templates/{template_id}")
def update_template(template_id: int, body: TemplateUpdate):
    conn = _db()
    sets, vals = [], []
    for field in ["name", "industry", "accounts_json", "updated_at"]:
        v = getattr(body, field)
        if v is not None:
            sets.append(f"{field}=?"); vals.append(v)
    if sets:
        vals.append(template_id)
        conn.execute(f"UPDATE templates SET {','.join(sets)} WHERE id=?", vals)
        conn.commit()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (template_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    d = dict(row)
    d["accounts"] = json.loads(d.pop("accounts_json", "[]"))
    return d

@app.delete("/api/templates/{template_id}")
def delete_template(template_id: int):
    conn = _db()
    conn.execute("DELETE FROM templates WHERE id=?", (template_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# ICFR Tests
# ═══════════════════════════════════════════════════════════════════════════

class ICFRCreate(BaseModel):
    client_id: Optional[int] = None
    client_name: str = ""
    process: str = ""
    control_name: str = ""
    test_method: str = ""
    status: str = "미실시"
    assignee: str = ""
    note: str = ""

class ICFRUpdate(BaseModel):
    client_name: Optional[str] = None
    process: Optional[str] = None
    control_name: Optional[str] = None
    test_method: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    note: Optional[str] = None

@app.get("/api/icfr-tests")
def list_icfr_tests(client_name: Optional[str] = None, status: Optional[str] = None):
    conn = _db()
    sql = "SELECT * FROM icfr_tests WHERE 1=1"
    params = []
    if client_name:
        sql += " AND client_name=?"
        params.append(client_name)
    if status:
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows_to_list(rows)

@app.post("/api/icfr-tests", status_code=201)
def create_icfr_test(body: ICFRCreate):
    conn = _db()
    conn.execute(
        "INSERT INTO icfr_tests (client_id, client_name, process, control_name, test_method, status, assignee, note) VALUES (?,?,?,?,?,?,?,?)",
        (body.client_id, body.client_name, body.process, body.control_name, body.test_method, body.status, body.assignee, body.note),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"id": rid, **body.model_dump()}

@app.put("/api/icfr-tests/{test_id}")
def update_icfr_test(test_id: int, body: ICFRUpdate):
    conn = _db()
    sets, vals = [], []
    for field in ["client_name", "process", "control_name", "test_method", "status", "assignee", "note"]:
        v = getattr(body, field)
        if v is not None:
            sets.append(f"{field}=?"); vals.append(v)
    if sets:
        vals.append(test_id)
        conn.execute(f"UPDATE icfr_tests SET {','.join(sets)} WHERE id=?", vals)
        conn.commit()
    row = conn.execute("SELECT * FROM icfr_tests WHERE id=?", (test_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    return row_to_dict(row)

@app.delete("/api/icfr-tests/{test_id}")
def delete_icfr_test(test_id: int):
    conn = _db()
    conn.execute("DELETE FROM icfr_tests WHERE id=?", (test_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Settings
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/settings")
def get_settings():
    conn = _db()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

@app.put("/api/settings")
def update_settings(body: dict):
    conn = _db()
    for k, v in body.items():
        val = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, val))
    conn.commit()
    conn.close()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Notifications
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/notifications")
def notifications():
    """Return tasks grouped by urgency: overdue, due_today, due_this_week, review_pending."""
    from datetime import date, timedelta
    conn = _db()
    today = date.today().isoformat()
    week_end = (date.today() + timedelta(days=7)).isoformat()

    base_sql = """
        SELECT t.id, t.title, t.status, t.due_date, t.priority, t.assignee,
               a.id AS account_id, a.name AS account_name,
               c.name AS client_name
        FROM tasks t
        JOIN accounts a ON a.id = t.account_id
        JOIN phases p ON p.id = a.phase_id
        JOIN clients c ON c.id = p.client_id
    """

    # Overdue: past due_date and not done
    overdue = rows_to_list(conn.execute(
        base_sql + " WHERE t.status != 'done' AND t.due_date IS NOT NULL AND t.due_date < ? ORDER BY t.due_date",
        (today,)
    ).fetchall())

    # Due today
    due_today = rows_to_list(conn.execute(
        base_sql + " WHERE t.status != 'done' AND t.due_date = ? ORDER BY t.priority DESC",
        (today,)
    ).fetchall())

    # Due this week (next 7 days, excluding today)
    due_week = rows_to_list(conn.execute(
        base_sql + " WHERE t.status != 'done' AND t.due_date > ? AND t.due_date <= ? ORDER BY t.due_date",
        (today, week_end)
    ).fetchall())

    # Review pending
    review = rows_to_list(conn.execute(
        base_sql + " WHERE t.status = 'review' ORDER BY t.due_date",
    ).fetchall())

    # Add node_id for navigation
    for lst in [overdue, due_today, due_week, review]:
        for item in lst:
            item["node_id"] = f"account-{item['account_id']}"

    conn.close()
    return {
        "overdue": overdue,
        "due_today": due_today,
        "due_week": due_week,
        "review": review,
        "total_count": len(overdue) + len(due_today) + len(due_week) + len(review),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Search
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/search")
def search(q: str = ""):
    """Full-text search across clients, accounts, tasks, assignees."""
    q = q.strip()
    if not q:
        return {"clients": [], "tasks": []}
    conn = _db()
    pattern = f"%{q}%"

    # Search clients (name match) – include breadcrumb path
    client_rows = conn.execute("""
        SELECT c.id, c.name, c.industry, fy.name AS fy_name
        FROM clients c
        JOIN fiscal_years fy ON fy.id = c.fy_id
        WHERE c.name LIKE ?
        ORDER BY c.id LIMIT 20
    """, (pattern,)).fetchall()
    clients = []
    for r in client_rows:
        r = dict(r)
        clients.append({
            "id": r["id"],
            "name": r["name"],
            "industry": r["industry"],
            "path": r["fy_name"],
            "node_id": f"client-{r['id']}",
        })

    # Search accounts (name match) – include breadcrumb path
    account_rows = conn.execute("""
        SELECT a.id, a.name AS account_name,
               p.name AS phase_name, c.name AS client_name, fy.name AS fy_name,
               c.id AS client_id, p.id AS phase_id
        FROM accounts a
        JOIN phases p ON p.id = a.phase_id
        JOIN clients c ON c.id = p.client_id
        JOIN fiscal_years fy ON fy.id = c.fy_id
        WHERE a.name LIKE ?
        ORDER BY a.id LIMIT 20
    """, (pattern,)).fetchall()
    account_results = []
    for r in account_rows:
        r = dict(r)
        account_results.append({
            "type": "account",
            "account_id": r["id"],
            "title": r["account_name"],
            "path": f"{r['fy_name']} > {r['client_name']} > {r['phase_name']}",
            "node_id": f"account-{r['id']}",
        })

    # Search tasks (title, assignee, memo match) – include breadcrumb path
    task_rows = conn.execute("""
        SELECT t.id, t.title, t.assignee, t.status, t.priority, t.memo,
               a.id AS account_id, a.name AS account_name,
               p.name AS phase_name, c.name AS client_name, fy.name AS fy_name
        FROM tasks t
        JOIN accounts a ON a.id = t.account_id
        JOIN phases p ON p.id = a.phase_id
        JOIN clients c ON c.id = p.client_id
        JOIN fiscal_years fy ON fy.id = c.fy_id
        WHERE t.title LIKE ? OR t.assignee LIKE ? OR t.memo LIKE ?
        ORDER BY t.id LIMIT 30
    """, (pattern, pattern, pattern)).fetchall()
    tasks = []
    for r in task_rows:
        r = dict(r)
        tasks.append({
            "id": r["id"],
            "title": r["title"],
            "assignee": r["assignee"],
            "status": r["status"],
            "priority": r["priority"],
            "account_id": r["account_id"],
            "path": f"{r['fy_name']} > {r['client_name']} > {r['phase_name']} > {r['account_name']}",
            "node_id": f"account-{r['account_id']}",
        })

    conn.close()
    return {"clients": clients, "accounts": account_results, "tasks": tasks}


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard aggregation (convenience endpoint)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
def dashboard():
    conn = _db()
    # Engagement progress per client
    clients = rows_to_list(conn.execute("""
        SELECT c.id, c.name, c.industry,
               COUNT(t.id) AS total_tasks,
               SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END) AS done_tasks
        FROM clients c
        LEFT JOIN phases p ON p.client_id = c.id
        LEFT JOIN accounts a ON a.phase_id = p.id
        LEFT JOIN tasks t ON t.account_id = a.id
        GROUP BY c.id
    """).fetchall())

    # Upcoming deadlines
    deadlines = rows_to_list(conn.execute("""
        SELECT t.id, t.title AS task, t.due_date AS date, t.status,
               c.name AS client
        FROM tasks t
        JOIN accounts a ON a.id = t.account_id
        JOIN phases p ON p.id = a.phase_id
        JOIN clients c ON c.id = p.client_id
        WHERE t.status != 'done' AND t.due_date IS NOT NULL
        ORDER BY t.due_date
        LIMIT 10
    """).fetchall())

    # ICFR summary
    icfr = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='완료' THEN 1 ELSE 0 END) AS completed
        FROM icfr_tests
    """).fetchone()

    conn.close()

    # Compute overall progress
    total = sum(c["total_tasks"] for c in clients)
    done = sum(c["done_tasks"] for c in clients)

    return {
        "overallProgress": round(done / total * 100) if total else 0,
        "totalTasks": total,
        "doneTasks": done,
        "clients": clients,
        "deadlines": deadlines,
        "icfrTotal": icfr["total"],
        "icfrCompleted": icfr["completed"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# Engagement tree (convenience endpoint)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/engagement-tree")
def engagement_tree():
    """Return the full FY → Client → Phase → Account tree."""
    conn = _db()
    fys = rows_to_list(conn.execute("SELECT * FROM fiscal_years ORDER BY id").fetchall())
    tree = []
    for fy in fys:
        fy_node = {"id": f"fy-{fy['id']}", "label": fy["name"], "type": "fy", "dbId": fy["id"], "children": []}
        clients_rows = conn.execute("SELECT * FROM clients WHERE fy_id=? ORDER BY id", (fy["id"],)).fetchall()
        for c in clients_rows:
            c = dict(c)
            c_node = {"id": f"client-{c['id']}", "label": c["name"], "type": "client", "dbId": c["id"], "children": []}
            phases_rows = conn.execute("SELECT * FROM phases WHERE client_id=? ORDER BY sort_order", (c["id"],)).fetchall()
            for p in phases_rows:
                p = dict(p)
                p_node = {"id": f"phase-{p['id']}", "label": p["name"], "type": "phase", "dbId": p["id"], "children": []}
                accs = conn.execute("SELECT * FROM accounts WHERE phase_id=? ORDER BY sort_order", (p["id"],)).fetchall()
                for a in accs:
                    a = dict(a)
                    p_node["children"].append({"id": f"account-{a['id']}", "label": a["name"], "type": "account", "dbId": a["id"]})
                c_node["children"].append(p_node)
            fy_node["children"].append(c_node)
        tree.append(fy_node)
    conn.close()
    return tree
