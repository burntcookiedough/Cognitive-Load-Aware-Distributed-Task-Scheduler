import ComparisonChart from '../components/ComparisonChart';
import { usePolling } from '../hooks/usePolling';
import { SCHEDULER_URL } from '../config';

export default function Analytics() {
  const { data: decisions, loading } = usePolling(`${SCHEDULER_URL}/decisions?limit=200`, 4000);
  const { data: stats }              = usePolling(`${SCHEDULER_URL}/decisions/stats`, 5000);

  const all       = Array.isArray(decisions) ? decisions : [];
  const clads     = all.filter(d => d.scheduler_mode === 'CLADS');
  const baseline  = all.filter(d => d.scheduler_mode === 'BASELINE');

  const avgCls    = clads.length > 0
    ? (clads.reduce((a, d) => a + (d.cls_score ?? 0), 0) / clads.length).toFixed(3)
    : '—';

  const highClsHighDis = clads.filter(d => d.cls_state === 'HIGH' && d.disruption_class === 'HIGH').length;
  const bgRouted       = clads.filter(d => d.assigned_node === 'node3').length;
  const bgBaselined    = baseline.filter(d => d.assigned_node === 'node3').length;

  const migrationAdvantage = bgRouted - bgBaselined;

  return (
    <div className="fade-up">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>CLADS vs Baseline — Performance Analytics</h2>
        <p style={{ color: 'var(--muted)', fontSize: '0.82rem', marginTop: 4 }}>
          Comparison of scheduling behaviour across both modes. Submit tasks in both CLADS and Baseline modes to populate charts.
        </p>
      </div>

      {/* Key metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'Avg CLS (CLADS tasks)',          val: avgCls,              color: 'var(--cyan)'   },
          { label: 'CLADS decisions',                val: clads.length,         color: 'var(--cyan)'   },
          { label: 'Baseline decisions',             val: baseline.length,      color: 'var(--purple)' },
          { label: 'High-Disrupt @ High-CLS (CLADS)',val: highClsHighDis,      color: 'var(--high)'   },
          { label: 'Background routed (CLADS)',      val: bgRouted,             color: 'var(--med)'    },
          { label: 'Background routed (Baseline)',   val: bgBaselined,          color: 'var(--med)'    },
          { label: 'Migration advantage',            val: migrationAdvantage >= 0 ? `+${migrationAdvantage}` : migrationAdvantage,
                                                                                color: 'var(--low)'    },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: '16px 18px' }}>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, fontFamily: 'var(--mono)', color: s.color }}>{s.val}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 4, lineHeight: 1.4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <ComparisonChart decisions={all} />

      {/* Policy table reference */}
      <div className="card mt-6" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            CLADS Policy Table Reference
          </h3>
        </div>
        <div style={{ overflowX: 'auto', padding: '0 0 4px' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>CLS State ↓ / Disruption →</th>
                <th>LOW Disruption</th>
                <th>MEDIUM Disruption</th>
                <th>HIGH Disruption</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['LOW',    'local_schedule', 'local_schedule',      'local_schedule'     ],
                ['MEDIUM', 'local_schedule', 'balanced_schedule',   'background_schedule'],
                ['HIGH',   'local_schedule', 'delayed_schedule',    'remote_schedule'    ],
              ].map(([cls, ...decisions]) => {
                const DCOL = {
                  local_schedule: 'var(--low)', balanced_schedule: 'var(--cyan)',
                  background_schedule: 'var(--med)', delayed_schedule: '#ffd700',
                  remote_schedule: 'var(--high)',
                };
                return (
                  <tr key={cls}>
                    <td><span className={`badge badge-${cls}`}>{cls}</span></td>
                    {decisions.map((d, i) => (
                      <td key={i}>
                        <span style={{ color: DCOL[d], fontWeight: 600, fontSize: '0.78rem' }}>
                          {d.replace(/_/g, ' ')}
                        </span>
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 20, color: 'var(--muted)', fontSize: '0.82rem' }}>
          ⏳ Loading analytics data…
        </div>
      )}
    </div>
  );
}
