# GreenRoute AI 🌿

An eco-conscious route comparison prototype for Sri Lanka. GreenRoute combines OpenStreetMap geocoding, OSRM driving-road data, an interactive Leaflet map, and transparent illustrative comparisons of travel time, cost, and CO₂.

> **Important:** The road distance, driving duration, and road geometry come from OSRM. Public-transport times, fares, reliability, and emissions are prototype estimates—not live bus schedules, confirmed fares, traffic-aware multimodal directions, or measured carbon data.

## Features

- Search Sri Lankan origin and destination locations.
- Compare fastest, cheapest, greenest, and balanced preferences.
- View an OSRM driving route on a Leaflet map with street, satellite, and hybrid layers.
- Save journey estimates locally in the browser.
- Review saved-estimate analytics and export journeys as CSV.
- FastAPI backend with health, geocoding, route comparison, and road-route endpoints.

## Architecture

- Frontend: React 19, Vite, React Leaflet, Leaflet, Lucide.
- Backend: Python, FastAPI, Pydantic, HTTPX.
- Geocoding: OpenStreetMap Nominatim.
- Road routing: OSRM public demo service.
- Saved journeys: browser localStorage (not cloud-synchronised).

## Run locally

### 1. Backend

Python 3.10+ recommended.

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API health: http://127.0.0.1:8000/api/health  
Interactive API docs: http://127.0.0.1:8000/docs

### 2. Frontend

In a second terminal, from the repository root:

```bash
npm ci
npm run dev
```

Vite normally serves the app at http://localhost:5173.

## Production configuration

Set these environment variables in your hosting providers:

### Frontend

`VITE_API_URL` — absolute HTTPS URL of the deployed FastAPI backend, without a trailing slash. If the frontend and API share an origin behind a reverse proxy, it may be left empty so requests use same-origin `/api` paths.

### Backend

`CORS_ORIGINS` — comma-separated exact frontend origins, for example:

```text
https://your-greenroute-frontend.example
```

Do not include URL paths or a trailing slash. Do not use `*` for production origins.

The API must be deployed separately from a static Vite frontend unless your hosting platform is configured to run the Python service and proxy `/api` requests.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Service status and version |
| GET | `/api/health` | Health check |
| GET | `/api/geocode?q=...` | Sri Lankan location lookup |
| POST | `/api/road-route` | OSRM driving route geometry |
| POST | `/api/routes` | Preference-ranked route estimates |

## Tests

Backend unit tests are in `backend/tests`. Install the test dependencies and run:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Frontend production build:

```bash
npm ci
npm run build
```

## Data, privacy, and limitations

- Geocoding queries are sent to OpenStreetMap Nominatim.
- Road-route requests are sent to the public OSRM demo service.
- Public endpoints have usage policies, rate limits, and availability constraints; production deployments should use suitable hosted services and comply with their terms.
- Saved trips stay in the current browser's localStorage and can be cleared by the user.
- No account system, cloud trip sync, live transit feed, verified fare feed, or measured emissions integration is currently provided.
- Estimates are intended for demonstration and learning, not safety-critical or financial decisions.

## License

No license has been declared yet. All rights remain with the repository owner unless a license is added.
