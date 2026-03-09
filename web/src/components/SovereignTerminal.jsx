import React, { useState, useEffect } from 'react';
import { Terminal, Database } from 'lucide-react';
import './SovereignTerminal.css';

const MOCK_OUTPUT = [
  "Initializing Cortex Persist v4.0...",
  "Loading Industrial Noir 2026 aesthetic matrices...",
  "Snapshot age: 4ms. Integrity: O(1).",
  "WARNING: Entropy detected in external nodes.",
  "Executing Quarantine Lockdown Ω₉...",
  "Action: [SUCCESS] 6/6 Attacks Intercepted.",
  "Database synced. WAL mode active. Zero deadlocks.",
  "Sovereign node operational. Waiting for input..."
];

const SovereignTerminal = () => {
  const [lines, setLines] = useState([]);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (index < MOCK_OUTPUT.length) {
      const timer = setTimeout(() => {
        setLines(prev => [...prev, MOCK_OUTPUT[index]]);
        setIndex(index + 1);
      }, Math.random() * 400 + 100);
      return () => clearTimeout(timer);
    }
  }, [index]);

  return (
    <section className="terminal-section" id="terminal">
      <div className="container">
        <div className="terminal-header">
          <h2>Core <span className="text-gradient-lime">Sovereignty</span></h2>
          <p className="text-secondary">O(1) O Muerte. Built on an immutable SQLite foundation.</p>
        </div>

        <div className="terminal-wrapper glass-panel">
          <div className="terminal-topbar">
            <div className="window-controls">
              <span className="control minimize"></span>
              <span className="control maximize"></span>
              <span className="control close"></span>
            </div>
            <div className="terminal-title">
              <Terminal size={14} /> SOVEREIGN_OS // CORTEX
            </div>
          </div>
          <div className="terminal-body">
            {lines.map((line, i) => (
              <div key={i} className="terminal-line">
                <span className="prompt">$&gt;</span> {line}
              </div>
            ))}
            {index < MOCK_OUTPUT.length && (
              <div className="terminal-line">
                <span className="prompt">$&gt;</span> <span className="cursor blink"></span>
              </div>
            )}
            {index >= MOCK_OUTPUT.length && (
              <div className="terminal-line">
                <span className="prompt text-gradient-lime">CORTEX$&gt;</span> <span className="cursor blink"></span>
              </div>
            )}
          </div>
        </div>

        <div className="features-grid">
          <div className="feature-card glass-panel">
            <Database className="feature-icon" color="var(--accent-lime)" size={32} />
            <h3>O(1) Resolution</h3>
            <p className="text-secondary">SQLite WAL optimized for instantaneous state fetching without blocking the main event loop.</p>
          </div>
          <div className="feature-card glass-panel">
            <div className="feature-icon" style={{color: 'var(--accent-violet)'}}>Ω₀</div>
            <h3>Self-Reference Axiom</h3>
            <p className="text-secondary">"If I write it, I execute it." Absolute agency in agentic code generation and validation.</p>
          </div>
          <div className="feature-card glass-panel">
            <div className="feature-icon" style={{color: 'var(--accent-gold)'}}>6/6</div>
            <h3>God Mode Security</h3>
            <p className="text-secondary">Zero-trust architecture with immune membranes stopping 100% of adversarial actions.</p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SovereignTerminal;
