"""Engagement type templates and the engagement-tree endpoint."""


def test_audit_engagement_seeds_two_phases(client, make):
    fy = make.fy()
    c = make.client(fy["id"])
    eng = make.engagement(c["id"], eng_type="audit")
    tree = client.get("/api/engagement-tree").json()
    eng_node = tree[0]["children"][0]["children"][0]
    names = [p["label"] for p in eng_node["children"]]
    assert names == ["기중감사", "기말감사"]
    assert all(p["type"] == "phase" for p in eng_node["children"])


def test_review_engagement_seeds_one_phase(client, make):
    fy = make.fy()
    c = make.client(fy["id"])
    make.engagement(c["id"], name="반기검토", eng_type="review")
    tree = client.get("/api/engagement-tree").json()
    eng_node = tree[0]["children"][0]["children"][0]
    assert [p["label"] for p in eng_node["children"]] == ["검토절차"]


def test_etc_engagement_is_empty(client, make):
    fy = make.fy()
    c = make.client(fy["id"])
    make.engagement(c["id"], name="내부회계감사", eng_type="etc")
    tree = client.get("/api/engagement-tree").json()
    eng_node = tree[0]["children"][0]["children"][0]
    assert eng_node["children"] == []
    assert eng_node["eng_type"] == "etc"


def test_apply_template_false_skips_phases(client, make):
    fy = make.fy()
    c = make.client(fy["id"])
    make.engagement(c["id"], eng_type="audit", apply_template=False)
    tree = client.get("/api/engagement-tree").json()
    assert tree[0]["children"][0]["children"][0]["children"] == []


def test_tree_returns_all_fys_with_active_flag(client, make):
    old = make.fy(label="FY2024", is_active=False)
    new = make.fy(label="FY2025", is_active=True)
    tree = client.get("/api/engagement-tree").json()
    by_label = {n["label"]: n for n in tree}
    assert set(by_label) == {"FY2024", "FY2025"}
    assert by_label["FY2025"]["is_active"] is True
    assert by_label["FY2024"]["is_active"] is False


def test_tree_account_carries_parent_label_and_task_count(client, make):
    fy = make.fy()
    c = make.client(fy["id"], name="한빛제조")
    eng = make.engagement(c["id"], eng_type="etc")
    ph = make.phase(eng["id"], name="기중감사")
    acc = make.account(ph["id"], name="매출채권")
    client.post("/api/tasks", json={"account_id": acc["id"], "title": "확인서 발송"})

    tree = client.get("/api/engagement-tree").json()
    acc_node = tree[0]["children"][0]["children"][0]["children"][0]["children"][0]
    assert acc_node["type"] == "account"
    assert acc_node["parent_label"] == "한빛제조 · 기중감사"
    assert acc_node["task_count"] == 1


def test_nested_folder_in_etc_engagement(client, make):
    fy = make.fy()
    c = make.client(fy["id"])
    eng = make.engagement(c["id"], eng_type="etc")
    folder = make.phase(eng["id"], name="전사수준통제", kind="folder")
    sub = make.phase(eng["id"], name="하위폴더", kind="folder", parent_id=folder["id"])
    make.account(sub["id"], name="통제기술서 입수")

    tree = client.get("/api/engagement-tree").json()
    folder_node = tree[0]["children"][0]["children"][0]["children"][0]
    assert folder_node["type"] == "folder"
    sub_node = folder_node["children"][0]
    assert sub_node["label"] == "하위폴더"
    assert sub_node["children"][0]["label"] == "통제기술서 입수"
