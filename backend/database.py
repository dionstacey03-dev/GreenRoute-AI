"""Database connection utilities for GreenRoute AI.

The API remains usable without a configured database during local development.
Set DATABASE_URL to a PostgreSQL/Neon connection string to enable persistence.
"""
from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy.orm import sessionmaker


def _database_url() -> str | URL:
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        raise RuntimeError("DATABASE_URL is not configured.")

    parsed = make_url(raw)
    if parsed.drivername in {"postgres", "postgresql"}:
        parsed = parsed.set(drivername="postgresql+psycopg")
    elif parsed.drivername.startswith("postgresql+") and parsed.drivername != "postgresql+psycopg":
        # Keep explicitly selected PostgreSQL drivers intact.
        return parsed
    return parsed


@lru_cache(maxsize=1)
def get_engine():
    url = _database_url()
    options = {"pool_pre_ping": True}
    if isinstance(url, SQLAlchemyURL) and url.drivername.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    if isinstance(url, str) and url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **options)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def check_database_connection() -> bool:
    """Return true only when a configured database answers a simple query."""
    with get_engine().connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1


def database_is_configured() -> bool:
    return bool(os.getenv("DATABASE_URL", "").strip())
