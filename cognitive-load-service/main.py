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

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="CLADS — Cognitive Load Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL   = os.getenv("REDIS_URL",   "redis://redis:6379")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
MAX_EVENTS  = int(os.getenv("MAX_EVENTS", "20"))

redis_client: Optional[aioredis.Redis] = None
db = None
hysteresis = HysteresisController()


# ─── Startup / shutdown ───────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global redis_client, db
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.clads


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

    # ── Persist raw event to MongoDB (async, non-blocking concern) ────────────
    try:
        await db.telemetry_events.insert_one({**event_dict, "_id": None})
    except Exception:
        pass  # telemetry storage failure is non-fatal

    # ── Compute CLS ───────────────────────────────────────────────────────────
    raw_events = await redis_client.lrange(window_key, 0, -1)
    events     = [json.loads(e) for e in raw_events]

    features   = extract_features(events)
    normalized = normalize(features)
    cls_score  = compute_cls(event.user_id, normalized)
    state      = hysteresis.update(event.user_id, cls_score)

    # ── Predictive CLS ────────────────────────────────────────────────────────
    history_key = f"cls_history:{event.user_id}"
    await redis_client.lpush(history_key, cls_score)
    await redis_client.ltrim(history_key, 0, 9) # keep last 10
    
    recent_scores = [float(s) for s in await redis_client.lrange(history_key, 0, -1)]
    recent_scores.reverse() # chronological
    
    predictions = compute_predictive_cls(recent_scores)

    cls_data = {
        "user_id":     event.user_id,
        "current_cls": cls_score,
        "state":       state,
        "predicted_cls": predictions["predicted_cls"],
        "probability_high": predictions["probability_high"],
        "features":    normalized,
        "raw_features":features,
        "updated_at":  datetime.utcnow().isoformat(),
    }

    # ── Cache in Redis (120-second TTL) ───────────────────────────────────────
    await redis_client.set(
        f"cls:{event.user_id}", json.dumps(cls_data), ex=120
    )

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
    }


@app.get("/cls/{user_id}")
async def get_cls(user_id: str):
    """Return the current CLS state for a user (Redis cache → MongoDB fallback)."""
    cached = await redis_client.get(f"cls:{user_id}")
    if cached:
        return json.loads(cached)

    # MongoDB fallback
    doc = await db.cls_states.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        return doc

    return {
        "user_id":     user_id,
        "current_cls": 0.0,
        "state":       "LOW",
        "predicted_cls": 0.0,
        "probability_high": 0.0,
        "features":    {},
        "updated_at":  datetime.utcnow().isoformat(),
    }


@app.get("/cls-history/{user_id}")
async def get_cls_history(user_id: str, limit: int = 50):
    """Return recent CLS records for a user (for analytics charts)."""
    cursor = db.cls_states.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("updated_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


@app.delete("/cls/{user_id}/reset")
async def reset_cls(user_id: str):
    """Reset rolling window and hysteresis for a user (demo helper)."""
    await redis_client.delete(f"telemetry:{user_id}", f"cls:{user_id}")
    hysteresis.reset(user_id)
    return {"status": "reset", "user_id": user_id}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cognitive-load-service"}
