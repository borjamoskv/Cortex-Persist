import React, { useEffect, useState } from 'react';
import './PreloadScreen.css';

/**
 * PreloadScreen – A cinematic loader that simulates the initialization of the
 * cryptographic guard (Z3 SMT Guard) before revealing the hero canvas.
 *
 * Design: Industrial Noir 2026 – dark background, neon accent, subtle glitch.
 */
const INIT_LOGS = [
  { text: 'LOG: Bootstrapping CORTEX-Persist engine (v10.0-LEGION)...', type: 'info' },
  { text: 'LOG: Activating Byzantine containment boundaries...', type: 'info' },
  { text: 'LOG: Checking Ed25519 signature registry...', type: 'info' },
  { text: 'SECURE: RingBuffer trust validation completed [2048-bit]', type: 'success' },
  { text: 'DB: Loading sqlite-vec & SQLite WASM virtual tables...', type: 'info' },
  { text: 'GUARD: Spawning Z3 SMT solver context...', type: 'info' },
  { text: 'VALID: Z3 SMT Guard state contradiction scan: 0 errors', type: 'success' },
  { text: 'LEDGER: Verifying cryptographic hash chain continuity...', type: 'info' },
  { text: 'AUDIT: Block chain verification: PREV_HASH matches', type: 'success' },
  { text: 'SYSTEM: Epistemic status C5-REAL verified. Launching...', type: 'success' },
];

export default function PreloadScreen() {
  const [visible, setVisible] = useState(true);
  const [logs, setLogs] = useState<{ text: string; type: string }[]>([]);

  useEffect(() => {
    // Add logs one by one
    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex < INIT_LOGS.length) {
        setLogs((prev) => [...prev, INIT_LOGS[currentIndex]]);
        currentIndex++;
      } else {
        clearInterval(interval);
        // Delay disappearance slightly after logs finish
        setTimeout(() => setVisible(false), 500);
      }
    }, 280);

    return () => clearInterval(interval);
  }, []);

  if (!visible) return null;

  return (
    <div className="preload-screen">
      <div className="preload-spinner" />
      <div className="preload-message">Initializing Z3 SMT Guard</div>
      <div className="preload-console">
        {logs.map((log, index) => (
          <div key={index} className={`preload-console-line ${log.type}`}>
            {log.text}
          </div>
        ))}
      </div>
    </div>
  );
}

