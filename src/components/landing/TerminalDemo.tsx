// @C5-REAL
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const demoSteps = [
  {
    command: 'cortex store "Vendor X failed compliance check" \\\n  --type decision \\\n  --project procurement \\\n  --confidence C4 \\\n  --source agent:reviewer',
    output: '[OK] Fact stored. Hash: 8f4e2a1b...',
  },
  {
    command: 'cortex search "compliance vendor failure"',
    output: 'Found 1 result:\n- "Vendor X failed compliance check" (confidence: C4) [8f4e2a1b]',
  },
  {
    command: 'cortex verify-ledger',
    output: '[OK] Ledger intact. 0 mutations detected.',
  }
];

export default function TerminalDemo() {
  const [stepIndex, setStepIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [showOutput, setShowOutput] = useState(false);

  useEffect(() => {
    if (stepIndex >= demoSteps.length) return;
    
    const currentCommand = demoSteps[stepIndex].command;
    
    if (charIndex < currentCommand.length) {
      const timeout = setTimeout(() => {
        setCharIndex(c => c + 1);
      }, 20 + Math.random() * 30);
      return () => clearTimeout(timeout);
    } else if (!showOutput) {
      const timeout = setTimeout(() => {
        setShowOutput(true);
      }, 400);
      return () => clearTimeout(timeout);
    } else {
      const timeout = setTimeout(() => {
        setStepIndex(s => s + 1);
        setCharIndex(0);
        setShowOutput(false);
      }, 2500);
      return () => clearTimeout(timeout);
    }
  }, [charIndex, showOutput, stepIndex]);

  return (
    <div className="surface-sunken" style={{ 
      borderRadius: 'var(--radius-xl)', 
      padding: '1.5rem', 
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: '0.85rem',
      lineHeight: 1.6,
      color: 'var(--accent-bright)',
      minHeight: '280px',
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem'
    }}>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.1)' }} />
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.1)' }} />
        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'rgba(255, 255, 255, 0.1)' }} />
      </div>
      
      {demoSteps.slice(0, stepIndex).map((step, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', opacity: 0.5 }}>
          <div><span style={{ color: 'var(--success)' }}>$</span> {step.command}</div>
          <div style={{ color: 'var(--muted)' }}>{step.output}</div>
        </div>
      ))}
      
      {stepIndex < demoSteps.length && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div>
            <span style={{ color: 'var(--success)' }}>$</span> {demoSteps[stepIndex].command.substring(0, charIndex)}
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ repeat: Infinity, duration: 0.8 }}
              style={{ display: 'inline-block', width: '8px', height: '1.2em', background: 'var(--accent-soft)', verticalAlign: 'middle', marginLeft: '4px' }}
            />
          </div>
          <AnimatePresence>
            {showOutput && (
              <motion.div 
                initial={{ opacity: 0, y: 5 }} 
                animate={{ opacity: 1, y: 0 }} 
                style={{ color: 'var(--muted)' }}
              >
                {demoSteps[stepIndex].output}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
