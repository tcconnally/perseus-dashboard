"""Perseus Dashboard API — FastAPI backend for H0 Hackathon.

Uses AWS Aurora PostgreSQL for production, falls back to mock data
when DATABASE_URL is not set or the database is unreachable.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("perseus-dashboard")

app = FastAPI(title="Perseus Dashboard API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database setup (graceful fallback if no DATABASE_URL)
# ---------------------------------------------------------------------------
db_available = False
SessionLocal = None
Project = None
ContextSnapshot = None
MemoryEvent = None
TokenAnalytics = None

DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    try:
        from database import (
            engine, SessionLocal as _SessionLocal,
            Project as _Project,
            ContextSnapshot as _ContextSnapshot,
            MemoryEvent as _MemoryEvent,
            TokenAnalytics as _TokenAnalytics,
            init_db,
        )
        SessionLocal = _SessionLocal
        Project = _Project
        ContextSnapshot = _ContextSnapshot
        MemoryEvent = _MemoryEvent
        TokenAnalytics = _TokenAnalytics
        init_db()
        db_available = True
        logger.info(f"Connected to database (Aurora PostgreSQL)")
    except Exception as e:
        logger.warning(f"Database unavailable, using mock data: {e}")
else:
    logger.info("DATABASE_URL not set, using mock data")


def get_db():
    """Yield a DB session or None if unavailable."""
    if not db_available or SessionLocal is None:
        return None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ServiceStatus(BaseModel):
    name: str
    status: str
    latency_ms: Optional[float] = None


class ContextOut(BaseModel):
    project_id: int
    resolved_at: str
    token_estimate: int
    services: list[dict]
    context_files: list[str]


class MemoryEventOut(BaseModel):
    id: int
    event_type: str
    fact_key: Optional[str] = None
    fact_value: Optional[str] = None
    confidence: float
    created_at: str


class AnalyticsSummary(BaseModel):
    project_id: int
    total_saved: int
    total_used: int
    sessions: int
    days: list[dict]


# ---------------------------------------------------------------------------
# Mock data (used when database is unavailable)
# ---------------------------------------------------------------------------
MOCK_SERVICES = [
    {"name": "CI (GitHub Actions)", "status": "up", "latency_ms": 234},
    {"name": "Aurora PostgreSQL", "status": "up", "latency_ms": 12},
    {"name": "Redis Cache", "status": "up", "latency_ms": 3},
    {"name": "API Gateway", "status": "up", "latency_ms": 45},
    {"name": "Docker Registry", "status": "up", "latency_ms": 89},
    {"name": "Sentry (Error Tracking)", "status": "up", "latency_ms": 156},
]

MOCK_CONTEXT_FILES = [
    "AGENTS.md", "pyproject.toml", "docker-compose.yml",
    "Makefile", ".env.example", ".github/workflows/ci.yml",
]

MOCK_MEMORIES = [
    {"id": 1, "event_type": "store", "fact_key": "database.postgres_version",
     "fact_value": "PostgreSQL 16.3 on AWS Aurora Serverless v2", "confidence": 0.95,
     "created_at": "2026-06-17T14:23:01Z"},
    {"id": 2, "event_type": "recall", "fact_key": "convention.python_formatter",
     "fact_value": "black --line-length 88", "confidence": 0.92,
     "created_at": "2026-06-17T14:22:00Z"},
    {"id": 3, "event_type": "insight", "fact_key": "pattern.api_structure",
     "fact_value": "FastAPI routes follow /api/resource/{id}/action pattern", "confidence": 0.88,
     "created_at": "2026-06-17T14:20:00Z"},
    {"id": 4, "event_type": "store", "fact_key": "config.ci_provider",
     "fact_value": "GitHub Actions with matrix build", "confidence": 0.90,
     "created_at": "2026-06-17T14:18:00Z"},
    {"id": 5, "event_type": "decay", "fact_key": "preference.old_editor",
     "fact_value": "vscode (switched to cursor)", "confidence": 0.15,
     "created_at": "2026-06-17T14:16:00Z"},
    {"id": 6, "event_type": "store", "fact_key": "infra.aws_region",
     "fact_value": "us-east-1 for Aurora PostgreSQL cluster", "confidence": 0.97,
     "created_at": "2026-06-17T14:15:00Z"},
    {"id": 7, "event_type": "recall", "fact_key": "convention.git_branching",
     "fact_value": "feature branches, squash merge to main", "confidence": 0.94,
     "created_at": "2026-06-17T14:10:00Z"},
]

MOCK_ANALYTICS_DAYS = [
    {"day": "Mon", "saved": 2100, "used": 8500},
    {"day": "Tue", "saved": 1800, "used": 7200},
    {"day": "Wed", "saved": 2400, "used": 9100},
    {"day": "Thu", "saved": 3100, "used": 10400},
    {"day": "Fri", "saved": 1950, "used": 7800},
    {"day": "Sat", "saved": 800, "used": 3200},
    {"day": "Sun", "saved": 697, "used": 2800},
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Seed demo data into Aurora on first launch
# ---------------------------------------------------------------------------
def seed_demo_data():
    """Insert demo project + sample data into Aurora PostgreSQL if empty."""
    if not db_available or Project is None:
        return
    db = SessionLocal()
    try:
        existing = db.query(Project).first()
        if existing:
            return  # Already seeded

        project = Project(
            name="perseus-dashboard",
            github_url="https://github.com/tcconnally/perseus-dashboard",
            perseus_config={"context_files": MOCK_CONTEXT_FILES},
        )
        db.add(project)
        db.flush()

        # Context snapshot
        snapshot = ContextSnapshot(
            project_id=project.id,
            content={"services": MOCK_SERVICES, "files": MOCK_CONTEXT_FILES},
            file_count=len(MOCK_CONTEXT_FILES),
            token_estimate=12400,
        )
        db.add(snapshot)

        # Memory events
        for mem in MOCK_MEMORIES:
            event = MemoryEvent(
                project_id=project.id,
                event_type=mem["event_type"],
                fact_key=mem.get("fact_key"),
                fact_value=mem.get("fact_value"),
                confidence=mem["confidence"],
            )
            db.add(event)

        # Token analytics
        for day in MOCK_ANALYTICS_DAYS:
            ta = TokenAnalytics(
                project_id=project.id,
                session_id=f"session-{day['day'].lower()}",
                tokens_saved=day["saved"],
                tokens_total=day["used"],
            )
            db.add(ta)

        db.commit()
        logger.info(f"Seeded demo project (id={project.id}) with sample data")
    except Exception as e:
        db.rollback()
        logger.warning(f"Seed failed (may already exist): {e}")
    finally:
        db.close()


# Seed on import
seed_demo_data()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "database": "aurora-postgresql" if db_available else "mock", "now": now_iso()}


@app.get("/api/projects")
def list_projects():
    if db_available and Project is not None:
        db = SessionLocal()
        try:
            projects = db.query(Project).all()
            return [{"id": p.id, "name": p.name, "github_url": p.github_url,
                     "created_at": p.created_at.isoformat() if p.created_at else None}
                    for p in projects]
        finally:
            db.close()
    return [{"id": 1, "name": "perseus-dashboard", "demo": True}]


@app.get("/api/projects/{project_id}")
def get_project(project_id: int):
    if db_available and Project is not None:
        db = SessionLocal()
        try:
            p = db.query(Project).filter(Project.id == project_id).first()
            if p:
                return {"id": p.id, "name": p.name, "github_url": p.github_url,
                        "created_at": p.created_at.isoformat() if p.created_at else None}
        finally:
            db.close()
    return {"id": project_id, "name": "perseus-dashboard", "demo": True}


@app.get("/api/projects/{project_id}/services")
def get_services(project_id: int):
    return MOCK_SERVICES


@app.get("/api/projects/{project_id}/context")
def get_context(project_id: int):
    if db_available and ContextSnapshot is not None:
        db = SessionLocal()
        try:
            snap = db.query(ContextSnapshot).filter(
                ContextSnapshot.project_id == project_id
            ).order_by(ContextSnapshot.resolved_at.desc()).first()
            if snap:
                return {
                    "project_id": project_id,
                    "resolved_at": snap.resolved_at.isoformat(),
                    "token_estimate": snap.token_estimate,
                    "services": MOCK_SERVICES,
                    "context_files": MOCK_CONTEXT_FILES,
                }
        finally:
            db.close()
    return {
        "project_id": project_id,
        "resolved_at": now_iso(),
        "token_estimate": 12400,
        "services": MOCK_SERVICES,
        "context_files": MOCK_CONTEXT_FILES,
    }


@app.get("/api/projects/{project_id}/memories")
def get_memories(project_id: int, limit: int = 50):
    if db_available and MemoryEvent is not None:
        db = SessionLocal()
        try:
            events = db.query(MemoryEvent).filter(
                MemoryEvent.project_id == project_id
            ).order_by(MemoryEvent.created_at.desc()).limit(limit).all()
            if events:
                return [{
                    "id": e.id,
                    "event_type": e.event_type,
                    "fact_key": e.fact_key,
                    "fact_value": e.fact_value,
                    "confidence": e.confidence,
                    "created_at": e.created_at.isoformat(),
                } for e in events]
        finally:
            db.close()
    return MOCK_MEMORIES[:limit]


@app.get("/api/projects/{project_id}/analytics/summary")
def get_analytics_summary(project_id: int):
    if db_available and TokenAnalytics is not None:
        db = SessionLocal()
        try:
            records = db.query(TokenAnalytics).filter(
                TokenAnalytics.project_id == project_id
            ).all()
            if records:
                total_saved = sum(r.tokens_saved for r in records)
                total_used = sum(r.tokens_total for r in records)
                days = [{"day": r.session_id.replace("session-", "").title() if r.session_id else "?",
                         "saved": r.tokens_saved, "used": r.tokens_total} for r in records]
                return {
                    "project_id": project_id,
                    "total_saved": total_saved,
                    "total_used": total_used,
                    "sessions": len(records),
                    "days": days,
                }
        finally:
            db.close()
    return {
        "project_id": project_id,
        "total_saved": sum(d["saved"] for d in MOCK_ANALYTICS_DAYS),
        "total_used": sum(d["used"] for d in MOCK_ANALYTICS_DAYS),
        "sessions": len(MOCK_ANALYTICS_DAYS),
        "days": MOCK_ANALYTICS_DAYS,
    }
