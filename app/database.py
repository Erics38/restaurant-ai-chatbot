"""
Database configuration and session management.

Technology choice: SQLite via SQLAlchemy ORM.
  - SQLite is file-based (no separate server process) which makes it ideal for a
    single-instance containerised deployment like this one.
  - The database file lives in data/conversations.db and is mounted as a Docker
    volume so conversations survive container restarts.
  - If you ever need to scale to multiple replicas, swap the SQLALCHEMY_DATABASE_URL
    for a PostgreSQL/MySQL URL — no other code needs to change.

Threading note:
  SQLite's default behaviour is to raise an error if the same connection is used
  from multiple threads.  FastAPI runs handlers in a thread pool, so we pass
  check_same_thread=False.  SQLAlchemy's session-per-request pattern (get_db below)
  guarantees each request gets its own isolated session, so this is safe.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------
# Format: sqlite:///  <relative-path-from-cwd>
# The path is relative to wherever Uvicorn is launched (project root in Docker).
# Change this to "postgresql://user:pass@host/dbname" to switch databases.
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/conversations.db"

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        # Required for SQLite when used in a multi-threaded context (see module docstring).
        "check_same_thread": False,
    },
    # echo=True prints every SQL statement to stdout — handy during development,
    # but very noisy in production. Leave False unless actively debugging queries.
    echo=False,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
# autocommit=False  → changes must be explicitly committed (or rolled back on error).
# autoflush=False   → SQLAlchemy won't flush pending changes before every query;
#                     we control flushing manually, which is safer in async contexts.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
# All SQLAlchemy ORM models (in models.py) inherit from this Base.
# It keeps track of every model class so create_all() can build the schema.
Base = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI dependency: one DB session per request
# ---------------------------------------------------------------------------
def get_db():
    """
    Yield a SQLAlchemy session for the duration of a single HTTP request,
    then close it when the request is done — regardless of success or error.

    Usage in an endpoint:
        from fastapi import Depends
        from app.database import get_db

        @app.post("/chat")
        async def chat(db: Session = Depends(get_db)):
            db.query(...)  # use the session here

    The `try / finally` block ensures the session is always closed even if an
    unhandled exception propagates up through the endpoint.
    """
    db = SessionLocal()
    try:
        yield db        # FastAPI injects this session into the endpoint
    finally:
        db.close()      # Always release the connection back to the pool


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------
def init_db():
    """
    Create all database tables that are registered with Base.

    This is called once during application startup (see main.py).
    It is idempotent — if the tables already exist they are left untouched,
    so it's safe to call on every startup without data loss.

    If you add a new model/column, you'll need a proper migration tool
    (Alembic is the standard choice) rather than relying on create_all,
    because create_all does NOT alter existing tables.
    """
    # Import models here (not at module top) to avoid a circular import:
    # models.py imports Base from this file, so importing models at the top
    # of this file would create a cycle.
    from app.models import DBSession, DBMessage  # noqa: F401 — needed for side-effects

    Base.metadata.create_all(bind=engine)
