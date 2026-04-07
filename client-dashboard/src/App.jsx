import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { useTelemetry } from './hooks/useTelemetry';
import LiveMonitor      from './pages/LiveMonitor';
import TaskLauncherPage from './pages/TaskLauncherPage';
import DecisionLogPage  from './pages/DecisionLogPage';
import Analytics        from './pages/Analytics';

function Sidebar({ mode, setMode }) {
  const loc = useLocation();

  const links = [
    { to: '/',          icon: '📡', label: 'Live Monitor'  },
    { to: '/tasks',     icon: '⚡', label: 'Task Launcher' },
    { to: '/decisions', icon: '📋', label: 'Decision Log'  },
    { to: '/analytics', icon: '📊', label: 'Analytics'     },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>CLADS</h1>
        <p>Cognitive Load–Aware Distributed Scheduler</p>
      </div>

      <nav className="sidebar-nav">
        {links.map(l => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <span className="nav-icon">{l.icon}</span>
            {l.label}
          </NavLink>
        ))}

        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--muted)', padding: '4px 14px 8px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Scheduler Mode
          </div>
          <div className="mode-toggle" style={{ margin: '0 4px' }}>
            <button
              className={`mode-btn${mode === 'CLADS' ? ' active' : ''}`}
              onClick={() => setMode('CLADS')}
            >CLADS</button>
            <button
              className={`mode-btn${mode === 'BASELINE' ? ' active-baseline' : ''}`}
              onClick={() => setMode('BASELINE')}
            >Baseline</button>
          </div>
        </div>
      </nav>

      <div className="sidebar-footer">
        <strong>User:</strong> u_shagun<br />
        <span style={{ color: 'var(--cyan)', fontSize: '0.68rem' }}>● Telemetry Active</span>
      </div>
    </aside>
  );
}

function Topbar({ mode, pageName }) {
  return (
    <header className="topbar">
      <span className="topbar-title">{pageName}</span>
      <div className="topbar-right">
        <span style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
          Mode:{' '}
          <span style={{ color: mode === 'CLADS' ? 'var(--cyan)' : 'var(--purple)', fontWeight: 700 }}>
            {mode}
          </span>
        </span>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: 'var(--low)',
          animation: 'pulse-anim 2s ease-in-out infinite',
          boxShadow: '0 0 6px var(--low)',
        }} />
      </div>
    </header>
  );
}

const PAGE_NAMES = {
  '/':          '📡 Live Monitor',
  '/tasks':     '⚡ Task Launcher',
  '/decisions': '📋 Decision Log',
  '/analytics': '📊 Analytics',
};

function AppInner() {
  const [mode, setMode] = useState('CLADS');
  const loc             = useLocation();
  const pageName        = PAGE_NAMES[loc.pathname] || 'CLADS';

  // Activate real interaction telemetry globally
  useTelemetry(true);

  return (
    <div className="app-shell">
      <Sidebar mode={mode} setMode={setMode} />
      <div className="main-area">
        <Topbar mode={mode} pageName={pageName} />
        <main className="page-content">
          <Routes>
            <Route path="/"          element={<LiveMonitor  mode={mode} />} />
            <Route path="/tasks"     element={<TaskLauncherPage mode={mode} />} />
            <Route path="/decisions" element={<DecisionLogPage />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  );
}
