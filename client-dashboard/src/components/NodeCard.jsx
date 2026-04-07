/**
 * NodeCard — displays live metrics for one cluster worker node.
 * CPU, memory, and queue bars animate via CSS transitions.
 */

const NODE_ICONS = { node1: '🖥️', node2: '⚖️', node3: '☁️' };

function MetricBar({ label, value, max = 100, unit = '%', color = 'var(--cyan)' }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="metric-bar-wrap">
      <div className="metric-bar-label">
        <span>{label}</span>
        <span style={{ color }}>{value}{unit}</span>
      </div>
      <div className="metric-bar-track">
        <div
          className="metric-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

function cpuColor(v) {
  if (v >= 80) return 'var(--high)';
  if (v >= 55) return 'var(--med)';
  return 'var(--low)';
}

export default function NodeCard({ metrics }) {
  if (!metrics) return null;

  const {
    node_id, node_label, cpu_usage, memory_usage,
    queue_length, latency_to_user_ms, status,
    tasks_processed, queue_capacity, currently_running,
  } = metrics;

  const isActive = status === 'active';
  const role     = node_id === 'node1' ? 'Low Latency' : node_id === 'node2' ? 'Balanced' : 'Background';
  const icon     = NODE_ICONS[node_id] || '🖥️';

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header strip */}
      <div style={{
        padding: '14px 18px',
        background: 'rgba(255,255,255,0.03)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '1.3rem' }}>{icon}</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.92rem' }}>{node_label || node_id}</div>
            <div style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>{role} · {node_id}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            className="pulse-dot"
            style={{ background: isActive ? 'var(--low)' : 'var(--high)',
                     boxShadow: `0 0 6px ${isActive ? 'var(--low)' : 'var(--high)'}` }}
          />
          <span style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>
            {isActive ? 'Active' : 'Down'}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <MetricBar label="CPU"    value={Math.round(cpu_usage)}    color={cpuColor(cpu_usage)} />
        <MetricBar label="Memory" value={Math.round(memory_usage)} color="var(--cyan)" />
        <MetricBar label="Queue"  value={queue_length} max={queue_capacity || 10}
          unit={`/${queue_capacity ?? '?'}`} color="var(--purple)" />
      </div>

      {/* Footer stats */}
      <div style={{
        padding: '10px 18px',
        borderTop: '1px solid var(--border)',
        display: 'flex', gap: 20,
        fontSize: '0.74rem', color: 'var(--muted)',
      }}>
        <span>📶 {Math.round(latency_to_user_ms)} ms</span>
        <span>✅ {tasks_processed ?? 0} done</span>
        {currently_running && (
          <span style={{ color: 'var(--cyan)', marginLeft: 'auto' }}>
            ⚙ {currently_running}
          </span>
        )}
      </div>
    </div>
  );
}
