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
# PATENT NOTE (Claim 1): β₁(ui_blocking) + β₂(notification) intentionally exceed
# the sum of hardware weights β₃+β₄+β₅. This ordering is a deliberate inventive
# step — ranking human-perceptual disruption above hardware cost in the scheduling
# penalty vector. See disruption_model.py for invariant assertion.
DISRUPTION_WEIGHTS = {
    "ui_blocking":  0.35,   # β₁ — highest: directly interrupts user flow
    "notification": 0.25,   # β₂ — second: breaks attention via popup/alert
    "cpu":          0.20,   # β₃ — hardware cost (below perceptual sum)
    "memory":       0.12,   # β₄
    "io":           0.08,   # β₅
}

# ─── Hysteresis settings (Claim 3) ────────────────────────────────────────────
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

# ─── Addition 1: CPU Frequency Governor (Claim 2) ─────────────────────────────
# Maps CLS states to cpufreq governor policies and frequency constraints.
# In production: written to /sys/devices/system/cpu/cpuN/cpufreq/scaling_governor
# In simulation: structured directives logged to MongoDB cpu_governor_log.
CPU_GOVERNOR_POLICIES = {
    "LOW": {
        "governor":       "performance",
        "freq_min_mhz":   2400,
        "freq_max_mhz":   4200,
        "background_gov": "performance",
        "description":    "No CLS pressure — full performance on all threads",
    },
    "MEDIUM": {
        "governor":       "ondemand",
        "freq_min_mhz":   2000,
        "freq_max_mhz":   4200,
        "background_gov": "conservative",
        "description":    "Medium CLS — foreground boosted, background conserved",
    },
    "HIGH": {
        "governor":       "performance",   # foreground thread pinned at high freq
        "freq_min_mhz":   3200,
        "freq_max_mhz":   4200,
        "background_gov": "powersave",     # background workers throttled
        "description":    "High CLS — foreground protected, background throttled to powersave",
    },
}
CPU_GOVERNOR_REAL_SYSFS = os.getenv("REAL_GOVERNOR", "false").lower() == "true"
CPU_SYSFS_PATH_TEMPLATE = "/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"

# ─── Addition 2: Predictive Migration (Claim 4) ───────────────────────────────
PREEMPTIVE_MIGRATION_PROBABILITY_THRESHOLD = 0.70  # probability_high threshold
PREEMPTIVE_MIGRATION_REGRESSION_WINDOW     = 10    # CLS history points for polyfit
PREDICTION_ACCURACY_CHECK_DELAY_SECONDS    = 30    # delay before verifying prediction

# ─── Addition 3: Flow State Protection Window (Claim 5) ───────────────────────
# Number of consecutive LOW-CLS windows required to activate flow lock.
# At WINDOW_UPDATE_INTERVAL=5s, default 180 = 15 minutes of sustained focus.
# Configurable at runtime via PUT /flow-config endpoint.
FLOW_STATE_THRESHOLD         = int(os.getenv("FLOW_STATE_THRESHOLD", "180"))
FLOW_STATE_CREDIT_DECAY_RATE = 0.95   # per-window decay when not in LOW state

# ─── Addition A: Adaptive Weight Calibration (Claim 6) ────────────────────────
# EMA learning rate λ: β_new = (1-λ)*β_old + λ*observed_impact
# Lower λ = slower adaptation, more stable. 0.05 ≈ 20-window convergence horizon.
ADAPTIVE_WEIGHT_LEARNING_RATE   = 0.05
OUTCOMES_FEEDBACK_DELAY_SECONDS = 30   # wait N seconds then check post-scheduling CLS
WEIGHT_CALIBRATION_MIN_SAMPLES  = 10   # min decisions before calibration activates

# ─── Addition B: Latency Probe (Section 11 Evidence) ─────────────────────────
LATENCY_PROBE_ENABLED          = True
LATENCY_BENCHMARK_WINDOW       = 50   # rolling window for summary stats

# ─── Addition C: Multi-Tenant Team CLS Aggregator (Claim 7) ──────────────────
TEAM_CLS_CACHE_TTL_SECONDS  = 30    # Redis TTL for aggregate CLS snapshot
TEAM_CLS_ACTIVE_USER_WEIGHT = 2.0   # multiplier for users with keystrokes > 0
TEAM_CLS_IDLE_USER_WEIGHT   = 1.0   # weight for idle users
