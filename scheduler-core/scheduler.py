"""
CLADS Scheduler — scores nodes and selects the best one for a task.

NodeScore(n) = w1·cpu_avail(n) + w2·mem_avail(n)
             - w3·latency_norm(n)
             - w4·disruption_penalty(task, CLS)
             - w5·queue_penalty(n)

The disruption penalty scales with both the task's disruption score and the
current CLS state, directly encoding the CLS-aware scheduling logic.
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

    # Multi-User Arbitration
    # Penalise node if global cluster is under high aggregate cognitive load, preserving resources
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
) -> tuple:
    """
    Select the best node for a task given the current CLS state and cluster-wide arbitration.

    Returns (node_id, policy_decision, reason, scored_nodes)
    """
    policy          = get_policy(cls_state, task.get("disruption_class", "MEDIUM"))
    preferred_order = get_preferred_nodes(policy)
    reason          = get_reason(policy)

    # Score every active node
    scored = {}
    for node_id, metrics in nodes.items():
        if metrics.get("status") == "active":
            scored[node_id] = score_node(metrics, task, cls_state, global_cluster_cls)

    if not scored:
        return "node1", policy, "Fallback: no metrics available", {}

    # SLA Bypass logic: If urgency is high and expected queue delay everywhere is bad, skip preferred and force fastest CPU
    max_score_node = max(scored.items(), key=lambda x: x[1])[0]

    # Re-rank by preference then by score within preferred groups
    def sort_key(item):
        nid, sc = item
        pref = preferred_order.index(nid) if nid in preferred_order else 99
        return (pref, -sc)

    ranked    = sorted(scored.items(), key=sort_key)
    best_node = ranked[0][0]

    return best_node, policy, reason, scored
