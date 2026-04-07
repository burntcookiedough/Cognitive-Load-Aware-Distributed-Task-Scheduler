// Backend service URLs — must match docker-compose port mappings
export const CLS_SERVICE_URL       = 'http://localhost:8001';
export const TASK_ANNOTATOR_URL    = 'http://localhost:8002';
export const SCHEDULER_URL         = 'http://localhost:8003';

export const NODE_URLS = {
  node1: 'http://localhost:8011',
  node2: 'http://localhost:8012',
  node3: 'http://localhost:8013',
};

// Demo user (single-user MVP)
export const USER_ID = 'u_shagun';

// Polling interval (ms)
export const POLL_INTERVAL = 2000;

// Telemetry batch interval (ms)
export const TELEMETRY_INTERVAL = 3000;

// CLS colour palette
export const CLS_COLORS = {
  LOW:    '#00ff88',
  MEDIUM: '#ffa500',
  HIGH:   '#ff3060',
};

export const CLS_BG_COLORS = {
  LOW:    'rgba(0, 255, 136, 0.12)',
  MEDIUM: 'rgba(255, 165, 0, 0.12)',
  HIGH:   'rgba(255, 48, 96, 0.12)',
};

// Decision colour palette
export const DECISION_COLORS = {
  local_schedule:      '#00ff88',
  balanced_schedule:   '#00d4ff',
  background_schedule: '#ffa500',
  delayed_schedule:    '#ffd700',
  remote_schedule:     '#ff3060',
  baseline_schedule:   '#a78bfa',
};

export const TASK_TYPES = [
  { id: 'build',               label: 'Build',                icon: '🔨', category: 'HIGH'   },
  { id: 'deploy',              label: 'Deploy',               icon: '🚀', category: 'HIGH'   },
  { id: 'dependency_install',  label: 'Install Deps',         icon: '📦', category: 'HIGH'   },
  { id: 'test_run',            label: 'Run Tests',            icon: '🧪', category: 'MEDIUM' },
  { id: 'ai_request',          label: 'AI Request',           icon: '🤖', category: 'MEDIUM' },
  { id: 'static_analysis',     label: 'Static Analysis',      icon: '🔍', category: 'MEDIUM' },
  { id: 'lint',                label: 'Lint',                 icon: '✅', category: 'LOW'    },
  { id: 'indexing',            label: 'Index Files',          icon: '📁', category: 'LOW'    },
  { id: 'autosave',            label: 'Autosave',             icon: '💾', category: 'LOW'    },
];
