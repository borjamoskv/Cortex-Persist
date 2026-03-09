import React from 'react';
import { Shield, Lock, EyeOff, XOctagon, Zap, Server } from 'lucide-react';
import './SecuritySection.css';

const SecuritySection = () => {
  return (
    <section className="security-section" id="security">
      <div className="container">
        <div className="section-header text-center">
          <h2 className="section-title">
            <span className="text-gradient-violet">6/6</span> Matrices Interceptées
          </h2>
          <p className="section-subtitle">Absolute God Mode Security. Bypassing the perception layer is impossible via the Immune Membrane.</p>
        </div>

        <div className="security-grid margin-top-xl">
          <div className="security-card glass-panel">
            <Shield className="sec-icon sec-icon-lime" size={32} />
            <h4>Immune Membrane</h4>
            <p className="text-secondary text-sm">Validates every inbound payload. If entropy is detected, the transaction is dropped in O(1). No parsing of deformed inputs.</p>
          </div>
          
          <div className="security-card glass-panel">
            <Lock className="sec-icon sec-icon-gold" size={32} />
            <h4>Quarantine Lockdown Ω₉</h4>
            <p className="text-secondary text-sm">Automated system isolation. On threshold breach, CORTEX enters Ω₉, barring network access while retaining internal compute.</p>
          </div>

          <div className="security-card glass-panel">
            <XOctagon className="sec-icon sec-icon-violet" size={32} />
            <h4>Zero-Trust Exceptions</h4>
            <p className="text-secondary text-sm">No `except Exception`. Every failure path is explicitly typed, handled, and logged for post-mortem derivation.</p>
          </div>
          
          <div className="security-card glass-panel">
            <EyeOff className="sec-icon sec-icon-blue" size={32} />
            <h4>Shadow Relay Proxy</h4>
            <p className="text-secondary text-sm">Local GIDATU instances communicate through edge proxies. Outer cloud APIs never touch the inner sovereign loop.</p>
          </div>
        </div>

        <div className="stat-banner glass-panel margin-top-xl text-center">
          <h3 className="text-gradient-lime">100% Attack Prevention</h3>
          <p className="text-secondary">Benchmark results: 6/6 critical vulnerabilities intercepted at the firewall layer.</p>
        </div>
      </div>
    </section>
  );
};

export default SecuritySection;
