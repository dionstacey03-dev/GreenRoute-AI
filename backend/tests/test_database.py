import uuid

import pytest
from sqlalchemy import create_engine, select
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
        with pytest.raises(Exception):
            session.commit()
