"""GreenRoute AI API.

Road distance and duration come from OSRM. Public-transport fares, times,
reliability and emissions are explicitly illustrative prototype estimates.
"""
import os
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="GreenRoute AI API", version="2.1.0")

# Set CORS_ORIGINS to a comma-separated list of exact deployed frontend origins.
# Keep localhost defaults for local development; do not use wildcard origins.
DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", ",".join(DEFAULT_ORIGINS)).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

class RouteRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=150)
    destination: str = Field(min_length=2, max_length=150)
    preference: Literal["fastest", "cheapest", "greenest", "balanced"] = "greenest"
    origin_latitude: float | None = Field(default=None, ge=-90, le=90)
    origin_longitude: float | None = Field(default=None, ge=-180, le=180)
    destination_latitude: float | None = Field(default=None, ge=-90, le=90)
    destination_longitude: float | None = Field(default=None, ge=-180, le=180)

class RoadRouteRequest(BaseModel):
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)

WEIGHTS = {
    "greenest": {"time": .05, "cost": .05, "co2": .80, "reliability": .10},
    "fastest": {"time": .65, "cost": .10, "co2": .10, "reliability": .15},
    "cheapest": {"time": .10, "cost": .65, "co2": .15, "reliability": .10},
    "balanced": {"time": .30, "cost": .25, "co2": .30, "reliability": .15},
}

async def geocode_one(query: str, client: httpx.AsyncClient):
    response = await client.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": f"{query}, Sri Lanka", "format": "jsonv2", "limit": 1, "countrycodes": "lk"},
        headers={"User-Agent": "GreenRouteAI-EducationalProject/2.1"},
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise HTTPException(status_code=404, detail=f"Location not found: {query}")
    return float(results[0]["lat"]), float(results[0]["lon"]), results[0].get("display_name", query)

async def road_data(a_lat, a_lon, b_lat, b_lon, client: httpx.AsyncClient):
    url = f"https://router.project-osrm.org/route/v1/driving/{a_lon},{a_lat};{b_lon},{b_lat}"
    response = await client.get(url, params={"overview": "full", "geometries": "geojson"})
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise HTTPException(status_code=404, detail="No road route could be found.")
    route = data["routes"][0]
    geometry = [[point[1], point[0]] for point in route.get("geometry", {}).get("coordinates", [])]
    if len(geometry) < 2:
        raise HTTPException(status_code=502, detail="Routing service returned invalid geometry.")
    return max(0, route["distance"] / 1000), max(0, route["duration"] / 60), geometry

def rank_routes(routes, preference):
    if not routes:
        return []
    def normalized_score(value, values):
        low, high = min(values), max(values)
        return 100.0 if high == low else 100 * (high - value) / (high - low)

    times = [route["time"] for route in routes]
    costs = [route["cost"] for route in routes]
    emissions = [route["co2"] for route in routes]
    weights = WEIGHTS[preference]
    for route in routes:
        time_score = normalized_score(route["time"], times)
        cost_score = normalized_score(route["cost"], costs)
        emission_score = normalized_score(route["co2"], emissions)
        route["ranking_score"] = round(
            time_score * weights["time"] + cost_score * weights["cost"]
            + emission_score * weights["co2"] + route["reliability"] * weights["reliability"], 1
        )
        route["score"] = round(
            emission_score * .7 + cost_score * .1 + route["reliability"] * .1 + time_score * .1
        )
        route["recommended"] = False
    routes.sort(key=lambda route: route["ranking_score"], reverse=True)
    routes[0]["recommended"] = True
    return routes

def estimate_routes(km: float, driving_minutes: float, preference: str):
    """Return illustrative comparisons, not verified transit itineraries or measurements."""
    km = max(0, km)
    drive = max(1, driving_minutes)
    routes = [
        {"id": 1, "name": "Green Multimodal", "transport": "Bus → Walk → Campus Shuttle",
         "time": round(drive * 1.45 + 14), "cost": round(45 + km * 5.5),
         "co2": round(km * .045, 2), "reliability": 85},
        {"id": 2, "name": "Public Transport", "transport": "Bus → Campus Shuttle",
         "time": round(drive * 1.25 + 10), "cost": round(65 + km * 7),
         "co2": round(km * .055, 2), "reliability": 88},
        {"id": 3, "name": "Direct Road", "transport": "Car / Ride Share",
         "time": round(drive + 2), "cost": round(180 + km * 34),
         "co2": round(km * .17, 2), "reliability": 82},
    ]
    return rank_routes(routes, preference)

@app.get("/")
def root():
    return {"status": "online", "project": "GreenRoute AI", "version": "2.1.0"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "GreenRoute API", "version": "2.1.0"}

@app.get("/api/geocode")
async def geocode_location(q: str = Query(min_length=2, max_length=150)):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Location must contain at least 2 characters.")
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{query}, Sri Lanka", "format": "jsonv2", "limit": 5,
                        "countrycodes": "lk", "addressdetails": 1},
                headers={"User-Agent": "GreenRouteAI-EducationalProject/2.1"},
            )
            response.raise_for_status()
            results = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Geocoding timed out.")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Geocoding service unavailable.")
    locations = [
        {"name": result.get("display_name", query), "latitude": float(result["lat"]),
         "longitude": float(result["lon"]), "type": result.get("type", "unknown")}
        for result in results if "lat" in result and "lon" in result
    ]
    return {"query": query, "count": len(locations), "locations": locations,
            "data_source": "OpenStreetMap Nominatim"}

@app.post("/api/road-route")
async def get_road_route(request: RoadRouteRequest):
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            km, minutes, geometry = await road_data(
                request.origin_latitude, request.origin_longitude,
                request.destination_latitude, request.destination_longitude, client
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Routing service timed out.")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Routing service unavailable.")
    return {"distance_km": round(km, 2), "duration_minutes": round(minutes, 1),
            "geometry": geometry, "geometry_points": len(geometry), "data_source": "OSRM"}

@app.post("/api/routes")
async def find_routes(request: RouteRequest):
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            coordinates = [
                request.origin_latitude, request.origin_longitude,
                request.destination_latitude, request.destination_longitude,
            ]
            if all(value is not None for value in coordinates):
                a_lat, a_lon, b_lat, b_lon = coordinates
            elif any(value is not None for value in coordinates):
                raise HTTPException(status_code=422, detail="Supply all four coordinates or none.")
            else:
                a_lat, a_lon, _ = await geocode_one(request.origin, client)
                import asyncio
                await asyncio.sleep(1.1)
                b_lat, b_lon, _ = await geocode_one(request.destination, client)
            km, minutes, _ = await road_data(a_lat, a_lon, b_lat, b_lon, client)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Location or routing service timed out.")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Location or routing service unavailable.")
    routes = estimate_routes(km, minutes, request.preference)
    return {
        "origin": request.origin, "destination": request.destination,
        "preference": request.preference, "route_count": len(routes), "routes": routes,
        "distance_km": round(km, 2), "driving_duration_minutes": round(minutes, 1),
        "data_source": "OSRM road data + illustrative transport estimates",
        "estimates_only": True,
        "assumptions": "Not live public transit, fares, traffic, or verified carbon measurements.",
    }
