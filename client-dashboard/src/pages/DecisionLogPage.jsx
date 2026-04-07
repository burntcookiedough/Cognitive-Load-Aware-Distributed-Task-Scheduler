import { useState } from 'react';
import DecisionLog from '../components/DecisionLog';
import { usePolling } from '../hooks/usePolling';
import { SCHEDULER_URL } from '../config';

export default function DecisionLogPage() {
  const [filter, setFilter] = useState('ALL');
  const { data, loading } = usePolling(`${SCHEDULER_URL}/decisions?limit=100`, 3000);

  const FILTERS = ['ALL', 'CLADS', 'BASELINE', 'HIGH CLS', 'HIGH Disruption'];

  const dataArr = Array.isArray(data) ? data : [];

  const filtered = dataArr.filter(d => {
    if (filter === 'ALL')              return true;
    if (filter === 'CLADS')            return d.scheduler_mode === 'CLADS';
    if (filter === 'BASELINE')         return d.scheduler_mode === 'BASELINE';
    if (filter === 'HIGH CLS')         return d.cls_state === 'HIGH';
    if (filter === 'HIGH Disruption')  return d.disruption_class === 'HIGH';
    return true;
  });

  // Summary stats
  const total   = dataArr.length;
  const clads   = dataArr.filter(d => d.scheduler_mode === 'CLADS').length;
  const bgNode  = dataArr.filter(d => d.assigned_node === 'node3').length;
  const highCls = dataArr.filter(d => d.cls_state === 'HIGH').length;

  return (
    <div className="fade-up">
      {/* Summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Total Decisions', val: total,   color: 'var(--white)'  },
          { label: 'CLADS',           val: clads,   color: 'var(--cyan)'   },
          { label: 'Background Routed',val: bgNode, color: 'var(--med)'    },
          { label: 'During HIGH CLS', val: highCls, color: 'var(--high)'   },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: '16px 18px' }}>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, fontFamily: 'var(--mono)', color: s.color }}>{s.val}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '12px 16px',
                      borderBottom: '1px solid var(--border)', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--muted)', marginRight: 8, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Filter:
          </span>
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '4px 12px', borderRadius: 8, cursor: 'pointer',
              border: '1px solid ' + (filter === f ? 'var(--cyan)' : 'var(--border)'),
              background: filter === f ? 'var(--cyan-dim)' : 'none',
              color: filter === f ? 'var(--cyan)' : 'var(--muted)',
              fontSize: '0.78rem', fontWeight: 600, fontFamily: 'var(--font)',
              transition: 'all 0.15s',
            }}>
              {f} {f !== 'ALL' && data ? `(${filtered.length})` : ''}
            </button>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--muted)' }}>
            {loading ? '⏳ Loading…' : `Showing ${filtered.length} of ${total}`}
          </span>
        </div>

        <div style={{ padding: '4px 0' }}>
          <DecisionLog decisions={filtered} />
        </div>
      </div>
    </div>
  );
}
