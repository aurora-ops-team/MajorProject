/* ============================================================
   AURORA OPS — API client
   Thin wrapper around the backend REST API (see ../backend).
   Every page file (dashboard.js, monitoring.js, ...) calls these
   instead of touching fetch() directly.
   ============================================================ */

const API_BASE = window.AURORA_API_BASE || "http://localhost:5000";

async function apiGet(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

const api = {
  getDashboard: () => apiGet("/api/dashboard"),
  getSatellites: () => apiGet("/api/satellites"),
  getSatellite: (id) => apiGet(`/api/satellite/${id}`),
  getSatelliteTelemetry: (id) => apiGet(`/api/satellite/${id}/telemetry`),
  getSatelliteHistory: (id, limit) => apiGet(`/api/satellite/${id}/history?limit=${limit || 100}`),

  getAnomalies: () => apiGet("/api/anomalies"),
  getAnomalyDetail: (id) => apiGet(`/api/anomalies/${id}`),
  getAnomalyParamHistory: (id, parameter, limit) =>
    apiGet(`/api/anomalies/${id}/history?parameter=${parameter}&limit=${limit || 100}`),

  getAlerts: () => apiGet("/api/alerts"),
  getAlert: (id) => apiGet(`/api/alerts/${id}`),
  acknowledgeAlert: (id) => apiPost(`/api/alerts/${id}/acknowledge`),
  investigateAlert: (id) => apiPost(`/api/alerts/${id}/investigate`),
  resolveAlert: (id) => apiPost(`/api/alerts/${id}/resolve`),

  getIncidents: () => apiGet("/api/incidents"),
  getIncident: (id) => apiGet(`/api/incidents/${id}`),
  setIncidentStage: (id, stage) => apiPost(`/api/incidents/${id}/status`, { stage }),

  getModels: () => apiGet("/api/models"),
  getModel: (name) => apiGet(`/api/models/${encodeURIComponent(name)}`),
  modelPlotUrl: (filename) => `${API_BASE}/api/models/plots/${filename}`,

  getSystemInfo: () => apiGet("/api/system/info"),
};
