"""TelemetryBot collector FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, auth, github, ingest, metrics, projects, runs
from app.db.session import init_db
from app.services.seed import seed_system_projects
from app.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_system_projects()
    yield


app = FastAPI(title="TelemetryBot Collector", version="0.2.0", lifespan=lifespan)

settings = get_settings()
_origins = [
    settings.dashboard_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(github.router, prefix="/v1", tags=["github"])
app.include_router(ingest.router, prefix="/v1", tags=["ingest"])
app.include_router(projects.router, prefix="/v1", tags=["projects"])
app.include_router(runs.router, prefix="/v1", tags=["runs"])
app.include_router(agents.router, prefix="/v1", tags=["agents"])
app.include_router(metrics.router, prefix="/v1", tags=["metrics"])


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "TelemetryBot collector",
        "health": "/health",
        "dashboard": settings.dashboard_url,
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
