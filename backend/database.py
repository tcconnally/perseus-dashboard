import os
import logging

logger = logging.getLogger("perseus-dashboard")

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    ""  # Empty = use mock data
)

engine = None
SessionLocal = None

if DATABASE_URL:
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10} if "postgresql" in DATABASE_URL else {},
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database engine created successfully")
    except Exception as e:
        logger.warning(f"Could not create database engine: {e}")
        DATABASE_URL = ""


# --- Models ---

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_url = Column(String(512), nullable=False)
    name = Column(String(256), nullable=False)
    perseus_config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_context_at = Column(DateTime, nullable=True)

    context_snapshots = relationship("ContextSnapshot", back_populates="project")
    memory_events = relationship("MemoryEvent", back_populates="project")
    token_analytics = relationship("TokenAnalytics", back_populates="project")


class ContextSnapshot(Base):
    __tablename__ = "context_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    content = Column(JSON, nullable=False)
    resolved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    file_count = Column(Integer, default=0)
    token_estimate = Column(Integer, default=0)

    project = relationship("Project", back_populates="context_snapshots")


class MemoryEvent(Base):
    __tablename__ = "memory_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    event_type = Column(String(32), nullable=False)  # store, recall, decay, insight
    fact_key = Column(String(512), nullable=True)
    fact_value = Column(Text, nullable=True)
    confidence = Column(Float, default=0.8)
    session_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="memory_events")


class TokenAnalytics(Base):
    __tablename__ = "token_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    session_id = Column(String(128), nullable=True)
    tokens_saved = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="token_analytics")


def init_db():
    """Create all tables if they don't exist."""
    if engine is not None:
        Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a database session."""
    if SessionLocal is None:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
