import os
import sys
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app")

from annotator import annotate_task
from task_profiles import TASK_PROFILES

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="CLADS — Task Annotator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
db = None


@app.on_event("startup")
async def startup():
    global db
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.clads


# ─── Request models ───────────────────────────────────────────────────────────
class TaskRequest(BaseModel):
    user_id: str
    task_type: str
    scheduler_mode: str = "CLADS"


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/annotate")
async def annotate(request: TaskRequest):
    """
    Annotate a task with disruption metadata.
    Returns a fully enriched task object ready for the scheduler.
    """
    if request.task_type not in TASK_PROFILES and request.task_type != "unknown":
        # Accept unknown tasks with default profile, but warn
        pass

    annotated = annotate_task(request.user_id, request.task_type, request.scheduler_mode)

    # Persist to MongoDB
    try:
        await db.tasks.insert_one({
            **annotated,
            "status":       "annotated",
            "annotated_at": datetime.utcnow().isoformat(),
        })
    except Exception:
        pass

    return annotated


@app.get("/profiles")
async def list_profiles():
    """Return all task type profiles with full Dk vector decomposition (Claim 1 evidence)."""
    from disruption_model import (
        compute_disruption_score, classify_disruption,
        compute_disruption_vector, DISRUPTION_WEIGHTS,
    )
    result = {}
    for task_type, profile in TASK_PROFILES.items():
        score  = compute_disruption_score(profile)
        vector = compute_disruption_vector(profile)
        result[task_type] = {
            **profile,
            "disruption_score":  score,
            "disruption_class":  classify_disruption(score),
            "disruption_vector": vector,
            "human_perceptual_weight_ratio": round(
                vector["perceptual_sum"] / vector["hardware_sum"], 4
            ) if vector["hardware_sum"] > 0 else None,
        }
    return result


@app.get("/disruption-model/info")
async def disruption_model_info():
    """
    Return the β weight vector with patent hierarchy documentation.
    Claim 1: β₁(ui_blocking)+β₂(notification) > β₃(cpu)+β₄(memory)+β₅(io)
    """
    from disruption_model import DISRUPTION_WEIGHTS, vector_hierarchy_satisfied
    perceptual_sum = DISRUPTION_WEIGHTS["ui_blocking"] + DISRUPTION_WEIGHTS["notification"]
    hardware_sum   = DISRUPTION_WEIGHTS["cpu"] + DISRUPTION_WEIGHTS["memory"] + DISRUPTION_WEIGHTS["io"]
    return {
        "weights":          DISRUPTION_WEIGHTS,
        "perceptual_sum":   round(perceptual_sum, 4),
        "hardware_sum":     round(hardware_sum, 4),
        "hierarchy_satisfied": perceptual_sum > hardware_sum,
        "patent_note": (
            "Claim 1 inventive step: human-perceptual weights (β₁+β₂) intentionally "
            "exceed hardware weights (β₃+β₄+β₅). This ordering ranks a task's "
            "human-perceptibility above its hardware cost in the scheduling penalty vector."
        ),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "task-annotator"}
