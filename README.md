# Aurora Ops

Aurora Ops is an AI-based satellite operations console. It combines a
Flask REST backend, live telemetry replay, trained health/anomaly models, a
mission-control frontend, operational alert workflows, and a read-only
satellite assistant.

The integrated application is designed for local development and demonstration.
The backend is the source of truth for telemetry, predictions, alerts,
incidents, model metadata, and chatbot context. The frontend is a static
HTML/CSS/JavaScript application that polls that API.

## What is implemented

### Backend

- Replays `SAT-01` and `SAT-02` telemetry from CSV files.
- Advances the shared simulation by one row every 30 seconds.
- Loads the trained preprocessing pipeline and model artifacts from
  `backend/model_artifacts/`.
- Uses Random Forest for supervised health prediction.
- Uses Isolation Forest for anomaly detection.
- Combines health and anomaly results into a final priority:
  `NORMAL`, `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
- Creates alerts from risk conditions and manages alert transitions:
  acknowledge, investigate, and resolve.
- Creates incidents for high-priority conditions and supports a five-stage
  resolution workflow.
- Serves model reports, model metadata, and plot images.
- Keeps operational state in backend memory so every browser tab sees the same
  current state. State resets when Flask restarts.
- Provides a read-only chatbot API with optional DeepSeek or another
  OpenAI-compatible provider and a deterministic local fallback.

### Frontend
- roshan
- Dashboard with live fleet overview, realistic Earth imagery, orbit paths, and
  animated satellite markers.
- SAT-01/SAT-02 hover and focus tooltips with current telemetry and priority.
- Satellite Monitoring page with current metrics, historical charts, searchable
  and sortable records, and CSV export.
- Anomaly Detection page with Isolation Forest status and parameter comparisons.
- Alert Center with operator lifecycle controls.
- Resolution Center with incident stage progression.
- Model Performance page with metrics and training plots.
- System Information page with live architecture, threshold, and system data.
- Shared mission assistant chat widget.
- Local Chart.js bundle so charts do not require a CDN connection.

## Architecture and data flow

```text
CSV telemetry
    |
    v
simulation_service.py  -- shared 30-second replay and history
    |
    +--> prediction_service.py  -- Random Forest health + confidence
    |
    +--> anomaly_service.py     -- Isolation Forest status + score
    |
    v
decision_service.py    -- health/anomaly combination and priority
    |
    +--> alert_service.py      -- active alerts and lifecycle
    +--> incident_service.py   -- high-priority incidents and stages
    +--> chat_service.py       -- grounded context for fallback/LLM replies
    |
    v
Flask routes (/api/*)
    |
    v
frontend/api.js and the seven frontend pages
```

The frontend never owns authoritative telemetry or alert state. It requests
current values from the API and refreshes the relevant views.

## Telemetry and model semantics

The seven model features must remain in the trained order defined in
`backend/config.py`:

1. `time_since_launch`
2. `orbital_altitude`
3. `battery_voltage`
4. `solar_panel_temperature`
5. `attitude_control_error`
6. `data_transmission_rate`
7. `thermal_control_status`

The risk thresholds used by the dataset labelling rules and UI highlighting
are:

| Parameter | Risk condition |
| --- | --- |
| Battery Voltage | `< 22.02 V` |
| Solar Panel Temperature | `< -40.11 °C` or `> 39.89 °C` |
| Attitude Control Error | `> 3.99°` |
| Data Transmission Rate | `< 28.14 Mbps` |
| Thermal Control Status | `0` / not nominal |
| Orbital Altitude | Informational only; not a health risk factor |

Thermal Status is a subsystem telemetry input. It is not a second health
prediction. Health is the overall supervised model result derived from the
telemetry features, while the final priority also considers the anomaly
detector:

```text
Healthy + Normal anomaly       -> NORMAL
Healthy + Anomaly              -> LOW
Unhealthy + Normal anomaly     -> MEDIUM
Unhealthy + Normal + high confidence -> HIGH
Unhealthy + Anomaly            -> CRITICAL
```

The Monitoring table intentionally renders Thermal Status as a distinct
subsystem indicator and Health as the overall priority chip.

## Dashboard orbit behavior

The dashboard orbit view is implemented in
[`frontend/index.html`](frontend/index.html).

- The realistic Earth is loaded from
  `frontend/assets/earth-realistic-crop.png`.
- The original attached artwork is retained as
  `frontend/assets/earth-realistic.png`.
- Orbit paths remain CSS elements independent of the Earth image.
- Satellite markers continue to rotate using CSS animation.
- Hover/focus changes marker scale in place; it does not rebuild the animated
  orbit DOM. This prevents animation resets.
- Orbit spinner wrappers do not intercept pointer events, so SAT-01 and SAT-02
  receive the correct hover events.
- Clicking a satellite opens its telemetry details panel.

## Chatbot

The shared chat UI is created by `renderShell()` and `initChatbot()` in
[`frontend/app.js`](frontend/app.js). Requests are sent through
[`frontend/api.js`](frontend/api.js) to `POST /api/chat`.

The backend builds a current, structured context containing:

- SAT-01 and SAT-02 telemetry and prediction summaries.
- Health prediction, confidence, anomaly status, anomaly score, priority, and
  update timestamp.
- Active unresolved alerts.
- Incidents and their current stages.
- System status and active alert count.
- Best health/anomaly models and the complete trained model list.

### Provider behavior

1. If a complete OpenAI-compatible configuration is present, the backend sends
   the grounded context and conversation to the configured provider.
2. DeepSeek is supported through its OpenAI-compatible chat completions URL.
3. If configuration is missing, the provider request fails, the response is
   malformed, or the response is empty, the backend uses the deterministic
   fallback responder.
4. The API response identifies whether `provider` is `llm` or `fallback` and
   whether `fallback` is `true` or `false`.
5. The frontend checks `GET /api/chat/status` and displays a provider-aware
   welcome message without receiving the API key.

The chatbot is read-only. It cannot acknowledge alerts, modify incidents,
change telemetry, or execute operational commands. User messages are limited
to 2,000 characters and each request accepts at most 12 messages.

### DeepSeek configuration

Copy the safe template:

```powershell
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env`:

```dotenv
AURORA_CHAT_PROVIDER=openai-compatible
AURORA_CHAT_API_URL=https://api.deepseek.com/chat/completions
AURORA_CHAT_API_KEY=replace-with-your-server-side-key
AURORA_CHAT_MODEL=deepseek-chat
AURORA_CHAT_TIMEOUT_SECONDS=15
```

`backend/config.py` loads `backend/.env` with `python-dotenv`. The real
`.env` is ignored by Git and the API key is never returned to the browser.
Rotate a key immediately if it has been exposed in chat, logs, screenshots, or
source control.

If credentials are not configured, the application still works and the
assistant uses its grounded local fallback.

## Running the application

### 1. Install backend dependencies

Use Python with a compatible scientific stack. The model artifacts were saved
with scikit-learn 1.5.1, so keep that version unless the models are retrained.

```powershell
cd backend
python -m pip install -r requirements.txt
```

The main dependencies are Flask, Flask-Cors, pandas, NumPy, joblib,
scikit-learn 1.5.1, and python-dotenv.

### 2. Start Flask

From `backend`:

```powershell
python app.py
```

The API listens on `http://localhost:5000`. The simulation starts when the
application module loads.

Basic checks:

```powershell
curl http://localhost:5000/api/health
curl http://localhost:5000/api/dashboard
curl http://localhost:5000/api/chat/status
```

### 3. Start the static frontend

Opening `frontend/index.html` directly works for local use. A static server is
recommended because it avoids browser `file://` restrictions:

```powershell
cd frontend
python -m http.server 8080
```

Open `http://localhost:8080`.

If the backend is hosted elsewhere, define this before `api.js` loads:

```html
<script>
  window.AURORA_API_BASE = "http://your-host:5000";
</script>
```

## Using the frontend

| Page | Purpose |
| --- | --- |
| Dashboard | Fleet status, orbit view, Earth, satellite tooltips, details, and charts |
| Satellite Monitoring | Current metrics, historical telemetry, filtering, sorting, and CSV export |
| Anomaly Detection | Isolation Forest results and risk-parameter comparisons |
| Alert Center | Active alerts and acknowledge/investigate/resolve operations |
| Resolution Center | Incident list and five-stage resolution workflow |
| Model Performance | Six trained model metrics, reports, and plot images |
| System Information | Backend architecture, telemetry facts, thresholds, and system status |

### Telemetry CSV export

The **Export CSV** button on the Monitoring page uses the currently selected satellite and exports
the records currently visible after search and sort are applied. The generated
file includes timestamp, satellite ID, all telemetry values, Thermal Status,
and Health. Files use this naming pattern:

```text
sat-01-telemetry-YYYY-MM-DD.csv
```

## REST API reference

### Health and satellite data

```text
GET  /api/health
GET  /api/dashboard
GET  /api/satellites
GET  /api/satellite/<satellite_id>
GET  /api/satellite/<satellite_id>/telemetry
GET  /api/satellite/<satellite_id>/history?limit=100
```

### Anomalies

```text
GET /api/anomalies
GET /api/anomalies/<satellite_id>
GET /api/anomalies/<satellite_id>/history?parameter=<name>&limit=100
```

### Alerts and incidents

```text
GET  /api/alerts
GET  /api/alerts/<alert_id>
POST /api/alerts/<alert_id>/acknowledge
POST /api/alerts/<alert_id>/investigate
POST /api/alerts/<alert_id>/resolve

GET  /api/incidents
GET  /api/incidents/<incident_id>
POST /api/incidents/<incident_id>/status
```

The incident status request supplies a JSON body containing the next stage,
for example `{ "stage": "Investigation" }`.

### Models, system, and chat

```text
GET  /api/models
GET  /api/models/<model_name>
GET  /api/models/plots/<filename>
GET  /api/system/info
GET  /api/chat/status
POST /api/chat
```

Chat requests use:

```json
{
  "messages": [
    { "role": "user", "content": "What is the status of SAT-01?" }
  ]
}
```

Only `user` and `assistant` roles are accepted, the array must be non-empty,
and the final message must be from the user.

## Project layout

```text
backend/
  app.py                    Flask entry point and blueprint registration
  config.py                 Paths, thresholds, simulation, and chat settings
  .env.example              Safe chatbot configuration template
  requirements.txt          Pinned Python dependencies
  data/                     SAT-01/SAT-02 telemetry CSV files
  model_artifacts/          Preprocessor and six trained models
  model_reports/            Training reports
  model_plots/              Training plot PNGs
  routes/                   REST endpoint blueprints
  services/                 Simulation, ML, alerts, incidents, models, chat
frontend/
  index.html                Dashboard and orbital visualization
  monitoring.html           Telemetry table, charts, and CSV export
  anomalies.html            Anomaly Detection page
  alerts.html               Alert Center
  resolution.html           Resolution Center
  models.html               Model Performance page
  system.html               System Information page
  app.js                    Shared shell, constants, and chat widget
  api.js                    Shared REST client
  universal.css             Shared design system
  assets/                   Earth imagery used by the dashboard
  vendor/chart.umd.js       Local Chart.js bundle
```

## Validation and troubleshooting

Validate the inline page scripts after frontend edits:

```powershell
$file = "frontend\monitoring.html"
$script = [regex]::Matches((Get-Content -Raw $file), "(?s)<script>(.*?)</script>") |
  Select-Object -Last 1
$encoded = [Convert]::ToBase64String(
  [Text.Encoding]::UTF8.GetBytes($script.Groups[1].Value)
)
node -e "new Function(Buffer.from(process.argv[1],'base64').toString())" -- $encoded
```

Common issues:

- **Charts are blank:** confirm `frontend/vendor/chart.umd.js` exists and the
  browser console has no script error.
- **API requests fail:** start Flask first and confirm port 5000 is reachable.
- **Model loading fails:** use the pinned scikit-learn 1.5.1 dependency or
  retrain and re-save the artifacts with the installed version.
- **Chatbot says fallback:** check `GET /api/chat/status`, the `.env` values,
  the provider URL, and the Flask console for provider failures.
- **Frontend opens but shows no data:** use the local static server and verify
  the browser can reach `http://localhost:5000`.

## Free deployment: GitHub Pages + Render

The recommended free deployment uses GitHub Pages for the static frontend and
Render for the Flask API:

```text
GitHub Pages  -->  https://<render-service>.onrender.com
                    Render Gunicorn API
```

This avoids trying to run the long-lived Flask telemetry simulator as a
serverless function. Vercel is suitable for the static frontend, but its
serverless runtime is not a drop-in host for the current continuously running
simulation and in-memory operational state.

### Deploy the backend to Render

1. Push the repository to GitHub. The included
   [`render.yaml`](render.yaml) describes the free web service.
2. In Render, choose **New > Blueprint**, select the repository, and approve
   the `render.yaml` configuration.
3. Confirm the service root directory is `backend`.
4. Render installs `backend/requirements.txt` and starts:

   ```text
   gunicorn --bind 0.0.0.0:$PORT app:app
   ```

5. After the first deployment, copy the public HTTPS service URL, for example:

   ```text
   https://aurora-ops-api.onrender.com
   ```

6. Configure these Render environment variables:

   ```text
   AURORA_CORS_ORIGINS=https://<github-user>.github.io
   AURORA_DEBUG=false
   AURORA_CHAT_PROVIDER=fallback
   ```

   For DeepSeek, additionally set:

   ```text
   AURORA_CHAT_PROVIDER=openai-compatible
   AURORA_CHAT_API_URL=https://api.deepseek.com/chat/completions
   AURORA_CHAT_API_KEY=<secret>
   AURORA_CHAT_MODEL=deepseek-chat
   AURORA_CHAT_TIMEOUT_SECONDS=15
   ```

   Store the API key only in Render's secret environment settings. Never put
   it in the repository or GitHub Pages files.

7. Verify the backend before deploying the frontend:

   ```powershell
   curl https://<render-service>.onrender.com/api/health
   curl https://<render-service>.onrender.com/api/chat/status
   ```

### Deploy the frontend to GitHub Pages

The repository includes
`.github/workflows/deploy-pages.yml`. It publishes only `frontend/` and
injects the backend URL into `frontend/runtime-config.js` during the workflow.

1. In the GitHub repository, enable **Settings > Pages > GitHub Actions**.
2. Add a repository variable named `RENDER_API_URL` with the complete Render
   URL and no trailing slash:

   ```text
   https://<render-service>.onrender.com
   ```

3. Push to the `roshan` branch or manually run **Deploy frontend to GitHub
   Pages** from the Actions tab.
4. Add the resulting Pages origin exactly to Render's
   `AURORA_CORS_ORIGINS`, then redeploy the backend if required.
5. Open the Pages URL and confirm the Dashboard, Monitoring, chatbot status,
   charts, alerts, and CSV export all use the Render API.

The local `frontend/runtime-config.js` defaults to an empty API base, so local
development continues to use the existing `http://localhost:5000` fallback in
`frontend/api.js`.

### Free-tier behavior

- Render free services can sleep after inactivity. The first request after
  sleeping may take longer.
- The telemetry simulator runs only while the Render process is active.
- Telemetry history, alerts, incidents, and chatbot context are held in
  memory. A restart or cold start resets them.
- Render's local filesystem should not be treated as durable application
  storage.
- Before production use, add persistent storage, authentication, rate
  limiting, restricted CORS, monitoring, and an always-on service if continuous
  telemetry is required.

## Limitations and deployment notes

- Telemetry, alert, incident, and history state is in memory and resets when
  Flask restarts. Add persistent storage before production deployment.
- CORS is currently configured as `*` for local development. Restrict
  `CORS_ORIGINS` before exposing the API publicly.
- The chatbot is read-only and grounded only in the context assembled by the
  backend. It should report unavailable data rather than inventing values.
- Do not commit `backend/.env`, API keys, model secrets, or other credentials.
- The included model artifacts and thresholds are project-specific; retrain
  and revalidate them when the telemetry schema or data distribution changes.
