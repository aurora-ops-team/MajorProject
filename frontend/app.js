/* ============================================================
   AURORA OPS — shared application logic
   Layout shell (sidebar/topbar/starfield/chatbot) + small UI utilities.
   Included on every page via <script src="app.js">, followed by
   <script src="api.js"> and the page's own script.

   NOTE: this file used to also hold hardcoded mock mission data
   (SATELLITES, generateTelemetry(), PARAMETERS, COMPARISON,
   DETECTED_ANOMALIES, ALERTS, INCIDENTS, MODELS, BEST_MODEL...).
   All of that has been removed -- every page now fetches live data
   from the Flask backend via api.js instead. See
   complete_page_by_page_integration_plan.md section 9.
   ============================================================ */

/* ---------------- deterministic RNG (still used for the decorative starfield) ---------------- */
function lcg(seed) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return function () {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

const PARAMETERS = [
  { key: "battery_voltage", label: "Battery Voltage", unit: "V", color: "var(--chart-1)" },
  { key: "solar_panel_temperature", label: "Solar Panel Temperature", unit: "°C", color: "var(--chart-4)" },
  { key: "orbital_altitude", label: "Orbital Altitude", unit: "km", color: "var(--chart-2)" },
  { key: "attitude_control_error", label: "Attitude Control Error", unit: "°", color: "var(--chart-5)" },
  { key: "data_transmission_rate", label: "Data Transmission Rate", unit: "Mbps", color: "var(--chart-3)" },
];

const SATELLITE_IDS = ["SAT-01", "SAT-02"];

/* ---------------- shared helpers ---------------- */
function statusColorVar(status) {
  const k = String(status).toUpperCase();
  if (k === "CRITICAL" || k === "DEGRADED") return "var(--critical)";
  if (k === "HIGH" || k === "CAUTION") return "var(--caution)";
  if (k === "MEDIUM" || k === "WARNING") return "var(--warning)";
  if (k === "LOW") return "var(--info)";
  return "var(--nominal)";
}
function statusChipHTML(status, dot) {
  dot = dot === undefined ? true : dot;
  const cls = "status-" + String(status).toUpperCase().replace(/\s+/g, "_");
  return '<span class="status-chip ' + cls + '">' + (dot ? '<span class="chip-dot"></span>' : "") + status + "</span>";
}
function escapeHTML(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
/* health/priority ("NORMAL"/"Healthy"/etc.) -> the chip status vocabulary above */
function healthToChip(healthOrPriority) {
  return healthOrPriority;
}
const ICONS = {
  dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>',
  satellite: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m13 7 5 5-4.5 4.5a3.54 3.54 0 0 1-5-5L13 7Z"/><path d="m18 12 2.5-2.5a2.12 2.12 0 0 0-3-3L15 9"/><path d="M7 17.5 3.5 21"/><path d="m3 21 2-6 6 2-2 6z"/></svg>',
  radar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19.07 4.93A10 10 0 0 0 6.99 3.34"/><path d="M4 6l.01.01"/><path d="M2.29 9.62A10 10 0 1 0 21.31 8.35"/><path d="M16.24 7.76A6 6 0 1 0 8.23 16.67"/><path d="M12 18a6 6 0 0 0 6-6"/><circle cx="12" cy="12" r="2"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
  wrench: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
  brain: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>',
  activity: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.268 21a2 2 0 0 0 3.464 0"/><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"/></svg>',
  bot: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
  sparkles: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 4.9L5 9.9l4.1 3-1.5 5L12 15l4.4 2.9-1.5-5 4.1-3-5.1-1.1z"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
  send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/></svg>',
};

const NAV = [
  { to: "index.html", label: "Dashboard", icon: ICONS.dashboard },
  { to: "monitoring.html", label: "Satellite Monitoring", icon: ICONS.satellite },
  { to: "anomalies.html", label: "Anomaly Detection", icon: ICONS.radar },
  { to: "alerts.html", label: "Alert Center", icon: ICONS.alert },
  { to: "resolution.html", label: "Resolution Center", icon: ICONS.wrench },
  { to: "models.html", label: "Model Performance", icon: ICONS.brain },
  { to: "system.html", label: "System Information", icon: ICONS.info },
];

/* ---------------- layout shell ---------------- */
function buildStarfield(count, seed) {
  count = count || 90; seed = seed || 77;
  const rnd = lcg(seed);
  let html = '<div class="grid-overlay" style="position:absolute;inset:0;opacity:.4"></div>';
  for (let i = 0; i < count; i++) {
    const left = rnd() * 100, top = rnd() * 100, size = 0.8 + rnd() * 1.8, delay = rnd() * 6, duration = 3 + rnd() * 5, opacity = 0.2 + rnd() * 0.6;
    html += `<span class="star" style="left:${left}%;top:${top}%;width:${size}px;height:${size}px;opacity:${opacity};animation:twinkle ${duration}s ease-in-out ${delay}s infinite"></span>`;
  }
  return html;
}

function currentPage() {
  const p = location.pathname.split("/").pop();
  return p === "" ? "index.html" : p;
}

function renderShell(pageTitle) {
  const page = currentPage();
  document.body.insertAdjacentHTML("afterbegin", `
    <div class="app-root">
      <div class="starfield">${buildStarfield()}</div>
      <div class="app-flex">
        <aside class="sidebar" id="sidebar">
          <div class="sidebar-brand">
            <span class="sidebar-brand-icon glow-primary">${ICONS.satellite}</span>
            <div class="sidebar-brand-text">
              <p>Aurora Ops</p>
              <p>Autonomous Assistant</p>
            </div>
          </div>
          <nav class="sidebar-nav">
            ${NAV.map((n) => `
              <a href="${n.to}" class="nav-item${n.to === page ? " active" : ""}" title="${n.label}">
                ${n.icon}<span class="nav-label">${n.label}</span>
              </a>`).join("")}
          </nav>
          <div class="sidebar-footer">
            <button class="sidebar-settings-btn" type="button">${ICONS.settings}<span class="sidebar-settings-text">Settings</span></button>
            <div class="sidebar-user">
              <span class="avatar-chip">RK</span>
              <div class="sidebar-user-text">
                <p>R. Kapoor</p>
                <p>Ground Operator</p>
              </div>
            </div>
          </div>
          <button class="sidebar-toggle" id="sidebarToggle" type="button" aria-label="Toggle navigation">${ICONS.chevron}</button>
        </aside>

        <div class="main-col">
          <header class="topbar">
            <div class="topbar-left">
              <span class="pill pill-nominal"><span class="live-dot"><span class="ring"></span><span class="dot"></span></span>Live</span>
              <span class="pill">${ICONS.shield} System Status: <span id="topbarSystemStatus" style="color:oklch(0.95 0.012 240 / 90%)">—</span></span>
              <span class="pill">${ICONS.activity} Telemetry Link: <span style="color:var(--nominal)">Streaming</span></span>
            </div>
            <div class="topbar-right">
              <span class="clock mono-num" id="clock">--:--:-- UTC</span>
              <button class="icon-btn" type="button" aria-label="Notifications">${ICONS.bell}<span class="badge-dot" id="topbarAlertBadge">0</span></button>
              <div class="user-chip">
                <span class="avatar-chip">RK</span>
                <div>
                  <p>R. Kapoor</p>
                  <p>Ops Console 2</p>
                </div>
              </div>
            </div>
          </header>
          <main class="page" id="pageRoot"></main>
        </div>
      </div>

      <button class="chat-fab" id="chatFab" type="button" aria-label="Open AI satellite assistant">
        <span class="ring"></span>
        ${ICONS.bot}
      </button>
      <div class="chat-window glass" id="chatWindow">
        <div class="chat-head">
          <div class="chat-head-left">
            <span class="chat-head-icon">${ICONS.sparkles}</span>
            <div>
              <p class="title">AI Satellite Assistant</p>
              <p class="desc">Ask anything about telemetry, anomalies, alerts, models and system health.</p>
            </div>
          </div>
          <button class="chat-clear" id="chatClear" type="button" aria-label="Clear conversation">${ICONS.trash}</button>
        </div>
        <div class="chat-body" id="chatBody"></div>
        <div class="chat-foot">
          <div class="chat-suggestions" id="chatSuggestions"></div>
          <form class="chat-form" id="chatForm">
            <input type="text" id="chatInput" placeholder="Ask the assistant…" autocomplete="off" />
            <button class="chat-send" type="submit" aria-label="Send message">${ICONS.send}</button>
          </form>
        </div>
      </div>
    </div>
  `);

  document.title = pageTitle ? pageTitle + " | Aurora Ops" : "Aurora Ops — Autonomous Satellite Operation Assistant";

  // clock
  function tick() {
    const now = new Date();
    const el = document.getElementById("clock");
    if (el) el.innerHTML = now.toISOString().slice(0, 10) + ' <span class="clock-time">' + now.toISOString().slice(11, 19) + "</span> UTC";
  }
  tick();
  setInterval(tick, 1000);

  // sidebar collapse
  const sidebar = document.getElementById("sidebar");
  document.getElementById("sidebarToggle").addEventListener("click", () => sidebar.classList.toggle("collapsed"));

  initChatbot();
  refreshTopbar();
  setInterval(refreshTopbar, 30000);

  return document.getElementById("pageRoot");
}

/* keep the topbar's system status + alert badge in sync with the backend,
   independent of whatever the current page itself is polling */
async function refreshTopbar() {
  try {
    const info = await api.getSystemInfo();
    const el = document.getElementById("topbarSystemStatus");
    if (el) el.textContent = info.system_status;
    const badge = document.getElementById("topbarAlertBadge");
    if (badge) badge.textContent = info.active_alerts;
    window.AURORA_LATEST_SYSTEM_INFO = info;
  } catch (e) {
    const el = document.getElementById("topbarSystemStatus");
    if (el) el.textContent = "Offline";
  }
}

/* ---------------- chatbot ---------------- */
const SUGGESTED_QUESTIONS = [
  "What is SAT-01's current status?", "What caused the latest anomaly?", "Show the critical alerts.",
  "Which model is used for health prediction?", "Explain battery voltage parameter.", "What does attitude control error mean?",
];

function initChatbot() {
  const fab = document.getElementById("chatFab");
  const win = document.getElementById("chatWindow");
  const body = document.getElementById("chatBody");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const suggestions = document.getElementById("chatSuggestions");
  const clearBtn = document.getElementById("chatClear");
  let typing = false;

  const FALLBACK_GREETING = "AI Satellite Assistant online in grounded fallback mode. I have live context on SAT-01 and SAT-02 telemetry, active anomalies, prioritised alerts and model performance. How can I help?";
  const LLM_GREETING = "Welcome to the Aurora Ops AI Satellite Assistant. DeepSeek is connected and ready with live context on SAT-01 and SAT-02 telemetry, active anomalies, prioritised alerts and model performance. How can I help?";
  const GREETING = { role: "ai", text: FALLBACK_GREETING };
  let messages = [GREETING];

  function formatChatText(text) {
    const lines = escapeHTML(text).split(/\r?\n/);
    const blocks = [];
    let paragraph = [];
    let list = [];

    function flushParagraph() {
      if (paragraph.length) {
        blocks.push(`<p>${paragraph.join(" ")}</p>`);
        paragraph = [];
      }
    }
    function flushList() {
      if (list.length) {
        blocks.push(`<ul>${list.map((item) => `<li>${item}</li>`).join("")}</ul>`);
        list = [];
      }
    }

    lines.forEach((line) => {
      const trimmed = line.trim();
      const bullet = trimmed.match(/^[-*•]\s+(.+)/);
      if (!trimmed) {
        flushParagraph();
        flushList();
      } else if (bullet) {
        flushParagraph();
        list.push(bullet[1]);
      } else {
        flushList();
        paragraph.push(trimmed);
      }
    });
    flushParagraph();
    flushList();

    return blocks.join("").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function renderMessages() {
    body.innerHTML = messages.map((m) =>
      `<div class="chat-msg ${m.role === "user" ? "user" : "ai"}"><div class="chat-bubble">${
        m.role === "user" ? escapeHTML(m.text) : formatChatText(m.text)
      }</div></div>`
    ).join("") + (typing ? '<div class="chat-typing"><span></span><span></span><span></span></div>' : "");
    body.scrollTop = body.scrollHeight;
  }
  function renderSuggestions() {
    suggestions.innerHTML = SUGGESTED_QUESTIONS.slice(0, 4).map((q) => `<button type="button">${escapeHTML(q)}</button>`).join("");
    suggestions.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => send(b.textContent)));
  }
  async function send(text) {
    const q = text.trim();
    if (!q || typing) return;
    messages.push({ role: "user", text: q });
    input.value = "";
    typing = true;
    renderMessages();
    let reply;
    try {
      reply = await assistantReply(q, messages);
    } catch (e) {
      reply = "I couldn't reach the backend just now. Make sure the Flask API (backend/app.py) is running on " + (window.AURORA_API_BASE || "http://localhost:5000") + ".";
    }
    messages.push({ role: "ai", text: reply });
    typing = false;
    renderMessages();
  }

  fab.addEventListener("click", () => win.classList.toggle("open"));
  clearBtn.addEventListener("click", () => { messages = [GREETING]; renderMessages(); });
  form.addEventListener("submit", (e) => { e.preventDefault(); send(input.value); });

  renderMessages();
  renderSuggestions();
  api.getChatStatus().then((status) => {
    GREETING.text = status.configured ? LLM_GREETING : FALLBACK_GREETING;
    messages[0] = GREETING;
    renderMessages();
  }).catch(() => {
    // Keep the local fallback greeting when the backend is unavailable.
  });
}

/* Lightweight, fully-grounded assistant: rather than a fabricated
   canned script, it answers from whatever the backend is reporting
   right now. A full retrieval-augmented LLM assistant is out of scope
   for this integration pass -- this keeps the chat widget honest about
   only ever surfacing real backend data. */
async function assistantReply(q, conversation) {
  try {
    const history = conversation
      .filter((message) => message.role === "user" || message.role === "ai")
      .map((message) => ({
        role: message.role === "ai" ? "assistant" : "user",
        content: message.text,
      }));
    const result = await api.chat(history);
    return result.reply;
  } catch (e) {
    return localAssistantReply(q);
  }
}

/* Offline fallback for development and for deployments without an LLM provider. */
async function localAssistantReply(q) {
  const s = q.toLowerCase();

  if (s.includes("sat-01") || s.includes("sat-02") || s.includes("status") || s.includes("health")) {
    const satId = s.includes("sat-02") ? "SAT-02" : "SAT-01";
    const sat = await api.getSatellite(satId);
    return `${satId} is currently ${sat.priority} (${sat.condition}). Health prediction: ${sat.health_prediction} `
      + `(${sat.health_confidence}% confidence). Anomaly status: ${sat.anomaly_status} (score ${sat.anomaly_score}).`;
  }
  if (s.includes("model")) {
    const info = await api.getSystemInfo();
    return `Health prediction uses ${info.active_models.health_prediction}; anomaly detection uses `
      + `${info.active_models.anomaly_detection}. All 6 trained models (${info.trained_models.join(", ")}) `
      + `are available on the Model Performance page.`;
  }
  if (s.includes("critical alert") || s.includes("alerts")) {
    const { alerts } = await api.getAlerts();
    const active = alerts.filter((a) => a.status !== "RESOLVED");
    if (!active.length) return "There are no active alerts right now — the fleet is nominal.";
    const critical = active.filter((a) => a.priority === "CRITICAL");
    return `${active.length} active alert(s), ${critical.length} CRITICAL. Most recent: ${active[0].id} — `
      + `${active[0].satellite} ${active[0].subsystem}, ${active[0].issue} (${active[0].priority}).`;
  }
  if (s.includes("battery"))
    return "Battery voltage is the main power-bus potential. In this dataset, values below 22.02 V are treated as a low-battery risk factor by the health-labelling rule, and it is one of the top features used by the Random Forest health classifier.";
  if (s.includes("attitude"))
    return "Attitude control error is the angular difference between commanded and measured orientation, in degrees. Values above 3.99° are treated as a high-attitude-error risk factor in this dataset.";
  if (s.includes("anomaly") || s.includes("caused")) {
    const { satellites } = await api.getAnomalies();
    const flagged = satellites.filter((s2) => s2.anomaly_status === "Anomaly");
    if (!flagged.length) return "No satellite is currently flagged as anomalous by the Isolation Forest detector.";
    return flagged.map((s2) => `${s2.id} is flagged Anomaly (score ${s2.anomaly_score}), health prediction ${s2.health_prediction}.`).join(" ");
  }

  const info = await api.getSystemInfo().catch(() => null);
  if (info) {
    return `System status: ${info.system_status}. ${info.active_alerts} active alert(s) across ${info.active_satellites} satellites. `
      + `Ask me about a specific satellite, parameter, alert or model and I'll pull the live value from the backend.`;
  }
  return "I monitor live telemetry, anomaly detections, prioritised alerts and model performance for SAT-01 and SAT-02. Ask me about a specific satellite, parameter, alert or model.";
}

/* ---------------- tiny chart helper (Chart.js is loaded by each page) ---------------- */
/* Chart.js is bundled locally at frontend/vendor/chart.umd.js (no CDN,
   no internet connection required). If it's somehow still missing,
   show a visible message in the chart's container instead of leaving
   it silently blank. */
function chartOrFallback(canvasId, buildFn) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  if (typeof Chart === "undefined") {
    canvas.outerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;font-size:.7rem;color:var(--muted-foreground);text-align:center;padding:0 1rem">
      Chart.js failed to load (vendor/chart.umd.js missing or blocked). Charts are unavailable, but live data is still working.
    </div>`;
    return null;
  }
  try {
    return buildFn(canvas);
  } catch (e) {
    console.error("Chart render failed for", canvasId, e);
    return null;
  }
}

function chartTheme() {
  return {
    grid: "rgba(148,163,184,0.18)",
    text: "#9aa5b8",
  };
}
