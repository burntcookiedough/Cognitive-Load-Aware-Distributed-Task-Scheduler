"""
CLADS Scheduler — scores nodes and selects the best one for a task.

NodeScore(n) = w1·cpu_avail(n) + w2·mem_avail(n)
             - w3·latency_norm(n)
             - w4·disruption_penalty(task, CLS)
             - w5·queue_penalty(n)

The disruption penalty scales with both the task's disruption score and the
current CLS state, directly encoding the CLS-aware scheduling logic.

PATENT ADDITIONS:
  - Claim 5: flow_state_locked unconditionally overrides scoring for HIGH-Dk tasks
  - Claim 7: aggregate_cls_state (TeamCLS) drives cluster-wide arbitration penalty
"""

from policy_engine import get_policy, get_preferred_nodes, get_reason

# w weights — must sum ≤ 1.0
WEIGHTS = {
    "cpu_availability":   0.30,
    "mem_availability":   0.25,
    "latency":            0.25,
    "disruption_penalty": 0.15,
    "queue_penalty":      0.05,
}

# CLS → disruption penalty multiplier
CLS_DISRUPTION_MULTIPLIER = {
    "LOW":    0.0,   # ignore disruption when user is relaxed
    "MEDIUM": 0.4,
    "HIGH":   1.0,   # fully apply disruption penalty when user is overloaded
}


def score_node(node: dict, task: dict, cls_state: str, global_cluster_cls: float = 0.0) -> float:
    """Compute scheduling score for a single node. Higher = more preferable."""
    cpu_avail    = 1.0 - node["cpu_usage"] / 100.0
    mem_avail    = 1.0 - node["memory_usage"] / 100.0
    latency_norm = 1.0 - min(1.0, node["latency_to_user_ms"] / 200.0)
    queue_pen    = min(1.0, node["queue_length"] / 10.0)

    disrupt_mult = CLS_DISRUPTION_MULTIPLIER.get(cls_state, 0.5)
    disrupt_pen  = disrupt_mult * task.get("disruption_score", 0.5)

    # Deadline / SLA Awareness
    est_queue_delay_ms = node["queue_length"] * 1500  # prototype estimation
    sla_ms = task.get("latency_sla_ms", 10000)
    sla_penalty = 0.0
    urgency = task.get("urgency_class", "standard")

    if est_queue_delay_ms > sla_ms:
        sla_penalty = 0.4 if urgency == "high" else 0.1

    # Addition C (Claim 7): Cluster-wide arbitration from TeamCLS aggregate.
    # Replaces naive global_cluster_cls mean with proper weighted aggregate.
    arbitration_penalty = global_cluster_cls * 0.15

    return (
        WEIGHTS["cpu_availability"]   * cpu_avail
        + WEIGHTS["mem_availability"] * mem_avail
        + WEIGHTS["latency"]          * latency_norm
        - WEIGHTS["disruption_penalty"] * disrupt_pen
        - WEIGHTS["queue_penalty"]    * queue_pen
        - sla_penalty
        - arbitration_penalty
    )


def select_node(
    nodes: dict,          # {node_id: NodeMetrics dict}
    task: dict,
    cls_state: str,
    cls_score: float,
    global_cluster_cls: float = 0.0,
    flow_state_locked: bool = False,   # Addition 3 (Claim 5)
    aggregate_cls_state: str = None,   # Addition C (Claim 7)
) -> tuple:
    """
    Select the best node for a task given the current CLS state and cluster-wide arbitration.

    PATENT ADDITIONS:
      flow_state_locked: When True AND task disruption_class==HIGH → unconditionally
                         force remote_schedule regardless of node scores (Claim 5).
      aggregate_cls_state: Override arbitration penalty using TeamCLS composite index
                           rather than naive arithmetic mean (Claim 7).

    Returns (node_id, policy_decision, reason, scored_nodes, flow_state_override)
    """
    disruption_class = task.get("disruption_class", "MEDIUM")

    # ── Addition 3 (Claim 5): Flow State Lock Override ─────────────────────────
    # When the user is in a protected flow state AND the task has HIGH disruption,
    # unconditionally defer to remote node regardless of hardware availability.
    flow_state_override = False
    if flow_state_locked and disruption_class == "HIGH":
        policy  = "remote_schedule"
        reason  = (
            "FLOW STATE LOCK: User in sustained low-CLS protected window. "
            "HIGH-Dk task unconditionally deferred to background node."
        )
        preferred_order = get_preferred_nodes(policy)
        flow_state_override = True
        # Score nodes anyway for transparency, but result is forced
        scored = {}
        for node_id, metrics in nodes.items():
            if metrics.get("status") == "active":
                scored[node_id] = score_node(metrics, task, cls_state, global_cluster_cls)
        best_node = next(
            (n for n in preferred_order if n in scored and nodes[n].get("status") == "active"),
            "node3",
        )
        return best_node, policy, reason, scored, flow_state_override

    # ── Normal scoring path ─────────────────────────────────────────────────────
    # Use aggregate_cls_state for cluster-wide policy if provided (Claim 7)
    effective_cls = aggregate_cls_state if aggregate_cls_state else cls_state

    policy          = get_policy(effective_cls, disruption_class)
    preferred_order = get_preferred_nodes(policy)
    reason          = get_reason(policy)

    # Score every active node
    scored = {}
    for node_id, metrics in nodes.items():
        if metrics.get("status") == "active":
            scored[node_id] = score_node(metrics, task, cls_state, global_cluster_cls)

    if not scored:
        return "node1", policy, "Fallback: no metrics available", {}, False

    # Re-rank by preference then by score within preferred groups
    def sort_key(item):
        nid, sc = item
        pref = preferred_order.index(nid) if nid in preferred_order else 99
        return (pref, -sc)

    ranked    = sorted(scored.items(), key=sort_key)
    best_node = ranked[0][0]

    return best_node, policy, reason, scored, False

