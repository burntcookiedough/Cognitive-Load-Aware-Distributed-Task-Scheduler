from typing import Dict, List, Optional
import numpy as np

# α weights — must sum to 1.0
CLS_WEIGHTS: Dict[str, float] = {
    "idle_time":           0.25,
    "typing_variance":     0.25,
    "tab_switch_rate":     0.20,
    "context_switch_rate": 0.20,
    "focus_change_count":  0.10,
}

# Dummy baseline store for prototype (In production, load from DB)
USER_BASELINES = {
    "u_shagun": {
        "idle_time": 0.1,
        "typing_variance": 0.15,
        "tab_switch_rate": 0.05,
        "context_switch_rate": 0.05,
        "focus_change_count": 0.05,
    }
}

def apply_baseline_correction(user_id: str, normalized_features: Dict[str, float]) -> Dict[str, float]:
    """Adjust features against user's normal baseline drift."""
    baseline = USER_BASELINES.get(user_id, {})
    corrected = {}
    for k, v in normalized_features.items():
        base_val = baseline.get(k, 0.0)
        # Drift = current - baseline (bounded)
        # Re-scale so max is still ~1.0
        corrected[k] = min(1.0, max(0.0, (v - base_val) / (1.0 - base_val) if base_val < 1.0 else 0.0))
    return corrected

def compute_cls(user_id: str, normalized_features: Dict[str, float]) -> float:
    """
    Compute the Cognitive Load Score (CLS) as a weighted sum of
    normalised interaction signals, adjusted for personal baseline drift.
    """
    corrected_features = apply_baseline_correction(user_id, normalized_features)
    score = 0.0
    for feature, weight in CLS_WEIGHTS.items():
        score += weight * corrected_features.get(feature, 0.0)
    return round(min(1.0, max(0.0, score)), 4)


def compute_predictive_cls(
    recent_scores: List[float],
    regression_window: int = 10,
) -> dict:
    """
    PATENT NOTE (Claim 4): Trend-slope analysis over a rolling telemetry window
    to preemptively detect CLS breach before it occurs.

    Uses numpy polynomial regression (degree=1, i.e. linear regression via
    numpy.polyfit) over the last ``regression_window`` CLS samples to compute:
      - trend_slope:             rate of CLS change per window (units/window)
      - r_squared:               coefficient of determination of the fit
      - predicted_cls:           extrapolated CLS value 3 windows ahead
      - probability_high:        calibrated probability that predicted value
                                  will cross the HIGH threshold (≥0.75)
      - estimated_breach_seconds: estimated seconds until CLS reaches 0.75,
                                   given current slope and window interval (5s)

    This is consumed by PredictiveMigrationEngine in scheduler-core to trigger
    preemptive task migration while CLS is still MEDIUM.
    """
    n = len(recent_scores)
    if n < 3:
        return {
            "predicted_cls":           recent_scores[-1] if recent_scores else 0.0,
            "probability_high":        0.0,
            "trend_slope":             0.0,
            "r_squared":               0.0,
            "estimated_breach_seconds": None,
        }

    # Use the last regression_window points (or all if fewer available)
    window = recent_scores[-regression_window:]
    x = np.arange(len(window), dtype=float)
    y = np.array(window, dtype=float)

    # Linear regression: y = slope * x + intercept
    coeffs  = np.polyfit(x, y, deg=1)
    slope   = float(coeffs[0])
    intercept = float(coeffs[1])

    # R² = 1 - SS_res / SS_tot
    y_pred  = slope * x + intercept
    ss_res  = float(np.sum((y - y_pred) ** 2))
    ss_tot  = float(np.sum((y - np.mean(y)) ** 2))
    r_sq    = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-9 else 0.0

    # Predict 3 windows ahead
    predicted = float(slope * (len(window) + 3 - 1) + intercept)
    predicted = min(1.0, max(0.0, predicted))

    # Calibrated probability_high
    prob_high = 0.0
    if predicted >= 0.70:
        prob_high = 0.8 + min(0.2, (predicted - 0.70) * 0.5)
    elif predicted >= 0.50:
        prob_high = (predicted - 0.50) / 0.20 * 0.8

    # Estimate windows until CLS crosses 0.75 (HIGH threshold)
    estimated_breach_seconds: Optional[float] = None
    WINDOW_INTERVAL_SECONDS = 5
    HIGH_THRESHOLD = 0.75
    current_cls = window[-1]
    if slope > 0 and current_cls < HIGH_THRESHOLD:
        windows_to_breach = (HIGH_THRESHOLD - current_cls) / slope
        if 0 < windows_to_breach <= 200:
            estimated_breach_seconds = round(windows_to_breach * WINDOW_INTERVAL_SECONDS, 1)

    return {
        "predicted_cls":           round(predicted, 4),
        "probability_high":        round(prob_high, 4),
        "trend_slope":             round(slope, 6),
        "r_squared":               round(max(0.0, r_sq), 4),
        "estimated_breach_seconds": estimated_breach_seconds,
    }

