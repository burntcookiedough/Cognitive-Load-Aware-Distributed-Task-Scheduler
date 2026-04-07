import { useState, useCallback } from 'react';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale,
  BarElement, LineElement, PointElement,
  ArcElement, Title, Tooltip, Legend,
} from 'chart.js';
import { Bar, Line, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale, LinearScale,
  BarElement, LineElement, PointElement,
  ArcElement, Title, Tooltip, Legend,
);

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: 'rgba(240,244,255,0.6)', font: { family: 'Inter', size: 11 } } },
    tooltip: {
      backgroundColor: '#0d1426',
      borderColor: 'rgba(255,255,255,0.1)',
      borderWidth: 1,
      titleColor: '#f0f4ff',
      bodyColor: 'rgba(240,244,255,0.7)',
    },
  },
  scales: {
    x: {
      ticks:  { color: 'rgba(240,244,255,0.45)', font: { size: 11 } },
      grid:   { color: 'rgba(255,255,255,0.05)' },
    },
    y: {
      ticks: { color: 'rgba(240,244,255,0.45)', font: { size: 11 } },
      grid:  { color: 'rgba(255,255,255,0.05)' },
    },
  },
};

function nodeDistChart(decisions) {
  const clads    = { node1: 0, node2: 0, node3: 0 };
  const baseline = { node1: 0, node2: 0, node3: 0 };

  decisions.forEach(d => {
    const target = d.scheduler_mode === 'CLADS' ? clads : baseline;
    if (d.assigned_node in target) target[d.assigned_node]++;
  });

  return {
    labels: ['node1 (Local)', 'node2 (Balanced)', 'node3 (Background)'],
    datasets: [
      {
        label: 'CLADS',
        data: [clads.node1, clads.node2, clads.node3],
        backgroundColor: ['rgba(0,255,136,0.7)', 'rgba(0,212,255,0.7)', 'rgba(255,165,0,0.7)'],
        borderRadius: 6,
      },
      {
        label: 'Baseline',
        data: [baseline.node1, baseline.node2, baseline.node3],
        backgroundColor: ['rgba(0,255,136,0.25)', 'rgba(0,212,255,0.25)', 'rgba(255,165,0,0.25)'],
        borderRadius: 6,
      },
    ],
  };
}

function clsTimeChart(decisions) {
  const last20 = decisions
    .filter(d => d.scheduler_mode === 'CLADS')
    .slice(0, 20)
    .reverse();

  const labels = last20.map((_, i) => `T-${last20.length - i}`);
  return {
    labels,
    datasets: [{
      label: 'CLS Score',
      data: last20.map(d => d.cls_score ?? 0),
      borderColor: 'var(--cyan)',
      backgroundColor: 'rgba(0,212,255,0.08)',
      borderWidth: 2,
      pointRadius: 3,
      fill: true,
      tension: 0.4,
    }],
  };
}

function highClsTasksChart(decisions) {
  const counts = { CLADS: { high_cls_high_dis: 0, other: 0 }, BASELINE: { high_cls_high_dis: 0, other: 0 } };
  decisions.forEach(d => {
    const mode = d.scheduler_mode || 'CLADS';
    if (d.cls_state === 'HIGH' && d.disruption_class === 'HIGH') {
      counts[mode].high_cls_high_dis++;
    } else {
      counts[mode].other++;
    }
  });
  return {
    labels: ['High Disruption during HIGH CLS', 'Other tasks'],
    datasets: [
      {
        label: 'CLADS',
        data: [counts.CLADS.high_cls_high_dis, counts.CLADS.other],
        backgroundColor: ['rgba(255,48,96,0.7)', 'rgba(0,212,255,0.5)'],
        borderWidth: 0,
      },
      {
        label: 'Baseline',
        data: [counts.BASELINE.high_cls_high_dis, counts.BASELINE.other],
        backgroundColor: ['rgba(255,48,96,0.3)', 'rgba(0,212,255,0.2)'],
        borderWidth: 0,
      },
    ],
  };
}

export default function ComparisonChart({ decisions = [] }) {
  const [tab, setTab] = useState('nodes');

  const tabs = [
    { id: 'nodes',   label: 'Node Distribution' },
    { id: 'cls',     label: 'CLS Over Time'     },
    { id: 'impact',  label: 'High-Load Impact'  },
  ];

  const cladsCount   = decisions.filter(d => d.scheduler_mode === 'CLADS').length;
  const baselineCount= decisions.filter(d => d.scheduler_mode === 'BASELINE').length;

  const highClsHighDis_CLADS    = decisions.filter(d =>
    d.scheduler_mode === 'CLADS' && d.cls_state === 'HIGH' && d.disruption_class === 'HIGH'
  ).length;
  const highClsHighDis_Baseline = decisions.filter(d =>
    d.scheduler_mode === 'BASELINE' && d.cls_state === 'HIGH' && d.disruption_class === 'HIGH'
  ).length;

  const remoteCount_CLADS = decisions.filter(d =>
    d.scheduler_mode === 'CLADS' && d.assigned_node === 'node3'
  ).length;

  return (
    <div>
      {/* Summary stat row */}
      <div className="grid-3 mb-4" style={{ gap: 12 }}>
        {[
          { label: 'CLADS Decisions',               val: cladsCount,             color: 'var(--cyan)'   },
          { label: 'Baseline Decisions',             val: baselineCount,          color: 'var(--purple)' },
          { label: 'High-CLS Migrations (CLADS)',    val: remoteCount_CLADS,      color: 'var(--med)'    },
          { label: 'High-Disrupt @ High-CLS (CLADS)',val: highClsHighDis_CLADS,  color: 'var(--high)'   },
          { label: 'High-Disrupt @ High-CLS (Base)', val: highClsHighDis_Baseline,color:'var(--high)'   },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: '16px 18px' }}>
            <div className="stat-num" style={{ color: s.color, fontSize: '1.8rem' }}>{s.val}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Chart tabs */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
          {tabs.map(t => (
            <button key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: '12px 20px', border: 'none', cursor: 'pointer',
                fontSize: '0.82rem', fontWeight: 600, background: 'none',
                fontFamily: 'var(--font)',
                color: tab === t.id ? 'var(--cyan)' : 'var(--muted)',
                borderBottom: tab === t.id ? '2px solid var(--cyan)' : '2px solid transparent',
                transition: 'all 0.15s',
              }}
            >{t.label}</button>
          ))}
        </div>

        <div style={{ padding: 24, height: 300 }}>
          {tab === 'nodes' && decisions.length > 0 && (
            <Bar
              data={nodeDistChart(decisions)}
              options={{ ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins,
                title: { display: true, text: 'Task Distribution by Node — CLADS vs Baseline', color: 'rgba(240,244,255,0.45)', font: { size: 12 } } } }}
            />
          )}
          {tab === 'cls' && decisions.length > 0 && (
            <Line
              data={clsTimeChart(decisions)}
              options={{ ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins,
                title: { display: true, text: 'CLS Score Over Recent Decisions', color: 'rgba(240,244,255,0.45)', font: { size: 12 } } } }}
            />
          )}
          {tab === 'impact' && decisions.length > 0 && (
            <Bar
              data={highClsTasksChart(decisions)}
              options={{ ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins,
                title: { display: true, text: 'High-Disruption Tasks During HIGH CLS', color: 'rgba(240,244,255,0.45)', font: { size: 12 } } } }}
            />
          )}
          {decisions.length === 0 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--muted)' }}>
              Submit some tasks in both CLADS and Baseline modes to generate comparison data.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
