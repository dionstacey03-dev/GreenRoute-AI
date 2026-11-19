# GreenRoute AI 🌿

An eco-conscious route comparison prototype for Sri Lanka. GreenRoute V3 combines OpenStreetMap Nominatim geocoding, OSRM driving-road data, an interactive Leaflet map, and clearly labelled illustrative comparisons of travel time, cost, reliability and CO₂.

> **Data transparency:** Road distance, duration and geometry are live responses from OSRM. Geocoding is provided by OpenStreetMap Nominatim. Public-transport itineraries, fares, reliability and emissions are illustrative model estimates—not live bus schedules, confirmed fares, traffic-aware multimodal directions, or measured carbon data.

## V3 foundation

- Versioned FastAPI API (`3.0.0`) with a source-transparency metadata endpoint.
- Consistent 0–100 multi-criteria route scoring, including normalized reliability.
- Explicit request validation for complete coordinate pairs and geographic ranges.
- Configurable geocoding and routing provider endpoints, HTTP timeouts and User-Agent.
- Defensive handling of malformed upstream route and geocoding responses.
- Exact-origin CORS configuration; wildcard origins are rejected.
- Automated API, validation, metadata and ranking tests.
- Existing React/Leaflet frontend and local journey-history experience retained.

## Features

- Search Sri Lankan origin and destination locations.
- Compare fastest, cheapest, greenest and balanced preferences.
- View an OSRM driving route on a Leaflet map with street, satellite, and hybrid layers.
- Save journey estimates locally in the browser; review analytics and export CSV.
- FastAPI health, metadata, geocoding, route comparison and road-route endpoints.

## Architecture

- Frontend: React 19, Vite, React Leaflet, Leaflet, Lucide.
- Backend: Python, FastAPI, Pydantic, HTTPX.
- Geocoding: OpenStreetMap Nominatim.
- Road routing: configurable OSRM endpoint (public demo by default).
- Saved journeys: browser localStorage (not cloud-synchronised).

## Run locally

### Backend

Python 3.10+ recommended.

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn main:app --reload --port 8000
```

- API health: http://127.0.0.1:8000/api/health
- API metadata: http://127.0.0.1:8000/api/meta
- Interactive API docs: http://127.0.0.1:8000/docs

### Frontend

```bash
npm ci
npm run dev
```

Vite normally serves the app at http://localhost:5173.

## Configuration

### Frontend

- `VITE_API_URL`: absolute HTTPS URL of the deployed FastAPI backend, without a trailing slash. Leave empty only when frontend and API share an origin behind a reverse proxy.

### Backend

- `CORS_ORIGINS`: comma-separated exact frontend origins. Do not include paths, trailing slashes or wildcard origins.
- `NOMINATIM_URL`: optional Nominatim-compatible search endpoint.
- `OSRM_URL`: optional OSRM-compatible routing base URL.
- `GREENROUTE_USER_AGENT`: descriptive User-Agent for geocoding requests.

The API must be deployed separately from a static Vite frontend unless the hosting platform is configured to run Python and proxy API requests.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Service status and version |
| GET | `/api/health` | Health check |
| GET | `/api/meta` | Provider and data-confidence metadata |
| GET | `/api/geocode?q=...` | Sri Lankan location lookup |
| POST | `/api/road-route` | OSRM driving route geometry |
| POST | `/api/routes` | Preference-ranked route estimates |

## Tests

From the `backend` directory:

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

Frontend production build:

```bash
npm ci
npm run build
```

## Known limitations and next V3 phases

- There is no authentication, PostgreSQL persistence or cloud trip synchronisation yet.
- Public transit is not connected to a verified Sri Lankan GTFS, operator or timetable feed.
- Fares and emissions are illustrative models; no measured carbon or confirmed fare feed is connected.
- Public Nominatim and OSRM endpoints are subject to provider policies, rate limits and availability. Production should use appropriately hosted services and comply with their terms.
- AI route advice is not yet connected to a model or grounded transport knowledge source.
- Production deployment and end-to-end integration checks still need configuration.

V3 should add persistent user data, verified transit integrations, reproducible emissions factors, secure authentication, observability and production deployment only when the required providers and credentials are selected.

## License

No license has been declared yet. All rights remain with the repository owner unless a license is added.
