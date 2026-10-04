# AI-Based Autonomous Satellite Operation Assistant — Integrated Build

This is the fully integrated project: the Flask backend (`backend/`) serves
live predictions from your actual trained models, and the frontend
(`frontend/`) has been rewired to consume that backend instead of the
original hardcoded mock data.

## What changed vs. your original files

- **`frontend/app.js`** — removed all mock data (`SATELLITES`,
  `generateTelemetry()`, `PARAMETERS` mock values, `COMPARISON`,
  `DETECTED_ANOMALIES`, `ALERTS`, `INCIDENTS`, `MODELS`, `BEST_MODEL`, the
  ROC/history/feature-importance generators). Kept the layout shell,
  sidebar, topbar clock, starfield background and chat widget.
- **`frontend/api.js`** (new) — a small fetch wrapper around every backend
  endpoint. Every page loads this after `app.js`.
- **All 7 HTML pages** (`index.html`, `monitoring.html`, `anomalies.html`,
  `alerts.html`, `resolution.html`, `models.html`, `system.html`) — rewired
  to call `api.js` instead of reading mock arrays. Visual design, layout and
  CSS are unchanged.
- **`frontend/vendor/chart.umd.js`** (new) — Chart.js is now bundled
  locally instead of loaded from a CDN. The charts on Dashboard, Satellite
  Monitoring, Anomaly Detection and Model Performance were previously
  loading `chart.umd.min.js` from `cdnjs.cloudflare.com`; on a machine
  without internet access that script silently never loads, `Chart` stays
  undefined, and every chart panel renders blank (everything else —
  gauges, tables, alerts — still works, since only the Chart.js-based
  panels depend on it). All 4 pages now load `vendor/chart.umd.js`
  instead, so the whole app works fully offline. If a chart is still
  blank for some other reason, `app.js`'s `chartOrFallback()` helper now
  shows a visible message in that panel instead of leaving it silently
  empty, and logs the real error to the browser console.
- **`backend/`** (new) — a Flask REST API, built from scratch, that:
  - Replays `satellite_1_telemetry.csv` / `satellite_2_telemetry.csv` one
    row at a time, advancing **one row every 30 seconds**, so every
    connected browser tab sees the same telemetry at the same time.
  - Runs your real `preprocessor.joblib` + `model_rf.joblib` (health
    prediction) and `model_isolation_forest.joblib` (anomaly detection) on
    every row.
  - Combines both predictions with a rule-based decision engine into a
    NORMAL / LOW / MEDIUM / HIGH / CRITICAL priority.
  - Generates alerts and incidents with a plain-language rationale, and
    tracks their operator-facing lifecycle (acknowledge / investigate /
    resolve, and 5-stage incident tracking) — all in backend memory, so
    every page and every client agree on the current state.
  - Serves the real training reports/metrics and plot images from
    `ModelTraining/` for the Model Performance page.

## A correction I made while integrating

Your frontend's original mock data used illustrative operating envelopes
(e.g. orbital altitude "540–560 km") that don't match the actual dataset
your team generated (`dataset_generation/regenerate_dataset.py`), where
orbital altitude ranges ~700–1900 km and is **not** a real risk factor at
all (near-zero correlation with health, lowest Random Forest feature
importance). I pulled the *real* thresholds straight from
`dataset_generation/dataset_regeneration_report.txt` instead:

| Parameter | Real risk threshold used by the labelling rule |
|---|---|
| Battery Voltage | risk if `< 22.02 V` |
| Solar Panel Temperature | risk if `< -40.11°C` or `> 39.89°C` |
| Attitude Control Error | risk if `> 3.99°` |
| Data Transmission Rate | risk if `< 28.14 Mbps` |
| Thermal Control Status | risk if `!= NOMINAL (1)` |
| Orbital Altitude | **not a risk factor** — shown for information only |

These live in `backend/config.py` (`FEATURE_RANGES`) and drive every
alert/anomaly-comparison table in the app.

## How to run it

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

This starts the API on **http://localhost:5000** and immediately begins the
30-second telemetry simulation for SAT-01 and SAT-02.

> **Important:** `requirements.txt` pins `scikit-learn==1.5.1` because your
> `.joblib` model files were saved with that version. Loading them with a
> different (especially newer) scikit-learn version can throw an
> `AttributeError` when unpickling. If you retrain and re-save the models
> yourself, you can relax this pin.

Quick check it's alive:

```bash
curl http://localhost:5000/api/health
curl http://localhost:5000/api/dashboard
```

### 2. Frontend

The frontend is static HTML/CSS/JS — no build step. Two ways to run it:

- **Directly**: open `frontend/index.html` in a browser (works because
  `api.js` defaults to `http://localhost:5000`).
- **Via a local static server** (recommended, avoids any `file://` quirks):
  ```bash
  cd frontend
  python -m http.server 8080
  ```
  then visit `http://localhost:8080`.

If your backend runs somewhere other than `localhost:5000`, set it before
loading `api.js`, e.g. add this to a page's `<head>`:
```html
<script>window.AURORA_API_BASE = "http://your-host:5000";</script>
```

### 3. Using it

- **Dashboard** — live orbital view, telemetry gauges and fleet overview
  for SAT-01/SAT-02.
- **Satellite Monitoring** — per-satellite historical charts + a
  searchable/sortable telemetry table.
- **Anomaly Detection** — Isolation Forest status per satellite, a
  parameter-by-parameter comparison table, and a chart with anomalous
  points highlighted.
- **Alert Center** — the live, backend-owned alert queue. Acknowledge,
  Investigate and Resolve buttons call the API and persist for every
  client.
- **Resolution Center** — incidents auto-opened from HIGH/CRITICAL alerts,
  with a 5-stage lifecycle you can advance.
- **Model Performance** — real accuracy/precision/recall/ROC-AUC/confusion
  matrices for all 6 trained models, plus the actual plot images generated
  by your training scripts.
- **System Information** — architecture, tech stack, dataset facts and
  parameter envelopes, all pulled live from the backend.
- **Mission Assistant** (chat bubble, bottom-right) — answers questions by
  calling the same REST API the dashboards use, so it only ever reports
  real, current data. It is a lightweight rule-based responder, not a full
  retrieval-augmented LLM — wiring in an actual LLM/RAG backend was outside
  the scope of this integration pass and would be a natural next step.

## Project layout

```
backend/
  app.py                    entry point
  config.py                 feature order, envelopes, simulation settings
  requirements.txt
  data/                     satellite_1/2_telemetry.csv (copied from project root)
  model_artifacts/          preprocessor + all 6 trained models (copied from step2/ and ModelTraining/)
  model_reports/            training reports (copied from ModelTraining/reports)
  model_plots/              training plot PNGs (copied from ModelTraining/plots)
  services/
    simulation_service.py   30s telemetry loop, single source of truth
    prediction_service.py   Random Forest health prediction
    anomaly_service.py      Isolation Forest anomaly detection
    decision_service.py     rule-based priority engine
    alert_service.py        alert generation + lifecycle
    incident_service.py     incident generation + lifecycle
    history_service.py      in-memory rolling telemetry history
    model_service.py        real training metrics for the Model page
  routes/
    satellite_routes.py     dashboard/satellites/telemetry/history/anomalies
    alert_routes.py         alerts + incidents
    model_routes.py         models + plot images
    system_routes.py        system info
frontend/
  index.html                Dashboard
  monitoring.html           Satellite Telemetry Monitoring
  anomalies.html            Anomaly Detection Center
  alerts.html               Alert Center
  resolution.html           Resolution Center
  models.html               Model Training & Performance Center
  system.html                System Information
  app.js                    shared shell + chat widget (mock data removed)
  api.js                    REST client used by every page
  universal.css              unchanged design system
```

## Known limitations / next steps

- The "Mission Assistant" chatbot is intentionally simple and rule-based
  (keyword-matched, calling the live API) rather than a true
  retrieval-augmented LLM, matching what was feasible to verify and test
  in this integration pass.
- All alert/incident/history state is in-memory and resets when the Flask
  process restarts, per your requirement to avoid an external database
  service. If you need persistence across restarts, the simplest next step
  would be periodically dumping `services/*_service.py` in-memory state to
  a local SQLite file.
- CORS is currently wide open (`origins: "*"`) for local development
  convenience; tighten `config.CORS_ORIGINS` before deploying anywhere
  public.
