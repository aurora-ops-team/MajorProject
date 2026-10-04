"""
simulation_service.py

Owns the "live" telemetry feed for both satellites.

- Loads satellite_1_telemetry.csv / satellite_2_telemetry.csv once at
  startup.
- Maintains a current row index per satellite.
- A background thread advances both satellites by one row every
  TELEMETRY_INTERVAL_SECONDS, wrapping back to row 0 at the end of the
  file so the demo runs indefinitely.
- The backend is the single source of truth: the browser only ever
  reads /api/... endpoints and never advances the row itself, so every
  page and every connected client sees the exact same telemetry at the
  exact same time.
"""

import threading
import time
from datetime import datetime, timezone

import pandas as pd

import config
from services import prediction_service, anomaly_service, decision_service, alert_service, history_service


class SimulationService:
    def __init__(self):
        self._lock = threading.Lock()
        self._frames = {}
        for sat_id, path in config.SATELLITE_CSV.items():
            df = pd.read_csv(path)
            self._frames[sat_id] = df

        self.state = {
            sat_id: {
                "current_row": 0,
                "telemetry": {},
                "prediction": {},
                "last_updated": None,
            }
            for sat_id in config.SATELLITE_CSV
        }

        self._started = False
        self._thread = None

    # ------------------------------------------------------------------
    def _row_to_telemetry(self, sat_id, row_idx):
        df = self._frames[sat_id]
        row = df.iloc[row_idx % len(df)]
        telemetry = {feat: float(row[feat]) for feat in config.FEATURE_ORDER}
        # thermal_control_status is a 0/1 flag, keep it as an int
        telemetry["thermal_control_status"] = int(row["thermal_control_status"])
        return telemetry

    def _process_row(self, sat_id):
        row_idx = self.state[sat_id]["current_row"]
        telemetry = self._row_to_telemetry(sat_id, row_idx)

        health = prediction_service.predict_health(telemetry)
        anomaly = anomaly_service.predict_anomaly(telemetry)
        decision = decision_service.decide(health, anomaly)

        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self.state[sat_id]["telemetry"] = telemetry
            self.state[sat_id]["prediction"] = {
                **health,
                **anomaly,
                **decision,
            }
            self.state[sat_id]["last_updated"] = now

        history_service.record(sat_id, row_idx, telemetry, self.state[sat_id]["prediction"], now)
        alert_service.evaluate(sat_id, telemetry, self.state[sat_id]["prediction"], now)

    def _advance(self):
        for sat_id in self.state:
            self._process_row(sat_id)
            with self._lock:
                self.state[sat_id]["current_row"] = (self.state[sat_id]["current_row"] + 1) % len(self._frames[sat_id])

    def _loop(self):
        while True:
            time.sleep(config.TELEMETRY_INTERVAL_SECONDS)
            self._advance()

    # ------------------------------------------------------------------
    def start(self):
        """Process row 0 immediately, then advance every 30s in the background."""
        if self._started:
            return
        self._started = True
        for sat_id in self.state:
            self._process_row(sat_id)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def get_satellite_state(self, sat_id):
        with self._lock:
            return {
                "id": sat_id,
                "current_row": self.state[sat_id]["current_row"],
                "telemetry": dict(self.state[sat_id]["telemetry"]),
                "prediction": dict(self.state[sat_id]["prediction"]),
                "last_updated": self.state[sat_id]["last_updated"],
            }

    def get_all_states(self):
        return {sat_id: self.get_satellite_state(sat_id) for sat_id in self.state}

    def row_count(self, sat_id):
        return len(self._frames[sat_id])


simulation = SimulationService()
