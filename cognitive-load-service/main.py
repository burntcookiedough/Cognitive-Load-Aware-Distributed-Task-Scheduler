import os
import json
import sys
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient

# Resolve local imports whether running inside or outside Docker
sys.path.insert(0, "/app")

from feature_extractor import extract_features
from normalizer import normalize
from cls_engine import compute_cls, compute_predictive_cls
from hysteresis import HysteresisController
from cpu_governor import CPUGovernorController, configure as configure_governor
from flow_state import FlowStateController

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="CLADS — Cognitive Load Service", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL   = os.getenv("REDIS_URL",   "redis://redis:6379")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
MAX_EVENTS  = int(os.getenv("MAX_EVENTS", "20"))

# Patent-specific env vars
FLOW_THRESHOLD = int(os.getenv("FLOW_STATE_THRESHOLD", "180"))
REAL_GOVERNOR  = os.getenv("REAL_GOVERNOR", "false").lower() == "true"

redis_client: Optional[aioredis.Redis] = None
db     = None
hysteresis = HysteresisController()
governor   = CPUGovernorController()
flow_ctrl  = FlowStateController(threshold=FLOW_THRESHOLD, decay_rate=0.95)

# ─── Governor policy defaults (used if shared/config.py not available) ────────
_DEFAULT_GOV_POLICIES = {
    "LOW": {
        "governor": "performance", "freq_min_mhz": 2400, "freq_max_mhz": 4200,
        "background_gov": "performance",
        "description": "No CLS pressure — full performance on all threads",
    },
    "MEDIUM": {
        "governor": "ondemand", "freq_min_mhz": 2000, "freq_max_mhz": 4200,
        "background_gov": "conservative",
        "description": "Medium CLS — foreground boosted, background conserved",
    },
    "HIGH": {
        "governor": "performance", "freq_min_mhz": 3200, "freq_max_mhz": 4200,
        "background_gov": "powersave",
        "description": "High CLS — foreground protected, background throttled to powersave",
    },
}
_DEFAULT_SYSFS_TEMPLATE = "/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_governor"


def _load_governor_config() -> tuple:
    """Load governor config from shared/config.py; fall back to inline defaults."""
    try:
        from config import CPU_GOVERNOR_POLICIES, CPU_SYSFS_PATH_TEMPLATE
        return CPU_GOVERNOR_POLICIES, CPU_SYSFS_PATH_TEMPLATE
    except ImportError:
        return _DEFAULT_GOV_POLICIES, _DEFAULT_SYSFS_TEMPLATE


# ─── Startup / shutdown ───────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global redis_client, db
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    client = AsyncIOMotorClient(MONGODB_URI)
    db     = client.clads

    # Configure governor (Addition 1)
    gov_policies, sysfs_template = _load_governor_config()
    configure_governor(gov_policies, REAL_GOVERNOR, sysfs_template)

    # Restore dashboard-configured flow threshold from Redis (Addition 3)
    await flow_ctrl.load_threshold(redis_client)


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()


# ─── Request models ───────────────────────────────────────────────────────────
class TelemetryEvent(BaseModel):
    user_id: str
    timestamp: str = ""
    keystrokes: int = 0
    avg_inter_key_interval: float = 0.0
    typing_variance: float = 0.0
    idle_duration: float = 0.0
    tab_switches: int = 0
    focus_changes: int = 0
    context_switches: int = 0


class FlowConfigRequest(BaseModel):
    threshold: int   # new window count threshold for flow lock activation


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/telemetry")
async def receive_telemetry(event: TelemetryEvent):
    """Ingest a telemetry batch, update rolling window, recompute CLS."""
    if not event.timestamp:
        event.timestamp = datetime.utcnow().isoformat()

    event_dict = event.model_dump()

    # ── Push into Redis rolling window ────────────────────────────────────────
    window_key = f"telemetry:{event.user_id}"
    await redis_client.lpush(window_key, json.dumps(event_dict))
    await redis_client.ltrim(window_key, 0, MAX_EVENTS - 1)
    await redis_client.expire(window_key, 300)

    # ── Persist raw event to MongoDB ─────────────────────────────────────────
    try:
        await db.telemetry_events.insert_one({**event_dict, "_id": None})
    except Exception:
        pass

    # ── Compute CLS ──────────────────────────────────────────────────────────
    raw_events = await redis_client.lrange(window_key, 0, -1)
    events     = [json.loads(e) for e in raw_events]
    features   = extract_features(events)
    normalized = normalize(features)
    cls_score  = compute_cls(event.user_id, normalized)

    # ── Hysteresis state machine ──────────────────────────────────────────────
    old_state = hysteresis.get_state(event.user_id)
    state     = hysteresis.update(event.user_id, cls_score)

    # ── Addition 1: CPU Governor directive ────────────────────────────────────
    governor_directive = await governor.apply(
        user_id=event.user_id,
        new_state=state,
        old_state=old_state,
        db=db,
    )

    # ── Addition 3: Flow State Protection Window ──────────────────────────────
    flow_data = await flow_ctrl.update(
        user_id=event.user_id,
        state=state,
        redis=redis_client,
        db=db,
    )

    # ── Addition 2: Predictive CLS (polyfit regression) ────────────────────────
    history_key = f"cls_history:{event.user_id}"
    await redis_client.lpush(history_key, cls_score)
    await redis_client.ltrim(history_key, 0, 19)   # keep last 20

    recent_scores = [float(s) for s in await redis_client.lrange(history_key, 0, -1)]
    recent_scores.reverse()  # chronological order
    predictions = compute_predictive_cls(recent_scores, regression_window=10)

    # ── Assemble full CLS payload ─────────────────────────────────────────────
    cls_data = {
        "user_id":     event.user_id,
        "current_cls": cls_score,
        "state":       state,
        # Addition 2 — Predictive (Claim 4)
        "predicted_cls":            predictions["predicted_cls"],
        "probability_high":         predictions["probability_high"],
        "trend_slope":              predictions["trend_slope"],
        "r_squared":                predictions["r_squared"],
        "estimated_breach_seconds": predictions["estimated_breach_seconds"],
        # Features
        "features":     normalized,
        "raw_features": features,
        # Addition 1 — Governor (Claim 2)
        "cpu_governor_directive": governor_directive,
        # Addition 3 — Flow State (Claim 5)
        "flow_state_locked":       flow_data["flow_state_locked"],
        "flow_streak":             flow_data["flow_streak"],
        "accumulated_flow_credit": flow_data["accumulated_flow_credit"],
        "flow_threshold":          flow_data["threshold"],
        "updated_at": datetime.utcnow().isoformat(),
    }

    # ── Cache in Redis (120-second TTL) ──────────────────────────────────────
    await redis_client.set(f"cls:{event.user_id}", json.dumps(cls_data), ex=120)

    # ── Upsert into MongoDB ───────────────────────────────────────────────────
    try:
        await db.cls_states.update_one(
            {"user_id": event.user_id},
            {"$set": cls_data},
            upsert=True,
        )
    except Exception:
        pass

    return {
        "status":    "ok",
        "cls_score": cls_score,
        "state":     state,
        "features":  normalized,
        "predicted_cls":            predictions["predicted_cls"],
        "probability_high":         predictions["probability_high"],
        "trend_slope":              predictions["trend_slope"],
        "estimated_breach_seconds": predictions["estimated_breach_seconds"],
        "flow_state_locked":        flow_data["flow_state_locked"],
        "flow_streak":              flow_data["flow_streak"],
        "cpu_governor_directive":   governor_directive,
    }


@app.get("/cls/{user_id}")
async def get_cls(user_id: str):
    """Return the current CLS state for a user (Redis cache → MongoDB fallback)."""
    cached = await redis_client.get(f"cls:{user_id}")
    if cached:
        return json.loads(cached)

    doc = await db.cls_states.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        return doc

    return {
        "user_id":                  user_id,
        "current_cls":              0.0,
        "state":                    "LOW",
        "predicted_cls":            0.0,
        "probability_high":         0.0,
        "trend_slope":              0.0,
        "estimated_breach_seconds": None,
        "flow_state_locked":        False,
        "flow_streak":              0,
        "accumulated_flow_credit":  0.0,
        "cpu_governor_directive":   None,
        "features":                 {},
        "updated_at":               datetime.utcnow().isoformat(),
    }


@app.get("/cls-history/{user_id}")
async def get_cls_history(user_id: str, limit: int = 50):
    """Return recent CLS records for a user (for analytics charts)."""
    cursor = db.cls_states.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("updated_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


@app.get("/governor/{user_id}")
async def get_governor_state(user_id: str):
    """Return the current CPU governor policy for a user (Claim 2 inspection)."""
    return governor.get_current_policy(user_id)


@app.get("/governor/log")
async def get_governor_log(limit: int = 50):
    """Return recent CPU governor directives (patent evidence log)."""
    cursor = db.cpu_governor_log.find({}, {"_id": 0}).sort("issued_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


@app.put("/flow-config")
async def update_flow_threshold(req: FlowConfigRequest):
    """
    Update Flow State lock threshold at runtime (dashboard-configurable).
    Claim 5: demonstrates the mechanism is a general-purpose controller,
    not a hardcoded rule.
    """
    if req.threshold < 1:
        raise HTTPException(status_code=400, detail="threshold must be >= 1")
    await flow_ctrl.set_threshold(req.threshold, redis_client)
    return {
        "status":        "updated",
        "new_threshold": req.threshold,
        "note":          "Flow lock activates after this many consecutive LOW windows",
    }


@app.get("/flow-state/{user_id}")
async def get_flow_state(user_id: str):
    """Return current Flow State data for a user."""
    streak_key = f"flow_streak:{user_id}"
    credit_key = f"flow_credit:{user_id}"
    streak = int((await redis_client.get(streak_key)) or 0)
    credit = float((await redis_client.get(credit_key)) or 0.0)
    return {
        "user_id":                 user_id,
        "flow_state_locked":       flow_ctrl.is_flow_locked(user_id),
        "flow_streak":             streak,
        "accumulated_flow_credit": round(credit, 4),
        "threshold":               flow_ctrl.threshold,
    }


@app.delete("/cls/{user_id}/reset")
async def reset_cls(user_id: str):
    """Reset rolling window and hysteresis for a user (demo helper)."""
    await redis_client.delete(
        f"telemetry:{user_id}", f"cls:{user_id}",
        f"flow_streak:{user_id}", f"flow_credit:{user_id}",
        f"cls_history:{user_id}",
    )
    hysteresis.reset(user_id)
    flow_ctrl.reset(user_id)
    return {"status": "reset", "user_id": user_id}


@app.get("/health")
async def health():
    return {
        "status":         "ok",
        "service":        "cognitive-load-service",
        "version":        "2.0.0",
        "governor_mode":  "real_sysfs" if REAL_GOVERNOR else "simulated",
        "flow_threshold": flow_ctrl.threshold,
    }
