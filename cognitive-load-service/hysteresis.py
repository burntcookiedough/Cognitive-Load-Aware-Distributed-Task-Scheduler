from typing import Dict


# Hysteresis transition rules.
# Each entry: (from_state, to_state) → (score_threshold, consecutive_windows_required)
RULES = {
    ("LOW",    "MEDIUM"): (0.45, 2),
    ("MEDIUM", "HIGH"):   (0.75, 2),
    ("HIGH",   "MEDIUM"): (0.65, 3),   # note: must DROP below this
    ("MEDIUM", "LOW"):    (0.35, 3),   # note: must DROP below this
    # Cross-skip shortcuts (emergency transitions)
    ("LOW",  "HIGH"):  (0.80, 2),
    ("HIGH", "LOW"):   (0.25, 4),
}

# Whether the transition fires when score EXCEEDS or FALLS BELOW the threshold
DIRECTION = {
    ("LOW",    "MEDIUM"): "above",
    ("MEDIUM", "HIGH"):   "above",
    ("HIGH",   "MEDIUM"): "below",
    ("MEDIUM", "LOW"):    "below",
    ("LOW",    "HIGH"):   "above",
    ("HIGH",   "LOW"):    "below",
}


class HysteresisController:
    """
    State machine that prevents rapid flickering between CLS states.
    A state transition only occurs after the score crosses a threshold
    for N consecutive windows.
    """

    def __init__(self):
        # user_id → {"state": str, "pending": str|None, "count": int}
        self._users: Dict[str, Dict] = {}

    def _get(self, user_id: str) -> Dict:
        if user_id not in self._users:
            self._users[user_id] = {"state": "LOW", "pending": None, "count": 0}
        return self._users[user_id]

    def _desired_state(self, current: str, score: float) -> str:
        """Determine raw desired state purely from score thresholds."""
        if score >= 0.75:
            return "HIGH"
        if score >= 0.45:
            return "MEDIUM"
        return "LOW"

    def update(self, user_id: str, cls_score: float) -> str:
        """
        Process a new CLS score for a user and return the (possibly unchanged)
        stable state after applying hysteresis.
        """
        s = self._get(user_id)
        current = s["state"]
        desired = self._desired_state(current, cls_score)

        if desired == current:
            # Score consistent with current state — reset pending counter
            s["pending"] = None
            s["count"]   = 0
            return current

        # Check if a transition rule exists
        rule_key = (current, desired)
        if rule_key not in RULES:
            # No direct rule; stay in current state
            return current

        threshold, required = RULES[rule_key]
        direction           = DIRECTION[rule_key]

        # Verify the score actually crosses the threshold in the right direction
        qualifies = (direction == "above" and cls_score >= threshold) or \
                    (direction == "below" and cls_score <= threshold)

        if not qualifies:
            s["pending"] = None
            s["count"]   = 0
            return current

        if s["pending"] == desired:
            s["count"] += 1
        else:
            s["pending"] = desired
            s["count"]   = 1

        if s["count"] >= required:
            s["state"]   = desired
            s["pending"] = None
            s["count"]   = 0

        return s["state"]

    def get_state(self, user_id: str) -> str:
        return self._get(user_id)["state"]

    def reset(self, user_id: str):
        if user_id in self._users:
            del self._users[user_id]
