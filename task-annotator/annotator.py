import uuid
from task_profiles import TASK_PROFILES, DEFAULT_PROFILE
from disruption_model import compute_disruption_score, classify_disruption


def annotate_task(user_id: str, task_type: str, scheduler_mode: str = "CLADS") -> dict:
    """
    Attach full disruption metadata to a task request.

    Returns a fully annotated task dict ready for the scheduler.
    """
    profile = TASK_PROFILES.get(task_type, DEFAULT_PROFILE)

    disruption_score = compute_disruption_score(profile)
    disruption_class = classify_disruption(disruption_score)

    return {
        "task_id":             str(uuid.uuid4())[:8],
        "user_id":             user_id,
        "task_type":           task_type,
        "cpu_profile":         profile["cpu_profile"],
        "mem_profile":         profile["mem_profile"],
        "io_profile":          profile["io_profile"],
        "ui_blocking_factor":  profile["ui_blocking_factor"],
        "notification_factor": profile["notification_factor"],
        "disruption_score":    disruption_score,
        "disruption_class":    disruption_class,
        "latency_sla_ms":      profile["latency_sla_ms"],
        "execution_time_ms":   profile["execution_time_ms"],
        "is_migratable":       profile["is_migratable"],
        "urgency_class":       profile.get("urgency_class", "standard"),
        "checkpoint_size_mb":  profile.get("checkpoint_size_mb", 0),
        "transfer_cost_ms":    profile.get("transfer_cost_ms", 0),
        "resume_penalty_ms":   profile.get("resume_penalty_ms", 0),
        "phases":              profile.get("phases", []),
        "scheduler_mode":      scheduler_mode,
    }
