"""
history_service.py

Keeps a rolling in-memory history of telemetry + predictions per
satellite so the Monitoring and Anomalies pages can draw charts and
tables without re-reading the CSV on every request.

This is intentionally simple in-memory state (a Python list per
satellite, capped at HISTORY_MAX_LENGTH) rather than an external
database, per the project's requirement to run entirely locally
without any external DB service.
"""

from collections import defaultdict
import threading

import config

_lock = threading.Lock()
_history = defaultdict(list)


def record(sat_id, row_idx, telemetry, prediction, timestamp):
    entry = {
        "row": row_idx,
        "timestamp": timestamp,
        "telemetry": dict(telemetry),
        "prediction": dict(prediction),
    }
    with _lock:
        _history[sat_id].append(entry)
        if len(_history[sat_id]) > config.HISTORY_MAX_LENGTH:
            _history[sat_id] = _history[sat_id][-config.HISTORY_MAX_LENGTH:]


def get_history(sat_id, limit=100):
    with _lock:
        items = list(_history[sat_id])
    if limit:
        items = items[-limit:]
    return items


def get_parameter_history(sat_id, parameter, limit=100):
    items = get_history(sat_id, limit)
    return [
        {
            "timestamp": e["timestamp"],
            "value": e["telemetry"].get(parameter),
            "anomaly_status": e["prediction"].get("anomaly_status"),
        }
        for e in items
    ]
