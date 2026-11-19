import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth import ClerkIdentity, require_clerk_user
from database import get_session_factory
from journeys import get_db
from main import app
from models import Base


@pytest.fixture
def client_and_identity():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    identity = {"value": ClerkIdentity("user_test_a", {"sub": "user_test_a"})}

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    def override_identity():
        return identity["value"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_clerk_user] = override_identity
    with TestClient(app) as client:
        yield client, identity
    app.dependency_overrides.clear()
    engine.dispose()


def test_saved_journeys_are_private_to_the_authenticated_clerk_user(client_and_identity):
    client, identity = client_and_identity
    payload = {
        "origin": "Negombo",
        "destination": "NSBM Green University",
        "route_name": "Green Multimodal",
        "preference": "greenest",
        "distance_km": 38.2,
        "duration_minutes": 72,
        "estimated_cost_lkr": 255,
        "estimated_co2_kg": 1.72,
        "green_score": 91,
        "ranking_score": 88.5,
    }

    created = client.post("/api/journeys", json=payload)
    assert created.status_code == 201
    journey_id = created.json()["id"]
    assert client.get("/api/journeys").json()["count"] == 1

    identity["value"] = ClerkIdentity("user_test_b", {"sub": "user_test_b"})
    assert client.get("/api/journeys").json()["count"] == 0
    assert client.delete(f"/api/journeys/{journey_id}").status_code == 404

    identity["value"] = ClerkIdentity("user_test_a", {"sub": "user_test_a"})
    assert client.delete(f"/api/journeys/{journey_id}").status_code == 200


def test_saved_journey_rejects_unexpected_fields(client_and_identity):
    client, _ = client_and_identity
    response = client.post("/api/journeys", json={
        "origin": "Negombo",
        "destination": "Colombo",
        "route_name": "Test",
        "preference": "greenest",
        "distance_km": 10,
        "duration_minutes": 30,
        "estimated_cost_lkr": 100,
        "estimated_co2_kg": 1,
        "green_score": 80,
        "ranking_score": 80,
        "user_id": "user_test_b",
    })
    assert response.status_code == 422


def test_profile_maps_clerk_subject_to_local_user(client_and_identity):
    client, _ = client_and_identity
    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.json()["clerk_user_id"] == "user_test_a"
    assert uuid.UUID(response.json()["application_user_id"])
