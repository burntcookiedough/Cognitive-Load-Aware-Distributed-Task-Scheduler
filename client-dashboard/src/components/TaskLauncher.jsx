import { useState } from 'react';
import axios from 'axios';
import { TASK_ANNOTATOR_URL, SCHEDULER_URL, CLS_COLORS, TASK_TYPES, USER_ID } from '../config';

const DISRUPTION_DESCS = {
  build:                'Full project build — heavy CPU + UI blocking',
  deploy:               'Production deployment — max disruption',
  dependency_install:   'Install packages — high I/O, notifications',
  test_run:             'Run test suite — moderate CPU + console logs',
  ai_request:           'AI code generation — GPU + UI updates',
  static_analysis:      'Code analysis — moderate CPU, some output',
  lint:                 'Lint source files — lightweight',
  indexing:             'Index workspace files — background I/O',
  autosave:             'Auto-save — nearly invisible',
};

export default function TaskLauncher({ mode = 'CLADS', onSubmit }) {
  const [submitting, setSubmitting] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  const handleSubmit = async (taskType) => {
    setSubmitting(taskType);
    try {
      // 1. Annotate
      const annRes = await axios.post(`${TASK_ANNOTATOR_URL}/annotate`, {
        user_id:        USER_ID,
        task_type:      taskType,
        scheduler_mode: mode,
      });
      const task = annRes.data;

      // 2. Schedule
      const schRes = await axios.post(`${SCHEDULER_URL}/schedule`, {
        task,
        scheduler_mode: mode,
      });
      const decision = schRes.data;

      setLastResult({ task, decision });
      if (onSubmit) onSubmit({ task, decision });
    } catch (e) {
      setLastResult({ error: e.message });
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div>
      {/* Task grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {TASK_TYPES.map(t => (
          <button
            key={t.id}
            className="task-card"
            onClick={() => handleSubmit(t.id)}
            disabled={!!submitting}
            style={{
              opacity: submitting && submitting !== t.id ? 0.5 : 1,
              border:  `1px solid ${
                t.category === 'HIGH'   ? 'rgba(255,48,96,0.25)'  :
                t.category === 'MEDIUM' ? 'rgba(255,165,0,0.25)'  :
                                          'rgba(0,255,136,0.2)'
              }`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="task-icon">{t.icon}</span>
              {submitting === t.id
                ? <span className="spinner" />
                : <span className={`badge badge-${t.category}`}>{t.category}</span>
              }
            </div>
            <div className="task-name">{t.label}</div>
            <div className="task-desc">{DISRUPTION_DESCS[t.id] || ''}</div>
          </button>
        ))}
      </div>

      {/* Last scheduling result */}
      {lastResult && (
        <div className="card mt-6 fade-up" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)',
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: '0.82rem', color: 'var(--muted)', fontWeight: 600,
                         textTransform: 'uppercase', letterSpacing: '0.07em' }}>
              Last Scheduling Decision
            </h3>
            <button
              onClick={() => setLastResult(null)}
              style={{ background: 'none', border: 'none', color: 'var(--muted)',
                       cursor: 'pointer', fontSize: '1rem' }}
            >✕</button>
          </div>

          {lastResult.error ? (
            <div style={{ padding: 18, color: 'var(--high)' }}>⚠ {lastResult.error}</div>
          ) : (
            <div style={{
              display: 'grid', gridTemplateColumns: '1fr 1fr',
              gap: 0, fontSize: '0.82rem',
            }}>
              {[
                ['Task Type',       lastResult.task?.task_type],
                ['Disruption',      lastResult.task?.disruption_class],
                ['Disruption Score',lastResult.task?.disruption_score?.toFixed(3)],
                ['CLS State',       lastResult.decision?.cls_state],
                ['CLS Score',       lastResult.decision?.cls_score?.toFixed(3)],
                ['Assigned Node',   lastResult.decision?.assigned_node],
                ['Decision',        lastResult.decision?.decision?.replace(/_/g, ' ')],
                ['Mode',            lastResult.decision?.scheduler_mode],
              ].map(([k, v]) => (
                <div key={k} style={{
                  padding: '10px 18px',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  display: 'flex', flexDirection: 'column', gap: 2,
                }}>
                  <span style={{ color: 'var(--muted)', fontSize: '0.72rem', textTransform: 'uppercase' }}>{k}</span>
                  <span style={{ fontWeight: 600, fontFamily: 'var(--mono)' }}>{v ?? '—'}</span>
                </div>
              ))}
              <div style={{ gridColumn: '1/-1', padding: '10px 18px',
                            borderTop: '1px solid var(--border)', fontSize: '0.78rem', color: 'var(--muted)' }}>
                💬 {lastResult.decision?.reason}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
