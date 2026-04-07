import { DECISION_COLORS, CLS_COLORS } from '../config';

const NODE_LABELS = { node1: '🖥 Local', node2: '⚖ Balanced', node3: '☁ Background' };

function DecisionBadge({ decision }) {
  const color = DECISION_COLORS[decision] || '#a78bfa';
  const label = decision?.replace(/_/g, ' ') || '—';
  return (
    <span style={{
      display: 'inline-block', padding: '2px 9px', borderRadius: 12,
      fontSize: '0.70rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em',
      color, background: color + '18', border: `1px solid ${color}44`,
    }}>
      {label}
    </span>
  );
}

function CLSBadge({ state, score }) {
  return (
    <span className={`badge badge-${state}`} style={{ fontSize: '0.69rem', padding: '2px 8px' }}>
      {state} {score != null ? `(${Number(score).toFixed(2)})` : ''}
    </span>
  );
}

export default function DecisionLog({ decisions = [], maxRows = 100 }) {
  const rows = decisions.slice(0, maxRows);

  if (!rows.length) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--muted)' }}>
        <div style={{ fontSize: '2rem', marginBottom: 12 }}>📋</div>
        <p>No scheduling decisions yet.</p>
        <p style={{ fontSize: '0.8rem', marginTop: 6 }}>Submit a task from the Task Launcher to see decisions here.</p>
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Task</th>
            <th>CLS</th>
            <th>Disruption</th>
            <th>Node</th>
            <th>Decision</th>
            <th>Mode</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => {
            const ts = d.timestamp ? new Date(d.timestamp).toLocaleTimeString() : '—';
            return (
              <tr key={d.decision_id || d.timestamp}>
                <td style={{ fontFamily: 'var(--mono)', fontSize: '0.75rem', color: 'var(--muted)' }}>{ts}</td>
                <td>
                  <span style={{ fontWeight: 600, fontSize: '0.82rem' }}>{d.task_type}</span>
                  <span style={{
                    marginLeft: 6, fontSize: '0.68rem', color: 'var(--muted)',
                    fontFamily: 'var(--mono)',
                  }}>#{d.task_id}</span>
                </td>
                <td><CLSBadge state={d.cls_state} score={d.cls_score} /></td>
                <td>
                  <span className={`badge badge-${d.disruption_class}`} style={{ fontSize: '0.69rem', padding: '2px 8px' }}>
                    {d.disruption_class} ({Number(d.disruption_score ?? 0).toFixed(2)})
                  </span>
                </td>
                <td style={{ fontWeight: 600, fontSize: '0.82rem' }}>
                  {NODE_LABELS[d.assigned_node] || d.assigned_node}
                </td>
                <td><DecisionBadge decision={d.decision} /></td>
                <td>
                  <span style={{
                    display: 'inline-block', padding: '2px 8px', borderRadius: 10,
                    fontSize: '0.68rem', fontWeight: 700,
                    color: d.scheduler_mode === 'CLADS' ? 'var(--cyan)' : 'var(--purple)',
                    background: d.scheduler_mode === 'CLADS' ? 'rgba(0,212,255,0.1)' : 'rgba(124,58,237,0.1)',
                  }}>
                    {d.scheduler_mode}
                  </span>
                </td>
                <td style={{ color: 'var(--muted)', fontSize: '0.75rem', maxWidth: 260,
                             overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {d.reason}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
