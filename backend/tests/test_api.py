import pytest
import httpx
from fastapi.testclient import TestClient

from main import app, estimate_routes, rank_routes

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["version"] == "3.0.0"


def test_metadata_labels_live_and_estimated_sources():
    data = client.get("/api/meta").json()
    assert data["routing"]["live"] is True
    assert data["transit"]["live"] is False
    assert data["emissions"]["measured"] is False


@pytest.mark.parametrize("preference", ["fastest", "cheapest", "greenest", "balanced"])
def test_estimate_routes_returns_one_recommendation(preference):
    routes = estimate_routes(12.5, 24, preference)
    assert len(routes) == 3
    assert sum(route["recommended"] for route in routes) == 1
    assert all(route["time"] > 0 and route["cost"] >= 0 for route in routes)
    assert all(0 <= route["ranking_score"] <= 100 for route in routes)


def test_greenest_preference_ranks_lowest_emissions_first():
    routes = estimate_routes(20, 30, "greenest")
    assert routes[0]["name"] == "Green Multimodal"


def test_fastest_preference_ranks_shortest_time_first():
    routes = estimate_routes(20, 30, "fastest")
    assert routes[0]["name"] == "Direct Road"


def test_cheapest_preference_ranks_lowest_cost_first():
    routes = estimate_routes(20, 30, "cheapest")
    assert routes[0]["name"] == "Green Multimodal"


def test_equal_metrics_are_stable_and_finite():
    routes = [
        {"id": "a", "time": 10, "cost": 10, "co2": 10, "reliability": 80},
        {"id": "b", "time": 10, "cost": 10, "co2": 10, "reliability": 80},
    ]
    ranked = rank_routes(routes, "balanced")
    assert all(route["ranking_score"] == 97 for route in ranked)
    assert ranked[0]["id"] == "a"
    assert sum(route["recommended"] for route in ranked) == 1


def test_empty_route_ranking_is_safe():
    assert rank_routes([], "balanced") == []


def test_route_request_rejects_partial_coordinates():
    response = client.post("/api/routes", json={
        "origin": "Colombo", "destination": "Galle", "origin_latitude": 6.9,
    })
    assert response.status_code == 422


def test_route_request_rejects_out_of_range_coordinates():
    response = client.post("/api/routes", json={
        "origin": "Colombo", "destination": "Galle",
        "origin_latitude": 120, "origin_longitude": 79,
        "destination_latitude": 6, "destination_longitude": 80,
    })
    assert response.status_code == 422


def test_geocode_rejects_short_query():
    response = client.get("/api/geocode?q=a")
    assert response.status_code == 422

