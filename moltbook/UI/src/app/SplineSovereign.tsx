"use client";

import Spline from '@splinetool/react-spline';
import { useRef, useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// CORTEX Sovereign Aesthetic Integration v3.0
// Live API bridge: Node Alpha → /health, Node Beta → /v1/ask (RAG)

export default function SovereignSplineInterface() {
  const splineRef = useRef<any>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [entropyLevel, setEntropyLevel] = useState(0.010);
  const [cortisol, setCortisol] = useState<number | null>(null);
  const [neuroplasticity, setNeuroplasticity] = useState<number | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const [apiStatus, setApiStatus] = useState<'offline' | 'online' | 'unknown'>('unknown');
  const [logs, setLogs] = useState<string[]>([
    "[SYS] CORTEX Spline Engine Initialized",
    "[SYS] Awaiting API handshake...",
  ]);

  const pushLog = useCallback((msg: string) => {
    setLogs(prev => [...prev.slice(-5), msg]);
  }, []);

  // Boot: probe CORTEX API on load
  useEffect(() => {
    if (!isLoaded) return;
    (async () => {
      try {
        const res = await fetch('/api/cortex/health');
        if (res.ok) {
          const data = await res.json();
          setApiStatus('online');
          setCortisol(data.cortisol);
          setNeuroplasticity(data.neuroplasticity);
          pushLog(`[API] ${data.status} · v${data.version}`);
        } else {
          setApiStatus('offline');
          pushLog('[API] CORTEX unreachable — offline mode');
        }
      } catch {
        setApiStatus('offline');
        pushLog('[API] Connection refused — start uvicorn');
      }
    })();
  }, [isLoaded, pushLog]);

  // Entropy ticker (local simulation, no API cost)
  useEffect(() => {
    if (!isLoaded) return;
    const interval = setInterval(() => {
      setEntropyLevel(prev => {
        const jump = (Math.random() - 0.5) * 0.005;
        return Math.max(0.001, Math.min(0.099, prev + jump));
      });
    }, 3000);
    return () => clearInterval(interval);
  }, [isLoaded]);

  function onLoad(splineApp: any) {
    splineRef.current = splineApp;
    setIsLoaded(true);
  }

  function handleHover(nodeName: string) {
    if (splineRef.current) {
      splineRef.current.emitEvent('mouseHover', nodeName);
    }
    setActiveNode(nodeName);
  }

  function handleRest() {
    if (splineRef.current) {
      splineRef.current.emitEvent('mouseLeave');
    }
    setActiveNode(null);
  }

  // NODE ALPHA → CORTEX /health probe
  async function engageNodeAlpha() {
    if (isFetching) return;
    setIsFetching(true);
    pushLog('[CMD] > cortex health --probe');
    if (splineRef.current) splineRef.current.emitEvent('mouseDown', 'NodeAlpha');
    try {
      const res = await fetch('/api/cortex/health');
      const data = await res.json();
      if (res.ok) {
        setApiStatus('online');
        setCortisol(data.cortisol);
        setNeuroplasticity(data.neuroplasticity);
        pushLog(`[SYS] ${data.status} | cortisol:${data.cortisol} neuro:${data.neuroplasticity}`);
        pushLog(`[SYS] Engine: ${data.engine} · v${data.version}`);
      } else {
        setApiStatus('offline');
        pushLog(`[ERR] API returned ${res.status}`);
      }
    } catch {
      setApiStatus('offline');
      pushLog('[ERR] CORTEX API unreachable');
    } finally {
      setIsFetching(false);
    }
  }

  // NODE BETA → CORTEX /v1/ask (RAG query)
  async function engageNodeBeta() {
    if (isFetching) return;
    setIsFetching(true);
    pushLog('[CMD] > cortex ask "System entropy report"');
    if (splineRef.current) splineRef.current.emitEvent('mouseDown', 'NodeBeta');
    try {
      const res = await fetch('/api/cortex/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'What is the current system entropy and latest decisions?',
          k: 5,
          temperature: 0.2,
          max_tokens: 256,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        pushLog(`[RAG] ${data.facts_found} facts · model:${data.model}`);
        const answer = data.answer?.slice(0, 120) || 'No answer synthesized';
        pushLog(`[ANS] ${answer}`);
      } else {
        pushLog(`[503] ${data.detail || 'LLM offline — configure provider'}`);
      }
    } catch {
      pushLog('[ERR] RAG query failed — API unreachable');
    } finally {
      setIsFetching(false);
    }
  }

  return (
    <div className="relative w-full h-screen bg-[#0A0A0A] overflow-hidden font-sans text-white/90 selection:bg-[#CCFF00] selection:text-black">
      
      {/* 3D Canvas Layer with deep space gradient */}
      <div className={`absolute inset-0 z-0 transition-opacity duration-1500 ease-in-out ${isLoaded ? 'opacity-100' : 'opacity-0'} bg-gradient-to-b from-[#0A0A0A] via-[#0D0D0D] to-[#0A0A0A]`}>
        <Spline 
          scene="https://prod.spline.design/6Wq1Q7YGyM-iab9i/scene.splinecode" 
          onLoad={onLoad}
          className="w-full h-full"
        />
      </div>

      {/* Loading State Overlay */}
      <AnimatePresence>
        {!isLoaded && (
          <motion.div 
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.8, ease: "easeInOut" }}
            className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#0A0A0A] backdrop-blur-xl"
          >
            <div className="w-24 h-24 mb-8 relative">
                <div className="absolute inset-0 border-t-2 border-r-2 border-[#CCFF00] rounded-full animate-spin" style={{ animationDuration: '3s' }}></div>
                <div className="absolute inset-2 border-b-2 border-l-2 border-white/40 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '2s' }}></div>
                <div className="absolute inset-6 bg-[#CCFF00]/10 rounded-full animate-pulse"></div>
            </div>
            <div className="overflow-hidden">
                <motion.span 
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="text-xs tracking-[0.5em] text-[#CCFF00] uppercase font-mono"
                >
                SYNTHESIZING GEOMETRY
                </motion.span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sovereign UI Overlay Layer */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: isLoaded ? 1 : 0 }}
        transition={{ duration: 1, delay: 0.5 }}
        className="relative z-10 flex flex-col justify-between h-full p-6 md:p-12 pointer-events-none"
      >
        {/* Top Header */}
        <header className="flex justify-between items-start w-full pointer-events-auto">
            <div className="flex flex-col">
                <h1 className="text-3xl md:text-5xl font-bold tracking-tighter mix-blend-difference text-white">
                  CORTEX <span className="text-[#CCFF00] font-light">SPLINE</span>
                </h1>
                <p className="text-[#CCFF00]/60 font-mono text-xs tracking-wider mt-2">v5.0.1_BETA // ZERO_HUMAN_READY</p>
            </div>
            <div className="text-right font-mono text-xs space-y-1 bg-black/40 backdrop-blur-md border border-white/5 p-4 rounded-lg">
                <div className="flex justify-between gap-8">
                    <span className="text-white/40">API</span>
                    <span className={apiStatus === 'online' ? 'text-[#CCFF00]' : apiStatus === 'offline' ? 'text-red-400' : 'text-white/50'}>
                        {apiStatus.toUpperCase()}
                    </span>
                </div>
                <div className="flex justify-between gap-8">
                    <span className="text-white/40">CORTISOL</span>
                    <span className="text-white">{cortisol !== null ? cortisol.toFixed(3) : '—'}</span>
                </div>
                <div className="flex justify-between gap-8">
                    <span className="text-white/40">NEURO</span>
                    <span className="text-white">{neuroplasticity !== null ? neuroplasticity.toFixed(3) : '—'}</span>
                </div>
                <div className="flex justify-between gap-8">
                    <span className="text-white/40">ENTROPY</span>
                    <span className={`${entropyLevel > 0.05 ? 'text-red-400' : 'text-[#CCFF00]'}`}>
                        {entropyLevel.toFixed(4)} H(X)
                    </span>
                </div>
            </div>
        </header>

        {/* Center/Bottom Interactions */}
        <div className="flex flex-col md:flex-row justify-between items-end w-full pointer-events-auto mt-auto">
          {/* Action Panel */}
          <div className="backdrop-blur-xl bg-[#0A0A0A]/60 border border-white/10 p-8 rounded-2xl shadow-2xl max-w-md w-full relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#CCFF00]/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            
            <h2 className="text-xl font-bold mb-6 text-white tracking-wide">ORCHESTRATION</h2>
            
            <div className="space-y-4">
              <button 
                onMouseEnter={() => handleHover('NodeAlpha')}
                onClick={engageNodeAlpha}
                onMouseLeave={handleRest}
                disabled={isFetching}
                className={`w-full relative flex items-center justify-between px-6 py-4 bg-white/5 border border-white/10 hover:border-[#CCFF00] hover:bg-[#CCFF00]/10 transition-all duration-300 group/btn ${isFetching ? 'opacity-50 cursor-wait' : ''}`}
              >
                <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${apiStatus === 'online' ? 'bg-[#CCFF00] shadow-[0_0_8px_#ccff00]' : 'bg-white/40'} group-hover/btn:bg-[#CCFF00] group-hover/btn:shadow-[0_0_10px_#ccff00] transition-colors`}></div>
                    <span className="font-mono text-sm tracking-widest text-white/80 group-hover/btn:text-white">PROBE HEALTH</span>
                </div>
                <span className="text-xs text-white/30 font-mono">/health</span>
              </button>
              
              <button 
                onMouseEnter={() => handleHover('NodeBeta')}
                onClick={engageNodeBeta}
                onMouseLeave={handleRest}
                disabled={isFetching}
                className={`w-full relative flex items-center justify-between px-6 py-4 bg-white/5 border border-white/10 hover:border-[#CCFF00] hover:bg-[#CCFF00]/10 transition-all duration-300 group/btn ${isFetching ? 'opacity-50 cursor-wait' : ''}`}
              >
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-white/40 group-hover/btn:bg-[#CCFF00] group-hover/btn:shadow-[0_0_10px_#ccff00] transition-colors"></div>
                    <span className="font-mono text-sm tracking-widest text-white/80 group-hover/btn:text-white">ASK CORTEX</span>
                </div>
                <span className="text-xs text-white/30 font-mono">/v1/ask</span>
              </button>
            </div>
            
            <div className="mt-8 font-mono text-xs text-white/40 flex justify-between uppercase border-t border-white/5 pt-4">
              <span>Target: {activeNode || 'NONE'}</span>
              <span className={activeNode ? 'text-[#CCFF00] animate-pulse' : ''}>
                {activeNode ? 'READY' : 'STANDBY'}
              </span>
            </div>
          </div>

          {/* Live Terminal/Logs */}
          <div className="hidden md:flex flex-col justify-end w-80 h-48 bg-black/80 backdrop-blur-md border border-white/10 p-4 font-mono text-xs rounded-lg rounded-br-none rounded-tr-none border-r-0">
            <div className="mb-2 text-[#CCFF00]/60 border-b border-white/10 pb-2">~ CORTEX TERMINAL // tty1</div>
            <div className="flex flex-col gap-1 overflow-hidden justify-end flex-grow">
               <AnimatePresence initial={false}>
                  {logs.map((log, i) => (
                    <motion.div 
                        key={`${log}-${i}`}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0 }}
                        className="text-white/70"
                    >
                        <span className="text-[#CCFF00]/40 mr-2">{'>'}</span>{log}
                    </motion.div>
                  ))}
               </AnimatePresence>
            </div>
          </div>
        </div>

      </motion.div>
      
      {/* Decorative Cybernetic Scanline */}
      <motion.div 
        animate={{ top: ['-10%', '110%'] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
        className="absolute left-0 w-full h-32 bg-gradient-to-b from-transparent via-[#CCFF00]/[0.02] to-transparent z-0 pointer-events-none"
      />
      
    </div>
  );
}
