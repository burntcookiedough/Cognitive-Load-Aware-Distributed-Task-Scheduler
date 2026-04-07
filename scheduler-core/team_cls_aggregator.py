"""
Multi-Tenant TeamCLS Aggregator — Addition C (Claim 7)

Collects individual CLS states from all active users sharing a cluster and
computes a composite cluster-level cognitive index used for shared
infrastructure scheduling policy.

PATENT NOTE (Claim 7):
    No prior art found covers the combination of:
      (a) aggregating individual user CLS scores across concurrent users
      (b) weighting by user activity level (typing users > idle users)
      (c) applying cluster-wide HIGH-Dk deferral based on the composite index

    WO2015167847A1 (Singh) operates per-user only.
    WO2023034847A1 (Matsuoka) migrates tasks per-user only.
    Neither covers the extension to shared infrastructure decisions.

    The activity-weighted aggregation is deliberate: an idle user's LOW CLS
    should not dilute the aggregate when 3 active developers are at HIGH CLS.
    The weighted mean formula is:
      AggCLS = Σ_i (w_i * cls_i) / Σ_i w_i
    where w_i = ACTIVE_WEIGHT if user i has keystrokes > 0 in current window,
              = IDLE_WEIGHT otherwise.

CACHING:
    The aggregate is cached in Redis with a configurable TTL (default 30s)
    to avoid O(N_users) MongoDB queries on every scheduling request.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_TTL:         int   = 30
_ACTIVE_WEIGHT:     float = 2.0
_IDLE_WEIGHT:       float = 1.0
_TEAM_CLS_REDIS_KEY          = "team_cls:aggregate"


def configure(cache_ttl: int, active_weight: float, idle_weight: float) -> None:
    global _CACHE_TTL, _ACTIVE_WEIGHT, _IDLE_WEIGHT
    _CACHE_TTL     = cache_ttl
    _ACTIVE_WEIGHT = active_weight
    _IDLE_WEIGHT   = idle_weight


class TeamCLSAggregator:
    """
    Computes and caches the activity-weighted aggregate CLS for the cluster.
    Replaces the naive arithmetic mean previously used in scheduler-core/main.py.
    """

    async def get_aggregate(self, redis, db) -> dict:
        """
        Returns cached aggregate if fresh, otherwise recomputes from MongoDB.
        """
        import json
        cached = await redis.get(_TEAM_CLS_REDIS_KEY)
        if cached:
            return json.loads(cached)

        result = await self._compute(db)

        # Cache result
        try:
            await redis.set(_TEAM_CLS_REDIS_KEY, json.dumps(result), ex=_CACHE_TTL)
        except Exception:
            pass

        return result

    async def _compute(self, db) -> dict:
        """Query all active cls_states and compute weighted aggregate."""
        try:
            docs = await db.cls_states.find(
                {}, {"user_id": 1, "current_cls": 1, "raw_features": 1, "_id": 0}
            ).to_list(length=200)
        except Exception:
            docs = []

        if not docs:
            return self._empty_aggregate()

        weighted_sum  = 0.0
        total_weight  = 0.0
        active_users  = 0
        idle_users    = 0

        for doc in docs:
            cls_score = float(doc.get("current_cls", 0.0))
            raw       = doc.get("raw_features", {})
            # A user is 'active' if they had any keystrokes in the last window
            is_active = (raw.get("typing_rate", 0.0) > 0) or \
                        (raw.get("tab_switch_rate", 0.0) > 0)
            weight    = _ACTIVE_WEIGHT if is_active else _IDLE_WEIGHT

            weighted_sum += weight * cls_score
            total_weight += weight
            if is_active:
                active_users += 1
            else:
                idle_users += 1

        aggregate_cls = weighted_sum / total_weight if total_weight > 0 else 0.0
        aggregate_cls = round(aggregate_cls, 4)

        # Classify aggregate state using same thresholds as individual CLS
        if aggregate_cls >= 0.75:
            agg_state = "HIGH"
        elif aggregate_cls >= 0.45:
            agg_state = "MEDIUM"
        else:
            agg_state = "LOW"

        result = {
            "aggregate_cls_score": aggregate_cls,
            "aggregate_cls_state": agg_state,
            "total_users":         len(docs),
            "active_users":        active_users,
            "idle_users":          idle_users,
            "computed_at":         datetime.utcnow().isoformat(),
        }

        # Persist snapshot for audit trail
        try:
            await db.team_cls_snapshots.insert_one({**result})
        except Exception:
            pass

        logger.debug(
            "TeamCLS: aggregate=%.4f state=%s active=%d idle=%d",
            aggregate_cls, agg_state, active_users, idle_users,
        )
        return result

    @staticmethod
    def _empty_aggregate() -> dict:
        return {
            "aggregate_cls_score": 0.0,
            "aggregate_cls_state": "LOW",
            "total_users":         0,
            "active_users":        0,
            "idle_users":          0,
            "computed_at":         datetime.utcnow().isoformat(),
        }
