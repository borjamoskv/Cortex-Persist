import React from 'react';
import { Database, Shield, Zap } from 'lucide-react';
import './Layout.css';

const Layout = ({ children }) => {
  return (
    <div className="layout-root">
      <nav className="navbar glass-panel">
        <div className="container nav-content">
          <div className="logo-section">
            <span className="logo-icon">C</span>
            <span className="logo-text">CORTEX<span className="accent-dot">.</span>PERSIST</span>
          </div>
          <div className="nav-links">
            <a href="#architecture" className="nav-link">Architecture</a>
            <a href="#security" className="nav-link">Security</a>
            <a href="#docs" className="nav-link">Docs</a>
            <a href="https://github.com/borjamoskv/Cortex-Persist" target="_blank" rel="noreferrer" className="btn btn-primary btn-sm">GitHub</a>
          </div>
        </div>
      </nav>

      <main>
        {children}
      </main>

      <footer className="footer border-top">
        <div className="container footer-content">
          <div className="footer-brand">
            <span className="logo-text">CORTEX<span className="accent-dot">.</span>PERSIST</span>
            <p className="footer-subtext">Sovereign State OS &copy; 2026. O(1) O Muerte.</p>
          </div>
          <div className="footer-links">
            <div className="link-col">
              <h4>System</h4>
              <a href="#">CLI</a>
              <a href="#">Relay Nodes</a>
            </div>
            <div className="link-col">
              <h4>Protocol</h4>
              <a href="#">ULTRATHINK</a>
              <a href="#">Security 6/6</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
