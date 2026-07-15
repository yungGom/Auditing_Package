"""Account bulk/reorder, task status history, and cascade delete."""
from datetime import date


def _scaffold(make):
    fy = make.fy()
    c = make.client(fy["id"])
    eng = make.engagement(c["id"], eng_type="etc")
    ph = make.phase(eng["id"], name="기중감사")
    return fy, c, eng, ph


def test_bulk_add_accounts(client, make):
    _, _, _, ph = _scaffold(make)
    r = client.post("/api/accounts/bulk", json={"phase_id": ph["id"], "names": ["매출채권", "재고자산", " "]})
    assert r.status_code == 201
    created = r.json()
    assert [a["name"] for a in created] == ["매출채권", "재고자산"]  # blank dropped
    assert [a["order_index"] for a in created] == [0, 1]


def test_reorder_accounts(client, make):
    _, _, _, ph = _scaffold(make)
    created = client.post(
        "/api/accounts/bulk", json={"phase_id": ph["id"], "names": ["A", "B", "C"]}
    ).json()
    ids = [a["id"] for a in created]
    reordered = client.put(
        "/api/accounts/reorder", json={"phase_id": ph["id"], "ordered_ids": [ids[2], ids[0], ids[1]]}
    ).json()
    assert [a["name"] for a in reordered] == ["C", "A", "B"]


def test_task_create_records_initial_history(client, make):
    _, _, _, ph = _scaffold(make)
    acc = make.account(ph["id"])
    task = client.post("/api/tasks", json={"account_id": acc["id"], "title": "t1"}).json()
    assert len(task["history"]) == 1
    assert task["history"][0]["status"] == "todo"
    assert task["history"][0]["at"] == date.today().isoformat()


def test_task_status_change_appends_history(client, make):
    _, _, _, ph = _scaffold(make)
    acc = make.account(ph["id"])
    task = client.post("/api/tasks", json={"account_id": acc["id"], "title": "t1"}).json()

    updated = client.put(f"/api/tasks/{task['id']}", json={"status": "in_progress"}).json()
    assert updated["status"] == "in_progress"
    assert [h["status"] for h in updated["history"]] == ["todo", "in_progress"]

    # editing a non-status field must NOT add history
    same = client.put(f"/api/tasks/{task['id']}", json={"memo": "메모"}).json()
    assert len(same["history"]) == 2

    # setting the same status again must NOT add history
    again = client.put(f"/api/tasks/{task['id']}", json={"status": "in_progress"}).json()
    assert len(again["history"]) == 2


def test_invalid_status_rejected(client, make):
    _, _, _, ph = _scaffold(make)
    acc = make.account(ph["id"])
    r = client.post("/api/tasks", json={"account_id": acc["id"], "title": "t", "status": "bogus"})
    assert r.status_code == 422


def test_cascade_delete_from_fy(client, make):
    fy, c, eng, ph = _scaffold(make)
    acc = make.account(ph["id"])
    task = client.post("/api/tasks", json={"account_id": acc["id"], "title": "t"}).json()

    assert client.delete(f"/api/fiscal-years/{fy['id']}").status_code == 204
    # whole subtree is gone
    assert client.get("/api/engagement-tree").json() == []
    assert client.get(f"/api/tasks?account_id={acc['id']}").json() == []
    assert client.put(f"/api/tasks/{task['id']}", json={"memo": "x"}).status_code == 404
