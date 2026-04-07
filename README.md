# CLADS — Cognitive Load-Aware Distributed Task Scheduler

> **Final-Year Project + Patent-Oriented Prototype**  
> Computes a Cognitive Load Score (CLS) from non-physiological interaction telemetry and uses it jointly with system metrics to schedule, delay, and migrate tasks across a simulated distributed cluster.

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Compose v2
- [Node.js 20+](https://nodejs.org/) (for the React dashboard)

### 1. Start all backend services

```bash
cd e:/Distributed/clads
docker compose up --build
```

This brings up:
| Container              | Port  | Role                          |
|------------------------|-------|-------------------------------|
| `clads-mongodb`        | 27017 | Persistent storage            |
| `clads-redis`          | 6379  | CLS cache + rolling windows   |
| `clads-cognitive-load` | 8001  | CLS computation service       |
| `clads-task-annotator` | 8002  | Task disruption annotator     |
| `clads-scheduler`      | 8003  | Scheduling + migration engine |
| `clads-node1`          | 8011  | Local/low-latency worker      |
| `clads-node2`          | 8012  | Balanced worker               |
| `clads-node3`          | 8013  | Background/remote worker      |

### 2. Start the React dashboard

```bash
cd e:/Distributed/clads/client-dashboard
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Architecture

```
Browser (React Dashboard)
   │
   ├── Telemetry Agent (keyboard/idle/tab/focus) ──► cognitive-load-service:8001
   │                                                      (Redis rolling window → CLS score)
   │
   └── Task Submission ──► task-annotator:8002 ──► scheduler-core:8003
                              (disruption score)        │
                                                        ├── node1:8011 (local)
                                                        ├── node2:8012 (balanced)
                                                        └── node3:8013 (background)
```

---

## CLS Formula

```
CLS = α₁·idle_time + α₂·typing_variance + α₃·tab_switch_rate
    + α₄·context_switch_rate + α₅·focus_change_count

α = [0.25, 0.25, 0.20, 0.20, 0.10]
```

State transitions use hysteresis (2–3 consecutive windows required).

---

## Disruption Score Formula

```
Dk = β₁·ui_blocking + β₂·notification + β₃·cpu + β₄·memory + β₅·io

β = [0.35, 0.25, 0.20, 0.12, 0.08]

0.00–0.33 → LOW  |  0.34–0.66 → MEDIUM  |  0.67–1.00 → HIGH
```

---

## Policy Table

| CLS ↓ / Disruption → | LOW         | MEDIUM       | HIGH              |
|-----------------------|-------------|--------------|-------------------|
| LOW                   | local       | local        | local             |
| MEDIUM                | local       | balanced     | background        |
| HIGH                  | local       | delayed      | **remote/delayed**|

---

## API Reference

### Cognitive Load Service (`:8001`)
- `POST /telemetry` — ingest telemetry batch
- `GET  /cls/{user_id}` — current CLS state
- `DELETE /cls/{user_id}/reset` — reset for demos

### Task Annotator (`:8002`)
- `POST /annotate` — annotate a task with disruption metadata
- `GET  /profiles` — all task profile definitions

### Scheduler Core (`:8003`)
- `POST /schedule` — schedule a task (CLADS or BASELINE mode)
- `GET  /decisions` — recent scheduler decisions
- `GET  /decisions/stats` — aggregated stats for charts
- `GET  /nodes/metrics` — live metrics from all nodes

---

## Project Modules

| Module | Key Files | Purpose |
|--------|-----------|---------|
| Telemetry Agent | `src/hooks/useTelemetry.js` | Captures browser interaction signals |
| CLS Engine | `cognitive-load-service/` | Rolling windows, normalisation, hysteresis |
| Task Annotator | `task-annotator/` | Disruption score + class per task type |
| Scheduler Core | `scheduler-core/` | CLADS + Baseline schedulers, migration engine |
| Worker Nodes | `cluster-nodes/` | 3 simulated compute nodes |
| Dashboard | `client-dashboard/` | React UI — Live Monitor, Task Launcher, Analytics |

---

## Demo Flow (Viva / Patent Discussion)

1. Open dashboard → all 3 nodes shown as Active
2. Type steadily → CLS stays LOW → submit **Build** → assigned to node1 (local)
3. Rapidly switch tabs, pause typing → CLS rises to **HIGH**
4. Submit **Deploy** → CLADS routes to node3 (remote), not node1
5. Switch to **BASELINE** mode → same task goes to node1 regardless of CLS
6. Open **Analytics** → compare node distributions + high-load decisions
7. Open **Decision Log** → filter by `HIGH CLS` to show all routed tasks + reasons

---

## Patent-Relevant Technical Claims

1. **Interaction-only telemetry** — no EEG/camera/wearables
2. **CLS as a first-class scheduler parameter** — directly controls node selection
3. **Disruption-aware task model** — UI blocking + notification factor, not just CPU
4. **Hysteresis-stabilised state transitions** — avoids noisy CLS flipping
5. **Dynamic migration on CLS transitions** — active tasks moved when user load spikes
6. **Human-state + system-state joint scheduling** — unique combination
