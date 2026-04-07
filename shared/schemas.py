from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class TelemetryEvent(BaseModel):
    user_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    keystrokes: int = 0
    avg_inter_key_interval: float = 0.0  # ms between consecutive keys
    typing_variance: float = 0.0          # variance of inter-key intervals
    idle_duration: float = 0.0            # seconds of idle time in this window
    tab_switches: int = 0
    focus_changes: int = 0
    context_switches: int = 0


class CLSState(BaseModel):
    user_id: str
    current_cls: float = 0.0
    state: str = "LOW"                    # LOW | MEDIUM | HIGH
    features: Dict[str, float] = {}
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    # Addition 1 — CPU Governor (Claim 2)
    cpu_governor_directive: Optional[Dict[str, Any]] = None
    # Addition 3 — Flow State (Claim 5)
    flow_state_locked: bool = False
    flow_streak: int = 0
    accumulated_flow_credit: float = 0.0
    # Addition 2 — Predictive (Claim 4)
    predicted_cls: float = 0.0
    probability_high: float = 0.0
    trend_slope: float = 0.0
    estimated_breach_seconds: Optional[float] = None


class TaskRequest(BaseModel):
    user_id: str
    task_type: str  # build | test_run | lint | ai_request | deploy | autosave | indexing | dependency_install
    scheduler_mode: str = "CLADS"  # CLADS | BASELINE


class TaskAnnotated(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str
    task_type: str
    cpu_profile: float
    mem_profile: float
    io_profile: float
    ui_blocking_factor: float
    notification_factor: float
    disruption_score: float
    disruption_class: str                  # LOW | MEDIUM | HIGH
    latency_sla_ms: int
    execution_time_ms: int
    is_migratable: bool = True
    scheduler_mode: str = "CLADS"
    # Addition 4 — Dk Vector (Claim 1 reframing)
    disruption_vector: Optional[Dict[str, float]] = None
    human_perceptual_weight_ratio: float = 0.0


class NodeMetrics(BaseModel):
    node_id: str
    node_label: str = ""
    cpu_usage: float
    memory_usage: float
    queue_length: int
    latency_to_user_ms: float
    status: str = "active"
    tasks_processed: int = 0


class ScheduleRequest(BaseModel):
    task: TaskAnnotated
    scheduler_mode: str = "CLADS"


class SchedulerDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    task_id: str
    user_id: str
    task_type: str
    cls_state: str
    cls_score: float
    disruption_class: str
    disruption_score: float
    assigned_node: str
    decision: str   # local_schedule | balanced_schedule | background_schedule | delayed_schedule | remote_schedule
    reason: str
    scheduler_mode: str  # CLADS | BASELINE
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completion_time_ms: Optional[int] = None
    # Addition 2 — Predictive migration (Claim 4)
    preemptive_migration_triggered: bool = False
    # Addition 3 — Flow State (Claim 5)
    flow_state_locked: bool = False
    flow_state_override: bool = False
    # Addition B — Latency Probe (Section 11)
    foreground_latency_ms: Optional[float] = None
    # Addition C — Team CLS (Claim 7)
    aggregate_cls_score: Optional[float] = None
    aggregate_cls_state: Optional[str] = None
