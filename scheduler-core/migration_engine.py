"""
Migration Engine — triggered when the user's CLS transitions from LOW/MEDIUM → HIGH.

Scans all active tasks for the user and:
  1. Migrates HIGH-disruption migratable tasks to node3 (background).
  2. Reduces effective priority for non-migratable HIGH-disruption tasks.
  3. Logs all migration decisions.
"""

import json
import random
from datetime import datetime
from typing import Optional


async def run_migration_check(
    user_id: str,
    new_cls_state: str,
    old_cls_state: str,
    db,
    node_clients: dict,          # {node_id: httpx.AsyncClient}
) -> list:
    """
    Called after a CLS state upgrade (e.g. MEDIUM → HIGH).
    Returns a list of migration action dicts.
    """
    if new_cls_state != "HIGH" or old_cls_state == "HIGH":
        return []  # Only act on transitions INTO HIGH

    # Find running or queued tasks for this user
    active_tasks = await db.tasks.find(
        {
            "user_id": user_id,
            "status":  {"$in": ["running", "queued"]},
        },
        {"_id": 0},
    ).to_list(length=50)

    actions = []
    for task in active_tasks:
        if task.get("disruption_class") == "HIGH" and task.get("is_migratable", False):
            # 1. Cost analysis
            chkpnt = task.get("checkpoint_size_mb", 50) * 10
            transf = task.get("transfer_cost_ms", 400)
            resume = task.get("resume_penalty_ms", 200)
            migration_cost = chkpnt + transf + resume
            
            # Phase safety logic (Prototype approximation: randomly 10% unsafe)
            unsafe_phase = (random.random() < 0.15)
            if unsafe_phase:
                actions.append({
                    "task_id":     task["task_id"],
                    "user_id":     user_id,
                    "action":      "phase_bound_pause",
                    "reason":      "Task in unsafe phase (e.g. active IO). Pausing until safe boundary.",
                    "timestamp":   datetime.utcnow().isoformat(),
                })
                continue

            # If cost is exceptionally high, throttle instead of migrating
            if migration_cost > 2500:
                actions.append({
                    "task_id":     task["task_id"],
                    "user_id":     user_id,
                    "action":      "throttle_cpu",
                    "reason":      f"Migration cost ({migration_cost}) exceeds threshold. Throttling local CPU instead.",
                    "timestamp":   datetime.utcnow().isoformat(),
                })
                # Update task DB logic left as stub...
                continue
                
            # Simulate Failure-Safe checkpoint & transfer
            failure_simulated = (random.random() < 0.05) # 5% chance of failure
            if failure_simulated:
                actions.append({
                    "task_id":     task["task_id"],
                    "user_id":     user_id,
                    "action":      "rollback_migration",
                    "reason":      "State transfer failed/integrity error. Rolling back to local execution.",
                    "timestamp":   datetime.utcnow().isoformat(),
                })
                continue

            action = {
                "task_id":     task["task_id"],
                "user_id":     user_id,
                "action":      "migrate_to_background",
                "from_node":   task.get("assigned_node", "node1"),
                "to_node":     "node3",
                "reason":      "CLS transitioned to HIGH — high-disruption migratable task moved to background node",
                "timestamp":   datetime.utcnow().isoformat(),
                "cls_trigger": new_cls_state,
            }

            # Attempt to notify destination node (best-effort)
            try:
                client = node_clients.get("node3")
                if client:
                    await client.post("/migrate", json={
                        "task_id":    task["task_id"],
                        "task_type":  task.get("task_type", "unknown"),
                        "from_node":  action["from_node"],
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

            actions.append(action)

        elif task.get("disruption_class") == "HIGH" and not task.get("is_migratable", True):
            # Non-migratable — log deprioritise action
            actions.append({
                "task_id":   task["task_id"],
                "user_id":   user_id,
                "action":    "deprioritize",
                "reason":    "CLS HIGH — non-migratable task deprioritised",
                "timestamp": datetime.utcnow().isoformat(),
            })

    return actions
