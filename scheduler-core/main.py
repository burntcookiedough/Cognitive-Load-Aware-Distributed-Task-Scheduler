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

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="CLADS — Scheduler Core", version="1.0.0")
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
http         = None          # shared httpx.AsyncClient
node_clients = {}            # per-node clients for direct calls


@app.on_event("startup")
async def startup():
    global redis_client, db, http, node_clients
    redis_client  = aioredis.from_url(REDIS_URL, decode_responses=True)
    mongo_client  = AsyncIOMotorClient(MONGODB_URI)
    db            = mongo_client.clads
    http          = httpx.AsyncClient(timeout=5.0)
    node_clients  = {nid: httpx.AsyncClient(base_url=url, timeout=5.0)
                     for nid, url in NODE_URLS.items()}


@app.on_event("shutdown")
async def shutdown():
    if http:    await http.aclose()
    for c in node_clients.values(): await c.aclose()
    if redis_client: await redis_client.close()


# ─── Request models ───────────────────────────────────────────────────────────
class ScheduleRequest(BaseModel):
    task: dict          # annotated task object from task-annotator
    scheduler_mode: str = "CLADS"   # CLADS | BASELINE


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
        return {"current_cls": 0.0, "state": "LOW"}


async def fetch_node_metrics() -> dict:
    """Fetch live metrics from all worker nodes concurrently."""
    metrics = {}
    for node_id, client in node_clients.items():
        try:
            r = await client.get("/metrics")
            metrics[node_id] = r.json()
        except Exception:
            # Node unreachable — use default high-load placeholder
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


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/schedule")
async def schedule_task(req: ScheduleRequest, background_tasks: BackgroundTasks):
    """
    Main scheduling endpoint.
    1. Fetch CLS state for the user.
    2. Fetch live node metrics.
    3. Apply CLADS or Baseline policy to select node.
    4. Dispatch task and log decision.
    """
    task           = req.task
    scheduler_mode = req.scheduler_mode.upper()
    user_id        = task.get("user_id", "u_unknown")

    # ── Fetch CLS ──────────────────────────────────────────────────────────────
    cls_data   = await fetch_cls(user_id)
    cls_state  = cls_data.get("state", "LOW")
    cls_score  = float(cls_data.get("current_cls", 0.0))

    # ── Fetch node metrics ─────────────────────────────────────────────────────
    nodes = await fetch_node_metrics()

    # ── Node selection ─────────────────────────────────────────────────────────
    if scheduler_mode == "BASELINE":
        best_node, policy, reason, scored = select_node_baseline(nodes)
    else:
        # Fetch global cluster CLS for multi-user arbitration
        cursor = db.cls_states.find({}, {"current_cls": 1, "_id": 0})
        all_states = await cursor.to_list(length=100)
        global_cluster_cls = 0.0
        if all_states:
            global_cluster_cls = sum(s.get("current_cls", 0.0) for s in all_states) / len(all_states)

        best_node, policy, reason, scored = select_node(nodes, task, cls_state, cls_score, global_cluster_cls)

    # ── Build decision record ──────────────────────────────────────────────────
    decision = {
        "decision_id":      str(uuid.uuid4())[:12],
        "task_id":          task.get("task_id", "?"),
        "user_id":          user_id,
        "task_type":        task.get("task_type", "?"),
        "cls_state":        cls_state,
        "cls_score":        cls_score,
        "disruption_class": task.get("disruption_class", "?"),
        "disruption_score": task.get("disruption_score", 0.0),
        "assigned_node":    best_node,
        "decision":         policy,
        "reason":           reason,
        "scheduler_mode":   scheduler_mode,
        "node_scores":      scored,
        "timestamp":        datetime.utcnow().isoformat(),
    }

    # ── Persist decision ───────────────────────────────────────────────────────
    try:
        await db.scheduler_decisions.insert_one({**decision})
        await db.tasks.update_one(
            {"task_id": task.get("task_id")},
            {"$set": {"status": "scheduled", "assigned_node": best_node}},
        )
    except Exception:
        pass

    # ── Dispatch to worker node (background so response is immediate) ──────────
    background_tasks.add_task(dispatch_task, best_node, task)

    # ── CLS transition migration check (background) ───────────────────────────
    old_cls = await redis_client.get(f"prev_cls:{user_id}")
    await redis_client.set(f"prev_cls:{user_id}", cls_state, ex=300)
    if old_cls and old_cls != cls_state:
        background_tasks.add_task(
            run_migration_check, user_id, cls_state, old_cls, db, node_clients
        )

    return decision


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
            "count": {"$sum": 1},
            "avg_cls_score": {"$avg": "$cls_score"},
        }},
        {"$sort": {"count": -1}},
    ]
    result = await db.scheduler_decisions.aggregate(pipeline).to_list(length=100)
    for r in result:
        r["_id"] = dict(r["_id"])
    return result


@app.get("/nodes/metrics")
async def nodes_metrics():
    """Proxy: return live metrics from all worker nodes."""
    return await fetch_node_metrics()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "scheduler-core"}
