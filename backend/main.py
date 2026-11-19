"""GreenRoute AI API — V3 foundation.

Road distance, duration and geometry are supplied by OSRM. Transit, fares,
reliability and emissions remain explicitly labelled estimates until verified
Sri Lankan transport data integrations are available.
"""
from __future__ import annotations

import asyncio
import os
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

VERSION = "3.0.0"
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=18.0, write=10.0, pool=5.0)
USER_AGENT = os.getenv("GREENROUTE_USER_AGENT", "GreenRouteAI/3.0 (Sri Lanka mobility research)")
DEFAULT_ORIGINS = [
    "http://localhost:5173", "http://localhost:5174",
    "http://127.0.0.1:5173", "http://127.0.0.1:5174",
]
allowed_origins = [
    item.strip().rstrip("/")
    for item in os.getenv("CORS_ORIGINS", ",".join(DEFAULT_ORIGINS)).split(",")
    if item.strip()
]
if "*" in allowed_origins:
    raise RuntimeError("Wildcard CORS origins are not permitted.")

app = FastAPI(
    title="GreenRoute AI API",
    description="Sustainable journey comparison for Sri Lanka. Estimates are labelled by source and confidence.",
    version=VERSION,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

Preference = Literal["fastest", "cheapest", "greenest", "balanced"]


class RouteRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=150)
    destination: str = Field(min_length=2, max_length=150)
    preference: Preference = "greenest"
    origin_latitude: float | None = Field(default=None, ge=-90, le=90)
    origin_longitude: float | None = Field(default=None, ge=-180, le=180)
    destination_latitude: float | None = Field(default=None, ge=-90, le=90)
    destination_longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates_are_complete(self):
        values = (
            self.origin_latitude, self.origin_longitude,
            self.destination_latitude, self.destination_longitude,
        )
        if any(value is not None for value in values) and not all(value is not None for value in values):
            raise ValueError("Supply all four coordinates or none.")
        return self


class RoadRouteRequest(BaseModel):
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)


WEIGHTS: dict[str, dict[str, float]] = {
    "greenest": {"time": 0.05, "cost": 0.05, "co2": 0.80, "reliability": 0.10},
    "fastest": {"time": 0.65, "cost": 0.10, "co2": 0.10, "reliability": 0.15},
    "cheapest": {"time": 0.10, "cost": 0.65, "co2": 0.15, "reliability": 0.10},
    "balanced": {"time": 0.30, "cost": 0.25, "co2": 0.30, "reliability": 0.15},
}


def _normalised_benefit(value: float, values: list[float]) -> float:
    """Convert a lower-is-better metric to a 0–100 benefit score."""
    low, high = min(values), max(values)
    return 100.0 if high == low else 100.0 * (high - value) / (high - low)


def rank_routes(routes: list[dict], preference: str) -> list[dict]:
    """Rank route candidates on a consistent 0–100 scale."""
    if preference not in WEIGHTS:
        raise ValueError(f"Unsupported preference: {preference}")
    if not routes:
        return []

    metrics = {
        key: [float(route[key]) for route in routes]
        for key in ("time", "cost", "co2")
    }
    weights = WEIGHTS[preference]
    ranked = []
    for original in routes:
        route = dict(original)
        reliability = max(0.0, min(100.0, float(route.get("reliability", 0))))
        scores = {
            "time": _normalised_benefit(float(route["time"]), metrics["time"]),
            "cost": _normalised_benefit(float(route["cost"]), metrics["cost"]),
            "co2": _normalised_benefit(float(route["co2"]), metrics["co2"]),
            "reliability": reliability,
        }
        route["ranking_score"] = round(sum(scores[key] * weights[key] for key in weights), 2)
        route["score"] = round(
            scores["co2"] * 0.7 + scores["cost"] * 0.1
            + scores["reliability"] * 0.1 + scores["time"] * 0.1, 2
        )
        route["recommended"] = False
        ranked.append(route)

    ranked.sort(key=lambda item: (-item["ranking_score"], str(item.get("id", ""))))
    ranked[0]["recommended"] = True
    return ranked


def estimate_routes(km: float, driving_minutes: float, preference: str) -> list[dict]:
    """Create illustrative comparison candidates; these are not live transit results."""
    km = max(0.0, float(km))
    drive = max(1.0, float(driving_minutes))
    candidates = [
        {"id": "green-multimodal", "name": "Green Multimodal",
         "transport": "Bus → Walk → Campus Shuttle", "time": round(drive * 1.45 + 14),
         "cost": round(45 + km * 5.5), "co2": round(km * 0.045, 2), "reliability": 85},
        {"id": "public-transport", "name": "Public Transport",
         "transport": "Bus → Campus Shuttle", "time": round(drive * 1.25 + 10),
         "cost": round(65 + km * 7), "co2": round(km * 0.055, 2), "reliability": 88},
        {"id": "direct-road", "name": "Direct Road",
         "transport": "Car / Ride Share", "time": round(drive + 2),
         "cost": round(180 + km * 34), "co2": round(km * 0.17, 2), "reliability": 82},
    ]
    return rank_routes(candidates, preference)


async def geocode_one(query: str, client: httpx.AsyncClient):
    response = await client.get(
        NOMINATIM_URL,
        params={"q": f"{query}, Sri Lanka", "format": "jsonv2", "limit": 1, "countrycodes": "lk"},
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise HTTPException(status_code=404, detail=f"Location not found: {query}")
    try:
        return float(results[0]["lat"]), float(results[0]["lon"]), results[0].get("display_name", query)
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=502, detail="Geocoding service returned invalid coordinates.")


async def road_data(a_lat, a_lon, b_lat, b_lon, client: httpx.AsyncClient):
    url = f"{OSRM_URL.rstrip('/')}/route/v1/driving/{a_lon},{a_lat};{b_lon},{b_lat}"
    response = await client.get(url, params={"overview": "full", "geometries": "geojson"})
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise HTTPException(status_code=404, detail="No road route could be found.")
    route = data["routes"][0]
    try:
        geometry = [[point[1], point[0]] for point in route["geometry"]["coordinates"]]
        distance_km = float(route["distance"]) / 1000
        duration_minutes = float(route["duration"]) / 60
    except (KeyError, IndexError, TypeError, ValueError):
        raise HTTPException(status_code=502, detail="Routing service returned an invalid response.")
    if len(geometry) < 2 or distance_km < 0 or duration_minutes < 0:
        raise HTTPException(status_code=502, detail="Routing service returned invalid route geometry or metrics.")
    return distance_km, duration_minutes, geometry


def _external_service_error(error: httpx.HTTPError, label: str):
    if isinstance(error, httpx.TimeoutException):
        raise HTTPException(status_code=504, detail=f"{label} timed out.")
    raise HTTPException(status_code=502, detail=f"{label} is unavailable.")


@app.get("/")
def root():
    return {"status": "online", "project": "GreenRoute AI", "version": VERSION}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "GreenRoute API", "version": VERSION}


@app.get("/api/meta")
def api_metadata():
    return {
        "version": VERSION,
        "region": "Sri Lanka",
        "routing": {"provider": "OSRM", "mode": "driving", "live": True},
        "geocoding": {"provider": "OpenStreetMap Nominatim", "live": True},
        "transit": {"live": False, "status": "illustrative_estimates_only"},
        "fares": {"live": False, "status": "illustrative_estimates_only"},
        "emissions": {"measured": False, "status": "modelled_estimates_only"},
    }


@app.get("/api/geocode")
async def geocode_location(q: str = Query(min_length=2, max_length=150)):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Location must contain at least 2 characters.")
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={"q": f"{query}, Sri Lanka", "format": "jsonv2", "limit": 5,
                        "countrycodes": "lk", "addressdetails": 1},
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            results = response.json()
    except httpx.HTTPError as error:
        _external_service_error(error, "Geocoding service")
    locations = []
    for result in results:
        try:
            if "lat" in result and "lon" in result:
                locations.append({
                    "name": result.get("display_name", query),
                    "latitude": float(result["lat"]),
                    "longitude": float(result["lon"]),
                    "type": result.get("type", "unknown"),
                })
        except (TypeError, ValueError):
            continue
    return {"query": query, "count": len(locations), "locations": locations,
            "data_source": "OpenStreetMap Nominatim", "live_data": True}


@app.post("/api/road-route")
async def get_road_route(request: RoadRouteRequest):
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            km, minutes, geometry = await road_data(
                request.origin_latitude, request.origin_longitude,
                request.destination_latitude, request.destination_longitude, client,
            )
    except httpx.HTTPError as error:
        _external_service_error(error, "Road routing service")
    return {"distance_km": round(km, 2), "duration_minutes": round(minutes, 1),
            "geometry": geometry, "geometry_points": len(geometry), "data_source": "OSRM",
            "live_data": True, "mode": "driving"}


@app.post("/api/routes")
async def find_routes(request: RouteRequest):
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            if request.origin_latitude is not None:
                a_lat, a_lon = request.origin_latitude, request.origin_longitude
                b_lat, b_lon = request.destination_latitude, request.destination_longitude
            else:
                a_lat, a_lon, _ = await geocode_one(request.origin.strip(), client)
                # Respect the public Nominatim usage policy for sequential lookups.
                await asyncio.sleep(1.1)
                b_lat, b_lon, _ = await geocode_one(request.destination.strip(), client)
            km, minutes, _ = await road_data(a_lat, a_lon, b_lat, b_lon, client)
    except httpx.HTTPError as error:
        _external_service_error(error, "Location or routing service")
    routes = estimate_routes(km, minutes, request.preference)
    return {
        "origin": request.origin.strip(), "destination": request.destination.strip(),
        "preference": request.preference, "route_count": len(routes), "routes": routes,
        "distance_km": round(km, 2), "driving_duration_minutes": round(minutes, 1),
        "data_sources": {"road": "OSRM", "transit": "illustrative_model",
                         "cost": "illustrative_model", "emissions": "illustrative_model"},
        "estimates_only": True,
        "assumptions": "Transit, fares, reliability and emissions are illustrative estimates, not verified live data.",
        "version": VERSION,
    }
