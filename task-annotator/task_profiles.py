# Task profiles – defines resource and disruption characteristics per task type.
# All weight fields are in [0.0, 1.0].

TASK_PROFILES = {
    # ── HIGH-disruption tasks ──────────────────────────────────────────────────
    "build": {
        "cpu_profile":           0.85,
        "mem_profile":           0.70,
        "io_profile":            0.60,
        "ui_blocking_factor":    0.90,
        "notification_factor":   0.80,
        "latency_sla_ms":        10_000,
        "execution_time_ms":     8_000,
        "is_migratable":         True,
        "category":              "HIGH",
        "urgency_class":         "standard",
        "checkpoint_size_mb":    150,
        "transfer_cost_ms":      1200,
        "resume_penalty_ms":     500,
        "phases": [
            {"name": "dependency_resolution", "duration_ms": 2000, "cpu_profile": 0.3, "is_safe_checkpoint": True},
            {"name": "compile", "duration_ms": 5000, "cpu_profile": 0.95, "is_safe_checkpoint": False},
            {"name": "packaging", "duration_ms": 1000, "cpu_profile": 0.4, "is_safe_checkpoint": True},
        ]
    },
    "deploy": {
        "cpu_profile":           0.75,
        "mem_profile":           0.55,
        "io_profile":            0.80,
        "ui_blocking_factor":    0.95,
        "notification_factor":   0.90,
        "latency_sla_ms":        15_000,
        "execution_time_ms":     10_000,
        "is_migratable":         False,
        "category":              "HIGH",
        "urgency_class":         "high",
        "checkpoint_size_mb":    0,
        "transfer_cost_ms":      0,
        "resume_penalty_ms":     0,
        "phases": [
            {"name": "upload", "duration_ms": 4000, "cpu_profile": 0.2, "is_safe_checkpoint": False},
            {"name": "restart_services", "duration_ms": 6000, "cpu_profile": 0.8, "is_safe_checkpoint": False},
        ]
    },
    "dependency_install": {
        "cpu_profile":           0.50,
        "mem_profile":           0.40,
        "io_profile":            0.85,
        "ui_blocking_factor":    0.60,
        "notification_factor":   0.70,
        "latency_sla_ms":        20_000,
        "execution_time_ms":     12_000,
        "is_migratable":         True,
        "category":              "HIGH",
        "urgency_class":         "low",
        "checkpoint_size_mb":    50,
        "transfer_cost_ms":      400,
        "resume_penalty_ms":     200,
        "phases": [
            {"name": "download", "duration_ms": 6000, "cpu_profile": 0.2, "is_safe_checkpoint": True},
            {"name": "extract", "duration_ms": 6000, "cpu_profile": 0.8, "is_safe_checkpoint": False},
        ]
    },
    # ── MEDIUM-disruption tasks ────────────────────────────────────────────────
    "test_run": {
        "cpu_profile":           0.60,
        "mem_profile":           0.45,
        "io_profile":            0.30,
        "ui_blocking_factor":    0.70,
        "notification_factor":   0.60,
        "latency_sla_ms":        6_000,
        "execution_time_ms":     5_000,
        "is_migratable":         True,
        "category":              "MEDIUM",
        "urgency_class":         "standard",
        "checkpoint_size_mb":    80,
        "transfer_cost_ms":      600,
        "resume_penalty_ms":     300,
        "phases": [
            {"name": "setup", "duration_ms": 1000, "cpu_profile": 0.4, "is_safe_checkpoint": True},
            {"name": "run", "duration_ms": 3000, "cpu_profile": 0.7, "is_safe_checkpoint": False},
            {"name": "teardown", "duration_ms": 1000, "cpu_profile": 0.2, "is_safe_checkpoint": True},
        ]
    },
    "ai_request": {
        "cpu_profile":           0.70,
        "mem_profile":           0.65,
        "io_profile":            0.40,
        "ui_blocking_factor":    0.80,
        "notification_factor":   0.50,
        "latency_sla_ms":        8_000,
        "execution_time_ms":     4_000,
        "is_migratable":         True,
        "category":              "MEDIUM",
        "urgency_class":         "high",
        "checkpoint_size_mb":    20,
        "transfer_cost_ms":      150,
        "resume_penalty_ms":     50,
        "phases": [
            {"name": "tokenize", "duration_ms": 500, "cpu_profile": 0.5, "is_safe_checkpoint": True},
            {"name": "inference", "duration_ms": 3000, "cpu_profile": 0.9, "is_safe_checkpoint": False},
            {"name": "format", "duration_ms": 500, "cpu_profile": 0.2, "is_safe_checkpoint": True},
        ]
    },
    "static_analysis": {
        "cpu_profile":           0.45,
        "mem_profile":           0.30,
        "io_profile":            0.35,
        "ui_blocking_factor":    0.40,
        "notification_factor":   0.40,
        "latency_sla_ms":        4_000,
        "execution_time_ms":     3_000,
        "is_migratable":         True,
        "category":              "MEDIUM",
        "urgency_class":         "low",
        "checkpoint_size_mb":    40,
        "transfer_cost_ms":      300,
        "resume_penalty_ms":     100,
        "phases": [
            {"name": "parse", "duration_ms": 1000, "cpu_profile": 0.6, "is_safe_checkpoint": True},
            {"name": "analyze", "duration_ms": 2000, "cpu_profile": 0.5, "is_safe_checkpoint": False},
        ]
    },
    # ── LOW-disruption tasks ───────────────────────────────────────────────────
    "lint": {
        "cpu_profile":           0.30,
        "mem_profile":           0.20,
        "io_profile":            0.25,
        "ui_blocking_factor":    0.20,
        "notification_factor":   0.30,
        "latency_sla_ms":        3_000,
        "execution_time_ms":     2_000,
        "is_migratable":         False,
        "category":              "LOW",
        "urgency_class":         "standard",
        "checkpoint_size_mb":    0,
        "transfer_cost_ms":      0,
        "resume_penalty_ms":     0,
        "phases": [
            {"name": "eval", "duration_ms": 2000, "cpu_profile": 0.3, "is_safe_checkpoint": False},
        ]
    },
    "indexing": {
        "cpu_profile":           0.40,
        "mem_profile":           0.35,
        "io_profile":            0.70,
        "ui_blocking_factor":    0.15,
        "notification_factor":   0.10,
        "latency_sla_ms":        5_000,
        "execution_time_ms":     3_000,
        "is_migratable":         True,
        "category":              "LOW",
        "urgency_class":         "low",
        "checkpoint_size_mb":    200,
        "transfer_cost_ms":      1500,
        "resume_penalty_ms":     600,
        "phases": [
            {"name": "scan", "duration_ms": 1000, "cpu_profile": 0.2, "is_safe_checkpoint": True},
            {"name": "index", "duration_ms": 2000, "cpu_profile": 0.6, "is_safe_checkpoint": False},
        ]
    },
    "autosave": {
        "cpu_profile":           0.10,
        "mem_profile":           0.05,
        "io_profile":            0.30,
        "ui_blocking_factor":    0.05,
        "notification_factor":   0.05,
        "latency_sla_ms":        1_000,
        "execution_time_ms":     500,
        "is_migratable":         False,
        "category":              "LOW",
        "urgency_class":         "high",
        "checkpoint_size_mb":    0,
        "transfer_cost_ms":      0,
        "resume_penalty_ms":     0,
        "phases": [
            {"name": "save", "duration_ms": 500, "cpu_profile": 0.1, "is_safe_checkpoint": False},
        ]
    },
}

# Default fallback if task_type is unknown
DEFAULT_PROFILE = {
    "cpu_profile":           0.50,
    "mem_profile":           0.40,
    "io_profile":            0.40,
    "ui_blocking_factor":    0.50,
    "notification_factor":   0.50,
    "latency_sla_ms":        5_000,
    "execution_time_ms":     3_000,
    "is_migratable":         True,
    "category":              "MEDIUM",
    "urgency_class":         "standard",
    "checkpoint_size_mb":    50,
    "transfer_cost_ms":      400,
    "resume_penalty_ms":     200,
    "phases": [
        {"name": "execute", "duration_ms": 3000, "cpu_profile": 0.5, "is_safe_checkpoint": True},
    ]
}
