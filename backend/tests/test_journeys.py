import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from auth import ClerkIdentity, require_clerk_user
from database import get_session_factory
from journeys import get_db
from main import app
from models import Base


@pytest.fixture
def client_with_user():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    identity = {"current": ClerkIdentity(clerk_user_id="user_owner_a", claims={"sub": "user_owner_a"})}

    def override_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_clerk_user] = lambda: identity["current"]
    with TestClient(app) as client:
        yield client, identity
    app.dependency_overrides.clear()
    engine.dispose()


def payload(**overrides):
    value = {
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
        "estimated_cost_difference_lkr": 180,
        "estimated_co2_difference_kg": 4.2,
    }
    value.update(overrides)
    return value


def test_authenticated_user_can_create_and_list_own_journeys(client_with_user):
    client, _ = client_with_user
    created = client.post("/api/journeys", json=payload())
    assert created.status_code == 201
    item = created.json()
    assert item["origin"] == "Negombo"
    assert item["estimated_cost_difference_lkr"] == 180
    assert item["estimated_co2_difference_kg"] == 4.2

    listed = client.get("/api/journeys")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["items"][0]["id"] == item["id"]


def test_journeys_are_isolated_between_clerk_users(client_with_user):
    client, identity = client_with_user
    created = client.post("/api/journeys", json=payload())
    assert created.status_code == 201

    identity["current"] = ClerkIdentity(clerk_user_id="user_owner_b", claims={"sub": "user_owner_b"})
    other_user_list = client.get("/api/journeys")
    assert other_user_list.status_code == 200
    assert other_user_list.json() == {"items": [], "count": 0}


def test_user_cannot_delete_another_users_journey(client_with_user):
    client, identity = client_with_user
    created = client.post("/api/journeys", json=payload())
    journey_id = created.json()["id"]

    identity["current"] = ClerkIdentity(clerk_user_id="user_owner_b", claims={"sub": "user_owner_b"})
    response = client.delete(f"/api/journeys/{journey_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Saved journey not found."


def test_journey_create_rejects_unexpected_client_fields(client_with_user):
    client, _ = client_with_user
    response = client.post("/api/journeys", json=payload(user_id=str(uuid.uuid4())))
    assert response.status_code == 422


def test_journey_create_rejects_invalid_preference(client_with_user):
    client, _ = client_with_user
    response = client.post("/api/journeys", json=payload(preference="unrestricted"))
    assert response.status_code == 422
