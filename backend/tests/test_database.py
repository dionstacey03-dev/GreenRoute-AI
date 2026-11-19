import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Base, SavedJourney, User


def test_user_and_saved_journey_schema_round_trip():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    user_id = uuid.uuid4()

    with Session(engine) as session:
        user = User(id=user_id, email="traveller@example.test", password_hash="test-hash")
        session.add(user)
        session.flush()
        session.add(SavedJourney(
            user_id=user_id,
            origin="Negombo",
            destination="NSBM Green University",
            route_name="Green Multimodal",
            preference="greenest",
            distance_km=38.2,
            duration_minutes=72,
            estimated_cost_lkr=255,
            estimated_co2_kg=1.72,
            green_score=91,
            ranking_score=88.5,
        ))
        session.commit()

        journey = session.scalars(select(SavedJourney).where(SavedJourney.user_id == user_id)).one()
        assert journey.origin == "Negombo"
        assert journey.estimated_cost_lkr == 255
        assert journey.user.email == "traveller@example.test"


def test_email_is_unique():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            User(email="same@example.test", password_hash="hash-a"),
            User(email="same@example.test", password_hash="hash-b"),
        ])
        with pytest.raises(IntegrityError):
            session.commit()


def test_alembic_initial_migration_creates_expected_tables(tmp_path, monkeypatch):
    database_path = tmp_path / "greenroute-migration-test.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    backend_dir = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {"users", "saved_journeys", "alembic_version"}.issubset(tables)
    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(saved_journeys)")}
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert {"estimated_cost_difference_lkr", "estimated_co2_difference_kg"}.issubset(columns)
    assert revision == "0003_journey_differences"
