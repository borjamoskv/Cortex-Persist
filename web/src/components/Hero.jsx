import React, { useEffect, useState } from 'react';
import './Hero.css';

const Hero = () => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <section className="hero-section">
      <div className="hero-bg-glow"></div>
      
      <div className={`container hero-content ${mounted ? 'animate-in' : ''}`}>
        <div className="badge-wrapper">
          <span className="badge">v4.0.0</span>
          <span className="badge-text text-gradient-lime">Sovereign State Architecture Fully Deployed</span>
        </div>
        
        <h1 className="hero-title">
          Context Is <br />
          <span className="text-gradient-lime">Immutable.</span><br />
          <span className="text-gradient-violet">Zero Entropy.</span>
        </h1>
        
        <p className="hero-subtitle">
          Cortex Persist enforces O(1) state resolution and immune memory membranes. Built for the Industrial Noir 2026 paradigm. Absolute technical sovereignty.
        </p>
        
        <div className="hero-actions">
          <a href="#architecture" className="btn btn-primary">Initialize Node</a>
          <a href="#docs" className="btn btn-outline">Read Protocol</a>
        </div>
      </div>
    </section>
  );
};

export default Hero;
