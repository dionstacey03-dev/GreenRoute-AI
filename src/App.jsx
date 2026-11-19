import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/react";
import { authenticatedApiRequest } from "./auth/api";

import {

  Leaf,

  LayoutDashboard,

  Map,

  Route,

  Bus,

  Footprints,

  Bike,

  BarChart3,

  Bot,

  Search,

  MapPin,

  Navigation,

  Clock,

  Wallet,

  Wind,

  ArrowRight,

  CheckCircle2,

} from "lucide-react";

import "./App.css";
import "./GreenRouteAnalytics.css";

import LiveMap from "./components/LiveMap";

// =========================================================

// PREFERENCES

// =========================================================

// Set VITE_API_URL in .env.production before deploying the frontend.
const API_BASE = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = 25000;

const preferences = [

  {

    id: "fastest",

    label: "⚡ Fastest",

  },

  {

    id: "cheapest",

    label: "💰 Cheapest",

  },

  {

    id: "greenest",

    label: "🌱 Greenest",

  },

  {

    id: "balanced",

    label: "⚖️ Balanced",

  },

];

// =========================================================

// APP

// =========================================================

function App() {
  const { getToken, isLoaded: clerkLoaded, isSignedIn } = useAuth();
  const requestInProgress = useRef(false);
  const [activePage, setActivePage] = useState("dashboard");
  const [from, setFrom] = useState("");
  const [destination, setDestination] = useState("");

  const [preference, setPreference] = useState("greenest");

const [routes, setRoutes] = useState([]);

const [routeMetadata, setRouteMetadata] = useState(null);
const [savedTrips, setSavedTrips] = useState([]);
const [saveMessage, setSaveMessage] = useState("");
const [journeySyncStatus, setJourneySyncStatus] = useState("loading");
const [journeySyncError, setJourneySyncError] = useState("");

useEffect(() => {
  let active = true;
  if (!clerkLoaded) return undefined;
  if (!isSignedIn) {
    setJourneySyncStatus("signed-out");
    setSavedTrips([]);
    return undefined;
  }

  const loadCloudJourneys = async () => {
    setJourneySyncStatus("loading");
    setJourneySyncError("");
    try {
      await authenticatedApiRequest("/api/me", getToken);
      const result = await authenticatedApiRequest("/api/journeys", getToken);
      if (!active) return;
      const items = Array.isArray(result?.items) ? result.items : [];
      setSavedTrips(items.map((item) => ({
        id: item.id,
        createdAt: item.created_at,
        origin: item.origin,
        destination: item.destination,
        name: item.route_name,
        preference: item.preference,
        distance: Number(item.distance_km) || 0,
        time: Number(item.duration_minutes) || 0,
        cost: Number(item.estimated_cost_lkr) || 0,
        co2: Number(item.estimated_co2_kg) || 0,
        score: Number(item.green_score) || 0,
        rankingScore: Number(item.ranking_score) || 0,
        costSaving: Number(item.estimated_cost_difference_lkr) || 0,
        carbonSaving: Number(item.estimated_co2_difference_kg) || 0,
        storage: "cloud",
      })));
      setJourneySyncStatus("ready");
    } catch (error) {
      if (!active) return;
      setJourneySyncStatus("error");
      setJourneySyncError(error.message || "Unable to load your saved journeys.");
    }
  };

  loadCloudJourneys();
  return () => { active = false; };
}, [clerkLoaded, isSignedIn, getToken]);

const [selectedRouteId, setSelectedRouteId] = useState(null);

const selectedRoute =

  routes.find((route) => route.id === selectedRouteId) ??

  routes.find((route) => route.recommended) ??

  routes[0] ??

  null;

const [error, setError] = useState("");

  const [searched, setSearched] =

    useState(false);

  const [loading, setLoading] =

    useState(false);

  // Real geocoded locations

  const [originLocation, setOriginLocation] =

    useState(null);

  const [

    destinationLocation,

    setDestinationLocation,

  ] = useState(null);

  // =======================================================

  // GEOCODE LOCATION

  // =======================================================

  const geocodeLocation = async (location, signal) => {

    const response = await fetch(

      `${API_BASE}/api/geocode?q=${encodeURIComponent(

        location

      )}`,
      { signal }
    );

    if (!response.ok) {

      throw new Error(

        `Geocoding failed with status ${response.status}`

      );

    }

    const data = await response.json();

    if (

      !data.locations ||

      data.locations.length === 0

    ) {

      throw new Error(

        `Could not find "${location}" in Sri Lanka.`

      );

    }

    return data.locations[0];

  };

  // =======================================================

  // FIND ROUTES

  // =======================================================

  const findRoutes = async (chosenPreference = preference) => {
    if (requestInProgress.current) return;
    const start = from.trim();
    const end = destination.trim();
    if (!start || !end) {
      setError("Please enter both your starting location and destination.");
      return;
    }
    if (start.toLocaleLowerCase() === end.toLocaleLowerCase()) {
      setError("Starting location and destination must be different.");
      return;
    }
    if (start.length > 150 || end.length > 150) {
      setError("Location names must be 150 characters or fewer.");
      return;
    }
    if (!API_BASE) {
      setError("API URL is not configured. Set VITE_API_URL for this deployment.");
      return;
    }
    requestInProgress.current = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    setLoading(true);
    setError("");
    setRoutes([]);
    setRouteMetadata(null);
    setSearched(false);
    setSelectedRouteId(null);
    setOriginLocation(null);
    setDestinationLocation(null);
    try {
      // Sequential geocoding is kinder to the public geocoding provider.
      const realOrigin = await geocodeLocation(start, controller.signal);
      const realDestination = await geocodeLocation(end, controller.signal);
      for (const point of [realOrigin, realDestination]) {
        if (!Number.isFinite(Number(point.latitude)) || !Number.isFinite(Number(point.longitude))) {
          throw new Error("Geocoding returned invalid coordinates.");
        }
      }
      const response = await fetch(`${API_BASE}/api/routes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          origin: start,
          destination: end,
          preference: chosenPreference,
          origin_latitude: realOrigin.latitude,
          origin_longitude: realOrigin.longitude,
          destination_latitude: realDestination.latitude,
          destination_longitude: realDestination.longitude,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : `GreenRoute API returned ${response.status}`);
      }
      if (!Array.isArray(data.routes) || data.routes.length === 0) {
        throw new Error("No route recommendations were returned.");
      }
      setOriginLocation(realOrigin);
      setDestinationLocation(realDestination);
      setRoutes(data.routes);
      setRouteMetadata(data);
      setSearched(true);
    } catch (requestError) {
      console.error("GreenRoute error:", requestError);
      setError(requestError.name === "AbortError"
        ? "The route request timed out. Please try again."
        : requestError instanceof TypeError
          ? "Cannot connect to GreenRoute API. Check that the backend is running and CORS is configured."
          : requestError.message || "Unable to calculate the journey.");
      setRoutes([]);
      setRouteMetadata(null);
      setSearched(false);
    } finally {
      clearTimeout(timeout);
      requestInProgress.current = false;
      setLoading(false);
    }
  };

  const changePreference = (newPreference) => {
    setPreference(newPreference);
    setRoutes([]);
    setRouteMetadata(null);
    setSearched(false);
    setSelectedRouteId(null);
    setError("");
  };

  const directRoad = routes.find((route) => route.id === 3);
  const referenceRoute = selectedRoute;
  const carbonSaving = directRoad && referenceRoute
    ? Math.max(0, directRoad.co2 - referenceRoute.co2)
    : null;
  const moneySaving = directRoad && referenceRoute
    ? Math.max(0, directRoad.cost - referenceRoute.cost)
    : null;

  const saveJourney = async () => {
    if (!selectedRoute || !routeMetadata || !directRoad) return;
    if (journeySyncStatus !== "ready") {
      setSaveMessage("Your cloud journey history is not ready yet. Please wait and try again.");
      return;
    }

    setSaveMessage("");
    try {
      const saved = await authenticatedApiRequest("/api/journeys", getToken, {
        method: "POST",
        body: JSON.stringify({
          origin: from.trim(),
          destination: destination.trim(),
          route_name: selectedRoute.name,
          preference,
          distance_km: Number(routeMetadata.distance_km) || 0,
          duration_minutes: Number(selectedRoute.time) || 0,
          estimated_cost_lkr: Number(selectedRoute.cost) || 0,
          estimated_co2_kg: Number(selectedRoute.co2) || 0,
          green_score: Number(selectedRoute.score) || 0,
          ranking_score: Number(selectedRoute.ranking_score) || 0,
          estimated_cost_difference_lkr: Math.max(0, Number(directRoad.cost) - Number(selectedRoute.cost)),
          estimated_co2_difference_kg: Math.max(0, Number(directRoad.co2) - Number(selectedRoute.co2)),
        }),
      });
      const trip = {
        id: saved.id,
        createdAt: saved.created_at,
        origin: saved.origin,
        destination: saved.destination,
        name: saved.route_name,
        preference: saved.preference,
        distance: Number(saved.distance_km) || 0,
        time: Number(saved.duration_minutes) || 0,
        cost: Number(saved.estimated_cost_lkr) || 0,
        co2: Number(saved.estimated_co2_kg) || 0,
        score: Number(saved.green_score) || 0,
        rankingScore: Number(saved.ranking_score) || 0,
        costSaving: Number(saved.estimated_cost_difference_lkr) || 0,
        carbonSaving: Number(saved.estimated_co2_difference_kg) || 0,
        storage: "cloud",
      };
      setSavedTrips((current) => [trip, ...current]);
      setSaveMessage("Journey saved securely to your account.");
    } catch (error) {
      setSaveMessage(error.message || "Unable to save this journey to your account.");
    }
  };

  const deleteJourney = async (id) => {
    setSaveMessage("");
    try {
      await authenticatedApiRequest(`/api/journeys/${encodeURIComponent(id)}`, getToken, { method: "DELETE" });
      setSavedTrips((current) => current.filter((trip) => trip.id !== id));
    } catch (error) {
      setSaveMessage(error.message || "Unable to delete this saved journey.");
    }
  };

  const clearJourneys = async () => {
    if (!savedTrips.length || !window.confirm("Delete all saved journeys from your GreenRoute account?")) return;
    setSaveMessage("");
    try {
      await Promise.all(savedTrips.map((trip) =>
        authenticatedApiRequest(`/api/journeys/${encodeURIComponent(trip.id)}`, getToken, { method: "DELETE" })
      ));
      setSavedTrips([]);
      setSaveMessage("Your cloud journey history has been cleared.");
    } catch (error) {
      setSaveMessage(error.message || "Some journeys could not be deleted. Refresh the list and try again.");
      try {
        const result = await authenticatedApiRequest("/api/journeys", getToken);
        setSavedTrips((result.items || []).map((item) => ({
          id: item.id, createdAt: item.created_at, origin: item.origin, destination: item.destination,
          name: item.route_name, preference: item.preference, distance: Number(item.distance_km) || 0,
          time: Number(item.duration_minutes) || 0, cost: Number(item.estimated_cost_lkr) || 0,
          co2: Number(item.estimated_co2_kg) || 0, score: Number(item.green_score) || 0,
          rankingScore: Number(item.ranking_score) || 0,
          costSaving: Number(item.estimated_cost_difference_lkr) || 0,
          carbonSaving: Number(item.estimated_co2_difference_kg) || 0, storage: "cloud",
        })));
      } catch { /* Keep the existing list visible if refresh also fails. */ }
    }
  };
  // Export browser-local estimates without sending them to a server.
  const exportJourneysCsv = () => {
    if (!savedTrips.length) return;
    const headers = ["Date", "Origin", "Destination", "Mode", "Preference", "Distance (km)", "Time (min)", "Cost (LKR)", "CO2 (kg)", "Estimated cost difference (LKR)", "Estimated CO2 difference (kg)"];
    const safeCell = (value) => {
      const text = String(value ?? "");
      // Prevent spreadsheet formula injection when exported CSV is opened.
      const escaped = /^[\s]*[=+\-@]/.test(text) ? "'" + text : text;
      return '"' + escaped.replace(/"/g, '""') + '"';
    };
    const rows = savedTrips.map(trip => [trip.createdAt, trip.origin, trip.destination, trip.name, trip.preference, trip.distance, trip.time, trip.cost, trip.co2, trip.costSaving, trip.carbonSaving]);
    const csv = "\uFEFF" + [headers, ...rows].map(row => row.map(safeCell).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "greenroute-journey-estimates.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const goToCarbonTracker = () => {
    setActivePage("dashboard");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      document.getElementById("carbon-tracker")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }));
  };

  const totalCarbon = savedTrips.reduce((sum, trip) => sum + (Number(trip.carbonSaving) || 0), 0);
  const totalCost = savedTrips.reduce((sum, trip) => sum + (Number(trip.costSaving) || 0), 0);
  const totalDistance = savedTrips.reduce((sum, trip) => sum + (Number(trip.distance) || 0), 0);

  // Charts use existing browser-local records, without changing their schema.
  const safeNumber = (value) => {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(0, number) : 0;
  };
  const chartTrips = [...savedTrips].slice(0, 8).reverse();
  const maxCarbon = Math.max(0.01, ...chartTrips.map(t => safeNumber(t.carbonSaving)));
  const maxCost = Math.max(1, ...chartTrips.map(t => safeNumber(t.costSaving)));
  const modeCounts = savedTrips.reduce((counts, trip) => {
    const mode = typeof trip.name === "string" && trip.name.trim() ? trip.name.trim() : "Other";
    counts[mode] = (counts[mode] || 0) + 1;
    return counts;
  }, {});
  const modeEntries = Object.entries(modeCounts).sort((a, b) => b[1] - a[1]);
  const averageCarbon = savedTrips.length ? totalCarbon / savedTrips.length : 0;
  const averageCost = savedTrips.length ? totalCost / savedTrips.length : 0;


  // =======================================================

  // OPEN MAP

  // =======================================================

  const openJourneyMap = () => {

    if (

      !originLocation ||

      !destinationLocation

    ) {

      setError(

        "Find a journey first so GreenRoute can place both locations on the map."

      );

      setActivePage("dashboard");

      return;

    }

    setActivePage("map");

  };

  // =======================================================

  // UI

  // =======================================================

  return (

    <div className="app">

      {/* =================================================

          SIDEBAR

      ================================================= */}

      <aside className="sidebar">

        <div className="logo">

          <div className="logo-icon">

            <Leaf size={25} />

          </div>

          <div>

            <h2>GreenRoute</h2>

            <span>AI Mobility</span>

          </div>

        </div>

        <nav>

          <button

            className={`nav-item ${

              activePage === "dashboard"

                ? "active"

                : ""

            }`}

            onClick={() =>

              setActivePage("dashboard")

            }

          >

            <LayoutDashboard size={20} />

            Dashboard

          </button>

          <button

            className="nav-item"

            onClick={() =>

              setActivePage("dashboard")

            }

          >

            <Route size={20} />

            Journey Planner

          </button>

          <button

            className={`nav-item ${

              activePage === "map"

                ? "active"

                : ""

            }`}

            onClick={() =>

              setActivePage("map")

            }

          >

            <Map size={20} />

            Live Map

          </button>

          <button className="nav-item">

            <Bus size={20} />

            Transport

          </button>

          <button className="nav-item" onClick={goToCarbonTracker}>

            <BarChart3 size={20} />

            Carbon Tracker

          </button>

          <button className="nav-item">

            <Bot size={20} />

            Green AI

          </button>

        </nav>

        <div className="sidebar-footer">

          <Leaf size={18} />

          <div>

            <strong>

              Smart Green City

            </strong>

            <span>

              GreenExe 4.0 Project

            </span>

          </div>

        </div>

      </aside>

      {/* =================================================

          MAIN

      ================================================= */}

      <main className="main">

        {activePage === "map" ? (

          <>

            {/* =========================================

                LIVE MAP PAGE

            ========================================= */}

            <header className="topbar">

              <div>

                <p className="eyebrow">

                  SMART GREEN MOBILITY

                </p>

                <h1>

                  Live Map 🗺️

                </h1>

                <p className="subtitle">

                  {originLocation &&

                  destinationLocation

                    ? `${from} → ${destination}`

                    : "Explore the GreenRoute smart mobility network."}

                </p>

              </div>

              <div className="status">

                <span className="status-dot" />

                Map Online

              </div>

            </header>

            <section className="map-page-card">

              <div className="map-page-heading">

                <div>

                  <p className="section-label">

                    GREENROUTE NETWORK

                  </p>

                  <h2>

                    Smart Mobility Map

                  </h2>

                  <p>

                    {originLocation &&

                    destinationLocation

                      ? "Showing the real geocoded start and destination locations."

                      : "Plan a journey to display your real start and destination locations."}

                  </p>

                </div>

                <Map size={30} />

              </div>

<LiveMap

  origin={originLocation}

  destination={destinationLocation}

  selectedRoute={selectedRoute}
  roadGeometry={routeMetadata?.road_geometry ?? null}

/>

            </section>

            {originLocation &&

              destinationLocation && (

                <section className="map-info-grid">

                  <div className="map-info-card">

                    <MapPin />

                    <div>

                      <strong>

                        Starting Location

                      </strong>

                      <span>

                        {from}

                      </span>

                    </div>

                  </div>

                  <div className="map-info-card">

                    <Navigation />

                    <div>

                      <strong>

                        Destination

                      </strong>

                      <span>

                        {destination}

                      </span>

                    </div>

                  </div>

                  <div className="map-info-card">

                    <Leaf />

                    <div>

                      <strong>

                        GreenRoute Journey

                      </strong>

                      <span>

                        Real locations connected

                      </span>

                    </div>

                  </div>

                </section>

              )}

          </>

        ) : (

          <>

            {/* =========================================

                DASHBOARD

            ========================================= */}

            <header className="topbar">

              <div>

                <p className="eyebrow">

                  SMART GREEN MOBILITY

                </p>

                <h1>

                  Good morning 👋

                </h1>

                <p className="subtitle">

                  Where would you like to go today?

                </p>

              </div>

              <div className="status">

                <span className="status-dot" />

                System Online

              </div>

            </header>

            {/* =========================================

                JOURNEY PLANNER

            ========================================= */}

            <section className="planner-card">

              <div className="planner-heading">

                <div>

                  <p className="section-label">

                    PLAN YOUR JOURNEY

                  </p>

                  <h2>

                    Find a greener way to travel.

                  </h2>

                </div>

                <Leaf size={30} />

              </div>

              <div className="route-inputs">

                <div className="input-box">

                  <MapPin size={20} />

                  <div>

                    <label>

                      FROM

                    </label>

                    <input

                      type="text"

                      placeholder="Enter starting location"

                      value={from}

                      onChange={(event) => {

                        setFrom(

                          event.target.value

                        );

                        setOriginLocation(null);
                        setRoutes([]);
                        setSearched(false);
                        setRouteMetadata(null);

                      }}

                    />

                  </div>

                </div>

                <ArrowRight className="route-arrow" />

                <div className="input-box">

                  <Navigation size={20} />

                  <div>

                    <label>

                      TO

                    </label>

                    <input

                      type="text"

                      placeholder="Enter destination"

                      value={destination}

                      onChange={(event) => {

                        setDestination(

                          event.target.value

                        );

                        setDestinationLocation(null);
                        setRoutes([]);
                        setSearched(false);
                        setRouteMetadata(null);

                      }}

                      onKeyDown={(event) => {

                        if (

                          event.key === "Enter" &&

                          !loading

                        ) {

                          findRoutes();

                        }

                      }}

                    />

                  </div>

                </div>

                <button

                  className="search-button"

                  onClick={() => findRoutes()}

                  disabled={loading}

                >

                  <Search size={20} />

                  {loading

                    ? "Finding..."

                    : "Find Routes"}

                </button>

              </div>

              <div className="preferences">

                <span>

                  Optimize for:

                </span>

                {preferences.map(

                  (item) => (

                    <button

                      key={item.id}

                      className={

                        preference ===

                        item.id

                          ? "selected"

                          : ""

                      }

                      onClick={() =>

                        changePreference(

                          item.id

                        )

                      }

                    >

                      {item.label}

                    </button>

                  )

                )}

              </div>

              {error && (

                <div className="planner-error">

                  {error}

                </div>

              )}

            </section>

            {/* =========================================

                RESULTS

            ========================================= */}

            {searched &&

              routes.length > 0 && (

                <section className="route-results">

                  <div className="results-heading">

                    <div>

                      <p className="section-label">

                        SMART ROUTE RESULTS

                      </p>

                      <h2>

                        {from} →{" "}

                        {destination}

                      </h2>

                    </div>

                    <button

                      className="select-route"

                      onClick={

                        openJourneyMap

                      }

                    >

                      View on Map

                      <Map size={17} />

                    </button>

                  </div>

                  <div className="route-results-grid">

                    {routes.map(

                      (route, index) => (

<article

  key={route.id}

  className={`route-card ${

    route.recommended ? "recommended-route" : ""

  } ${

    selectedRoute?.id === route.id ? "selected-route" : ""

  }`}

  role="button"

  tabIndex={0}

  aria-pressed={selectedRoute?.id === route.id}

  onClick={() => setSelectedRouteId(route.id)}

  onKeyDown={(event) => {

    if (event.key === "Enter" || event.key === " ") {

      event.preventDefault();

      setSelectedRouteId(route.id);

    }

  }}

>

                          {route.recommended && (

                            <div className="recommended-label">

                              <CheckCircle2

                                size={15}

                              />

                              AI Recommended

                            </div>

                          )}

                          <div className="route-card-heading">

                            <div>

                              <p>

                                ROUTE{" "}

                                {index + 1}

                              </p>

                              <h3>

                                {route.name}

                              </h3>

                            </div>

                            <div className="route-score">

                              <strong>

                                {route.score}

                              </strong>

                              <span>

                                Green Score

                              </span>

                            </div>

                          </div>

                          <div className="transport-path">

                            <Bus size={19} />

                            <span>

                              {

                                route.transport

                              }

                            </span>

                          </div>

                          <div className="route-metrics">

                            <div>

                              <Clock size={18} />

                              <span>

                                Time

                              </span>

                              <strong>

                                {route.time} min

                              </strong>

                            </div>

                            <div>

                              <Wallet size={18} />

                              <span>

                                Cost

                              </span>

                              <strong>

                                Rs.{" "}

                                {route.cost}

                              </strong>

                            </div>

                            <div>

                              <Wind size={18} />

                              <span>

                                CO₂

                              </span>

                              <strong>

                                {route.co2} kg

                              </strong>

                            </div>

                          </div>

                          <div className="ranking">

                            <span>

                              Preference Score

                            </span>

                            <strong>

                              {

                                route.ranking_score

                              }

                            </strong>

                          </div>

                          {directRoad && route.id !== directRoad.id && route.co2 < directRoad.co2 && (
                            <div className="carbon-saving">
                              <Leaf size={17} />
                              <span>
                                Approximately {(directRoad.co2 - route.co2).toFixed(2)} kg less CO₂
                                than the estimated direct-road option.
                              </span>
                            </div>
                          )}

                          <button

                            className="select-route"

                            onClick={(event) => {
                              event.stopPropagation();
                              setSelectedRouteId(route.id);
                              openJourneyMap();
                            }}

                          >

                            Select Route

                            <ArrowRight

                              size={17}

                            />

                          </button>

                        </article>

                      )

                    )}

                  </div>

                                     <p className="demo-notice">
                     {routeMetadata?.distance_km != null && (
                       <>Road distance: {routeMetadata.distance_km} km. </>
                     )}
                     Road routing uses OSRM. Public transport times, costs, reliability and CO₂
                     are illustrative estimates, not live schedules, fares or verified emissions.
                     {savedTrips.length > 0 && (
                       <> Locally saved journeys: {savedTrips.length}; estimated CO₂ difference: {totalCarbon.toFixed(2)} kg; estimated cost difference: Rs. {Math.round(totalCost)}. These are not verified savings.</>
                     )}
                   </p>
                   <button className="select-route" type="button" onClick={saveJourney} disabled={!selectedRoute || journeySyncStatus !== "ready"}>
                     {journeySyncStatus === "loading" ? "Connecting account..." : "Save journey to account"}
                   </button>
                   {journeySyncStatus === "error" && <p role="alert" className="demo-notice">Cloud journey sync unavailable: {journeySyncError}</p>}
                   {saveMessage && <p role="alert" className="demo-notice">{saveMessage}</p>}
                   <div style={{ marginTop: 22, overflowX: "auto" }}>
                     <h3 style={{ marginBottom: 12 }}>Compare route estimates</h3>
                     <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 580, color: "#d9f9e9", textAlign: "left" }}>
                       <thead><tr>{["Route", "Time", "Cost", "CO₂", "Green score", "Ranking"].map(label => <th key={label} style={{ padding: 12, borderBottom: "1px solid #27614a" }}>{label}</th>)}</tr></thead>
                       <tbody>{routes.map(route => <tr key={route.id} style={{ background: selectedRoute?.id === route.id ? "#123e2c" : "transparent", cursor: "pointer" }} onClick={() => setSelectedRouteId(route.id)}>
                         <td style={{ padding: 12 }}>{route.name}{route.recommended ? " ★" : ""}</td>
                         <td style={{ padding: 12 }}>{route.time} min</td>
                         <td style={{ padding: 12 }}>Rs. {route.cost}</td>
                         <td style={{ padding: 12 }}>{route.co2} kg</td>
                         <td style={{ padding: 12 }}>{route.score}</td>
                         <td style={{ padding: 12 }}>{route.ranking_score}</td>
                       </tr>)}</tbody>
                     </table>
                   </div>
                </section>

              )}

            {/* =========================================

                STATS

            ========================================= */}

            <section className="stats-grid">

              <div className="stat-card">

                <div className="stat-icon">

                  <Wind />

                </div>

                <div>

                  <p>Estimated CO₂ Difference</p>

                  <h3>{carbonSaving === null ? "—" : `${carbonSaving.toFixed(2)} kg`}</h3>

                  <span>

                    Current journey estimate

                  </span>

                </div>

              </div>

              <div className="stat-card">

                <div className="stat-icon">

                  <Wallet />

                </div>

                <div>

                  <p>Estimated Cost Difference</p>

                  <h3>{moneySaving === null ? "—" : `Rs. ${Math.round(moneySaving)}`}</h3>

                  <span>

                    Current journey estimate

                  </span>

                </div>

              </div>

              <div className="stat-card">

                <div className="stat-icon">

                  <Clock />

                </div>

                <div>

                  <p>Journey Distance</p>

                  <h3>{routeMetadata?.distance_km != null ? `${routeMetadata.distance_km} km` : "—"}</h3>

                  <span>

                    Current journey estimate

                  </span>

                </div>

              </div>

              <div className="stat-card">

                <div className="stat-icon">

                  <Leaf />

                </div>

                <div>

                  <p>Green Score</p>

                  <h3>{referenceRoute?.score ?? "—"}</h3>

                  <span>

                    Current journey estimate

                  </span>

                </div>

              </div>

            </section>

            <section id="carbon-tracker" className="planner-card" style={{ marginTop: 24, scrollMarginTop: 24 }} aria-label="Carbon tracker">
              <div className="planner-heading"><div><p className="section-label">CARBON TRACKER</p><h2>Saved journey estimates</h2></div><Leaf size={28} /></div>
              <p className="demo-notice">Your saved journeys are stored in your signed-in GreenRoute account. These are modeled differences compared with the direct-road estimate, not verified environmental savings or completed-trip records. Existing history from earlier browser-only versions remains in that browser and is not automatically uploaded.</p>
              {journeySyncStatus === "loading" && <p className="demo-notice">Loading your secure journey history...</p>}
              {journeySyncStatus === "error" && <p role="alert" className="demo-notice">Cloud sync error: {journeySyncError}</p>}
              <div className="stats-grid" style={{ margin: "18px 0" }}>
                <div className="stat-card"><div><p>Saved journeys</p><h3>{savedTrips.length}</h3></div></div>
                <div className="stat-card"><div><p>Estimated CO₂ difference</p><h3>{totalCarbon.toFixed(2)} kg</h3></div></div>
                <div className="stat-card"><div><p>Estimated cost difference</p><h3>Rs. {Math.round(totalCost)}</h3></div></div>
                <div className="stat-card"><div><p>Distance represented</p><h3>{totalDistance.toFixed(1)} km</h3></div></div>
              </div>
              {savedTrips.length > 0 && (
                <div className="gr-analytics" aria-label="Saved journey analytics">
                  <div className="gr-analytics-summary">
                    <div><span>Average estimated CO₂ difference</span><strong>{averageCarbon.toFixed(2)} kg / saved journey</strong></div>
                    <div><span>Average estimated cost difference</span><strong>Rs. {averageCost.toFixed(0)} / saved journey</strong></div>
                  </div>
                  <div className="gr-chart-grid">
                    <div className="gr-chart-card">
                      <h3>CO₂ difference by saved journey</h3>
                      <p>Latest {chartTrips.length} saved entries · kilograms compared with direct road</p>
                      <div className="gr-bar-list">
                        {chartTrips.map((trip, index) => (
                          <div className="gr-bar-row" key={trip.id}>
                            <span title={`${trip.origin} → ${trip.destination}`}>#{savedTrips.length - chartTrips.length + index + 1}</span>
                            <div className="gr-bar-track"><div className="gr-bar-fill gr-carbon" style={{ width: `${100 * safeNumber(trip.carbonSaving) / maxCarbon}%` }} /></div>
                            <strong>{safeNumber(trip.carbonSaving).toFixed(2)} kg</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="gr-chart-card">
                      <h3>Cost difference by saved journey</h3>
                      <p>Latest {chartTrips.length} saved entries · Sri Lankan rupees</p>
                      <div className="gr-bar-list">
                        {chartTrips.map((trip, index) => (
                          <div className="gr-bar-row" key={trip.id}>
                            <span title={`${trip.origin} → ${trip.destination}`}>#{savedTrips.length - chartTrips.length + index + 1}</span>
                            <div className="gr-bar-track"><div className="gr-bar-fill gr-cost" style={{ width: `${100 * safeNumber(trip.costSaving) / maxCost}%` }} /></div>
                            <strong>Rs. {safeNumber(trip.costSaving).toFixed(0)}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="gr-chart-card gr-mode-card">
                      <h3>Selected route types</h3>
                      <p>Distribution across locally saved journey estimates</p>
                      <div className="gr-bar-list">
                        {modeEntries.map(([name, count]) => (
                          <div className="gr-mode-row" key={name}>
                            <div><span>{name}</span><strong>{count} ({(count / savedTrips.length * 100).toFixed(0)}%)</strong></div>
                            <div className="gr-bar-track"><div className="gr-bar-fill gr-mode" style={{ width: `${100 * count / savedTrips.length}%` }} /></div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <p className="gr-analytics-note">Charts describe saved estimates, not confirmed journeys or measured emissions. Saving the same route twice counts as two entries.</p>
                </div>
              )}
              {savedTrips.length > 0 ? <>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", minWidth: 630, color: "#d9f9e9", borderCollapse: "collapse", textAlign: "left" }}>
                    <thead><tr>{["Saved", "Journey", "Mode", "CO₂ difference", "Cost difference", ""].map(label => <th key={label} style={{ padding: 10, borderBottom: "1px solid #27614a" }}>{label}</th>)}</tr></thead>
                    <tbody>{savedTrips.map(trip => <tr key={trip.id}>
                      <td style={{ padding: 10 }}>{trip.createdAt ? new Date(trip.createdAt).toLocaleDateString() : "—"}</td>
                      <td style={{ padding: 10 }}>{trip.origin} → {trip.destination}</td>
                      <td style={{ padding: 10 }}>{trip.name}</td>
                      <td style={{ padding: 10 }}>{Number(trip.carbonSaving || 0).toFixed(2)} kg</td>
                      <td style={{ padding: 10 }}>Rs. {Math.round(Number(trip.costSaving || 0))}</td>
                      <td style={{ padding: 10 }}><button type="button" onClick={() => deleteJourney(trip.id)} aria-label={`Delete ${trip.origin} to ${trip.destination} journey`} style={{ background: "transparent", border: "1px solid #27614a", borderRadius: 8, color: "#d9f9e9", padding: "6px 10px", cursor: "pointer" }}>Delete</button></td>
                    </tr>)}</tbody>
                  </table>
                </div>
                <button type="button" onClick={exportJourneysCsv} disabled={!savedTrips.length} style={{ marginTop: 12, marginRight: 10, background: "#176647", border: "1px solid #29996a", borderRadius: 8, color: "#ffffff", padding: "10px 14px", cursor: "pointer" }}>Export journeys (CSV)</button>
                <button type="button" onClick={clearJourneys} style={{ marginTop: 12, background: "transparent", border: "1px solid #27614a", borderRadius: 8, color: "#d9f9e9", padding: "10px 14px", cursor: "pointer" }}>Clear journey history</button>
              </> : <p style={{ color: "#a9c7b8" }}>No cloud journeys yet. Find a route, select it, and choose “Save journey to account”.</p>}
              {saveMessage && <p role="alert">{saveMessage}</p>}
            </section>

            {/* =========================================

                LOWER DASHBOARD

            ========================================= */}

            <section className="dashboard-grid">

              <div className="panel">

                <div className="panel-header">

                  <div>

                    <p className="section-label">

                      TRANSPORT

                    </p>

                    <h2>

                      Available mobility

                    </h2>

                  </div>

                  <span>

                    Prototype

                  </span>

                </div>

                <div className="transport-list">

                  <div className="transport">

                    <Bus />

                    <div>

                      <strong>

                        Public Bus

                      </strong>

                      <span>

                        Lower-emission

                        shared travel

                      </span>

                    </div>

                  </div>

                  <div className="transport">

                    <Bus />

                    <div>

                      <strong>

                        Campus Shuttle

                      </strong>

                      <span>

                        NSBM transport

                        integration

                      </span>

                    </div>

                  </div>

                  <div className="transport">

                    <Footprints />

                    <div>

                      <strong>

                        Walking

                      </strong>

                      <span>

                        Direct travel

                        emissions: zero

                      </span>

                    </div>

                  </div>

                  <div className="transport">

                    <Bike />

                    <div>

                      <strong>

                        Cycling

                      </strong>

                      <span>

                        Direct travel

                        emissions: zero

                      </span>

                    </div>

                  </div>

                </div>

              </div>

              <div className="panel ai-panel">

                <div className="ai-icon">

                  <Bot size={30} />

                </div>

                <p className="section-label">

                  GREEN AI

                </p>

                <h2>

                  Your intelligent

                  mobility assistant.

                </h2>

                <p>

                  GreenRoute compares travel

                  time, estimated cost,

                  emissions and reliability

                  to recommend routes

                  according to your

                  priorities.

                </p>

                <button>

                  Green AI coming next

                  <ArrowRight size={18} />

                </button>

              </div>

            </section>

          </>

        )}

      </main>

    </div>

  );

}

export default App;