import os

os.makedirs("patent-figures", exist_ok=True)

html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Figure {fig_num}</title>
    <style>
        body {{
            background-color: white;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }}
        .mermaid {{
            background-color: white;
            padding: 2rem;
            border-radius: 8px;
            font-size: 16px;
        }}
        /* Force consistent formal line thicknesses where Mermaid misses them */
        .mermaid .node rect, .mermaid .node circle, .mermaid .node ellipse, .mermaid .node polygon {{
            stroke-width: 2px !important;
        }}
        .html-table-wrapper table {{
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            margin: 25px 0;
            font-size: 18px;
            min-width: 400px;
            box-shadow: none;
            border: 2px solid #000;
        }}
        .html-table-wrapper th, .html-table-wrapper td {{
            padding: 15px 20px;
            border: 2px solid #000;
            text-align: center;
        }}
        .html-table-wrapper th {{
            background-color: #fff;
            color: #000;
            font-weight: bold;
            border-bottom: 2px solid #000;
        }}
        .html-table-wrapper tbody td.bold-row {{
            font-weight: bold;
            border-right: 2px solid #000;
        }}
        .html-table-wrapper h2 {{
            text-align: center;
            color: #000;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="{div_class}">
{mermaid_code}
    </div>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ 
          startOnLoad: true, 
          theme: 'base',
          themeVariables: {{
              primaryColor: '#ffffff',
              primaryTextColor: '#000000',
              primaryBorderColor: '#000000',
              lineColor: '#000000',
              secondaryColor: '#ffffff',
              tertiaryColor: '#ffffff',
              background: '#ffffff',
              noteBkgColor: '#ffffff',
              noteBorderColor: '#000000',
              noteTextColor: '#000000',
              actorBkg: '#ffffff',
              actorBorder: '#000000',
              actorTextColor: '#000000',
              signalColor: '#000000',
              signalTextColor: '#000000'
          }},
          flowchart: {{
              htmlLabels: true,
              curve: 'basis'
          }},
          sequence: {{
              actorMargin: 50
          }}
      }});
    </script>
</body>
</html>
"""

figures = {
    "1_system_architecture": """graph TD
    classDef default fill:#fff,stroke:#000,stroke-width:2px;
    classDef boundary fill:none,stroke:#000,stroke-width:2px,stroke-dasharray: 5 5;
    
    subgraph Client ["Client Device (Edge)"]
        A["Telemetry Agent (Passive Sensor)"]
        C["Client Application (Task Source)"]
    end
    
    subgraph Backend ["CLADS Control Plane"]
        B["Cognitive Load Service\n(CLS Engine)"]
        D["Task Annotator\n(Dk Engine)"]
        E{"Scheduler Core\n(2D Arbitration)"}
    end
    
    subgraph Cluster ["Distributed Execution Cluster"]
        G["Node 1: Local\n(Foreground)"]
        H["Node 2: Balanced\n(Cluster)"]
        I["Node 3: Background\n(Remote Offload)"]
    end
    
    A -->|"Interaction Vectors (κ, I, C, ...)"| B
    C -->|"Submit Task Payload"| D
    D -->|"Annotated Task & Dk Vector"| E
    B -->|"CLS State & Predictive Metrics"| E
    B -.->|"cpufreq Directives via sysfs"| F["CPU Governor\n(Hardware Layer)"]
    
    E -->|"Route/Migrate/Defer"| G
    E -->|"Route/Migrate/Defer"| H
    E -->|"Route/Migrate/Defer"| I
    E -.->|"EMA Weight Feedback Loop"| D
    
    class Client,Backend,Cluster boundary;""",
    
    "2_cls_computation_pipeline": """flowchart LR
    classDef default fill:#fff,stroke:#000,stroke-width:2px;
    
    A["Raw Telemetry Batch\n(User Interactions)"] --> B["Min-Max\nNormalization"]
    B --> C["Polynomial Scoring:\nCLS = Σ (αi * Xi)"]
    
    C --> D["Hysteresis Controller\n(Window Gating)"]
    D --> E["Discrete CLS State\n(LOW / MEDIUM / HIGH)"]
    
    C --> F["Rolling History\nBuffer (N=10)"]
    F --> G["Numpy Polyfit\n(Linear Regression)"]
    G --> H["Predictive Target:\n(Trend Slope, Breach Prob)"]""",
    
    "3_disruption_score_vector_decomposition": """flowchart TD
    classDef default fill:#fff,stroke:#000,stroke-width:2px;
    classDef perceptual fill:#fff,stroke:#000,stroke-width:3px;
    classDef hardware fill:#fff,stroke:#000,stroke-width:2px,stroke-dasharray: 3 3;
    
    subgraph Dk ["Task Disruption Score (Dk) Calculation"]
        direction TB
        subgraph Human ["Human-Perceptual Penalties (Dominant)"]
            UI["UI Blocking Impact (β1: 0.35)"]
            NOT["Notification Output (β2: 0.25)"]
        end
        subgraph Hard ["Hardware Resource Penalties (Subordinate)"]
            CPU["CPU Utilization (β3: 0.20)"]
            MEM["Memory Footprint (β4: 0.12)"]
            IO["Disk/Network I/O (β5: 0.08)"]
        end
        
        Human --> SumH["Σ(Human weights) = 0.60"]
        Hard --> SumR["Σ(Hardware weights) = 0.40"]
        
        SumH --> INV{"Invariant Checked at Boot:\n(β1 + β2) > (β3 + β4 + β5)"}
        SumR --> INV
        
        INV --> DkVal["Final Task Dk Annotated"]
    end
    
    class UI,NOT,Human,SumH perceptual;
    class CPU,MEM,IO,Hard,SumR hardware;""",
    
    "4_cls_dk_routing_policy_matrix": """<h2>Fig 4. CLS × Dk Routing Policy Matrix</h2>
<table>
    <thead>
        <tr>
            <th></th>
            <th>Task Dk: LOW</th>
            <th>Task Dk: MEDIUM</th>
            <th>Task Dk: HIGH</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="bold-row">USER CLS: LOW</td>
            <td style="border-style: dashed;">Local Node</td>
            <td style="border-style: dashed;">Local Node</td>
            <td>Balanced Node</td>
        </tr>
        <tr>
            <td class="bold-row">USER CLS: MEDIUM</td>
            <td style="border-style: dashed;">Local Node</td>
            <td>Balanced Node</td>
            <td style="border-width: 4px; font-weight:bold;">Background Node</td>
        </tr>
        <tr>
            <td class="bold-row">USER CLS: HIGH</td>
            <td>Balanced Node</td>
            <td style="border-width: 4px; font-weight:bold;">Background Node</td>
            <td style="border-width: 4px; font-weight:bold;">Background Node (Deferred)</td>
        </tr>
    </tbody>
</table>""",
    
    "5_cpu_governor_state_machine": """stateDiagram-v2
    direction LR
    
    state "USER CLS: LOW" as LOW
    state "USER CLS: MEDIUM" as MED
    state "USER CLS: HIGH" as HIGH
    
    LOW: Foreground = 'performance'
    LOW: Background = 'performance'
    
    MED: Foreground = 'ondemand'
    MED: Background = 'conservative'
    MED: BG Freq Cap = 2000 MHz
    
    HIGH: Foreground = 'performance'
    HIGH: Background = 'powersave'
    HIGH: BG Freq Cap = 800 MHz
    
    LOW --> MED : "Hysteresis Confirm Increment"
    MED --> HIGH : "Hysteresis Confirm Increment"
    HIGH --> MED : "Hysteresis Confirm Decrement"
    MED --> LOW : "Hysteresis Confirm Decrement"
    
    note right of HIGH
      Directives written to OS sysfs
      at scaling_governor interface.
    end note""",
    
    "6_flow_state_lock_timeline": """sequenceDiagram
    autonumber
    participant U as User Telem (CLS)
    participant F as Flow Controller
    participant S as Scheduler Core
    
    U->>F: Broadcast LOW State
    loop Wait for N consecutive LOW windows
        U->>F: Broadcast LOW State
        Note over F: Streak Counter ++
    end
    
    U->>F: Broadcast LOW State (Window = Threshold)
    Note over F: Threshold Met (eg. 15 mins)
    F->>S: SET Boolean flag: flow_state_locked = TRUE
    
    Note over S: -- SYSTEM ENTERS DEEP WORK OVERRIDE --
    
    S->>S: Evaluates new HIGH-Dk Task 
    S->>S: Bypass Standard 3x3 Routing Matrix
    S->>S: Enforce Unconditional Remote Deferral
    
    Note over S: -- OVERRIDE END --
    
    U->>F: Broadcast MEDIUM State
    Note over F: Streak Broken
    F->>S: SET Boolean flag: flow_state_locked = FALSE""",
    
    "7_predictive_migration_sequence": """sequenceDiagram
    autonumber
    participant C as CLS Engine
    participant S as Scheduler Core
    participant W as Worker Nodes
    participant DB as MongoDB Telemetry
    
    C->>S: Emit State=MEDIUM, probability_high=0.85
    Note right of S: Trigger threshold >= 0.70 <br/>(Preemptive Action Authorized)
    
    S->>W: SIGSTOP active HIGH-Dk Task on local node
    S->>W: Migrate process state to Background Node
    
    S->>S: Start async verification timer (t=30s)
    
    opt At t=30 Seconds (Empirical Accuracy Track)
        S->>C: Query current actual CLS State
        
        alt User is actually HIGH
            S->>DB: Log Accuracy = TRUE POSITIVE
        else User remains MEDIUM/LOW
            S->>DB: Log Accuracy = FALSE POSITIVE
        end
    end""",
    
    "8_adaptive_weight_calibration_loop": """flowchart TD
    classDef default fill:#fff,stroke:#000,stroke-width:2px;
    classDef decision fill:#fff,stroke:#000,stroke-width:3px;
    
    A["Incoming Task Evaluated\n(Base Disruption Score)"] --> B["Scheduler Core Routes Task"]
    B --> C["Start Feedback Timer\n(Delay = 30 seconds)"]
    C --> D["Monitor CLS State\nTransition Outcome"]
    
    D --> E{"Did CLS state\nunexpectedly degrade\npost-scheduling?"}
    
    E -- "Yes (Negative UI Impact)" --> F["Increase (β1, β2) penalty via EMA\nλ = 0.05"]
    E -- "No (No Impact)" --> G["Decay (β1, β2) penalty via EMA\nλ = 0.05"]
    
    F --> H{"Check Invariant:\n(β1+β2) > (β3+β4+β5)"}
    G --> H
    
    H -- "Invariant Maintained" --> I["Store Updated Weights to\nUser's Profile (MongoDB)"]
    H -- "Invariant Violated" --> J["Renormalize weights to\npreserve strict constraint"]
    J --> I
    
    class E,H decision;""",
    
    "9_multi_tenant_teamcls_aggregation": """flowchart LR
    classDef default fill:#fff,stroke:#000,stroke-width:2px;
    classDef agg fill:#fff,stroke:#000,stroke-width:3px,stroke-dasharray: 5 5;
    
    subgraph Users ["Cluster Tenants"]
        U1["User Node 1\n(Active Interaction)\nCLS = HIGH\nWeight Coefficient = 2.0"]
        U2["User Node 2\n(Active Interaction)\nCLS = MEDIUM\nWeight Coefficient = 2.0"]
        U3["User Node 3\n(Idle / Away)\nCLS = LOW\nWeight Coefficient = 1.0"]
    end
    
    U1 --> Aggregator
    U2 --> Aggregator
    U3 --> Aggregator
    
    Aggregator{"TeamCLS Aggregation Engine\n[ Σ(CLS * W) / Σ(W) ]"}
    
    Aggregator --> TCLS["Composite TeamCLS Score"]
    
    TCLS --> Policy{"TeamCLS >= Threshold?"}
    Policy -- "Yes" --> Action["Trigger Cluster-Wide\nTask Deferment Policy"]
    Policy -- "No" --> Proceed["Normal Independent Routing"]
    
    class Aggregator agg;""",
    
    "10_latency_benchmark_results": """<h2>Fig 10. Latency Benchmark Results (ms)</h2>
<table>
    <thead>
        <tr>
            <th>Cognitive Load State</th>
            <th>BASELINE Latency</th>
            <th>CLADS Latency (Reduced)</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="bold-row">LOW CLS State</td>
            <td style="border-style: dashed;">119 ms</td>
            <td>91 ms</td>
        </tr>
        <tr>
            <td class="bold-row">MEDIUM CLS State</td>
            <td style="border-style: dashed;">145 ms</td>
            <td>105 ms</td>
        </tr>
        <tr>
            <td class="bold-row">HIGH CLS State</td>
            <td style="border-style: dashed;">120 ms</td>
            <td style="border-width: 4px; font-weight: bold;">68.6 ms (42.8% Improvement)</td>
        </tr>
    </tbody>
</table>"""
}

for name, body in figures.items():
    filename = f"patent-figures/figure_{name}.html"
    is_html = body.strip().startswith("<h2") or body.strip().startswith("<table")
    div_class = "html-table-wrapper" if is_html else "mermaid"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template.format(fig_num=name.split("_", 1)[1], div_class=div_class, mermaid_code=body))

print("Created 10 highly uniform stroke html files in patent-figures/")
