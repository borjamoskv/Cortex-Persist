import React from 'react';
import { Database, Zap, Cpu, Activity } from 'lucide-react';
import './ArchitectureSection.css';

const ArchitectureSection = () => {
  return (
    <section className="architecture-section" id="architecture">
      <div className="container">
        <div className="arch-header">
          <h2 className="section-title">O(1) State <span className="text-gradient-lime">Resolution</span></h2>
          <p className="section-subtitle">A database that is a file. A file that is the OS.</p>
        </div>

        <div className="arch-features-wrapper">
          <div className="arch-main-feature glass-panel">
            <Database className="arch-icon main-icon" size={48} />
            <div className="arch-content">
              <h3>SQLite WAL Protocol</h3>
              <p className="text-secondary">Concurrency without locks. The Write-Ahead Log allows O(1) reads while asynchronous writes are persisted instantly. Data is immutable, ensuring no ghost state is ever orphaned.</p>
              <ul className="arch-list">
                <li><Zap size={16} color="var(--accent-lime)" /> <strong>Instantaneous Execution</strong></li>
                <li><Activity size={16} color="var(--accent-lime)" /> <strong>Asynchronous I/O</strong></li>
              </ul>
            </div>
          </div>

          <div className="arch-grid">
            <div className="arch-feature glass-panel">
              <Cpu className="arch-icon" size={24} color="var(--accent-gold)" />
              <h4>Context Boundary</h4>
              <p className="text-secondary text-sm">Every operation is isolated. A failed query leaves the system untouched. Entropy is nullified.</p>
            </div>
            <div className="arch-feature glass-panel">
              <Activity className="arch-icon" size={24} color="var(--accent-violet)" />
              <h4>Chronos Delta</h4>
              <p className="text-secondary text-sm">Temporal measurements dictate compaction strategies, maintaining lightweight persistence globally.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ArchitectureSection;
