"""Fiscal-year tests, including the single-active-FY rule (bug-prevention #1)."""


def test_initial_state_is_empty(client):
    assert client.get("/api/fiscal-years").json() == []


def test_create_returns_resource(client):
    r = client.post("/api/fiscal-years", json={"label": "FY2025", "is_active": True})
    assert r.status_code == 201
    body = r.json()
    assert body["label"] == "FY2025"
    assert body["is_active"] is True
    assert isinstance(body["id"], int)


def test_only_one_fy_active_on_create(client):
    a = client.post("/api/fiscal-years", json={"label": "FY2024", "is_active": True}).json()
    b = client.post("/api/fiscal-years", json={"label": "FY2025", "is_active": True}).json()

    rows = {fy["id"]: fy for fy in client.get("/api/fiscal-years").json()}
    assert rows[a["id"]]["is_active"] is False
    assert rows[b["id"]]["is_active"] is True


def test_activating_via_put_deactivates_others(client):
    a = client.post("/api/fiscal-years", json={"label": "FY2024", "is_active": True}).json()
    b = client.post("/api/fiscal-years", json={"label": "FY2025", "is_active": False}).json()

    # activate b through PUT
    put = client.put(f"/api/fiscal-years/{b['id']}", json={"is_active": True})
    assert put.status_code == 200
    assert put.json()["is_active"] is True

    rows = {fy["id"]: fy for fy in client.get("/api/fiscal-years").json()}
    assert rows[a["id"]]["is_active"] is False
    assert rows[b["id"]]["is_active"] is True
    assert sum(fy["is_active"] for fy in rows.values()) == 1


def test_partial_update_keeps_other_fields(client):
    fy = client.post("/api/fiscal-years", json={"label": "FY2025", "is_active": True}).json()
    client.put(f"/api/fiscal-years/{fy['id']}", json={"label": "FY2025 (수정)"})
    got = client.get(f"/api/fiscal-years/{fy['id']}").json()
    assert got["label"] == "FY2025 (수정)"
    assert got["is_active"] is True  # unchanged


def test_delete_fy(client):
    fy = client.post("/api/fiscal-years", json={"label": "FY2025"}).json()
    assert client.delete(f"/api/fiscal-years/{fy['id']}").status_code == 204
    assert client.get(f"/api/fiscal-years/{fy['id']}").status_code == 404
