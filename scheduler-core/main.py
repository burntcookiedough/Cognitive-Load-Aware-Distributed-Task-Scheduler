import os
import sys
import json
import uuid
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app")

from scheduler import select_node
from baseline_scheduler import select_node_baseline
from migration_engine import run_migration_check
from predictive_migration import PredictiveMigrationEngine, configure as configure_pred
from weight_calibrator import WeightCalibrator, configure as configure_calibrator
from latency_probe import LatencyProbe
from team_cls_aggregator import TeamCLSAggregator, configure as configure_team_cls

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="CLADS — Scheduler Core", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL          = os.getenv("REDIS_URL",          "redis://redis:6379")
MONGODB_URI        = os.getenv("MONGODB_URI",        "mongodb://mongodb:27017")
COGNITIVE_LOAD_URL = os.getenv("COGNITIVE_LOAD_URL", "http://cognitive-load-service:8001")
NODE_URLS          = {
    "node1": os.getenv("NODE1_URL", "http://node1:8011"),
    "node2": os.getenv("NODE2_URL", "http://node2:8012"),
    "node3": os.getenv("NODE3_URL", "http://node3:8013"),
}

redis_client = None
db           = None
http         = None
node_clients = {}

# ─── Patent module instances ──────────────────────────────────────────────────
pred_engine    = PredictiveMigrationEngine()
weight_cal     = WeightCalibrator()
latency_probe  = LatencyProbe(enabled=True, window_size=50)
team_cls       = TeamCLSAggregator()


@app.on_event("startup")
async def startup():
    global redis_client, db, http, node_clients
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    db           = mongo_client.clads
    http         = httpx.AsyncClient(timeout=5.0)
    node_clients = {nid: httpx.AsyncClient(base_url=url, timeout=5.0)
                    for nid, url in NODE_URLS.items()}

    # Configure patent modules from env / shared config
    _prob_threshold = float(os.getenv("PREEMPTIVE_MIGRATION_PROB_THRESHOLD", "0.70"))
    _check_delay    = int(os.getenv("PREDICTION_ACCURACY_CHECK_DELAY",       "30"))
    _lr             = float(os.getenv("ADAPTIVE_WEIGHT_LEARNING_RATE",       "0.05"))
    _feedback_delay = int(os.getenv("OUTCOMES_FEEDBACK_DELAY_SECONDS",       "30"))
    _min_samples    = int(os.getenv("WEIGHT_CALIBRATION_MIN_SAMPLES",        "10"))
    _cache_ttl      = int(os.getenv("TEAM_CLS_CACHE_TTL_SECONDS",            "30"))
    _active_weight  = float(os.getenv("TEAM_CLS_ACTIVE_USER_WEIGHT",         "2.0"))
    _idle_weight    = float(os.getenv("TEAM_CLS_IDLE_USER_WEIGHT",           "1.0"))

    configure_pred(
        prob_threshold=_prob_threshold,
        check_delay=_check_delay,
        cls_service_url=COGNITIVE_LOAD_URL,
    )
    configure_calibrator(
        learning_rate=_lr,
        feedback_delay=_feedback_delay,
        min_samples=_min_samples,
        cls_service_url=COGNITIVE_LOAD_URL,
    )
    configure_team_cls(
        cache_ttl=_cache_ttl,
        active_weight=_active_weight,
        idle_weight=_idle_weight,
    )


@app.on_event("shutdown")
async def shutdown():
    if http:    await http.aclose()
    for c in node_clients.values(): await c.aclose()
    if redis_client: await redis_client.close()


# ─── Request models ───────────────────────────────────────────────────────────
class ScheduleRequest(BaseModel):
    task: dict
    scheduler_mode: str = "CLADS"


# ─── Helpers ─────────────────────────────────────────────────────────────────
async def fetch_cls(user_id: str) -> dict:
    """Fetch current CLS state from cognitive-load-service, fallback to cache."""
    cached = await redis_client.get(f"cls:{user_id}")
    if cached:
        return json.loads(cached)
    try:
        r = await http.get(f"{COGNITIVE_LOAD_URL}/cls/{user_id}")
        return r.json()
    except Exception:
        return {
            "current_cls": 0.0, "state": "LOW",
            "predicted_cls": 0.0, "probability_high": 0.0,
            "trend_slope": 0.0, "estimated_breach_seconds": None,
            "flow_state_locked": False,
        }


async def fetch_node_metrics() -> dict:
    """Fetch live metrics from all worker nodes concurrently."""
    metrics = {}
    for node_id, client in node_clients.items():
        try:
            r = await client.get("/metrics")
            metrics[node_id] = r.json()
        except Exception:
            metrics[node_id] = {
                "node_id":           node_id,
                "cpu_usage":         95.0,
                "memory_usage":      90.0,
                "queue_length":      10,
                "latency_to_user_ms":200.0,
                "status":            "unreachable",
            }
    return metrics


async def dispatch_task(node_id: str, task: dict) -> dict:
    """Send task to a worker node for execution."""
    try:
        r = await node_clients[node_id].post("/submit", json=task)
        return r.json()
    except Exception as e:
        return {"status": "dispatch_error", "error": str(e)}


# ─── Main schedule endpoint ───────────────────────────────────────────────────
@app.post("/schedule")
async def schedule_task(req: ScheduleRequest, background_tasks: BackgroundTasks):
    """
    Main scheduling endpoint — all patent additions integrated here.

    Flow:
    1. Fetch CLS (includes predictions, flow state, governor directive)
    2. Fetch TeamCLS aggregate (Claim 7)
    3. Fetch node metrics
    4. Select node via CLADS or BASELINE policy
       - Flow state lock applied if flow_state_locked (Claim 5)
       - Aggregate CLS state used for cluster-wide policy (Claim 7)
    5. Check for preemptive migration (Claim 4)
    6. Dispatch task
    7. Record decision + trigger:
       - Reactive migration check (original)
       - Weight calibration outcome check (Claim 6, Addition A)
    """
    # ── Addition B: Latency probe — start timer ────────────────────────────────
    t_start = latency_probe.start()

    task           = req.task
    scheduler_mode = req.scheduler_mode.upper()
    user_id        = task.get("user_id", "u_unknown")

    # ── Fetch CLS (contains all Addition 1/2/3 fields) ────────────────────────
    cls_data  = await fetch_cls(user_id)
    cls_state = cls_data.get("state",        "LOW")
    cls_score = float(cls_data.get("current_cls",  0.0))

    # Addition 2 — predictive fields
    probability_high         = float(cls_data.get("probability_high",         0.0))
    predicted_cls            = float(cls_data.get("predicted_cls",            0.0))
    trend_slope              = float(cls_data.get("trend_slope",              0.0))
    estimated_breach_seconds = cls_data.get("estimated_breach_seconds")

    # Addition 3 — flow state
    flow_state_locked = bool(cls_data.get("flow_state_locked", False))

    # ── Addition C: TeamCLS Aggregate (Claim 7) ────────────────────────────────
    team_data         = await team_cls.get_aggregate(redis_client, db)
    aggregate_cls_score = float(team_data.get("aggregate_cls_score", 0.0))
    aggregate_cls_state = team_data.get("aggregate_cls_state", "LOW")

    # ── Fetch node metrics ────────────────────────────────────────────────────
    nodes = await fetch_node_metrics()

    # ── Node selection ────────────────────────────────────────────────────────
    flow_state_override = False
    if scheduler_mode == "BASELINE":
        best_node, policy, reason, scored = select_node_baseline(nodes)
    else:
        best_node, policy, reason, scored, flow_state_override = select_node(
            nodes               = nodes,
            task                = task,
            cls_state           = cls_state,
            cls_score           = cls_score,
            global_cluster_cls  = aggregate_cls_score,   # Addition C (Claim 7)
            flow_state_locked   = flow_state_locked,     # Addition 3 (Claim 5)
            aggregate_cls_state = aggregate_cls_state,   # Addition C (Claim 7)
        )

    # ── Addition 2: Preemptive migration check (Claim 4) ──────────────────────
    preemptive_triggered = False
    if scheduler_mode == "CLADS":
        preemptive_actions = await pred_engine.evaluate(
            user_id                  = user_id,
            current_state            = cls_state,
            probability_high         = probability_high,
            predicted_cls            = predicted_cls,
            trend_slope              = trend_slope,
            estimated_breach_seconds = estimated_breach_seconds,
            db                       = db,
            node_clients             = node_clients,
        )
        preemptive_triggered = len(preemptive_actions) > 0

    # ── Addition B: Latency probe — record ────────────────────────────────────
    foreground_latency_ms = await latency_probe.record(
        start_time       = t_start,
        scheduler_mode   = scheduler_mode,
        cls_state        = cls_state,
        disruption_class = task.get("disruption_class", "MEDIUM"),
        assigned_node    = best_node,
        user_id          = user_id,
        task_type        = task.get("task_type", "unknown"),
        db               = db,
    )

    # ── Build decision record ─────────────────────────────────────────────────
    decision = {
        "decision_id":                str(uuid.uuid4())[:12],
        "task_id":                    task.get("task_id", "?"),
        "user_id":                    user_id,
        "task_type":                  task.get("task_type", "?"),
        "cls_state":                  cls_state,
        "cls_score":                  cls_score,
        "disruption_class":           task.get("disruption_class", "?"),
        "disruption_score":           task.get("disruption_score", 0.0),
        "assigned_node":              best_node,
        "decision":                   policy,
        "reason":                     reason,
        "scheduler_mode":             scheduler_mode,
        "node_scores":                scored,
        # Addition 2 — predictive (Claim 4)
        "predicted_cls":              predicted_cls,
        "probability_high":           probability_high,
        "trend_slope":                trend_slope,
        "estimated_breach_seconds":   estimated_breach_seconds,
        "preemptive_migration_triggered": preemptive_triggered,
        # Addition 3 — flow state (Claim 5)
        "flow_state_locked":          flow_state_locked,
        "flow_state_override":        flow_state_override,
        # Addition B — latency (Section 11)
        "foreground_latency_ms":      foreground_latency_ms,
        # Addition C — team CLS (Claim 7)
        "aggregate_cls_score":        aggregate_cls_score,
        "aggregate_cls_state":        aggregate_cls_state,
        "timestamp":                  datetime.utcnow().isoformat(),
    }

    # ── Persist decision ──────────────────────────────────────────────────────
    try:
        await db.scheduler_decisions.insert_one({**decision})
        await db.tasks.update_one(
            {"task_id": task.get("task_id")},
            {"$set": {"status": "scheduled", "assigned_node": best_node}},
        )
    except Exception:
        pass

    # ── Dispatch to worker node (background) ──────────────────────────────────
    background_tasks.add_task(dispatch_task, best_node, task)

    # ── Background: reactive CLS migration check ───────────────────────────────
    old_cls = await redis_client.get(f"prev_cls:{user_id}")
    await redis_client.set(f"prev_cls:{user_id}", cls_state, ex=300)
    if old_cls and old_cls != cls_state:
        background_tasks.add_task(
            run_migration_check, user_id, cls_state, old_cls, db, node_clients
        )

    # ── Addition A: Weight calibrator outcome check (Claim 6) ─────────────────
    if scheduler_mode == "CLADS":
        await weight_cal.record_decision(
            user_id          = user_id,
            decision_id      = decision["decision_id"],
            cls_state_at     = cls_state,
            cls_score_at     = cls_score,
            disruption_class = task.get("disruption_class", "MEDIUM"),
            disruption_score = task.get("disruption_score", 0.5),
            assigned_node    = best_node,
            db               = db,
        )

    return decision


# ─── Read endpoints ───────────────────────────────────────────────────────────
@app.get("/decisions")
async def list_decisions(limit: int = 50, user_id: Optional[str] = None):
    """Return recent scheduler decisions (newest first)."""
    query = {"user_id": user_id} if user_id else {}
    cursor = db.scheduler_decisions.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


@app.get("/decisions/stats")
async def decision_stats():
    """Aggregate stats for CLADS vs Baseline comparison."""
    pipeline = [
        {"$group": {
            "_id": {
                "scheduler_mode":   "$scheduler_mode",
                "cls_state":        "$cls_state",
                "disruption_class": "$disruption_class",
                "assigned_node":    "$assigned_node",
            },
            "count":         {"$sum": 1},
            "avg_cls_score": {"$avg": "$cls_score"},
        }},
        {"$sort": {"count": -1}},
    ]
    result = await db.scheduler_decisions.aggregate(pipeline).to_list(length=100)
    for r in result:
        r["_id"] = dict(r["_id"])
    return result


@app.get("/preemptive-migrations")
async def get_preemptive_migrations(limit: int = 50):
    """Return preemptive migration history with accuracy verification status."""
    cursor = db.preemptive_migrations.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    records = await cursor.to_list(length=limit)
    accuracy = await PredictiveMigrationEngine.get_accuracy_summary(db)
    return {"migrations": records, "accuracy_summary": accuracy}


@app.get("/weight-profiles/{user_id}")
async def get_weight_profile(user_id: str):
    """Return the adaptive weight profile for a user (Claim 6 inspection)."""
    return await weight_cal.get_profile(user_id, db)


@app.get("/weight-profiles")
async def list_weight_profiles():
    """List all users with calibrated weight profiles."""
    cursor = db.weight_profiles.find({}, {"_id": 0}).sort("last_updated", -1)
    return await cursor.to_list(length=100)


@app.get("/benchmarks/summary")
async def get_benchmark_summary():
    """
    CLADS vs BASELINE latency comparison (Section 11 experimental evidence).
    Returns improvement % at HIGH CLS × HIGH Dk — quote directly in patent spec.
    """
    return await LatencyProbe.get_summary(db, window=50)


@app.get("/team-cls")
async def get_team_cls():
    """Return the current cluster-wide composite CLS aggregate (Claim 7)."""
    return await team_cls.get_aggregate(redis_client, db)


@app.get("/nodes/metrics")
async def nodes_metrics():
    """Proxy: return live metrics from all worker nodes."""
    return await fetch_node_metrics()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "scheduler-core", "version": "2.0.0"}
