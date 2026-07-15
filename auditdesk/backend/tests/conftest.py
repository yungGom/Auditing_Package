"""Pytest fixtures: a fresh in-memory SQLite DB per test, wired into the app via
dependency override. PRAGMA foreign_keys is enabled so cascade tests are real.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, connection_record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


# ---- small builders so each test reads top-down ----
@pytest.fixture()
def make(client):
    """Helper namespace for creating nested entities quickly."""

    def fy(label="FY2025", is_active=True):
        return client.post("/api/fiscal-years", json={"label": label, "is_active": is_active}).json()

    def client_(fy_id, name="한빛제조", industry="제조업"):
        return client.post("/api/clients", json={"fy_id": fy_id, "name": name, "industry": industry}).json()

    def engagement(client_id, name="기말감사 FY2025", eng_type="audit", apply_template=True):
        return client.post(
            "/api/engagements",
            json={"client_id": client_id, "name": name, "eng_type": eng_type, "apply_template": apply_template},
        ).json()

    def phase(engagement_id, name="기중감사", kind="phase", parent_id=None):
        return client.post(
            "/api/phases",
            json={"engagement_id": engagement_id, "name": name, "kind": kind, "parent_id": parent_id},
        ).json()

    def account(phase_id, name="매출채권"):
        return client.post("/api/accounts", json={"phase_id": phase_id, "name": name}).json()

    class Make:
        pass

    m = Make()
    m.fy = fy
    m.client = client_
    m.engagement = engagement
    m.phase = phase
    m.account = account
    return m
