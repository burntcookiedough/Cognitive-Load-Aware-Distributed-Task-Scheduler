"""
Baseline Scheduler — schedules tasks using only CPU / memory / latency.
No cognitive load input.  Used for A/B comparison against CLADS.
"""


def score_node_baseline(node: dict) -> float:
    """Score node purely on system metrics, ignoring task disruption and CLS."""
    cpu_avail    = 1.0 - node["cpu_usage"] / 100.0
    mem_avail    = 1.0 - node["memory_usage"] / 100.0
    latency_norm = 1.0 - min(1.0, node["latency_to_user_ms"] / 200.0)
    queue_pen    = min(1.0, node["queue_length"] / 10.0)

    return (
        0.40 * cpu_avail
        + 0.30 * mem_avail
        + 0.25 * latency_norm
        - 0.05 * queue_pen
    )


def select_node_baseline(nodes: dict) -> tuple:
    """
    Select best node using baseline (system-only) metrics.

    Returns (node_id, "baseline_schedule", reason, scored_nodes)
    """
    scored = {
        nid: score_node_baseline(metrics)
        for nid, metrics in nodes.items()
        if metrics.get("status") == "active"
    }

    if not scored:
        return "node1", "baseline_schedule", "Fallback: no metrics", {}

    best_node = max(scored, key=scored.get)
    reason    = (
        f"Baseline: selected {best_node} by CPU/mem/latency score "
        f"({scored[best_node]:.3f}) — CLS not considered"
    )
    return best_node, "baseline_schedule", reason, scored
