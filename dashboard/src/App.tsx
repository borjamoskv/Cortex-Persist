import React, { useState, useEffect } from 'react';
import './index.css';

function App() {
  const [agentsActive, setAgentsActive] = useState(10000);
  const [throughput, setThroughput] = useState(238162);
  const [entropy, setEntropy] = useState(0);

  // Simulate telemetry
  useEffect(() => {
    const interval = setInterval(() => {
      setThroughput(prev => prev + Math.floor(Math.random() * 5000) - 2500);
      setEntropy(prev => Math.max(0, prev + (Math.random() > 0.8 ? 0.01 : -0.01)));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <header className="app-header">
        <div className="logo-group">
          <div className="logo-symbol">Ω</div>
          <div className="logo-text">
            <h1>CORTEX ADMIN</h1>
            <span>SOVEREIGN CLOUD DASHBOARD</span>
          </div>
        </div>
        <div className="status-indicator">
          <div className="status-dot"></div>
          <span>C5-REAL // LEGION-10K ACTIVE</span>
        </div>
      </header>

      <main className="dashboard-grid">
        <div className="panel metric-card">
          <span className="label">ACTIVE AGENTS</span>
          <span className="value">{agentsActive.toLocaleString()}</span>
          <span className="mono" style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>LEGION-10k SWARM</span>
        </div>

        <div className="panel metric-card">
          <span className="label">THROUGHPUT O(1)</span>
          <span className="value">{throughput.toLocaleString()} <span style={{fontSize: '1rem', color: 'var(--color-text-secondary)'}}>op/s</span></span>
          <span className="mono" style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>ZERO-COPY RING BUFFER</span>
        </div>

        <div className="panel metric-card">
          <span className="label">SYSTEM ENTROPY</span>
          <span className="value" style={{ color: entropy > 0.5 ? 'var(--color-danger)' : 'var(--color-text-primary)' }}>
            {entropy.toFixed(3)}
          </span>
          <span className="mono" style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>THERMODYNAMIC EXERGY</span>
        </div>

        <div className="panel" style={{ gridColumn: '1 / -1' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>CRYPTOGRAPHIC DECISION LEDGER</h3>
            <button className="btn btn-primary">EXPORT AUDIT</button>
          </div>
          <div style={{ 
            background: 'var(--color-bg-elevated)', 
            padding: '1rem', 
            borderRadius: 'var(--radius-sm)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.875rem',
            color: 'var(--color-text-secondary)'
          }}>
            <div style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', display: 'flex', gap: '1rem' }}>
              <span style={{ color: 'var(--color-accent)' }}>0x8a4c1f9d...</span>
              <span>EViction Triggered. Target: UUID-4412. Priority: LOW.</span>
              <span style={{ marginLeft: 'auto' }}>Just now</span>
            </div>
            <div style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', display: 'flex', gap: '1rem' }}>
              <span style={{ color: 'var(--color-accent)' }}>0x7b2b0a11...</span>
              <span>Swarm Request Routed. Optimal Node: Arbitrum (42161).</span>
              <span style={{ marginLeft: 'auto' }}>2s ago</span>
            </div>
            <div style={{ padding: '0.5rem 0', display: 'flex', gap: '1rem' }}>
              <span style={{ color: 'var(--color-accent)' }}>0x9c3f4e22...</span>
              <span>Sovereign Magic Decorator applied. Tenant: sys-01.</span>
              <span style={{ marginLeft: 'auto' }}>5s ago</span>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}

export default App;
