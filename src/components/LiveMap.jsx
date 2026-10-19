
import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const TILES = {
  street:
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  satellite:
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  labels:
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
};

function createMarker(color, letter) {
  return L.divIcon({
    className: "greenroute-custom-marker",
    html: `
      <div style="
        display:flex;
        align-items:center;
        justify-content:center;
        width:32px;
        height:32px;
        background:${color};
        border:3px solid white;
        border-radius:50%;
        box-shadow:0 3px 12px rgba(0,0,0,.45);
        color:white;
        font-size:14px;
        font-weight:800;
      ">${letter}</div>
    `,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
    popupAnchor: [0, -20],
  });
}

const originIcon = createMarker("#10b981", "A");
const destinationIcon = createMarker("#ef4444", "B");

function AutoFit({ origin, destination, geometry }) {
  const map = useMap();

  useEffect(() => {
    if (geometry.length > 1) {
      map.fitBounds(L.latLngBounds(geometry), {
        padding: [50, 50],
        maxZoom: 15,
      });
    } else if (origin && destination) {
      map.fitBounds(
        [
          [origin.latitude, origin.longitude],
          [destination.latitude, destination.longitude],
        ],
        {
          padding: [50, 50],
          maxZoom: 15,
        }
      );
    }
  }, [
    map,
    origin?.latitude,
    origin?.longitude,
    destination?.latitude,
    destination?.longitude,
    geometry,
  ]);

  return null;
}

export default function LiveMap({
  origin,
  destination,
  selectedRoute,
}) {
  const [mapStyle, setMapStyle] = useState("hybrid");
  const [roadRoute, setRoadRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const originLat = origin?.latitude;
  const originLon = origin?.longitude;
  const destinationLat = destination?.latitude;
  const destinationLon = destination?.longitude;

  useEffect(() => {
    if (
      !Number.isFinite(originLat) ||
      !Number.isFinite(originLon) ||
      !Number.isFinite(destinationLat) ||
      !Number.isFinite(destinationLon)
    ) {
      setRoadRoute(null);
      setError("");
      setLoading(false);
      return;
    }

    const controller = new AbortController();

    async function fetchRoadRoute() {
      setLoading(true);
      setError("");
      setRoadRoute(null);

      try {
        const response = await fetch(
          `${API_URL}/api/road-route`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              origin_latitude: originLat,
              origin_longitude: originLon,
              destination_latitude: destinationLat,
              destination_longitude: destinationLon,
            }),
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          throw new Error(
            `Road routing failed (HTTP ${response.status})`
          );
        }

        const data = await response.json();

        if (
          !Array.isArray(data.geometry) ||
          data.geometry.length < 2
        ) {
          throw new Error(
            "Routing service returned invalid geometry."
          );
        }

        setRoadRoute(data);
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(
            err.message || "Unable to load the road route."
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchRoadRoute();

    return () => controller.abort();
  }, [
    originLat,
    originLon,
    destinationLat,
    destinationLon,
  ]);

  const geometry = useMemo(
    () => roadRoute?.geometry ?? [],
    [roadRoute]
  );

  const center =
    Number.isFinite(originLat) &&
    Number.isFinite(originLon)
      ? [originLat, originLon]
      : [6.9271, 79.8612];

  const mapModes = ["street", "satellite", "hybrid"];

  const showSatellite =
    mapStyle === "satellite" || mapStyle === "hybrid";

  return (
    <section style={{ width: "100%" }}>
      <div
        style={{
          background: "#071c15",
          padding: "16px",
          borderRadius: "14px 14px 0 0",
          color: "#fff",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 14,
        }}
      >
        <div>
          <strong>GreenRoute Live Map</strong>

          <div
            style={{
              fontSize: 13,
              opacity: 0.8,
              marginTop: 4,
            }}
          >
            {loading
              ? "Calculating road route..."
              : roadRoute
              ? `${roadRoute.distance_km} km • ${roadRoute.duration_minutes} min driving estimate`
              : "Choose a journey to display its route"}
          </div>
        </div>

        <div
          role="group"
          aria-label="Map display style"
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
          }}
        >
          {mapModes.map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setMapStyle(mode)}
              aria-pressed={mapStyle === mode}
              style={{
                padding: "10px 14px",
                borderRadius: 9,
                cursor: "pointer",
                border: "1px solid #34d399",
                background:
                  mapStyle === mode
                    ? "#34d399"
                    : "#102d23",
                color:
                  mapStyle === mode
                    ? "#052016"
                    : "#fff",
                fontWeight: 700,
              }}
            >
              {mode.charAt(0).toUpperCase() +
                mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            background: "#3a1717",
            color: "#ffb4b4",
            padding: 12,
          }}
        >
          {error}
        </div>
      )}

      <MapContainer
        center={center}
        zoom={12}
        scrollWheelZoom
        style={{
          width: "100%",
          height: "540px",
          borderRadius: "0 0 14px 14px",
        }}
      >
        {showSatellite ? (
          <TileLayer
            key="satellite-base"
            url={TILES.satellite}
            attribution="Imagery &copy; Esri"
            maxZoom={19}
          />
        ) : (
          <TileLayer
            key="street-base"
            url={TILES.street}
            attribution="&copy; OpenStreetMap contributors"
            maxZoom={19}
          />
        )}

        {mapStyle === "hybrid" && (
          <TileLayer
            key="hybrid-labels"
            url={TILES.labels}
            attribution="Reference labels &copy; Esri"
            maxZoom={19}
            zIndex={500}
          />
        )}

        {Number.isFinite(originLat) &&
          Number.isFinite(originLon) && (
            <Marker
              position={[originLat, originLon]}
              icon={originIcon}
            >
              <Popup>
                <strong>Starting Location</strong>
                <div>
                  {origin?.name || "Origin"}
                </div>
              </Popup>
            </Marker>
          )}

        {Number.isFinite(destinationLat) &&
          Number.isFinite(destinationLon) && (
            <Marker
              position={[destinationLat, destinationLon]}
              icon={destinationIcon}
            >
              <Popup>
                <strong>Destination</strong>
                <div>
                  {destination?.name || "Destination"}
                </div>
              </Popup>
            </Marker>
          )}

        {geometry.length > 1 && (
          <Polyline
            positions={geometry}
            pathOptions={{
              color: "#34d399",
              weight: 6,
              opacity: 0.95,
            }}
          />
        )}

        <AutoFit
          origin={origin}
          destination={destination}
          geometry={geometry}
        />
      </MapContainer>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 18,
          padding: "16px 4px",
          color: "#c5e9da",
          fontSize: 13,
        }}
      >
        <span>🟢 A — Starting point</span>
        <span>🔴 B — Destination</span>
        <span>🟩 Driving road route</span>
      </div>

      {selectedRoute && (
        <div
          style={{
            padding: 16,
            border: "1px solid #20513e",
            borderRadius: 12,
            background: "#0a241a",
            color: "#e5fff2",
          }}
        >
          <strong>
            Selected: {selectedRoute.name}
          </strong>

          <p style={{ margin: "8px 0 0" }}>
            Estimated travel time:{" "}
            {selectedRoute.time} min
            {" • "}
            Cost: Rs. {selectedRoute.cost}
            {" • "}
            CO₂: {selectedRoute.co2} kg
          </p>
        </div>
      )}

      <p
        style={{
          marginTop: 12,
          fontSize: 12,
          color: "#9cb5aa",
        }}
      >
        The displayed line is an OSRM driving-road route.
        Public transport and multimodal options are modeled
        estimates, not verified transit itineraries.
        Satellite imagery and place labels require internet
        access and are subject to provider availability.
      </p>
    </section>
  );
}
