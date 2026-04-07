# CLADS

**Cognitive Load-Aware Distributed Task Scheduler**

CLADS is a distributed scheduling prototype that combines human cognitive state with system telemetry to decide where a task should run, whether it should be delayed, and when it should be migrated. Instead of relying only on CPU, memory, and queue depth, CLADS continuously estimates a **Cognitive Load Score (CLS)** from non-physiological interaction signals such as typing variance, idle time, tab switches, context switches, and focus changes.

This repository contains a complete multi-service prototype built for final-year project demonstration, experimentation, and patent-oriented documentation.

---

## Overview

CLADS is designed around one core idea:

> **Scheduling decisions should account for the user's mental load, not only machine load.**

The platform captures browser interaction telemetry, converts it into a rolling CLS signal, classifies incoming tasks by human disruption cost, and routes work across a small distributed cluster of simulated worker nodes.

The current implementation includes:

- Real-time cognitive load estimation from browser interaction telemetry
- Disruption-aware task annotation with perceptual-first weighting
- CLADS scheduling and baseline scheduling for side-by-side comparison
- Predictive migration logic based on rising CLS trends
- Flow-state protection to keep high-disruption tasks away from focused users
- Adaptive scheduling weight calibration
- Team-wide aggregate CLS support for multi-user arbitration
- A React dashboard for live monitoring, task launching, decision review, and analytics

---

## Architecture

```text
React Dashboard (Vite + React)
  |
  |-- Browser telemetry stream --------------------------> Cognitive Load Service (:8001)
  |                                                        |- rolling telemetry window in Redis
  |                                                        |- CLS scoring + hysteresis
  |                                                        |- predictive CLS
  |                                                        |- flow-state lock
  |                                                        |- CPU governor directive simulation
  |
  |-- Task request -------------------------------------> Task Annotator (:8002)
                                                           |- disruption score
                                                           |- task profile enrichment
                                                           v
                                                       Scheduler Core (:8003)
                                                         |- CLADS policy engine
                                                         |- baseline scheduler
                                                         |- preemptive migration logic
                                                         |- latency benchmarking
                                                         |- team CLS aggregation
                                                         v
                           -------------------------------------------------------------
                           |                           |                              |
                        Node 1                       Node 2                         Node 3
                      Local (:8011)               Balanced (:8012)             Background (:8013)
```

### Runtime services

| Service | Port | Purpose |
|---|---:|---|
| `clads-mongodb` | `27017` | Persistent storage for telemetry, tasks, decisions, and logs |
| `clads-redis` | `6380 -> 6379` | Rolling windows, CLS cache, and transient state |
| `clads-cognitive-load` | `8001` | CLS computation, prediction, flow-state logic |
| `clads-task-annotator` | `8002` | Disruption modeling and task enrichment |
| `clads-scheduler` | `8003` | Scheduling, migration, node scoring, analytics |
| `clads-node1` | `8011` | Local low-latency worker |
| `clads-node2` | `8012` | Balanced worker |
| `clads-node3` | `8013` | Background/remote worker |
| `client-dashboard` | `5173` | Frontend dashboard during local development |

---

## Core Model

### 1. Cognitive Load Score

CLADS computes a **Cognitive Load Score (CLS)** from interaction-only telemetry.

```text
CLS = α1·idle_time
    + α2·typing_variance
    + α3·tab_switch_rate
    + α4·context_switch_rate
    + α5·focus_change_count
```

### CLS weights

| Feature | Weight |
|---|---:|
| `idle_time` | `0.25` |
| `typing_variance` | `0.25` |
| `tab_switch_rate` | `0.20` |
| `context_switch_rate` | `0.20` |
| `focus_change_count` | `0.10` |

### Hysteresis

To avoid noisy state oscillation, CLS transitions are stabilized with a hysteresis controller:

- `LOW -> MEDIUM`: threshold `0.45`, requires `2` windows
- `MEDIUM -> HIGH`: threshold `0.75`, requires `2` windows
- `HIGH -> MEDIUM`: threshold `0.65`, requires `3` windows
- `MEDIUM -> LOW`: threshold `0.35`, requires `3` windows

This means the user state changes only after repeated evidence, not on a single spike.

---

### 2. Disruption Score

Each task is annotated with a **disruption score** representing how interruptive it is to the user.

```text
Dk = β1·ui_blocking
   + β2·notification
   + β3·cpu
   + β4·memory
   + β5·io
```

### Disruption weights

| Factor | Weight |
|---|---:|
| `ui_blocking` | `0.35` |
| `notification` | `0.25` |
| `cpu` | `0.20` |
| `memory` | `0.12` |
| `io` | `0.08` |

### Disruption classes

| Score Range | Class |
|---|---|
| `0.00 - 0.33` | `LOW` |
| `0.34 - 0.66` | `MEDIUM` |
| `0.67 - 1.00` | `HIGH` |

The implementation intentionally makes the sum of perceptual weights (`ui_blocking + notification = 0.60`) greater than the sum of hardware weights (`cpu + memory + io = 0.40`), reflecting the system's human-centric design.

---

### 3. Node Scoring

The scheduler evaluates each worker node using a weighted score:

```text
NodeScore(n) =
  w1·cpu_availability
  + w2·mem_availability
  + w3·latency_preference
  - w4·disruption_penalty
  - w5·queue_penalty
  - sla_penalty
  - arbitration_penalty
```

### Scheduler weights

| Signal | Weight |
|---|---:|
| CPU availability | `0.30` |
| Memory availability | `0.25` |
| Latency | `0.25` |
| Disruption penalty | `0.15` |
| Queue penalty | `0.05` |

### CLS-aware routing policy

| CLS State | Disruption LOW | Disruption MEDIUM | Disruption HIGH |
|---|---|---|---|
| `LOW` | Local | Local | Local |
| `MEDIUM` | Local | Balanced | Background |
| `HIGH` | Local | Delayed | Remote / Delayed |

---

## Advanced Features Implemented

### Predictive CLS and preemptive migration

The cognitive load service stores recent CLS history and estimates:

- `predicted_cls`
- `probability_high`
- `trend_slope`
- `estimated_breach_seconds`

The scheduler can use those signals to trigger **preemptive migration** before the user's state fully reaches `HIGH`.

### Flow-state protection

When a user remains in a sustained low-load window, CLADS can mark them as being in a protected flow state. If the flow lock is active and a `HIGH` disruption task arrives, the scheduler can force it to the background node even if raw infrastructure metrics suggest otherwise.

Default threshold:

- `FLOW_STATE_THRESHOLD = 180`
- With `WINDOW_UPDATE_INTERVAL = 5s`, this corresponds to roughly **15 minutes** of sustained low-load interaction

### CPU governor directives

The cognitive load service also computes a CPU governor directive per CLS state:

- `LOW`: full performance
- `MEDIUM`: balanced foreground boost / background conservation
- `HIGH`: foreground protection with background throttling

By default, this runs in simulation mode and is logged as structured output.

### Adaptive weight calibration

The scheduler contains a weight calibration module that records decisions and later updates user-specific weight profiles after enough samples accumulate.

### Team CLS aggregation

The scheduler can aggregate multiple users' CLS states into a cluster-wide arbitration signal, enabling multi-tenant scheduling experiments rather than only single-user routing.

### Latency benchmarking

The system records foreground scheduling latency and exposes a benchmark summary endpoint so CLADS can be compared with baseline mode using the same workload.

---

## Task Catalog

The dashboard and task annotator currently support the following task types:

| Task Type | Category | Typical Disruption |
|---|---|---|
| `build` | `HIGH` | CPU-heavy and visibly disruptive |
| `deploy` | `HIGH` | Urgent, high interruption potential |
| `dependency_install` | `HIGH` | IO-heavy with moderate/high interruption |
| `test_run` | `MEDIUM` | Moderate execution and feedback cost |
| `ai_request` | `MEDIUM` | Interactive compute-heavy request |
| `static_analysis` | `MEDIUM` | Background-capable analysis |
| `lint` | `LOW` | Light and short |
| `indexing` | `LOW` | Background-friendly file indexing |
| `autosave` | `LOW` | Minimal disruption |

Unknown tasks are still accepted with a default medium profile.

---

## Repository Structure

```text
.
|-- client-dashboard/         React frontend for live monitoring and analytics
|-- cluster-nodes/            Generic worker node service used by node1/node2/node3
|-- cognitive-load-service/   CLS engine, prediction, hysteresis, flow-state logic
|-- scheduler-core/           CLADS scheduler, baseline scheduler, migration engine
|-- shared/                   Shared configuration and schema helpers
|-- task-annotator/           Task enrichment and disruption scoring
|-- docker-compose.yml        Full local stack orchestration
|-- run_tests.py              Demo workload + benchmark collection script
|-- benchmark_results.json    Sample benchmark output artifact
```

### Frontend pages

The React dashboard exposes four main views:

- `Live Monitor`
- `Task Launcher`
- `Decision Log`
- `Analytics`

---

## Local Setup

### Prerequisites

- Docker Desktop with Docker Compose v2
- Node.js `20+`
- Python `3.11+` recommended for local utility scripts

### 1. Start backend services

From the repository root:

```bash
docker compose up --build
```

This will build and start MongoDB, Redis, the three backend APIs, and all three worker nodes.

### 2. Start the frontend

Open a second terminal:

```bash
cd client-dashboard
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

## Default Local Endpoints

### Frontend

- Dashboard: `http://localhost:5173`

### Backend APIs

- Cognitive Load Service: `http://localhost:8001`
- Task Annotator: `http://localhost:8002`
- Scheduler Core: `http://localhost:8003`

### Worker Nodes

- Node 1: `http://localhost:8011`
- Node 2: `http://localhost:8012`
- Node 3: `http://localhost:8013`

### Datastores

- MongoDB: `mongodb://localhost:27017`
- Redis: `localhost:6380`

Note that inside Docker, Redis is addressed as `redis:6379`; the host-side mapping exposes it on port `6380`.

---

## API Reference

### Cognitive Load Service `:8001`

### `POST /telemetry`

Ingest a telemetry event and recompute CLS.

Example payload:

```json
{
  "user_id": "u_shagun",
  "keystrokes": 24,
  "avg_inter_key_interval": 54.0,
  "typing_variance": 180.0,
  "idle_duration": 2.0,
  "tab_switches": 1,
  "focus_changes": 1,
  "context_switches": 1
}
```

### `GET /cls/{user_id}`

Returns the current CLS state, predictive fields, feature breakdown, flow-state lock, and governor directive.

### `GET /cls-history/{user_id}`

Returns recent CLS history for analytics.

### `GET /governor/{user_id}`

Returns the current governor policy for the user.

### `GET /governor/log`

Returns recent governor directive log entries.

### `PUT /flow-config`

Updates the runtime flow-state threshold.

Example payload:

```json
{
  "threshold": 180
}
```

### `GET /flow-state/{user_id}`

Returns current flow-state status and streak data.

### `DELETE /cls/{user_id}/reset`

Resets telemetry and CLS-related transient state for a user.

### `GET /health`

Health probe for the service.

---

### Task Annotator `:8002`

### `POST /annotate`

Annotates a task with disruption metadata and profile information.

Example payload:

```json
{
  "user_id": "u_shagun",
  "task_type": "build",
  "scheduler_mode": "CLADS"
}
```

### `GET /profiles`

Returns task profiles, disruption scores, and vector decomposition for all known task types.

### `GET /disruption-model/info`

Returns the disruption weight vector and hierarchy metadata.

### `GET /health`

Health probe for the service.

---

### Scheduler Core `:8003`

### `POST /schedule`

Schedules an already annotated task.

Example payload:

```json
{
  "task": {
    "task_id": "task-001",
    "user_id": "u_shagun",
    "task_type": "build",
    "disruption_class": "HIGH",
    "disruption_score": 0.95,
    "latency_sla_ms": 10000,
    "execution_time_ms": 8000
  },
  "scheduler_mode": "CLADS"
}
```

### `GET /decisions`

Returns recent scheduling decisions. Supports optional `user_id`.

### `GET /decisions/stats`

Returns aggregate decision counts and averages for dashboard charts.

### `GET /preemptive-migrations`

Returns preemptive migration history and prediction accuracy summary.

### `GET /weight-profiles`

Lists all calibrated user weight profiles.

### `GET /weight-profiles/{user_id}`

Returns the calibrated weight profile for a specific user.

### `GET /benchmarks/summary`

Returns latency benchmark breakdown used to compare CLADS against baseline.

### `GET /team-cls`

Returns the cluster-wide composite CLS aggregate.

### `GET /nodes/metrics`

Returns live worker-node metrics.

### `GET /health`

Health probe for the service.

---

### Worker Node APIs `:8011`, `:8012`, `:8013`

### `POST /submit`

Queue a task on a worker.

### `POST /migrate`

Accept a migrated task.

### `GET /metrics`

Return current CPU, memory, queue length, latency, and activity state.

### `GET /health`

Health probe for the worker.

---

## How the Demo Works

### Recommended demo flow

1. Start the full stack with Docker Compose.
2. Start the React dashboard.
3. Open `Live Monitor` and watch node metrics update.
4. Interact normally with the page to generate low-load telemetry.
5. Launch a `build` or `test_run` task in `CLADS` mode.
6. Increase context switching and pauses to drive CLS upward.
7. Launch a `deploy` or `build` task again and compare the assigned node.
8. Switch to `BASELINE` mode and submit the same task type.
9. Open `Decision Log` and `Analytics` to compare routing behavior.

### Expected behavior

- Under `LOW` CLS, disruptive tasks can still stay local.
- Under `MEDIUM` CLS, disruptive tasks drift toward balanced or background nodes.
- Under `HIGH` CLS, CLADS should favor remote/background handling or delay logic.
- In `BASELINE` mode, task placement ignores cognitive load and is driven only by node metrics.

---

## Benchmarking and Verification

The repository includes a simple asynchronous workload generator:

- Script: `run_tests.py`
- Output artifact: `benchmark_results.json`

The script:

- Sends telemetry to push users through rising CLS conditions
- Schedules the same workload in both `CLADS` and `BASELINE` modes
- Waits for asynchronous accuracy checks
- Pulls benchmark summaries and preemptive migration records
- Saves the result to `benchmark_results.json`

Run it after the stack is up:

```bash
python run_tests.py
```

Current sample benchmark data in the repository contains latency breakdown entries, but the headline `HIGH CLS x HIGH Dk` comparison fields are still `null`, so benchmark evidence is present but not yet complete for that scenario.

---

## Development Notes

### Frontend stack

- React `18`
- Vite `5`
- React Router `6`
- Chart.js `4`
- Axios

### Backend stack

- FastAPI
- Pydantic v2
- MongoDB with Motor
- Redis asyncio client
- HTTPX
- NumPy in the cognitive load service

### Environment notes

The services are configured primarily through environment variables exposed in `docker-compose.yml` and shared defaults in `shared/config.py`.

Important runtime knobs include:

- `REDIS_URL`
- `MONGODB_URI`
- `COGNITIVE_LOAD_URL`
- `FLOW_STATE_THRESHOLD`
- `REAL_GOVERNOR`
- `PREEMPTIVE_MIGRATION_PROB_THRESHOLD`
- `ADAPTIVE_WEIGHT_LEARNING_RATE`

---

## Research and Patent-Oriented Claims Reflected in Code

The codebase explicitly implements the following claim-oriented ideas:

1. Interaction-only cognitive load estimation without EEG, camera, or wearables
2. CLS-aware CPU governor directive generation
3. Hysteresis-stabilized cognitive-state transitions
4. Predictive migration before a user fully enters `HIGH` CLS
5. Flow-state protection that overrides normal scoring for highly disruptive tasks
6. Adaptive user-specific weight calibration
7. Team-level aggregate CLS for multi-user scheduling arbitration

These concepts are visible in the service modules and reflected in the API surface, logs, and benchmark helpers.

---

## Known Constraints

- The worker nodes simulate execution rather than running real workloads.
- CPU and memory readings on worker nodes are synthetic but consistent enough for scheduling experiments.
- The dashboard currently uses a single demo user: `u_shagun`.
- Some benchmark headline fields are not yet populated in the checked-in sample output.
- The existing implementation is optimized for demonstration and experimentation rather than production hardening.

---

## Suggested Next Steps

If you want to extend this prototype, the most useful follow-up work would be:

- Add a formal end-to-end test suite per service
- Persist richer CLS history instead of overwriting current state documents
- Expand multi-user dashboard support beyond the single demo user
- Add authentication and scoped data access
- Replace simulated worker execution with real task adapters
- Export benchmark and patent-evidence reports automatically

---

## License and Usage

This repository appears to be a project and research prototype. If you plan to publish or distribute it, add an explicit license file and any required academic or IP attribution statements.
