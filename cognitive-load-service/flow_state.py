"""
Flow State Protection Window — Addition 3 (Claim 5)

When CLS has been continuously LOW for a sustained, configurable period,
this controller activates a 'Flow State Lock' that unconditionally defers
all HIGH-Dk tasks regardless of instantaneous hardware availability.

PATENT NOTE (Claim 5):
    The mechanism introduces the concept of 'accumulated flow credit' — a
    monotonically increasing value representing sustained cognitive focus
    time that the system protects.  Unlike reactive schedulers (prior art),
    this controller is *proactive*: it accumulates evidence of deep work and
    guards it unconditionally.  No prior art found combines:
      (a) sustained low-CLS duration as a scheduling axis
      (b) unconditional HIGH-Dk deferral irrespective of hardware state
      (c) a configurable credit threshold (making the mechanism general-purpose)

    The configurable threshold (FLOW_STATE_THRESHOLD) is critical — the patent
    claims the *mechanism*, not a specific value.  Dashboard configurability
    demonstrates the invention is a reusable controller, not a hardcoded rule.

FLOW CREDIT ACCUMULATION:
    credit(t+1) = credit(t) + 1.0         when state == LOW
    credit(t+1) = credit(t) * DECAY_RATE  when state != LOW

    Lock activates when streak >= THRESHOLD (not credit, streak is the counter).
    Credit is a separate floating-point metric used for analytics + Claim 5 evidence.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class FlowStateController:
    """
    Tracks per-user consecutive LOW-state window count in Redis.
    In-memory cache used for latency; Redis for persistence across restarts.
    """

    def __init__(self, threshold: int, decay_rate: float = 0.95):
        self.threshold  = threshold
        self.decay_rate = decay_rate
        # In-memory shadow (Redis is source of truth via update())
        self._streak: dict[str, int]   = {}
        self._credit: dict[str, float] = {}
        self._locked: dict[str, bool]  = {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def update(
        self,
        user_id:  str,
        state:    str,
        redis,
        db,
    ) -> dict:
        """
        Process a new CLS state for a user. Updates streak, credit and lock.
        Returns a dict with flow state metadata to embed in the CLS response.
        """
        streak_key = f"flow_streak:{user_id}"
        credit_key = f"flow_credit:{user_id}"

        # Read current values from Redis
        streak = int((await redis.get(streak_key)) or 0)
        credit = float((await redis.get(credit_key)) or 0.0)

        was_locked = self._locked.get(user_id, False)

        if state == "LOW":
            streak += 1
            credit += 1.0
        else:
            streak  = 0
            credit  = credit * self.decay_rate

        # Activate or deactivate lock
        locked = streak >= self.threshold

        # Detect transitions for logging
        if locked and not was_locked:
            await self._log_transition(user_id, "entered", streak, credit, db)
            logger.info("FLOW LOCK ACTIVATED: user=%s streak=%d", user_id, streak)
        elif was_locked and not locked:
            await self._log_transition(user_id, "exited", streak, credit, db)
            logger.info("FLOW LOCK RELEASED: user=%s", user_id)

        # Write back to Redis
        await redis.set(streak_key, streak, ex=3600)
        await redis.set(credit_key, round(credit, 4), ex=3600)

        # Update in-memory shadow
        self._streak[user_id] = streak
        self._credit[user_id] = credit
        self._locked[user_id] = locked

        return {
            "flow_state_locked":      locked,
            "flow_streak":            streak,
            "accumulated_flow_credit": round(credit, 4),
            "threshold":              self.threshold,
        }

    def is_flow_locked(self, user_id: str) -> bool:
        """Return current flow lock status from in-memory cache."""
        return self._locked.get(user_id, False)

    async def set_threshold(self, new_threshold: int, redis) -> None:
        """
        Update the flow lock threshold at runtime (dashboard-configurable).
        Persists the new value in Redis so it survives service restarts.
        """
        self.threshold = new_threshold
        await redis.set("flow_threshold_global", new_threshold)
        logger.info("Flow state threshold updated to %d windows", new_threshold)

    async def load_threshold(self, redis) -> None:
        """Restore threshold from Redis on startup."""
        stored = await redis.get("flow_threshold_global")
        if stored:
            self.threshold = int(stored)

    def reset(self, user_id: str) -> None:
        self._streak.pop(user_id, None)
        self._credit.pop(user_id, None)
        self._locked.pop(user_id, None)

    # ── Private ───────────────────────────────────────────────────────────────

    async def _log_transition(
        self,
        user_id:    str,
        event_type: str,   # 'entered' | 'exited'
        streak:     int,
        credit:     float,
        db,
    ) -> None:
        if db is None:
            return
        try:
            await db.flow_state_log.insert_one({
                "user_id":                 user_id,
                "event":                   event_type,
                "streak_at_transition":    streak,
                "accumulated_flow_credit": round(credit, 4),
                "threshold_used":          self.threshold,
                "timestamp":               datetime.utcnow().isoformat(),
            })
        except Exception:
            pass
