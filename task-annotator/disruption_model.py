"""
Disruption Score (Dk) Model — Addition 4 (Claim 1 — Patent Core)

PATENT NOTE (Claim 1):
    The DISRUPTION_WEIGHTS dict below implements the inventive step at the
    heart of CLADS's independent Claim 1:

        β₁(ui_blocking)  = 0.35   ←─ highest
        β₂(notification) = 0.25   ←─ second highest
        ─────────────────────────────
        β₃(cpu)          = 0.20   ←─ hardware cost starts here
        β₄(memory)       = 0.12
        β₅(io)           = 0.08

    The sum of human-perceptual weights (β₁ + β₂ = 0.60) is intentionally,
    deliberately, and invariantly greater than the sum of hardware weights
    (β₃ + β₄ + β₅ = 0.40).  This ordering is the novel scheduling principle:
    a task's HUMAN PERCEPTIBILITY is ranked above its hardware resource cost
    when computing the disruption penalty for node scoring.

    No prior art found (as of priority date) adopts this ordering.  Prior
    schedulers that incorporate cognitive context (WO2015167847A1, Singh;
    WO2023034847A1, Matsuoka) treat such weights as hardware-only or do not
    decompose the disruption vector at all.

    The invariant is enforced programmatically by vector_hierarchy_satisfied().
    A runtime assertion failure immediately signals that a configuration change
    has accidentally violated the patent's core claim.
"""

# β weights for disruption score — must sum to 1.0
# INVARIANT: β₁ + β₂  >  β₃ + β₄ + β₅  (human-perceptual > hardware)
DISRUPTION_WEIGHTS = {
    "ui_blocking":  0.35,   # β₁ — direct visual/input interrupt
    "notification": 0.25,   # β₂ — attention break via alert/popup
    "cpu":          0.20,   # β₃ — hardware cost
    "memory":       0.12,   # β₄
    "io":           0.08,   # β₅
}

# Human-perceptual weight axes (used in hierarchy check)
_PERCEPTUAL_AXES = {"ui_blocking", "notification"}
_HARDWARE_AXES   = {"cpu", "memory", "io"}


def vector_hierarchy_satisfied(weights: dict = None) -> bool:
    """
    Assert that the sum of human-perceptual weights exceeds hardware weights.
    This invariant is the patent's core Claim 1 scheduling principle.
    Returns True if satisfied; raises AssertionError if violated.
    """
    w = weights or DISRUPTION_WEIGHTS
    perceptual_sum = sum(w.get(k, 0.0) for k in _PERCEPTUAL_AXES)
    hardware_sum   = sum(w.get(k, 0.0) for k in _HARDWARE_AXES)
    satisfied      = perceptual_sum > hardware_sum
    assert satisfied, (
        f"PATENT INVARIANT VIOLATED: human-perceptual weight sum ({perceptual_sum:.3f}) "
        f"≤ hardware weight sum ({hardware_sum:.3f}). "
        f"This breaks Claim 1. Revert weight changes."
    )
    return satisfied


def compute_disruption_score(profile: dict, weights: dict = None) -> float:
    """
    Dk = β₁·ui_blocking + β₂·notification + β₃·cpu + β₄·memory + β₅·io

    Returns a scalar float in [0, 1].
    Use compute_disruption_vector() for the full per-component breakdown.
    """
    w = weights or DISRUPTION_WEIGHTS
    score = (
        w["ui_blocking"]  * profile.get("ui_blocking_factor",  0.0)
        + w["notification"] * profile.get("notification_factor", 0.0)
        + w["cpu"]          * profile.get("cpu_profile",         0.0)
        + w["memory"]       * profile.get("mem_profile",         0.0)
        + w["io"]           * profile.get("io_profile",          0.0)
    )
    return round(min(1.0, max(0.0, score)), 4)


def compute_disruption_vector(profile: dict, weights: dict = None) -> dict:
    """
    Returns the full per-component Dk vector showing each weight × factor
    contribution separately.  Used for patent evidence logging.

    Output format:
    {
      "ui_blocking_contribution":  float,   # β₁ × ui_blocking_factor
      "notification_contribution": float,   # β₂ × notification_factor
      "cpu_contribution":          float,   # β₃ × cpu_profile
      "memory_contribution":       float,   # β₄ × mem_profile
      "io_contribution":           float,   # β₅ × io_profile
      "perceptual_sum":            float,   # β₁ + β₂ components combined
      "hardware_sum":              float,   # β₃+β₄+β₅ components combined
      "hierarchy_satisfied":       bool,    # perceptual_sum > hardware_sum
      "total_dk":                  float,   # scalar sum = disruption_score
    }
    """
    w = weights or DISRUPTION_WEIGHTS
    ui_bl  = round(w["ui_blocking"]  * profile.get("ui_blocking_factor",  0.0), 6)
    notif  = round(w["notification"] * profile.get("notification_factor", 0.0), 6)
    cpu    = round(w["cpu"]          * profile.get("cpu_profile",         0.0), 6)
    mem    = round(w["memory"]       * profile.get("mem_profile",         0.0), 6)
    io     = round(w["io"]           * profile.get("io_profile",          0.0), 6)

    perceptual_sum = round(ui_bl + notif, 6)
    hardware_sum   = round(cpu + mem + io, 6)
    total          = round(min(1.0, perceptual_sum + hardware_sum), 4)

    return {
        "ui_blocking_contribution":  ui_bl,
        "notification_contribution": notif,
        "cpu_contribution":          cpu,
        "memory_contribution":       mem,
        "io_contribution":           io,
        "perceptual_sum":            perceptual_sum,
        "hardware_sum":              hardware_sum,
        "hierarchy_satisfied":       perceptual_sum > hardware_sum,
        "total_dk":                  total,
    }


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

