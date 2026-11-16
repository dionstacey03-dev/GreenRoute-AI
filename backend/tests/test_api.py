import pytest
from fastapi.testclient import TestClient
from main import app, estimate_routes, rank_routes

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.parametrize("preference", ["fastest", "cheapest", "greenest", "balanced"])
def test_estimate_routes_returns_one_recommendation(preference):
    routes = estimate_routes(12.5, 24, preference)
    assert len(routes) == 3
    assert sum(route["recommended"] for route in routes) == 1
    assert all(route["time"] > 0 and route["cost"] >= 0 for route in routes)

def test_greenest_preference_ranks_lowest_emissions_first():
    routes = estimate_routes(20, 30, "greenest")
    assert routes[0]["name"] == "Green Multimodal"

def test_empty_route_ranking_is_safe():
    assert rank_routes([], "balanced") == []

def test_route_request_rejects_partial_coordinates():
    response = client.post("/api/routes", json={
        "origin": "Colombo", "destination": "Galle",
        "origin_latitude": 6.9,
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
