from typing import Dict

# Fixed global min/max ranges for each feature.
# Calibrated to typical developer interaction patterns.
FEATURE_RANGES: Dict[str, tuple] = {
    "typing_rate":          (0.0,  20.0),
    "typing_variance":      (0.0, 500.0),
    "idle_time":            (0.0,  60.0),
    "tab_switch_rate":      (0.0,  10.0),
    "context_switch_rate":  (0.0,   5.0),
    "focus_change_count":   (0.0,   5.0),
}


def normalize(features: Dict[str, float]) -> Dict[str, float]:
    """
    Min-max normalise each feature to [0, 1] using calibrated global ranges.
    Higher values of idle_time, typing_variance, tab_switch_rate, etc. indicate
    higher cognitive disruption / load.
    """
    normalized: Dict[str, float] = {}
    for key, value in features.items():
        min_val, max_val = FEATURE_RANGES.get(key, (0.0, 1.0))
        if max_val == min_val:
            normalized[key] = 0.0
        else:
            norm = (value - min_val) / (max_val - min_val)
            normalized[key] = round(max(0.0, min(1.0, norm)), 4)
    return normalized
