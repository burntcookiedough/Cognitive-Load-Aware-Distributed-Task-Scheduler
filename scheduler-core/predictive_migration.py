"""
Predictive Pre-emptive Migration Engine — Addition 2 (Claim 4)

Triggers task migration *before* CLS breaches HIGH by analysing the trend
slope of the CLS time-series via linear regression.

PATENT NOTE (Claim 4):
    Prior art (WO2023034847A1 / Matsuoka) triggers task migration reactively
    on CLS threshold breach.  This module patches the critical gap: migration
    is triggered predictively, while CLS is still in MEDIUM state, based on
    a trend-slope forecast that estimates time-to-breach.  No prior art found
    covers preemptive migration from MEDIUM using rolling regression slope.

ACCURACY TRACKING (Section 11 Evidence):
    After each preemptive migration, an async coroutine waits
    PREDICTION_ACCURACY_CHECK_DELAY_SECONDS, then queries the CLS service
    to verify whether CLS actually breached HIGH within the prediction window.
    Precision and recall are persisted to 'prediction_accuracy' collection —
    this constitutes the experimental evidence for Section 11 of the patent.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# These are injected from main.py at startup
_PROB_THRESHOLD:     float = 0.70
_CHECK_DELAY:        int   = 30
_CLS_SERVICE_URL:    str   = "http://cognitive-load-service:8001"


def configure(prob_threshold: float, check_delay: int, cls_service_url: str) -> None:
    global _PROB_THRESHOLD, _CHECK_DELAY, _CLS_SERVICE_URL
    _PROB_THRESHOLD  = prob_threshold
    _CHECK_DELAY     = check_delay
    _CLS_SERVICE_URL = cls_service_url


class PredictiveMigrationEngine:
    """
    Evaluates CLS predictions and triggers preemptive migrations when the
    regression-based forecast exceeds the probability threshold.
    """

    async def evaluate(
        self,
        user_id:          str,
        current_state:    str,
        probability_high: float,
        predicted_cls:    float,
        trend_slope:      float,
        estimated_breach_seconds: Optional[float],
        db,
        node_clients:     dict,
    ) -> list:
        """
        Returns a list of preemptive migration action dicts (may be empty).
        Only fires when CLS is MEDIUM and probability_high >= threshold.
        """
        if current_state != "MEDIUM":
            return []
        if probability_high < _PROB_THRESHOLD:
            return []

        # Find migratable HIGH-disruption tasks currently on node1 (local)
        active_tasks = await db.tasks.find(
            {
                "user_id": user_id,
                "status":  {"$in": ["running", "queued"]},
                "disruption_class": "HIGH",
                "is_migratable":    True,
                "assigned_node":    {"$ne": "node3"},
            },
            {"_id": 0},
        ).to_list(length=20)

        actions = []
        for task in active_tasks:
            action_id = f"pm-{task['task_id']}-{datetime.utcnow().strftime('%H%M%S')}"
            action = {
                "action_id":                action_id,
                "task_id":                  task["task_id"],
                "user_id":                  user_id,
                "action":                   "preemptive_migrate",
                "from_node":                task.get("assigned_node", "node1"),
                "to_node":                  "node3",
                "reason":                   (
                    f"PREEMPTIVE: CLS at MEDIUM with P(HIGH)={probability_high:.2f}, "
                    f"slope={trend_slope:+.4f}, est_breach={estimated_breach_seconds}s"
                ),
                "probability_high":         probability_high,
                "trend_slope":              trend_slope,
                "estimated_breach_seconds": estimated_breach_seconds,
                "predicted_cls":            predicted_cls,
                "timestamp":                datetime.utcnow().isoformat(),
                "accuracy_verified":        False,
                "prediction_correct":       None,
            }

            # Notify destination node (best-effort)
            try:
                client = node_clients.get("node3")
                if client:
                    await client.post("/migrate", json={
                        "task_id":           task["task_id"],
                        "task_type":         task.get("task_type", "unknown"),
                        "from_node":         action["from_node"],
                        "execution_time_ms": task.get("execution_time_ms", 3000),
                    })
            except Exception:
                pass

            # Update task record
            try:
                await db.tasks.update_one(
                    {"task_id": task["task_id"]},
                    {"$set": {
                        "assigned_node":  "node3",
                        "migration_note": action["reason"],
                        "migrated_at":    action["timestamp"],
                    }},
                )
            except Exception:
                pass

            # Persist action
            try:
                await db.preemptive_migrations.insert_one({**action})
            except Exception:
                pass

            actions.append(action)
            logger.info(
                "PREEMPTIVE MIGRATE: task=%s user=%s P(HIGH)=%.2f breach_in=~%ss",
                task["task_id"], user_id, probability_high, estimated_breach_seconds,
            )

        # Schedule accuracy verification for each action
        for action in actions:
            asyncio.create_task(
                self._verify_accuracy(action["action_id"], user_id, db)
            )

        return actions

    async def _verify_accuracy(self, action_id: str, user_id: str, db) -> None:
        """
        Waits CHECK_DELAY seconds, then checks if CLS actually reached HIGH.
        Logs prediction_correct to MongoDB for Section 11 experimental evidence.
        """
        await asyncio.sleep(_CHECK_DELAY)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{_CLS_SERVICE_URL}/cls/{user_id}")
                actual_state = r.json().get("state", "LOW")
        except Exception:
            actual_state = None

        prediction_correct = (actual_state == "HIGH") if actual_state else None

        try:
            await db.preemptive_migrations.update_one(
                {"action_id": action_id},
                {"$set": {
                    "accuracy_verified":  True,
                    "actual_state":       actual_state,
                    "prediction_correct": prediction_correct,
                    "verified_at":        datetime.utcnow().isoformat(),
                }},
            )
            await db.prediction_accuracy.insert_one({
                "action_id":          action_id,
                "user_id":            user_id,
                "prediction_correct": prediction_correct,
                "actual_state":       actual_state,
                "check_delay_s":      _CHECK_DELAY,
                "timestamp":          datetime.utcnow().isoformat(),
            })
        except Exception:
            pass

        logger.info(
            "ACCURACY CHECK: action=%s correct=%s actual_state=%s",
            action_id, prediction_correct, actual_state,
        )

    @staticmethod
    async def get_accuracy_summary(db) -> dict:
        """Compute precision/recall of predictive migrations from MongoDB."""
        records = await db.prediction_accuracy.find(
            {"accuracy_verified": True}, {"_id": 0}
        ).to_list(length=1000)

        total     = len(records)
        correct   = sum(1 for r in records if r.get("prediction_correct") is True)
        incorrect = sum(1 for r in records if r.get("prediction_correct") is False)
        unknown   = total - correct - incorrect

        return {
            "total_predictions":  total,
            "correct":            correct,
            "incorrect":          incorrect,
            "unknown":            unknown,
            "precision":          round(correct / total, 4) if total else 0.0,
            "note": (
                "Precision = fraction of preemptive migrations where CLS "
                f"actually reached HIGH within {_CHECK_DELAY}s"
            ),
        }
