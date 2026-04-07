from typing import Dict, List

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


def compute_predictive_cls(recent_scores: List[float]) -> dict:
    """
    Use mathematical trend-line of recent rolling windows to predict near-future CLS state.
    """
    if len(recent_scores) < 3:
        return {"predicted_cls": recent_scores[-1] if recent_scores else 0.0, "probability_high": 0.0}
    
    # Simple derivative trend
    delta = recent_scores[-1] - recent_scores[0]
    trend = delta / len(recent_scores)
    
    # Predict ~3 steps into the future
    predicted = min(1.0, max(0.0, recent_scores[-1] + (trend * 3)))
    
    prob_high = 0.0
    if predicted >= 0.70:
        prob_high = 0.8 + min(0.2, (predicted - 0.70) * 0.5)
    elif predicted >= 0.50:
        prob_high = (predicted - 0.50) / 0.20 * 0.8
        
    return {
        "predicted_cls": round(predicted, 4),
        "probability_high": round(prob_high, 4)
    }
