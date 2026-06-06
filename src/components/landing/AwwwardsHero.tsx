// @C5-REAL
import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import HeroCanvas from './HeroCanvas';
import CortexAuditLedger from '../CortexAuditLedger';

export default function AwwwardsHero() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Create a scroll trigger range over 250vh
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start']
  });

  // Hero Copy fades out early and moves up
  const opacityHero = useTransform(scrollYProgress, [0, 0.3], [1, 0]);
  const yHero = useTransform(scrollYProgress, [0, 0.3], [0, -120]);
  const scaleHero = useTransform(scrollYProgress, [0, 0.3], [1, 0.9]);

  // Ledger fades in, scales up, and moves up to center
  const opacityLedger = useTransform(scrollYProgress, [0.25, 0.6], [0, 1]);
  const yLedger = useTransform(scrollYProgress, [0.25, 0.6], [150, 0]);
  const scaleLedger = useTransform(scrollYProgress, [0.25, 0.6], [0.9, 1]);
  const zIndexLedger = useTransform(scrollYProgress, [0, 0.3, 0.31], [0, 0, 20]);

  // Subtle background zoom
  const scaleBg = useTransform(scrollYProgress, [0, 1], [1, 1.15]);

  return (
    <div ref={containerRef} style={{ height: '250vh', position: 'relative', width: '100%', zIndex: 10 }}>
      {/* Sticky Container */}
      <div style={{ position: 'sticky', top: 0, height: '100vh', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        
        {/* Background Canvas */}
        <motion.div style={{ position: 'absolute', inset: 0, zIndex: 0, scale: scaleBg }}>
          <HeroCanvas />
        </motion.div>

        {/* Hero Content */}
        <motion.div 
          style={{ 
            opacity: opacityHero, 
            y: yHero, 
            scale: scaleHero, 
            position: 'absolute', 
            zIndex: 10, 
            width: '100%', 
            maxWidth: '1200px', 
            padding: '0 2rem' 
          }}
        >
          <div className="hero-copy" style={{ textAlign: 'center', alignItems: 'center', margin: '0 auto', maxWidth: '800px' }}>
            <p className="eyebrow" style={{ marginBottom: '1.5rem', display: 'inline-block', padding: '0.5rem 1rem', background: 'rgba(43, 59, 229, 0.1)', border: '1px solid rgba(43, 59, 229, 0.3)', borderRadius: '999px', color: 'var(--accent-soft)' }}>
              Developer SaaS / Built for AI Agent Teams
            </p>
            <h1 style={{ fontSize: 'clamp(3.5rem, 8vw, 6.5rem)', lineHeight: 0.95, marginBottom: '2rem', textWrap: 'balance', fontFamily: '"Orbitron", sans-serif' }}>
              Know exactly what your <span style={{ color: 'var(--accent-soft)' }}>AI agents</span> did.
            </h1>
            <p className="hero-text" style={{ fontSize: '1.25rem', maxWidth: '640px', margin: '0 auto 2.5rem', color: 'var(--muted)' }}>
              Track every decision, prove integrity, and replay failures without relying on logs, screenshots, or human memory.
            </p>
            <div className="action-row" style={{ justifyContent: 'center' }}>
              <a className="button-primary" href="/api-key" style={{ padding: '1rem 2rem', fontSize: '1.1rem' }}>Start logging events</a>
              <a className="button-secondary" href="https://github.com/borjamoskv/Cortex-Persist" target="_blank" rel="noreferrer" style={{ padding: '1rem 2rem', fontSize: '1.1rem' }}>
                View Documentation
              </a>
            </div>
            
            <div style={{ marginTop: '3rem', opacity: 0.7 }}>
              <p className="eyebrow" style={{ marginBottom: '1rem', fontSize: '0.7rem' }}>Scroll to experience the cryptographic ledger</p>
              <div style={{ width: '1px', height: '40px', background: 'linear-gradient(to bottom, var(--accent-soft), transparent)', margin: '0 auto' }} />
            </div>
          </div>
        </motion.div>

        {/* Live Demo Ledger */}
        <motion.div 
          style={{ 
            opacity: opacityLedger, 
            y: yLedger, 
            scale: scaleLedger, 
            zIndex: zIndexLedger,
            position: 'absolute', 
            width: '100%', 
            maxWidth: '1080px', 
            padding: '0 2rem' 
          }}
        >
          <div className="surface-sunken" style={{ padding: '0.5rem', borderRadius: 'var(--radius-xl)', boxShadow: '0 30px 120px rgba(43, 59, 229, 0.15)', border: '1px solid var(--line-strong)', background: 'var(--bg-1)' }}>
            <CortexAuditLedger />
          </div>
        </motion.div>

      </div>
    </div>
  );
}
