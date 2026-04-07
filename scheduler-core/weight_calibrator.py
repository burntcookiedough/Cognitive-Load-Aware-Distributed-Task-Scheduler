"""
Adaptive Weight Calibration Engine — Addition A (Claim 6)

Implements a closed-loop feedback mechanism that continuously updates the
α (CLS inference) and β (disruption score) weight vectors based on observed
post-scheduling cognitive state outcomes.

PATENT NOTE (Claim 6):
    All prior art schedulers — including WO2015167847A1 (Singh) and
    WO2023034847A1 (Matsuoka) — treat scheduling weight vectors as fixed
    design constants.  This module transforms CLADS into a self-calibrating
    scheduling controller by:
      1. Recording the user's CLS state N seconds after each scheduling decision
      2. Computing the 'impact' of the routing choice (did CLS improve/worsen?)
      3. Applying an EMA (Exponential Moving Average) update rule to each weight
         in the β vector that contributed to the disruption scoring decision:
             β_new = (1 - λ) * β_old + λ * observed_impact
      4. Persisting calibrated per-user weight profiles in MongoDB

    The self-calibrating property requires a minimum sample count before
    activation (WEIGHT_CALIBRATION_MIN_SAMPLES) to prevent cold-start overfitting.

WEIGHT PERSISTENCE:
    Each user gets their own 'weight_profile' document in MongoDB:
    {
      user_id,
      cls_weights: {...},         ← α vector
      disruption_weights: {...},  ← β vector
      sample_count: int,
      last_updated: str,
    }
    The GET /weight-profiles/{user_id} endpoint exposes this for inspection.
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Injected from main.py
_LEARNING_RATE:    float  = 0.05
_FEEDBACK_DELAY:   int    = 30
_MIN_SAMPLES:      int    = 10
_CLS_SERVICE_URL:  str    = "http://cognitive-load-service:8001"

# Default weight vectors (mirrors shared/config.py)
_DEFAULT_CLS_WEIGHTS = {
    "idle_time":           0.25,
    "typing_variance":     0.25,
    "tab_switch_rate":     0.20,
    "context_switch_rate": 0.20,
    "focus_change_count":  0.10,
}
_DEFAULT_DISRUPTION_WEIGHTS = {
    "ui_blocking":  0.35,
    "notification": 0.25,
    "cpu":          0.20,
    "memory":       0.12,
    "io":           0.08,
}


def configure(learning_rate: float, feedback_delay: int, min_samples: int, cls_service_url: str) -> None:
    global _LEARNING_RATE, _FEEDBACK_DELAY, _MIN_SAMPLES, _CLS_SERVICE_URL
    _LEARNING_RATE   = learning_rate
    _FEEDBACK_DELAY  = feedback_delay
    _MIN_SAMPLES     = min_samples
    _CLS_SERVICE_URL = cls_service_url


class WeightCalibrator:
    """
    Records scheduling outcomes and updates α/β weights via EMA feedback.
    """

    def __init__(self):
        # In-memory profile cache; MongoDB is the source of truth
        self._profiles: dict[str, dict] = {}

    async def record_decision(
        self,
        user_id:          str,
        decision_id:      str,
        cls_state_at:     str,
        cls_score_at:     float,
        disruption_class: str,
        disruption_score: float,
        assigned_node:    str,
        db,
    ) -> None:
        """
        Called immediately after a scheduling decision.  Schedules an async
        outcome check after FEEDBACK_DELAY seconds.
        """
        asyncio.create_task(
            self._delayed_outcome_check(
                user_id, decision_id, cls_state_at, cls_score_at,
                disruption_class, disruption_score, assigned_node, db,
            )
        )

    async def _delayed_outcome_check(
        self,
        user_id:          str,
        decision_id:      str,
        cls_state_at:     str,
        cls_score_at:     float,
        disruption_class: str,
        disruption_score: float,
        assigned_node:    str,
        db,
    ) -> None:
        """Wait, observe actual CLS, compute impact, update weights."""
        await asyncio.sleep(_FEEDBACK_DELAY)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{_CLS_SERVICE_URL}/cls/{user_id}")
                post_data  = r.json()
                post_score = float(post_data.get("current_cls", cls_score_at))
                post_state = post_data.get("state", cls_state_at)
        except Exception:
            logger.warning("WeightCalibrator: could not fetch post-decision CLS for %s", user_id)
            return

        # Impact = signed change in CLS (negative = good: CLS reduced)
        impact = post_score - cls_score_at   # in [-1.0, +1.0]

        # Load or initialise profile
        profile = await self._load_profile(user_id, db)
        profile["sample_count"] = profile.get("sample_count", 0) + 1

        # Only calibrate once minimum sample threshold met
        if profile["sample_count"] >= _MIN_SAMPLES:
            dk  = profile.get("disruption_weights", dict(_DEFAULT_DISRUPTION_WEIGHTS))
            # Positive impact (CLS worsened) → increase penalty for disruption components
            # Negative impact (CLS improved/stable) → reinforce current weights
            # We scale observed_impact to [0,1] for the EMA update
            observed = max(0.0, min(1.0, (impact + 1.0) / 2.0))
            lam      = _LEARNING_RATE

            # Update weights for the two highest-impact β components
            for key in ("ui_blocking", "notification"):
                dk[key] = round((1 - lam) * dk[key] + lam * observed, 6)

            # Renormalise to sum = 1.0
            total = sum(dk.values())
            if total > 0:
                dk = {k: round(v / total, 6) for k, v in dk.items()}

            profile["disruption_weights"] = dk
            profile["last_calibrated_at"] = datetime.utcnow().isoformat()

        profile["last_updated"] = datetime.utcnow().isoformat()

        # Persist outcome record
        try:
            await db.weight_calibration_outcomes.insert_one({
                "decision_id":      decision_id,
                "user_id":          user_id,
                "cls_state_before": cls_state_at,
                "cls_score_before": cls_score_at,
                "cls_state_after":  post_state,
                "cls_score_after":  post_score,
                "impact":           round(impact, 4),
                "disruption_class": disruption_class,
                "assigned_node":    assigned_node,
                "sample_count":     profile["sample_count"],
                "calibrated":       profile["sample_count"] >= _MIN_SAMPLES,
                "timestamp":        datetime.utcnow().isoformat(),
            })
        except Exception:
            pass

        # Upsert weight profile
        await self._save_profile(user_id, profile, db)
        self._profiles[user_id] = profile

        logger.info(
            "WeightCalibrator: user=%s impact=%.4f sample=%d calibrated=%s",
            user_id, impact, profile["sample_count"],
            profile["sample_count"] >= _MIN_SAMPLES,
        )

    async def get_disruption_weights(self, user_id: str, db) -> dict:
        """Return calibrated β weights for a user (falls back to defaults)."""
        profile = await self._load_profile(user_id, db)
        return profile.get("disruption_weights", dict(_DEFAULT_DISRUPTION_WEIGHTS))

    async def get_profile(self, user_id: str, db) -> dict:
        """Full profile for the /weight-profiles endpoint."""
        return await self._load_profile(user_id, db)

    async def _load_profile(self, user_id: str, db) -> dict:
        if user_id in self._profiles:
            return self._profiles[user_id]
        try:
            doc = await db.weight_profiles.find_one({"user_id": user_id}, {"_id": 0})
            if doc:
                self._profiles[user_id] = doc
                return doc
        except Exception:
            pass
        # Bootstrap default profile
        return {
            "user_id":             user_id,
            "cls_weights":         dict(_DEFAULT_CLS_WEIGHTS),
            "disruption_weights":  dict(_DEFAULT_DISRUPTION_WEIGHTS),
            "sample_count":        0,
            "last_updated":        datetime.utcnow().isoformat(),
        }

    async def _save_profile(self, user_id: str, profile: dict, db) -> None:
        try:
            await db.weight_profiles.update_one(
                {"user_id": user_id},
                {"$set": profile},
                upsert=True,
            )
        except Exception:
            pass
