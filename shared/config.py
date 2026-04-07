import os

# ─── Infrastructure ────────────────────────────────────────────────────────────
REDIS_URL   = os.getenv("REDIS_URL",    "redis://redis:6379")
MONGODB_URI = os.getenv("MONGODB_URI",  "mongodb://mongodb:27017")
MONGODB_DB  = "clads"

# ─── Internal service URLs (Docker network) ────────────────────────────────────
COGNITIVE_LOAD_URL  = os.getenv("COGNITIVE_LOAD_URL",  "http://cognitive-load-service:8001")
TASK_ANNOTATOR_URL  = os.getenv("TASK_ANNOTATOR_URL",  "http://task-annotator:8002")

NODE_URLS = {
    "node1": os.getenv("NODE1_URL", "http://node1:8011"),
    "node2": os.getenv("NODE2_URL", "http://node2:8012"),
    "node3": os.getenv("NODE3_URL", "http://node3:8013"),
}

# Node descriptive profiles (used by dashboard / docs)
NODE_PROFILES = {
    "node1": {"label": "Local",      "base_latency_ms": 20,  "role": "low_latency"},
    "node2": {"label": "Balanced",   "base_latency_ms": 85,  "role": "balanced"},
    "node3": {"label": "Background", "base_latency_ms": 120, "role": "remote"},
}

# ─── CLS weights (α) ───────────────────────────────────────────────────────────
# Must sum to 1.0
CLS_WEIGHTS = {
    "idle_time":          0.25,
    "typing_variance":    0.25,
    "tab_switch_rate":    0.20,
    "context_switch_rate":0.20,
    "focus_change_count": 0.10,
}

# ─── Disruption weights (β) ────────────────────────────────────────────────────
DISRUPTION_WEIGHTS = {
    "ui_blocking": 0.35,
    "notification": 0.25,
    "cpu":          0.20,
    "memory":       0.12,
    "io":           0.08,
}

# ─── Hysteresis settings ───────────────────────────────────────────────────────
HYSTERESIS = {
    "low_to_medium":  {"threshold": 0.45, "windows": 2},
    "medium_to_high": {"threshold": 0.75, "windows": 2},
    "high_to_medium": {"threshold": 0.65, "windows": 3},
    "medium_to_low":  {"threshold": 0.35, "windows": 3},
}

# ─── Rolling window ────────────────────────────────────────────────────────────
WINDOW_DURATION_SECONDS  = 60
WINDOW_UPDATE_INTERVAL   = 5
MAX_EVENTS_IN_WINDOW     = 20

# ─── Scheduler weights (w) ─────────────────────────────────────────────────────
SCHEDULER_WEIGHTS = {
    "cpu_availability":  0.30,
    "mem_availability":  0.25,
    "latency":           0.25,
    "disruption_penalty":0.15,
    "queue_penalty":     0.05,
}

# Feature normalisation ranges (min, max)
FEATURE_RANGES = {
    "typing_rate":          (0, 20),
    "typing_variance":      (0, 500),
    "idle_time":            (0, 60),
    "tab_switch_rate":      (0, 10),
    "context_switch_rate":  (0, 5),
    "focus_change_count":   (0, 5),
}
