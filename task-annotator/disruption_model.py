# β weights for disruption score — must sum to 1.0
DISRUPTION_WEIGHTS = {
    "ui_blocking": 0.35,
    "notification": 0.25,
    "cpu":          0.20,
    "memory":       0.12,
    "io":           0.08,
}


def compute_disruption_score(profile: dict) -> float:
    """
    Dk = β1·ui_blocking + β2·notification + β3·cpu + β4·memory + β5·io

    Returns a float in [0, 1].
    """
    score = (
        DISRUPTION_WEIGHTS["ui_blocking"] * profile.get("ui_blocking_factor", 0.0)
        + DISRUPTION_WEIGHTS["notification"] * profile.get("notification_factor", 0.0)
        + DISRUPTION_WEIGHTS["cpu"] * profile.get("cpu_profile", 0.0)
        + DISRUPTION_WEIGHTS["memory"] * profile.get("mem_profile", 0.0)
        + DISRUPTION_WEIGHTS["io"] * profile.get("io_profile", 0.0)
    )
    return round(min(1.0, max(0.0, score)), 4)


def classify_disruption(score: float) -> str:
    """
    0.00–0.33 → LOW
    0.34–0.66 → MEDIUM
    0.67–1.00 → HIGH
    """
    if score <= 0.33:
        return "LOW"
    if score <= 0.66:
        return "MEDIUM"
    return "HIGH"
