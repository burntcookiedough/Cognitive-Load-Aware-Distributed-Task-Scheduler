from datetime import datetime


def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def minmax_norm(value: float, min_val: float, max_val: float) -> float:
    if max_val == min_val:
        return 0.0
    return clamp((value - min_val) / (max_val - min_val))


def disruption_to_class(score: float) -> str:
    if score <= 0.33:
        return "LOW"
    elif score <= 0.66:
        return "MEDIUM"
    return "HIGH"


def cls_to_class(score: float) -> str:
    if score < 0.40:
        return "LOW"
    elif score < 0.70:
        return "MEDIUM"
    return "HIGH"
