from typing import List, Dict
import numpy as np


def extract_features(events: List[Dict]) -> Dict[str, float]:
    """
    Extract CLS-relevant features from a rolling window of telemetry events.

    Returns:
        typing_rate          – average keystrokes per event window
        typing_variance      – variance of inter-key intervals (ms)
        idle_time            – average idle seconds per window
        tab_switch_rate      – average tab-switch events per window
        context_switch_rate  – average context-switch events per window
        focus_change_count   – average focus change events per window
    """
    if not events:
        return {
            "typing_rate":          0.0,
            "typing_variance":      0.0,
            "idle_time":            0.0,
            "tab_switch_rate":      0.0,
            "context_switch_rate":  0.0,
            "focus_change_count":   0.0,
        }

    n = len(events)

    typing_rate = sum(e.get("keystrokes", 0) for e in events) / n

    intervals = [e.get("avg_inter_key_interval", 0.0) for e in events]
    typing_variance = float(np.var(intervals)) if intervals else 0.0

    idle_time          = sum(e.get("idle_duration",   0.0) for e in events) / n
    tab_switch_rate    = sum(e.get("tab_switches",    0)   for e in events) / n
    context_switch_rate= sum(e.get("context_switches",0)   for e in events) / n
    focus_change_count = sum(e.get("focus_changes",   0)   for e in events) / n

    return {
        "typing_rate":          round(typing_rate, 4),
        "typing_variance":      round(typing_variance, 4),
        "idle_time":            round(idle_time, 4),
        "tab_switch_rate":      round(tab_switch_rate, 4),
        "context_switch_rate":  round(context_switch_rate, 4),
        "focus_change_count":   round(focus_change_count, 4),
    }
