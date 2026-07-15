"""ICFR (nested RCM) and Template tests, plus settings."""


def _client(make):
    fy = make.fy()
    return make.client(fy["id"])


def test_icfr_create_returns_nested_rcm(client, make):
    c = _client(make)
    payload = {
        "client_id": c["id"],
        "code": "RV-01",
        "process": "수익",
        "description": "매출 인식 전 계약조건 검토·승인",
        "ctrl_type": "operating",
        "status": "in_progress",
        "rcm": {
            "risk": "조기 인식 위험",
            "mrc": True, "ipe": True,
            "accounts": ["매출", "매출채권"],
            "assertions": ["발생사실", "기간귀속"],
            "test_types": ["질문", "검사", "재수행"],
            "eval_result": "평가중",
        },
    }
    ctrl = client.post("/api/icfr", json=payload).json()
    assert ctrl["code"] == "RV-01"
    assert ctrl["rcm"]["mrc"] is True
    assert ctrl["rcm"]["accounts"] == ["매출", "매출채권"]
    assert ctrl["rcm"]["test_types"] == ["질문", "검사", "재수행"]


def test_icfr_update_rcm(client, make):
    c = _client(make)
    ctrl = client.post("/api/icfr", json={"client_id": c["id"], "code": "X-1"}).json()
    upd = client.put(f"/api/icfr/{ctrl['id']}", json={
        "status": "exception",
        "rcm": {"exception_note": "미비점 발견", "residual_risk": "높음"},
    }).json()
    assert upd["status"] == "exception"
    assert upd["rcm"]["exception_note"] == "미비점 발견"
    assert upd["rcm"]["residual_risk"] == "높음"


def test_icfr_filter_by_client(client, make):
    fy = make.fy()
    c1 = make.client(fy["id"], name="A")
    c2 = make.client(fy["id"], name="B")
    client.post("/api/icfr", json={"client_id": c1["id"], "code": "A-1"})
    client.post("/api/icfr", json={"client_id": c2["id"], "code": "B-1"})
    rows = client.get(f"/api/icfr?client_id={c1['id']}").json()
    assert [r["code"] for r in rows] == ["A-1"]


def test_template_crud_with_accounts(client):
    tpl = client.post("/api/templates", json={
        "name": "제조업 기본", "industry": "제조업",
        "accounts": [{"name": "매출채권", "task_count": 4}, {"name": "재고자산", "task_count": 4}],
    }).json()
    assert len(tpl["accounts"]) == 2
    assert tpl["name"] == "제조업 기본"

    upd = client.put(f"/api/templates/{tpl['id']}", json={
        "accounts": [{"name": "유형자산", "task_count": 3}],
    }).json()
    assert [a["name"] for a in upd["accounts"]] == ["유형자산"]


def test_settings_get_creates_default_then_updates(client):
    s = client.get("/api/settings").json()
    assert s["id"] == 1
    assert s["deadline_threshold"] == "D-7"

    upd = client.put("/api/settings", json={"user_name": "김감사", "deadline_threshold": "D-3"}).json()
    assert upd["user_name"] == "김감사"
    assert upd["deadline_threshold"] == "D-3"
    assert upd["startup_alert"] is True  # unchanged
