"""
Generic worker node — three instances run with different env-var profiles:

  node1  (Local)      → base_latency=20ms,  queue_cap=3,  cpu_limit=0.80
  node2  (Balanced)   → base_latency=85ms,  queue_cap=6,  cpu_limit=0.60
  node3  (Background) → base_latency=120ms, queue_cap=10, cpu_limit=0.90
"""

import os
import sys
import asyncio
import random
import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

# ─── Node configuration (from environment) ───────────────────────────────────
NODE_ID        = os.getenv("NODE_ID",        "node1")
NODE_LABEL     = os.getenv("NODE_LABEL",     "Local")
NODE_PORT      = int(os.getenv("NODE_PORT",  "8011"))
BASE_LATENCY_MS= float(os.getenv("BASE_LATENCY_MS", "20"))
QUEUE_CAPACITY = int(os.getenv("QUEUE_CAPACITY",     "3"))
CPU_LIMIT      = float(os.getenv("CPU_LIMIT",        "0.80"))
MONGODB_URI    = os.getenv("MONGODB_URI",    "mongodb://mongodb:27017")

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title=f"CLADS — Worker Node [{NODE_ID}]", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── State ───────────────────────────────────────────────────────────────────
db               = None
task_queue       = None          # set in startup
tasks_processed  = 0
currently_running: dict | None = None   # task being processed right now

# Simulate realistic "baseline" load on this node
_base_cpu = random.uniform(15, 35)
_base_mem = random.uniform(25, 45)


# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    global db, task_queue
    client     = AsyncIOMotorClient(MONGODB_URI)
    db         = client.clads
    task_queue = asyncio.Queue(maxsize=QUEUE_CAPACITY + 2)   # small overflow buffer
    asyncio.create_task(_process_queue())


# ─── Models ───────────────────────────────────────────────────────────────────
class TaskSubmission(BaseModel):
    task_id:            str   = ""
    task_type:          str   = "build"
    execution_time_ms:  int   = 3000
    user_id:            str   = "u_unknown"
    disruption_class:   str   = "MEDIUM"
    disruption_score:   float = 0.5


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/submit")
async def submit_task(task: TaskSubmission):
    """Accept a new task into the processing queue."""
    if task_queue.full():
        return {
            "status":  "rejected",
            "reason":  "queue_full",
            "node_id": NODE_ID,
            "queue_length": task_queue.qsize(),
        }
    if not task.task_id:
        task.task_id = str(uuid.uuid4())[:8]

    await task_queue.put(task)
    return {
        "status":         "queued",
        "task_id":        task.task_id,
        "node_id":        NODE_ID,
        "node_label":     NODE_LABEL,
        "queue_position": task_queue.qsize(),
        "queued_at":      datetime.utcnow().isoformat(),
    }


@app.post("/migrate")
async def migrate_task(task: TaskSubmission):
    """Accept a task migrated from another node."""
    if not task.task_id:
        task.task_id = str(uuid.uuid4())[:8]
    try:
        task_queue.put_nowait(task)
        return {"status": "accepted_migration", "task_id": task.task_id, "node_id": NODE_ID}
    except asyncio.QueueFull:
        return {"status": "rejected_migration", "reason": "queue_full"}


@app.get("/metrics")
async def get_metrics():
    """Return live node metrics — CPU and memory are simulated based on queue depth."""
    q        = task_queue.qsize()
    busy     = currently_running is not None

    # CPU scales with queue depth and current task running
    cpu_load = _base_cpu + q * 14 + (18 if busy else 0) + random.uniform(-2, 4)
    cpu_load = min(100.0, cpu_load * (CPU_LIMIT + 0.1))

    mem_load = _base_mem + q * 9 + (12 if busy else 0) + random.uniform(-1, 3)
    mem_load = min(100.0, mem_load)

    # Small jitter to latency to feel real
    latency  = BASE_LATENCY_MS + random.uniform(-3, 8)

    return {
        "node_id":            NODE_ID,
        "node_label":         NODE_LABEL,
        "cpu_usage":          round(cpu_load, 1),
        "memory_usage":       round(mem_load, 1),
        "queue_length":       q,
        "latency_to_user_ms": round(latency, 1),
        "status":             "active",
        "tasks_processed":    tasks_processed,
        "queue_capacity":     QUEUE_CAPACITY,
        "currently_running":  currently_running["task_type"] if currently_running else None,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "node_id": NODE_ID, "node_label": NODE_LABEL}


# ─── Background queue processor ───────────────────────────────────────────────
async def _process_queue():
    """Continuously dequeue and execute tasks (simulated with async sleep)."""
    global tasks_processed, currently_running
    while True:
        task = await task_queue.get()
        currently_running = {"task_type": task.task_type, "task_id": task.task_id}

        # Scale execution time to 8% of real for snappy demo
        sim_seconds = max(0.4, task.execution_time_ms / 12_500)
        await asyncio.sleep(sim_seconds)

        tasks_processed  += 1
        currently_running = None

        # Update MongoDB task record
        try:
            await db.tasks.update_one(
                {"task_id": task.task_id},
                {"$set": {
                    "status":         "completed",
                    "completed_node": NODE_ID,
                    "completed_at":   datetime.utcnow().isoformat(),
                }},
            )
        except Exception:
            pass

        task_queue.task_done()
