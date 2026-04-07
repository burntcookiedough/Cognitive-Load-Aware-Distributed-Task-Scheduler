import uuid
from task_profiles import TASK_PROFILES, DEFAULT_PROFILE
from disruption_model import (
    compute_disruption_score,
    compute_disruption_vector,
    classify_disruption,
    vector_hierarchy_satisfied,
    DISRUPTION_WEIGHTS,
)

# Validate hierarchy invariant at import time — fails fast if weights misconfigured
vector_hierarchy_satisfied()


def annotate_task(user_id: str, task_type: str, scheduler_mode: str = "CLADS", custom_weights: dict = None) -> dict:
    """
    Attach full disruption metadata to a task request.

    Returns a fully annotated task dict ready for the scheduler.
    Includes the decomposed Dk vector and human_perceptual_weight_ratio
    for patent evidence (Claim 1 documentation).
    """
    profile = TASK_PROFILES.get(task_type, DEFAULT_PROFILE)
    weights = custom_weights or DISRUPTION_WEIGHTS

    disruption_score  = compute_disruption_score(profile, weights)
    disruption_class  = classify_disruption(disruption_score)
    disruption_vector = compute_disruption_vector(profile, weights)

    # human_perceptual_weight_ratio = (β₁+β₂) / (β₃+β₄+β₅)
    # PATENT: this ratio is always > 1.0 by Claim 1 invariant
    perceptual_sum = disruption_vector["perceptual_sum"]
    hardware_sum   = disruption_vector["hardware_sum"]
    hp_ratio = round(perceptual_sum / hardware_sum, 4) if hardware_sum > 0 else float("inf")

    return {
        "task_id":                     str(uuid.uuid4())[:8],
        "user_id":                     user_id,
        "task_type":                   task_type,
        "cpu_profile":                 profile["cpu_profile"],
        "mem_profile":                 profile["mem_profile"],
        "io_profile":                  profile["io_profile"],
        "ui_blocking_factor":          profile["ui_blocking_factor"],
        "notification_factor":         profile["notification_factor"],
        "disruption_score":            disruption_score,
        "disruption_class":            disruption_class,
        # Addition 4 — decomposed vector (Claim 1 evidence)
        "disruption_vector":           disruption_vector,
        "human_perceptual_weight_ratio": hp_ratio,
        "latency_sla_ms":              profile["latency_sla_ms"],
        "execution_time_ms":           profile["execution_time_ms"],
        "is_migratable":               profile["is_migratable"],
        "urgency_class":               profile.get("urgency_class", "standard"),
        "checkpoint_size_mb":          profile.get("checkpoint_size_mb", 0),
        "transfer_cost_ms":            profile.get("transfer_cost_ms", 0),
        "resume_penalty_ms":           profile.get("resume_penalty_ms", 0),
        "phases":                      profile.get("phases", []),
        "scheduler_mode":              scheduler_mode,
    }

