"""
AuditLink API – comprehensive pytest test suite.
Run:  pytest backend/test_api.py -v
"""
import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient

# ── Ensure parent of 'auditlink' is on sys.path ──
_here = os.path.dirname(os.path.abspath(__file__))          # .../auditlink/backend
_auditlink_dir = os.path.dirname(_here)                     # .../auditlink
_project_root = os.path.dirname(_auditlink_dir)             # .../Auditing_Package
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Override DB path BEFORE importing anything from backend
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
TEST_DB = _tmp.name

import auditlink.backend.database as database
database.DB_PATH = TEST_DB

from auditlink.backend.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_db():
    """Fresh database for every test function."""
    database.DB_PATH = TEST_DB
    # Drop all tables and re-init
    conn = database.get_connection()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]
    for t in tables:
        conn.execute(f"DROP TABLE IF EXISTS [{t}]")
    conn.commit()
    conn.close()
    database.init_db()
    yield
    # cleanup handled by autouse


@pytest.fixture()
def seed():
    """Return ids of seeded FY / client / phase / account for convenience."""
    fys = client.get("/api/fiscal-years").json()
    fy = fys[0]
    clients_ = client.get("/api/clients").json()
    cl = clients_[0]
    phases = client.get(f"/api/phases?client_id={cl['id']}").json()
    ph = phases[0]
    accounts = client.get(f"/api/accounts?phase_id={ph['id']}").json()
    acc = accounts[0]
    tasks = client.get(f"/api/tasks?account_id={acc['id']}").json()
    return {"fy": fy, "client": cl, "phase": ph, "account": acc, "tasks": tasks}


# ═══════════════════════════════════════════════════════════════════════════
# 1. Fiscal Years CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestFiscalYears:
    def test_list(self):
        r = client.get("/api/fiscal-years")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # seeded FY2025

    def test_create(self):
        r = client.post("/api/fiscal-years", json={"name": "FY2026", "is_active": False})
        assert r.status_code == 201
        assert r.json()["name"] == "FY2026"

    def test_update(self):
        # create then update
        created = client.post("/api/fiscal-years", json={"name": "FY_TEMP"}).json()
        r = client.put(f"/api/fiscal-years/{created['id']}", json={"name": "FY_RENAMED"})
        assert r.status_code == 200
        assert r.json()["name"] == "FY_RENAMED"

    def test_delete(self):
        created = client.post("/api/fiscal-years", json={"name": "FY_DEL"}).json()
        r = client.delete(f"/api/fiscal-years/{created['id']}")
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ═══════════════════════════════════════════════════════════════════════════
# 2. Clients CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestClients:
    def test_list(self):
        r = client.get("/api/clients")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_list_by_fy(self, seed):
        r = client.get(f"/api/clients?fy_id={seed['fy']['id']}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_create_and_get(self, seed):
        r = client.post("/api/clients", json={
            "fy_id": seed["fy"]["id"], "name": "테스트사", "industry": "IT"
        })
        assert r.status_code == 201
        cid = r.json()["id"]

        r2 = client.get(f"/api/clients/{cid}")
        assert r2.status_code == 200
        assert r2.json()["name"] == "테스트사"

    def test_update(self, seed):
        cid = seed["client"]["id"]
        r = client.put(f"/api/clients/{cid}", json={"industry": "변경됨"})
        assert r.status_code == 200
        assert r.json()["industry"] == "변경됨"

    def test_delete(self, seed):
        created = client.post("/api/clients", json={
            "fy_id": seed["fy"]["id"], "name": "삭제용"
        }).json()
        r = client.delete(f"/api/clients/{created['id']}")
        assert r.status_code == 200

    def test_summary(self, seed):
        r = client.get(f"/api/clients/{seed['client']['id']}/summary")
        assert r.status_code == 200
        data = r.json()
        assert "client" in data
        assert "accounts" in data
        assert "status_counts" in data
        assert "assignees" in data
        assert "progress" in data

    def test_overview(self, seed):
        r = client.get(f"/api/clients/{seed['client']['id']}/overview")
        assert r.status_code == 200
        data = r.json()
        assert "client" in data
        assert "pbc" in data
        assert "interviews" in data
        assert "total" in data["pbc"]
        assert "received" in data["pbc"]
        assert "overdue" in data["pbc"]
        assert "total" in data["interviews"]
        assert "followup_needed" in data["interviews"]


# ═══════════════════════════════════════════════════════════════════════════
# 3. Phases CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestPhases:
    def test_list(self, seed):
        r = client.get(f"/api/phases?client_id={seed['client']['id']}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_create(self, seed):
        r = client.post("/api/phases", json={
            "client_id": seed["client"]["id"], "name": "추가Phase", "sort_order": 2
        })
        assert r.status_code == 201
        assert r.json()["name"] == "추가Phase"

    def test_update(self, seed):
        pid = seed["phase"]["id"]
        r = client.put(f"/api/phases/{pid}", json={"name": "수정Phase"})
        assert r.status_code == 200
        assert r.json()["name"] == "수정Phase"

    def test_delete(self, seed):
        created = client.post("/api/phases", json={
            "client_id": seed["client"]["id"], "name": "삭제Phase"
        }).json()
        r = client.delete(f"/api/phases/{created['id']}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 4. Accounts CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestAccounts:
    def test_list(self, seed):
        r = client.get(f"/api/accounts?phase_id={seed['phase']['id']}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_create(self, seed):
        r = client.post("/api/accounts", json={
            "phase_id": seed["phase"]["id"], "name": "테스트계정"
        })
        assert r.status_code == 201

    def test_update(self, seed):
        aid = seed["account"]["id"]
        r = client.put(f"/api/accounts/{aid}", json={"name": "수정계정"})
        assert r.status_code == 200
        assert r.json()["name"] == "수정계정"

    def test_delete(self, seed):
        created = client.post("/api/accounts", json={
            "phase_id": seed["phase"]["id"], "name": "삭제계정"
        }).json()
        r = client.delete(f"/api/accounts/{created['id']}")
        assert r.status_code == 200

    def test_bulk_create(self, seed):
        items = [
            {"phase_id": seed["phase"]["id"], "name": f"일괄계정{i}", "sort_order": 10 + i}
            for i in range(4)
        ]
        r = client.post("/api/accounts/bulk", json=items)
        assert r.status_code == 201
        data = r.json()
        assert len(data) == 4
        assert data[0]["name"] == "일괄계정0"

    def test_reorder(self, seed):
        pid = seed["phase"]["id"]
        # Create 3 accounts
        ids = []
        for i in range(3):
            r = client.post("/api/accounts", json={"phase_id": pid, "name": f"순서{i}", "sort_order": i})
            ids.append(r.json()["id"])
        # Reverse order
        r = client.patch("/api/accounts/reorder", json={"phase_id": pid, "ordered_ids": list(reversed(ids))})
        assert r.status_code == 200
        # Verify order
        accs = client.get(f"/api/accounts?phase_id={pid}").json()
        reordered = [a for a in accs if a["id"] in ids]
        assert reordered[0]["id"] == ids[2]  # was last, now first


# ═══════════════════════════════════════════════════════════════════════════
# 4b. Account Groups CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestAccountGroups:
    def test_create_and_list(self, seed):
        r = client.post("/api/account-groups", json={
            "phase_id": seed["phase"]["id"], "name": "자산", "sort_order": 0
        })
        assert r.status_code == 201
        gid = r.json()["id"]

        r2 = client.get(f"/api/account-groups?phase_id={seed['phase']['id']}")
        assert r2.status_code == 200
        assert any(g["id"] == gid for g in r2.json())

    def test_update(self, seed):
        created = client.post("/api/account-groups", json={
            "phase_id": seed["phase"]["id"], "name": "수정전"
        }).json()
        r = client.put(f"/api/account-groups/{created['id']}", json={"name": "부채"})
        assert r.status_code == 200
        assert r.json()["name"] == "부채"

    def test_delete(self, seed):
        created = client.post("/api/account-groups", json={
            "phase_id": seed["phase"]["id"], "name": "삭제용"
        }).json()
        r = client.delete(f"/api/account-groups/{created['id']}")
        assert r.status_code == 200

    def test_accounts_in_group_show_in_tree(self, seed):
        # Create group
        grp = client.post("/api/account-groups", json={
            "phase_id": seed["phase"]["id"], "name": "손익"
        }).json()
        # Create account with group_id
        acc = client.post("/api/accounts", json={
            "phase_id": seed["phase"]["id"], "name": "매출"
        }).json()
        client.put(f"/api/accounts/{acc['id']}", json={"group_id": grp["id"]})

        # Check tree has group with account inside
        tree = client.get("/api/engagement-tree").json()
        found = False
        for fy in tree:
            for cl in fy.get("children", []):
                for ph in cl.get("children", []):
                    for child in ph.get("children", []):
                        if child["type"] == "group" and child["dbId"] == grp["id"]:
                            acc_ids = [a["dbId"] for a in child.get("children", [])]
                            if acc["id"] in acc_ids:
                                found = True
        assert found, "Account should appear inside its group in the tree"

    def test_tree_has_active_fy_flag(self):
        tree = client.get("/api/engagement-tree").json()
        assert len(tree) >= 1
        active_count = sum(1 for fy in tree if fy.get("isActive"))
        assert active_count >= 1

    def test_reorder_groups(self, seed):
        pid = seed["phase"]["id"]
        g1 = client.post("/api/account-groups", json={"phase_id": pid, "name": "A", "sort_order": 0}).json()
        g2 = client.post("/api/account-groups", json={"phase_id": pid, "name": "B", "sort_order": 1}).json()
        # Reverse
        r = client.patch("/api/account-groups/reorder", json={"phase_id": pid, "ordered_ids": [g2["id"], g1["id"]]})
        assert r.status_code == 200
        groups = client.get(f"/api/account-groups?phase_id={pid}").json()
        ordered = [g for g in groups if g["id"] in [g1["id"], g2["id"]]]
        assert ordered[0]["id"] == g2["id"]

    def test_move_account_to_group(self, seed):
        pid = seed["phase"]["id"]
        grp = client.post("/api/account-groups", json={"phase_id": pid, "name": "이동테스트"}).json()
        acc = client.post("/api/accounts", json={"phase_id": pid, "name": "이동계정"}).json()
        # Move into group
        r = client.patch(f"/api/accounts/{acc['id']}/move-to-group?group_id={grp['id']}")
        assert r.status_code == 200
        # Verify
        tree = client.get("/api/engagement-tree").json()
        found = False
        for fy in tree:
            for cl in fy.get("children", []):
                for ph in cl.get("children", []):
                    for child in ph.get("children", []):
                        if child.get("type") == "group" and child.get("dbId") == grp["id"]:
                            if any(a["dbId"] == acc["id"] for a in child.get("children", [])):
                                found = True
        assert found

    def test_move_account_out_of_group(self, seed):
        pid = seed["phase"]["id"]
        grp = client.post("/api/account-groups", json={"phase_id": pid, "name": "해제테스트"}).json()
        acc = client.post("/api/accounts", json={"phase_id": pid, "name": "해제계정"}).json()
        client.patch(f"/api/accounts/{acc['id']}/move-to-group?group_id={grp['id']}")
        # Move out (no group)
        r = client.patch(f"/api/accounts/{acc['id']}/move-to-group")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 5. Tasks CRUD + Status History
# ═══════════════════════════════════════════════════════════════════════════

class TestTasks:
    def test_list(self, seed):
        r = client.get(f"/api/tasks?account_id={seed['account']['id']}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_create(self, seed):
        r = client.post("/api/tasks", json={
            "account_id": seed["account"]["id"],
            "title": "새 할일",
            "status": "todo",
            "priority": "high",
            "assignee": "테스터",
        })
        assert r.status_code == 201
        d = r.json()
        assert d["title"] == "새 할일"
        assert "updated_at" in d

    def test_get_single(self, seed):
        tid = seed["tasks"][0]["id"]
        r = client.get(f"/api/tasks/{tid}")
        assert r.status_code == 200
        assert "path" in r.json()

    def test_update_fields(self, seed):
        tid = seed["tasks"][0]["id"]
        r = client.put(f"/api/tasks/{tid}", json={"title": "수정된 제목", "memo": "메모추가"})
        assert r.status_code == 200
        assert r.json()["title"] == "수정된 제목"

    def test_status_change_records_history(self, seed):
        tid = seed["tasks"][0]["id"]
        # Change status
        client.put(f"/api/tasks/{tid}", json={"status": "done"})
        # Check history
        r = client.get(f"/api/tasks/{tid}/history")
        assert r.status_code == 200
        history = r.json()
        assert len(history) >= 1
        assert history[0]["new_status"] == "done"

    def test_delete(self, seed):
        created = client.post("/api/tasks", json={
            "account_id": seed["account"]["id"], "title": "삭제할일"
        }).json()
        r = client.delete(f"/api/tasks/{created['id']}")
        assert r.status_code == 200

    def test_bulk_create(self, seed):
        items = [
            {"account_id": seed["account"]["id"], "title": f"일괄할일{i}", "status": "todo", "priority": "mid", "assignee": "테스터"}
            for i in range(5)
        ]
        r = client.post("/api/tasks/bulk", json=items)
        assert r.status_code == 201
        data = r.json()
        assert len(data) == 5
        assert all("updated_at" in d for d in data)

    def test_bulk_create_with_tab_fields(self, seed):
        """Verify assignee and due_date from tab-separated input."""
        items = [
            {"account_id": seed["account"]["id"], "title": "확인서 발송", "assignee": "김감사", "due_date": "2025-03-30", "status": "todo", "priority": "mid"},
            {"account_id": seed["account"]["id"], "title": "잔액검증", "assignee": "", "status": "todo", "priority": "mid"},
        ]
        r = client.post("/api/tasks/bulk", json=items)
        assert r.status_code == 201
        data = r.json()
        assert data[0]["assignee"] == "김감사"
        assert data[0]["due_date"] == "2025-03-30"
        assert data[1]["assignee"] == ""


# ═══════════════════════════════════════════════════════════════════════════
# 6. Templates CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestTemplates:
    def test_list(self):
        r = client.get("/api/templates")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_create_and_get(self):
        r = client.post("/api/templates", json={
            "name": "테스트템플릿", "industry": "기타",
            "accounts_json": '[{"name":"테스트","tasks":["a","b"]}]'
        })
        assert r.status_code == 201
        tid = r.json()["id"]

        r2 = client.get(f"/api/templates/{tid}")
        assert r2.status_code == 200
        assert r2.json()["name"] == "테스트템플릿"
        assert isinstance(r2.json()["accounts"], list)

    def test_update(self):
        created = client.post("/api/templates", json={
            "name": "수정전", "industry": "X"
        }).json()
        r = client.put(f"/api/templates/{created['id']}", json={"name": "수정후"})
        assert r.status_code == 200
        assert r.json()["name"] == "수정후"

    def test_delete(self):
        created = client.post("/api/templates", json={"name": "삭제용"}).json()
        r = client.delete(f"/api/templates/{created['id']}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 7. ICFR Tests CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestICFR:
    def test_list(self):
        r = client.get("/api/icfr-tests")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_list_filter(self):
        r = client.get("/api/icfr-tests?client_name=한빛제조&status=완료")
        assert r.status_code == 200

    def test_create(self, seed):
        r = client.post("/api/icfr-tests", json={
            "client_name": "테스트사", "process": "매출",
            "control_name": "테스트통제", "test_method": "검사",
            "status": "미실시", "assignee": "테스터"
        })
        assert r.status_code == 201

    def test_update(self):
        all_tests = client.get("/api/icfr-tests").json()
        tid = all_tests[0]["id"]
        r = client.put(f"/api/icfr-tests/{tid}", json={"status": "완료"})
        assert r.status_code == 200
        assert r.json()["status"] == "완료"

    def test_delete(self):
        created = client.post("/api/icfr-tests", json={
            "client_name": "삭제용", "process": "x", "control_name": "y"
        }).json()
        r = client.delete(f"/api/icfr-tests/{created['id']}")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 8. Settings
# ═══════════════════════════════════════════════════════════════════════════

class TestSettings:
    def test_get(self):
        r = client.get("/api/settings")
        assert r.status_code == 200
        data = r.json()
        assert "activeFY" in data

    def test_update(self):
        r = client.put("/api/settings", json={"userName": "감사인", "customKey": "value"})
        assert r.status_code == 200

        r2 = client.get("/api/settings")
        assert r2.json()["userName"] == "감사인"
        assert r2.json()["customKey"] == "value"


# ═══════════════════════════════════════════════════════════════════════════
# 9. PBC Items CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestPBCItems:
    def test_list(self, seed):
        r = client.get(f"/api/pbc-items?client_id={seed['client']['id']}")
        assert r.status_code == 200
        assert len(r.json()) >= 1  # seeded PBC data for 한빛제조

    def test_create_and_get(self, seed):
        r = client.post("/api/pbc-items", json={
            "client_id": seed["client"]["id"],
            "name": "테스트자료",
            "status": "미요청",
        })
        assert r.status_code == 201
        pid = r.json()["id"]

        r2 = client.get(f"/api/pbc-items/{pid}")
        assert r2.status_code == 200
        assert r2.json()["name"] == "테스트자료"

    def test_update(self, seed):
        items = client.get(f"/api/pbc-items?client_id={seed['client']['id']}").json()
        pid = items[0]["id"]
        r = client.put(f"/api/pbc-items/{pid}", json={"status": "수령완료"})
        assert r.status_code == 200
        assert r.json()["status"] == "수령완료"

    def test_delete(self, seed):
        created = client.post("/api/pbc-items", json={
            "client_id": seed["client"]["id"], "name": "삭제용"
        }).json()
        r = client.delete(f"/api/pbc-items/{created['id']}")
        assert r.status_code == 200

    def test_bulk_create(self, seed):
        items = [
            {"client_id": seed["client"]["id"], "name": f"일괄{i}", "status": "미요청"}
            for i in range(3)
        ]
        r = client.post("/api/pbc-items/bulk", json=items)
        assert r.status_code == 201
        assert len(r.json()) == 3

    def test_bulk_update(self, seed):
        # Create items to update
        items = [
            {"client_id": seed["client"]["id"], "name": f"수정대상{i}", "status": "미요청"}
            for i in range(3)
        ]
        created = client.post("/api/pbc-items/bulk", json=items).json()
        ids = [c["id"] for c in created]

        r = client.patch("/api/pbc-items/bulk-update", json={
            "ids": ids, "updates": {"status": "요청완료", "auditor": "김감사"}
        })
        assert r.status_code == 200
        assert r.json()["updated"] == 3

        # Verify
        item = client.get(f"/api/pbc-items/{ids[0]}").json()
        assert item["status"] == "요청완료"
        assert item["auditor"] == "김감사"

    def test_bulk_delete(self, seed):
        items = [
            {"client_id": seed["client"]["id"], "name": f"삭제대상{i}", "status": "미요청"}
            for i in range(2)
        ]
        created = client.post("/api/pbc-items/bulk", json=items).json()
        ids = [c["id"] for c in created]

        r = client.post("/api/pbc-items/bulk-delete", json={"ids": ids})
        assert r.status_code == 200
        assert r.json()["deleted"] == 2

        # Verify deleted
        r2 = client.get(f"/api/pbc-items/{ids[0]}")
        assert r2.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# 10. Search API
# ═══════════════════════════════════════════════════════════════════════════

class TestSearch:
    def test_empty_query(self):
        r = client.get("/api/search?q=")
        assert r.status_code == 200
        data = r.json()
        assert data["clients"] == []
        assert data["tasks"] == []

    def test_search_client(self):
        r = client.get("/api/search?q=한빛")
        assert r.status_code == 200
        data = r.json()
        assert len(data["clients"]) >= 1
        assert "path" in data["clients"][0]

    def test_search_task(self):
        r = client.get("/api/search?q=매출채권")
        assert r.status_code == 200
        data = r.json()
        # Should find accounts and/or tasks
        total = len(data.get("accounts", [])) + len(data.get("tasks", []))
        assert total >= 1

    def test_search_assignee(self):
        r = client.get("/api/search?q=김감사")
        assert r.status_code == 200
        assert len(r.json()["tasks"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# 11. Dashboard API
# ═══════════════════════════════════════════════════════════════════════════

class TestDashboard:
    def test_dashboard(self):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "overallProgress" in data
        assert "totalTasks" in data
        assert "doneTasks" in data
        assert "todoCount" in data
        assert "overdueCount" in data
        assert "reviewCount" in data
        assert "clients" in data
        assert "deadlines" in data
        assert "icfrTotal" in data
        assert isinstance(data["clients"], list)
        assert data["totalTasks"] >= 1
        # Clients should have progress and node_id
        if data["clients"]:
            c = data["clients"][0]
            assert "progress" in c
            assert "node_id" in c
            assert "next_deadline" in c
        # Deadlines should have node_id
        if data["deadlines"]:
            dl = data["deadlines"][0]
            assert "node_id" in dl
            assert "account_id" in dl


# ═══════════════════════════════════════════════════════════════════════════
# 12. Notifications API
# ═══════════════════════════════════════════════════════════════════════════

class TestNotifications:
    def test_notifications(self):
        r = client.get("/api/notifications")
        assert r.status_code == 200
        data = r.json()
        assert "overdue" in data
        assert "due_today" in data
        assert "due_week" in data
        assert "review" in data
        assert "total_count" in data
        assert isinstance(data["overdue"], list)


# ═══════════════════════════════════════════════════════════════════════════
# 13. Engagement Tree API
# ═══════════════════════════════════════════════════════════════════════════

class TestEngagementTree:
    def test_tree_structure(self):
        r = client.get("/api/engagement-tree")
        assert r.status_code == 200
        tree = r.json()
        assert isinstance(tree, list)
        assert len(tree) >= 1
        fy = tree[0]
        assert fy["type"] == "fy"
        assert "children" in fy
        # Drill down
        cl = fy["children"][0]
        assert cl["type"] == "client"
        ph = cl["children"][0]
        assert ph["type"] == "phase"
        acc = ph["children"][0]
        assert acc["type"] == "account"


# ═══════════════════════════════════════════════════════════════════════════
# 14. Template Checklists
# ═══════════════════════════════════════════════════════════════════════════

class TestTemplateChecklists:
    def test_upsert_and_list(self):
        # upsert
        r = client.put("/api/template-checklists", json={
            "template_id": 1, "sheet_name": "Sheet1",
            "row_index": 0, "is_completed": True, "note": "done"
        })
        assert r.status_code == 200

        # list
        r2 = client.get("/api/template-checklists?template_id=1")
        assert r2.status_code == 200
        items = r2.json()
        assert len(items) >= 1
        assert items[0]["is_completed"] == 1

    def test_bulk_upsert(self):
        items = [
            {"template_id": 1, "sheet_name": "S", "row_index": i, "is_completed": i % 2 == 0}
            for i in range(5)
        ]
        r = client.put("/api/template-checklists/bulk", json=items)
        assert r.status_code == 200

        r2 = client.get("/api/template-checklists?template_id=1")
        assert len(r2.json()) >= 5

    def test_delete(self):
        client.put("/api/template-checklists", json={
            "template_id": 99, "sheet_name": "X", "row_index": 0, "is_completed": True
        })
        r = client.delete("/api/template-checklists?template_id=99")
        assert r.status_code == 200
        r2 = client.get("/api/template-checklists?template_id=99")
        assert len(r2.json()) == 0


# ═══════════════════════════════════════════════════════════════════════════
# 15. Interviews
# ═══════════════════════════════════════════════════════════════════════════

class TestInterviews:
    def test_create_and_list(self, seed):
        r = client.post("/api/interviews", json={
            "client_id": seed["client"]["id"], "date": "2025-04-10",
            "interviewee": "김재무", "position": "재무팀장",
            "topic": "매출채권 확인", "status": "진행중"
        })
        assert r.status_code == 201
        iid = r.json()["id"]

        r2 = client.get(f"/api/interviews?client_id={seed['client']['id']}")
        assert r2.status_code == 200
        assert any(i["id"] == iid for i in r2.json())

    def test_get_with_questions(self, seed):
        created = client.post("/api/interviews", json={
            "client_id": seed["client"]["id"], "date": "2025-04-11",
            "interviewee": "박회계", "topic": "재고실사"
        }).json()
        iid = created["id"]

        # Sync questions
        qs = [
            {"interview_id": iid, "order_num": 0, "question": "실사 일정은?", "answer": "4월 15일", "answerer": "박회계"},
            {"interview_id": iid, "order_num": 1, "question": "외부 창고도 포함?", "answer": "포함", "answerer": "박회계", "needs_followup": True, "followup_note": "창고 목록 수령 필요"},
        ]
        r = client.put(f"/api/interview-questions/sync?interview_id={iid}", json=qs)
        assert r.status_code == 200

        # Get with questions
        r2 = client.get(f"/api/interviews/{iid}")
        assert r2.status_code == 200
        data = r2.json()
        assert len(data["questions"]) == 2
        assert data["questions"][1]["needs_followup"] == 1

    def test_update(self, seed):
        created = client.post("/api/interviews", json={
            "client_id": seed["client"]["id"], "date": "2025-04-12",
            "interviewee": "이감사", "status": "진행중"
        }).json()
        r = client.put(f"/api/interviews/{created['id']}", json={"status": "완료", "memo": "특이사항 없음"})
        assert r.status_code == 200
        assert r.json()["status"] == "완료"

    def test_delete(self, seed):
        created = client.post("/api/interviews", json={
            "client_id": seed["client"]["id"], "date": "2025-04-13",
            "interviewee": "삭제용"
        }).json()
        r = client.delete(f"/api/interviews/{created['id']}")
        assert r.status_code == 200

    def test_question_sync_replaces(self, seed):
        created = client.post("/api/interviews", json={
            "client_id": seed["client"]["id"], "date": "2025-04-14",
            "interviewee": "동기화테스트"
        }).json()
        iid = created["id"]
        # First sync: 3 questions
        client.put(f"/api/interview-questions/sync?interview_id={iid}", json=[
            {"interview_id": iid, "order_num": i, "question": f"Q{i}"} for i in range(3)
        ])
        # Second sync: 1 question (should replace)
        client.put(f"/api/interview-questions/sync?interview_id={iid}", json=[
            {"interview_id": iid, "order_num": 0, "question": "Only one"}
        ])
        data = client.get(f"/api/interviews/{iid}").json()
        assert len(data["questions"]) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 16. PBC Excel Items
# ═══════════════════════════════════════════════════════════════════════════

class TestPBCExcelItems:
    def test_upsert_and_list(self, seed):
        cid = seed["client"]["id"]
        r = client.put("/api/pbc-excel-items", json={
            "client_id": cid, "file_name": "test.xlsx",
            "sheet_name": "Sheet1", "row_index": 0,
            "is_received": True, "received_date": "2025-03-20",
            "completion_status": "○", "note": "OK"
        })
        assert r.status_code == 200

        r2 = client.get(f"/api/pbc-excel-items?client_id={cid}&file_name=test.xlsx")
        assert r2.status_code == 200
        items = r2.json()
        assert len(items) >= 1
        assert items[0]["is_received"] == 1
        assert items[0]["completion_status"] == "○"

    def test_upsert_updates_existing(self, seed):
        cid = seed["client"]["id"]
        # First insert
        client.put("/api/pbc-excel-items", json={
            "client_id": cid, "file_name": "dup.xlsx",
            "sheet_name": "S", "row_index": 0,
            "is_received": False, "completion_status": ""
        })
        # Update same row
        client.put("/api/pbc-excel-items", json={
            "client_id": cid, "file_name": "dup.xlsx",
            "sheet_name": "S", "row_index": 0,
            "is_received": True, "completion_status": "△"
        })
        items = client.get(f"/api/pbc-excel-items?client_id={cid}&file_name=dup.xlsx").json()
        # Should be only 1 row, not 2
        matching = [i for i in items if i["sheet_name"] == "S" and i["row_index"] == 0]
        assert len(matching) == 1
        assert matching[0]["completion_status"] == "△"

    def test_bulk_upsert(self, seed):
        cid = seed["client"]["id"]
        items = [
            {"client_id": cid, "file_name": "bulk.xlsx", "sheet_name": "S",
             "row_index": i, "is_received": i % 2 == 0, "completion_status": "○" if i == 0 else ""}
            for i in range(4)
        ]
        r = client.put("/api/pbc-excel-items/bulk", json=items)
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    try:
        os.unlink(TEST_DB)
    except OSError:
        pass
