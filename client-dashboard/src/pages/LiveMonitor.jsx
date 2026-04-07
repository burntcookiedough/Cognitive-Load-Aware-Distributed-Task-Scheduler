import { useState, useCallback } from 'react';
import CLSGauge       from '../components/CLSGauge';
import NodeCard       from '../components/NodeCard';
import TelemetryPanel from '../components/TelemetryPanel';
import { usePolling } from '../hooks/usePolling';
import { useTelemetry } from '../hooks/useTelemetry';
import { CLS_SERVICE_URL, SCHEDULER_URL, USER_ID, CLS_COLORS } from '../config';

export default function LiveMonitor({ mode }) {
  const [lastBatch, setLastBatch] = useState(null);

  // Capture real interaction telemetry and expose last batch to panel
  useTelemetry(true, setLastBatch);

  // Poll CLS state every 2s
  const { data: clsData } = usePolling(`${CLS_SERVICE_URL}/cls/${USER_ID}`, 2000);

  // Poll node metrics every 2s
  const { data: nodesData } = usePolling(`${SCHEDULER_URL}/nodes/metrics`, 2000);

  // Poll recent decisions for feed
  const { data: decisions } = usePolling(`${SCHEDULER_URL}/decisions?limit=8`, 2000);

  const cls      = Number(clsData?.current_cls ?? 0);
  const state    = clsData?.state ?? 'LOW';
  const features = clsData?.features ?? {};
  const decisionsArr = Array.isArray(decisions) ? decisions : [];

  const nodes = (nodesData && typeof nodesData === 'object' && !Array.isArray(nodesData))
    ? Object.entries(nodesData).map(([id, m]) => ({ ...m, node_id: id }))
    : [];

  return (
    <div className="fade-up">
      {/* ── Top row: Gauge + Quick Stats + Telemetry ────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 280px', gap: 16, alignItems: 'start' }}>

        {/* CLS Gauge */}
        <div className={`card cls-border-${state}`} style={{ padding: '28px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <CLSGauge clsScore={cls} clsState={state} size={190} />
          <div style={{ width: '100%', fontSize: '0.78rem' }}>
            {Object.entries(features).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between',
                                    padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span style={{ color: 'var(--muted)' }}>{k.replace(/_/g, ' ')}</span>
                <span style={{ fontFamily: 'var(--mono)', color: 'var(--cyan)' }}>{Number(v).toFixed(3)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Middle: Stats + Decision feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Stat cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {[
              { label: 'CLS Score',   val: cls.toFixed(3),          color: CLS_COLORS[state] },
              { label: 'CLS State',   val: state,                   color: CLS_COLORS[state] },
              { label: 'Sched. Mode', val: mode,                    color: mode === 'CLADS' ? 'var(--cyan)' : 'var(--purple)' },
              { label: 'Active Nodes',val: nodes.filter(n => n.status === 'active').length, color: 'var(--low)' },
              { label: 'Queue (Total)',val: nodes.reduce((a, n) => a + (n.queue_length || 0), 0), color: 'var(--med)' },
              { label: 'Decisions',   val: decisionsArr.length,  color: 'var(--cyan)' },
            ].map(s => (
              <div key={s.label} className="card" style={{ padding: '14px 16px' }}>
                <div style={{ color: s.color, fontSize: '1.5rem', fontWeight: 800, fontFamily: 'var(--mono)' }}>{s.val}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 4 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Live decision feed */}
          <div className="card" style={{ padding: 0, overflow: 'hidden', flex: 1 }}>
            <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)',
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase',
                             letterSpacing: '0.08em', color: 'var(--muted)' }}>Recent Decisions</span>
              <span style={{ fontSize: '0.68rem', color: 'var(--cyan)' }}>● Live</span>
            </div>
            <div style={{ maxHeight: 280, overflowY: 'auto' }}>
              {decisionsArr.map((d, i) => {
                const DCOL = {
                  local_schedule: 'var(--low)', balanced_schedule: 'var(--cyan)',
                  background_schedule: 'var(--med)', delayed_schedule: '#ffd700',
                  remote_schedule: 'var(--high)', baseline_schedule: 'var(--purple)',
                };
                const col = DCOL[d.decision] || 'var(--cyan)';
                return (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '9px 18px', borderBottom: '1px solid rgba(255,255,255,0.04)',
                    fontSize: '0.78rem',
                  }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: col, flexShrink: 0 }} />
                    <span style={{ fontWeight: 600 }}>{d.task_type}</span>
                    <span className={`badge badge-${d.cls_state}`} style={{ fontSize: '0.65rem', padding: '1px 7px' }}>{d.cls_state}</span>
                    <span style={{ marginLeft: 'auto', color: col, fontFamily: 'var(--mono)', fontSize: '0.72rem' }}>→ {d.assigned_node}</span>
                  </div>
                );
              })}
              {decisionsArr.length === 0 && (
                <div style={{ padding: '24px 18px', textAlign: 'center', color: 'var(--muted)', fontSize: '0.8rem' }}>
                  No decisions yet — submit a task.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Telemetry panel */}
        <TelemetryPanel lastBatch={lastBatch} />
      </div>

      {/* ── Node grid ─────────────────────────────────────────────────────────── */}
      <div className="mt-6">
        <div style={{ fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase',
                      letterSpacing: '0.08em', color: 'var(--muted)', marginBottom: 12 }}>
          Cluster Nodes
        </div>
        <div className="grid-3" style={{ gap: 16 }}>
          {nodes.length > 0
            ? nodes.map(n => <NodeCard key={n.node_id} metrics={n} />)
            : ['node1','node2','node3'].map(id => (
                <div key={id} className="card" style={{ padding: 20, textAlign: 'center', color: 'var(--muted)' }}>
                  <div style={{ fontSize: '1.5rem', marginBottom: 8 }}>⏳</div>
                  <div style={{ fontSize: '0.82rem' }}>{id} — connecting…</div>
                </div>
              ))
          }
        </div>
      </div>
    </div>
  );
}
