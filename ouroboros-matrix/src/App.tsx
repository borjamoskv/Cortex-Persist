import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { Terminal, Activity, AlertCircle, Database, Shield, Zap, Cpu, HeartPulse } from 'lucide-react';
import { SwarmScene } from './components/SwarmScene';
import { useOuroborosStream } from './hooks/useOuroborosStream';

function App() {
  const { stats, ledger, isConnected } = useOuroborosStream();

  return (
    <>
      {/* Background 3D Layer (GPU Accelerated) */}
      <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0 }}>
        <Canvas camera={{ position: [0, 0, 45], fov: 45 }}>
          <color attach="background" args={['#000000']} />
          <ambientLight intensity={0.4} />
          <SwarmScene />
          <EffectComposer>
            <Bloom luminanceThreshold={stats.isHealing ? 0.05 : 0.1} luminanceSmoothing={0.9} mipmapBlur />
          </EffectComposer>
          <OrbitControls enableZoom={true} autoRotate autoRotateSpeed={stats.isHealing ? 2.0 : 0.2} />
        </Canvas>
      </div>

      {/* Sovereign HUD Overlay (Industrial Noir) */}
      <div id="hud-root" style={{ 
        position: 'absolute', 
        inset: 0, 
        padding: '2rem', 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'space-between',
        pointerEvents: 'none',
        border: stats.isHealing ? '2px solid var(--accent-red)' : 'none',
        transition: 'border 0.5s ease'
      }}>
        
        {/* Header: OS Status & Global Exergy */}
        <header style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'flex-start' }}>
          <div className="mica-panel" style={{ pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: '1.2rem', minWidth: '320px' }}>
            <div className={`p-3 rounded-full ${isConnected ? 'bg-accent-green-alpha' : 'bg-accent-red-alpha'}`} style={{ 
              background: isConnected ? 'rgba(0, 255, 102, 0.1)' : 'rgba(255, 32, 64, 0.1)',
              padding: '0.8rem',
              borderRadius: '50%'
            }}>
              <Cpu size={28} color={isConnected ? 'var(--accent-green)' : 'var(--accent-red)'} />
            </div>
            <div>
              <h1 className="display-title" style={{ fontSize: '1.4rem', letterSpacing: '0.1em' }}>
                {stats.isHealing ? "AUTOPOIESIS_ACTIVE" : "OUROBOROS_MATRIX_V5.0"}
              </h1>
              <div className="mono-metric" style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span className={`pulse-dot ${isConnected ? 'glow-active' : 'glow-danger'}`} style={{ 
                  width: '8px', height: '8px', borderRadius: '50%', background: isConnected ? 'var(--accent-green)' : 'var(--accent-red)' 
                }} />
                {isConnected ? 'C5_SOVEREIGN_ONTOGENY' : 'OFFLINE_FALSATION_ENGINE'} | CYCLE_{stats.cycleCount}
              </div>
            </div>
          </div>

          {stats.isHealing && (
            <div className="mica-panel glow-danger" style={{ pointerEvents: 'auto', background: 'rgba(255,32,64,0.1)', border: '1px solid var(--accent-red)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--accent-red)' }}>
                    <HeartPulse className="animate-pulse" size={24} />
                    <div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>REMEDIATION_IN_PROGRESS</div>
                        <div style={{ fontSize: '0.6rem', opacity: 0.8 }}>SOVEREIGN_SURGEON_ACTIVE</div>
                    </div>
                </div>
            </div>
          )}

          <div className="mica-panel" style={{ pointerEvents: 'auto', display: 'flex', gap: '3rem', minWidth: '400px' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.4rem' }}>
                Exergy Yield (C5_YIELD)
              </div>
              <div className="mono-metric" style={{ fontSize: '2rem', color: 'var(--accent-green)', textShadow: '0 0 15px rgba(0,255,102,0.3)' }}>
                ${stats.totalExergy.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div style={{ borderLeft: '1px solid var(--border-light)', paddingLeft: '2rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.2rem' }}>
                System_State
              </div>
              <div className="stat-card">
                  <span className={`pulse-dot ${stats.isHealing ? 'glow-danger' : 'glow-active'}`} />
                  <span style={{ fontSize: '0.8rem', color: stats.isHealing ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                      {stats.isHealing ? 'AUTOPOIESIS' : 'STABLE_C5'}
                  </span>
              </div>
              <div className="stat-card">
                  <span style={{ fontSize: '0.6rem', color: 'var(--text-dim)' }}>EFFICIENCY_GEN:</span>
                  <span className="mono-metric" style={{ color: 'var(--accent-blue)', marginLeft: '0.5rem' }}>98.4%</span>
              </div>
            </div>
          </div>
        </header>

        {/* Footer: Multi-Agent Metrics & Real-Time Ledger */}
        <footer style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', width: '100%', gap: '2rem' }}>
          
          <div className="mica-panel" style={{ pointerEvents: 'auto', width: '350px' }}>
            <h2 className="display-title" style={{ fontSize: '0.9rem', marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--accent-blue)' }}>
              <Activity size={18} /> SWARM_KERNEL_TELEMETRY
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              <div className="flex-between">
                <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>ACTIVE_VSA_DIMENSIONS</span>
                <span className="mono-metric">10,000 / 10,000</span>
              </div>
              <div className="flex-between">
                <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>FUZZ_THROUGHPUT</span>
                <span className="mono-metric">{stats.totalScanned.toLocaleString()} OPS/s</span>
              </div>
              <div className="flex-between">
                <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>EPISTEMIC_CERTAINTY</span>
                <span className="mono-metric">98.4%</span>
              </div>
              <div style={{ marginTop: '0.5rem', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: stats.isHealing ? '100%' : '85%', height: '100%', background: stats.isHealing ? 'var(--accent-red)' : 'var(--accent-blue)', transition: 'all 2s linear' }} />
              </div>
            </div>
          </div>

          <div className="mica-panel mica-noir" style={{ pointerEvents: 'auto', flex: 1, maxWidth: '600px', maxHeight: '300px', overflowY: 'auto' }}>
            <h2 className="display-title" style={{ fontSize: '0.9rem', marginBottom: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--accent-green)' }}>
              <Database size={18} /> SOVEREIGN_LEDGER_SYSTEM
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {ledger.length === 0 ? (
                <div className="flex-center" style={{ color: 'var(--text-dim)', fontSize: '0.75rem', height: '100px', border: '1px dashed var(--border-light)', borderRadius: '8px' }}>
                  AWAITING_STREAM_INITIALIZATION...
                </div>
              ) : (
                ledger.map((entry, i) => (
                  <div key={entry.id} className="ledger-row" style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    padding: '0.6rem 0.8rem', 
                    background: i === 0 ? 'rgba(43, 59, 229, 0.05)' : 'transparent',
                    borderLeft: `3px solid ${entry.type === 'hit' ? 'var(--accent-red)' : entry.type === 'remediation' ? 'var(--accent-red)' : entry.type === 'yield' ? 'var(--accent-green)' : 'var(--accent-blue)'}`,
                    fontSize: '0.75rem',
                    animation: entry.type === 'remediation' ? 'glitch-anim 0.2s infinite' : 'none'
                  }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                      <span className="mono-metric" style={{ color: 'var(--text-dim)', width: '70px' }}>
                        {entry.timestamp.split('T')[1].substring(0,8)}
                      </span>
                      <span style={{ color: entry.type === 'hit' || entry.type === 'remediation' ? 'var(--accent-red)' : entry.type === 'yield' ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                        {entry.source}
                      </span>
                    </div>
                    <div className="mono-metric" style={{ color: entry.type === 'yield' ? 'var(--accent-green)' : 'var(--text-secondary)' }}>
                      {entry.value || 'ACTIVE'}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}

export default App;
