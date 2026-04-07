import { useState } from 'react';
import TaskLauncher from '../components/TaskLauncher';
import { usePolling } from '../hooks/usePolling';
import { SCHEDULER_URL, CLS_SERVICE_URL, USER_ID } from '../config';

export default function TaskLauncherPage({ mode }) {
  const [submissions, setSubmissions] = useState([]);

  const { data: clsData } = usePolling(`${CLS_SERVICE_URL}/cls/${USER_ID}`, 2000);
  const cls   = clsData?.current_cls ?? 0;
  const state = clsData?.state ?? 'LOW';

  const handleSubmit = (result) => {
    setSubmissions(prev => [result, ...prev].slice(0, 20));
  };

  const CLS_COL = { LOW: 'var(--low)', MEDIUM: 'var(--med)', HIGH: 'var(--high)' };

  return (
    <div className="fade-up">
      {/* Context bar */}
      <div className="card mb-4" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
        <div>
          <span style={{ fontSize: '0.72rem', color: 'var(--muted)', textTransform: 'uppercase' }}>Current CLS</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, fontFamily: 'var(--mono)', color: CLS_COL[state] }}>
            {cls.toFixed(3)}
          </div>
        </div>
        <div>
          <span style={{ fontSize: '0.72rem', color: 'var(--muted)', textTransform: 'uppercase' }}>State</span>
          <div style={{ marginTop: 4 }}>
            <span className={`badge badge-${state}`} style={{ fontSize: '0.9rem', padding: '6px 16px' }}>{state}</span>
          </div>
        </div>
        
        {/* Predictive CLS Block */}
        <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 24 }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--muted)', textTransform: 'uppercase' }}>Predicted Trend (T+3)</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--cyan)' }}>
              {clsData?.predicted_cls ? clsData.predicted_cls.toFixed(3) : '0.000'}
            </div>
            {clsData?.probability_high > 0.5 && (
              <span className="badge badge-HIGH" style={{ fontSize: '0.7rem' }}>
                {(clsData.probability_high * 100).toFixed(0)}% HIGH RISK
              </span>
            )}
          </div>
        </div>
        <div style={{ marginLeft: 'auto', fontSize: '0.82rem', color: 'var(--muted)', maxWidth: 400 }}>
          {state === 'HIGH'
            ? '⚠️  High cognitive load detected. CLADS will delay or offload high-disruption tasks.'
            : state === 'MEDIUM'
            ? '⚡ Medium load. High-disruption tasks will be routed to balanced or background nodes.'
            : '✅ Low cognitive load. Tasks run on the fastest local node.'
          }
        </div>
        <div style={{
          padding: '8px 16px', borderRadius: 8,
          background: mode === 'CLADS' ? 'rgba(0,212,255,0.1)' : 'rgba(124,58,237,0.1)',
          border: `1px solid ${mode === 'CLADS' ? 'rgba(0,212,255,0.25)' : 'rgba(124,58,237,0.25)'}`,
          fontSize: '0.82rem', fontWeight: 700,
          color: mode === 'CLADS' ? 'var(--cyan)' : 'var(--purple)',
        }}>
          {mode} Mode
        </div>
      </div>

      {/* Task buttons */}
      <TaskLauncher mode={mode} onSubmit={handleSubmit} />

      {/* Submission history */}
      {submissions.length > 0 && (
        <div className="mt-6">
          <div style={{ fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase',
                        letterSpacing: '0.08em', color: 'var(--muted)', marginBottom: 12 }}>
            Submission History
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {submissions.map((s, i) => (
              <div key={i} className="card fade-up" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', gap: 16, fontSize: '0.82rem' }}>
                <span style={{ fontWeight: 700 }}>{s.task?.task_type}</span>
                <span className={`badge badge-${s.task?.disruption_class}`} style={{ fontSize: '0.68rem' }}>
                  {s.task?.disruption_class}
                </span>
                <span className={`badge badge-${s.decision?.cls_state}`} style={{ fontSize: '0.68rem' }}>
                  CLS {s.decision?.cls_state}
                </span>
                <span style={{ marginLeft: 'auto', color: 'var(--cyan)', fontFamily: 'var(--mono)' }}>
                  → {s.decision?.assigned_node}
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>
                  {s.decision?.decision?.replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
