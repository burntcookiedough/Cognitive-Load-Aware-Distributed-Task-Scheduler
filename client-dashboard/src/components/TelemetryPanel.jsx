/**
 * TelemetryPanel — shows the six live telemetry signals captured from
 * the browser interaction telemetry agent.
 */

const SIGNALS = [
  { key: 'keystrokes',             label: 'Keystrokes',         icon: '⌨️', max: 60,  unit: '/win' },
  { key: 'avg_inter_key_interval', label: 'Avg Key Interval',   icon: '⏱', max: 500, unit: 'ms'  },
  { key: 'typing_variance',        label: 'Typing Variance',    icon: '〰', max: 500, unit: 'ms²' },
  { key: 'idle_duration',          label: 'Idle Time',          icon: '😴', max: 30,  unit: 's'   },
  { key: 'tab_switches',           label: 'Tab Switches',       icon: '🔀', max: 10,  unit: ''    },
  { key: 'focus_changes',          label: 'Focus Changes',      icon: '🎯', max: 8,   unit: ''    },
];

function SignalRow({ signal, value }) {
  const pct   = Math.min(100, (value / signal.max) * 100);
  const color = pct > 75 ? 'var(--high)' : pct > 45 ? 'var(--med)' : 'var(--low)';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0',
                  borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      <span style={{ fontSize: '1rem', width: 24, textAlign: 'center' }}>{signal.icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>{signal.label}</span>
          <span style={{ fontSize: '0.78rem', fontFamily: 'var(--mono)', color }}>
            {typeof value === 'number' ? (Number.isInteger(value) ? value : value.toFixed(1)) : '—'}
            {' '}{signal.unit}
          </span>
        </div>
        <div style={{ height: 4, background: 'rgba(255,255,255,0.07)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${pct}%`, background: color,
            borderRadius: 3, transition: 'width 0.5s ease',
          }} />
        </div>
      </div>
    </div>
  );
}

export default function TelemetryPanel({ lastBatch }) {
  const values = lastBatch || {};

  return (
    <div className="card" style={{ height: '100%' }}>
      <div className="card-header" style={{ marginBottom: 4 }}>
        <h3>Interaction Signals</h3>
        <span style={{ fontSize: '0.7rem', color: 'var(--cyan)' }}>● Live · 3s window</span>
      </div>
      <div className="card-body" style={{ paddingTop: 8 }}>
        {SIGNALS.map(sig => (
          <SignalRow key={sig.key} signal={sig} value={values[sig.key] ?? 0} />
        ))}
        {!lastBatch && (
          <p style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '0.8rem', marginTop: 12 }}>
            Interact with the page to generate telemetry…
          </p>
        )}
      </div>
    </div>
  );
}
