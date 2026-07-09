"""AuditLink v2 API — FastAPI app entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import (
    clients,
    engagements,
    fiscal_years,
    icfr,
    interviews,
    pbc,
    settings,
    structure,
    tasks,
    templates,
    tree,
)

# Create tables on startup. (For schema migrations later, swap in Alembic.)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AuditLink v2 API", version="2.0.0")

# Vite dev server runs on 5173; allow local origins during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    fiscal_years,
    clients,
    engagements,
    structure,
    tasks,
    pbc,
    interviews,
    icfr,
    templates,
    settings,
    tree,
):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
