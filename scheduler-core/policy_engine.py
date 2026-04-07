"""
Policy Engine — implements the 3×3 CLS × Disruption scheduling table.

CLS State  | LOW disruption | MEDIUM disruption | HIGH disruption
-----------+----------------+-------------------+----------------------
LOW        | local          | local             | local (low-latency)
MEDIUM     | local          | balanced          | background
HIGH       | local (light)  | delayed/balanced  | remote/delayed

Decision codes (used as-is in SchedulerDecision.decision):
  local_schedule      → assign to node1 (lowest latency)
  balanced_schedule   → assign to node2 (balanced)
  background_schedule → assign to node3 (remote/background)
  delayed_schedule    → queue with delay preference on node2/node3
  remote_schedule     → force to node3 regardless of score
"""

POLICY_TABLE = {
    ("LOW",    "LOW"):    "local_schedule",
    ("LOW",    "MEDIUM"): "local_schedule",
    ("LOW",    "HIGH"):   "local_schedule",

    ("MEDIUM", "LOW"):    "local_schedule",
    ("MEDIUM", "MEDIUM"): "balanced_schedule",
    ("MEDIUM", "HIGH"):   "background_schedule",

    ("HIGH",   "LOW"):    "local_schedule",
    ("HIGH",   "MEDIUM"): "delayed_schedule",
    ("HIGH",   "HIGH"):   "remote_schedule",
}

# For each policy, ordered preferred node list
POLICY_NODE_PREFERENCE = {
    "local_schedule":         ["node1", "node2", "node3"],
    "balanced_schedule":      ["node2", "node1", "node3"],
    "background_schedule":    ["node3", "node2", "node1"],
    "delayed_schedule":       ["node2", "node3", "node1"],
    "remote_schedule":        ["node3", "node2", "node1"],
    "throttle_cpu_schedule":  ["node1", "node2", "node3"],
    "suppress_logs_schedule": ["node1", "node2", "node3"],
}

# Human-readable reasons for the dashboard / patent logs
POLICY_REASONS = {
    "local_schedule":         "Low CLS or low disruption — task runs on fastest local node",
    "balanced_schedule":      "Medium CLS with medium disruption — balanced node selected",
    "background_schedule":    "Medium CLS with high disruption — offloaded to background node",
    "delayed_schedule":       "High CLS with medium disruption — routed to non-local node",
    "remote_schedule":        "High CLS with high disruption — forced to remote background node",
    "throttle_cpu_schedule":  "High CLS - CPU heavily throttled to preserve local workflow",
    "suppress_logs_schedule": "High CLS - Notification and log bursts suppressed locally",
}


def get_policy(cls_state: str, disruption_class: str) -> str:
    return POLICY_TABLE.get((cls_state, disruption_class), "balanced_schedule")


def get_preferred_nodes(policy: str) -> list:
    return POLICY_NODE_PREFERENCE.get(policy, ["node1", "node2", "node3"])


def get_reason(policy: str) -> str:
    return POLICY_REASONS.get(policy, "Default scheduling policy applied")
