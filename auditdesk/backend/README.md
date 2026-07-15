# AuditLink v2 — Backend (FastAPI + SQLite)

REST API for AuditLink v2. Implements the expanded hierarchy from the design:

```
FiscalYear → Client → Engagement(type: 감사/검토/기타) → Phase(/Folder) → Account → Task
                                                                        ├─ PBCItem
                                                                        └─ Interview
Client → IcfrControl (RCM detail)
```

## Setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000
```

Interactive API docs: http://localhost:8000/docs

The database (`auditlink.db`) and tables are created automatically on startup.
**The app starts empty** — no mock data (per the implementation brief). To load
the sample data from the design prototype for demos:

```bash
python seed.py            # seed only if DB is empty
python seed.py --reset    # wipe everything, then seed
```

## Tests

```bash
pytest                    # 29 tests, in-memory SQLite, no side effects
```

## Design decisions / bug-prevention rules

These four rules from the brief are enforced server-side:

1. **One active fiscal year.** Creating or updating a FY with `is_active=true`
   deactivates all others in the same transaction
   (`POST/PUT /api/fiscal-years`). See `routers/fiscal_years.py`.
2. **Writes return the resource.** Every create/update returns the saved object
   so the client can update state without a reload (no F5).
3. **No mock data.** List endpoints return `[]` until you create rows; the
   prototype's sample data lives only in the optional `seed.py`.
4. **engagement-tree returns all FYs.** `GET /api/engagement-tree` returns every
   fiscal year; the active one is flagged `is_active: true` so the client expands
   only that one by default.

Other notes:
- **Phase = phase or folder.** One table with `kind` + self-referential
  `parent_id` supports the flexible nesting used by "기타" engagements.
- **Engagement templates.** `POST /api/engagements` seeds default phases by type
  (audit → 기중감사·기말감사, review → 검토절차, etc → empty). Pass
  `apply_template=false` to skip.
- **Task status history** is appended server-side whenever `status` changes.
- **ICFR RCM** is stored flat but exposed nested (`rcm: {...}`) to match the UI.
- **Cascade deletes** rely on FK constraints with `PRAGMA foreign_keys=ON`.

## Endpoint summary

| Resource | Routes |
|---|---|
| Fiscal years | `GET/POST /api/fiscal-years`, `GET/PUT/DELETE /api/fiscal-years/{id}` |
| Clients | `GET/POST /api/clients`, `PUT/DELETE /api/clients/{id}` |
| Engagements | `GET/POST /api/engagements`, `PUT/DELETE /api/engagements/{id}` |
| Phases/folders | `POST /api/phases`, `PUT/DELETE /api/phases/{id}` |
| Accounts | `GET/POST /api/accounts`, `POST /api/accounts/bulk`, `PUT /api/accounts/reorder`, `PUT/DELETE /api/accounts/{id}` |
| Tasks | `GET/POST /api/tasks`, `PUT/DELETE /api/tasks/{id}` |
| PBC | `GET/POST /api/pbc`, `POST /api/pbc/bulk`, `PUT/DELETE /api/pbc/{id}` |
| Interviews | `GET/POST /api/interviews`, `PUT/DELETE /api/interviews/{id}` |
| ICFR | `GET/POST /api/icfr`, `PUT/DELETE /api/icfr/{id}` |
| Templates | `GET/POST /api/templates`, `PUT/DELETE /api/templates/{id}` |
| Settings | `GET/PUT /api/settings` |
| Tree | `GET /api/engagement-tree` |
| Health | `GET /api/health` |
