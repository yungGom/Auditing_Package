"""PBC and Interview (nested questions) tests."""


def _account(make):
    fy = make.fy()
    c = make.client(fy["id"])
    eng = make.engagement(c["id"], eng_type="etc")
    ph = make.phase(eng["id"])
    return make.account(ph["id"])


def test_pbc_crud_and_done_cycle(client, make):
    acc = _account(make)
    item = client.post("/api/pbc", json={"account_id": acc["id"], "name": "채권 명세서"}).json()
    assert item["status"] == "draft"
    assert item["done"] == "none"

    upd = client.put(f"/api/pbc/{item['id']}", json={"done": "partial", "status": "received", "recv_date": "2025-04-19"}).json()
    assert upd["done"] == "partial"
    assert upd["status"] == "received"
    assert upd["recv_date"] == "2025-04-19"

    assert client.delete(f"/api/pbc/{item['id']}").status_code == 204
    assert client.get(f"/api/pbc?account_id={acc['id']}").json() == []


def test_pbc_bulk_import(client, make):
    acc = _account(make)
    payload = {"items": [
        {"account_id": acc["id"], "name": "자료1"},
        {"account_id": acc["id"], "name": "자료2"},
    ]}
    created = client.post("/api/pbc/bulk", json=payload).json()
    assert len(created) == 2
    assert {i["name"] for i in created} == {"자료1", "자료2"}


def test_interview_with_questions(client, make):
    acc = _account(make)
    payload = {
        "account_id": acc["id"],
        "date": "2025-04-29",
        "person": "이회계", "title": "차장", "topic": "결산 프로세스",
        "questions": [
            {"q": "마감 일정은?", "a": "", "follow_up": False},
            {"q": "수동분개 승인은?", "a": "팀장 승인", "answerer": "이회계", "follow_up": True, "follow_up_note": "표본 확인"},
        ],
    }
    iv = client.post("/api/interviews", json=payload).json()
    assert len(iv["questions"]) == 2
    assert iv["questions"][0]["order_index"] == 0
    assert iv["questions"][1]["follow_up"] is True


def test_interview_update_replaces_questions(client, make):
    acc = _account(make)
    iv = client.post("/api/interviews", json={
        "account_id": acc["id"], "topic": "t",
        "questions": [{"q": "q1"}, {"q": "q2"}, {"q": "q3"}],
    }).json()

    # reorder + drop to two questions
    reordered = client.put(f"/api/interviews/{iv['id']}", json={
        "status": "done",
        "questions": [{"q": "q3"}, {"q": "q1"}],
    }).json()
    assert reordered["status"] == "done"
    assert [q["q"] for q in reordered["questions"]] == ["q3", "q1"]
    assert [q["order_index"] for q in reordered["questions"]] == [0, 1]


def test_interview_list_sorted_desc(client, make):
    acc = _account(make)
    client.post("/api/interviews", json={"account_id": acc["id"], "date": "2025-03-18", "topic": "old"})
    client.post("/api/interviews", json={"account_id": acc["id"], "date": "2025-04-29", "topic": "new"})
    rows = client.get(f"/api/interviews?account_id={acc['id']}").json()
    assert [r["topic"] for r in rows] == ["new", "old"]
