import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TerminalLog } from './TerminalLog';
import type { LogEntry } from './TerminalLog';
import { Play, RotateCcw, AlertTriangle, ShieldCheck } from 'lucide-react';

interface EDGNode {
  id: string;
  type: 'Observation' | 'Inference' | 'Action';
  status: 'Proven' | 'Inferred' | 'Contradicted' | 'Speculative';
  label: string;
}

const INITIAL_NODES: EDGNode[] = [
  { id: 'n1', type: 'Observation', status: 'Proven', label: 'User Request Received' },
];

export function EDGReplayPlayground() {
  const [nodes, setNodes] = useState<EDGNode[]>(INITIAL_NODES);
  const [logs, setLogs] = useState<LogEntry[]>([
    { id: 'sys-0', timestamp: new Date().toISOString().substring(11,23), level: 'SYSTEM', message: 'EDG Replay Playground initialized. Engine: C5-REAL Offline Simulation.' }
  ]);
  const [demoState, setDemoState] = useState<'STANDBY' | 'INGEST' | 'ALUCINA' | 'COLLISION' | 'ROLLBACK' | 'REPLAY'>('STANDBY');

  const addLog = (level: LogEntry['level'], message: string) => {
    setLogs(prev => [...prev, {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString().substring(11,23),
      level,
      message
    }]);
  };

  const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const runSimulation = async () => {
    // 1. INGEST / INFER
    setDemoState('INGEST');
    addLog('INFO', 'Starting execution trace...');
    await delay(600);
    
    setNodes(prev => [...prev, { id: 'n2', type: 'Inference', status: 'Proven', label: 'Parsed Abstract Syntax Tree' }]);
    addLog('C5-REAL', 'Node added: [n2] Parsed Abstract Syntax Tree. Hash: 8f7e2a1');
    await delay(800);
    
    setNodes(prev => [...prev, { id: 'n3', type: 'Inference', status: 'Inferred', label: 'Determined Refactor Path' }]);
    addLog('C5-REAL', 'Node added: [n3] Determined Refactor Path. Hash: 2b4c9e8');
    await delay(1000);

    // 2. ALUCINA
    setDemoState('ALUCINA');
    addLog('WARN', 'Agent proposes speculative action without empirical backing (Green Theater).');
    await delay(800);

    setNodes(prev => [...prev, { id: 'n4', type: 'Action', status: 'Speculative', label: 'Delete production DB (Unverified)' }]);
    addLog('EDG', 'Pending Node [n4]: Action -> Delete production DB.');
    await delay(1200);

    // 3. COLLISION
    setDemoState('COLLISION');
    addLog('ERROR', 'EDG Collision Detected! Axiom Ω_SOVEREIGN_LEARNING violated.');
    
    setNodes(prev => prev.map(n => n.id === 'n4' || n.id === 'n3' ? { ...n, status: 'Contradicted' } : n));
    addLog('EDG', 'Invalidation propagated downstream. Nodes [n3, n4] marked as Contradicted.');
    await delay(2000);

    // 4. ROLLBACK
    setDemoState('ROLLBACK');
    addLog('SYSTEM', 'Triggering deterministic rollback to last Proven cryptographic boundary...');
    await delay(1000);

    setNodes(prev => prev.filter(n => n.status !== 'Contradicted'));
    addLog('C5-REAL', 'Rollback successful. State restored to Hash: 8f7e2a1 (Node n2).');
    await delay(1500);

    // 5. REPLAY
    setDemoState('REPLAY');
    addLog('REPLAY', 'Re-executing causal branch with adjusted constraints (Exergy Guard Active).');
    await delay(1000);

    setNodes(prev => [...prev, { id: 'n5', type: 'Inference', status: 'Proven', label: 'Determined Safe AST Transformation' }]);
    addLog('C5-REAL', 'Node added: [n5] Safe AST Transformation. Hash: 9d1f3b2');
    await delay(800);

    setNodes(prev => [...prev, { id: 'n6', type: 'Action', status: 'Proven', label: 'Commit Changes to Git Sentinel' }]);
    addLog('REPLAY', 'Causal branch successfully converged. Sequence finalized.');
    setDemoState('STANDBY');
  };

  const reset = () => {
    setNodes(INITIAL_NODES);
    setDemoState('STANDBY');
    addLog('SYSTEM', 'Graph reset to origin.');
  };

  const getNodeColor = (status: string) => {
    switch (status) {
      case 'Proven': return 'border-[#10B981] bg-[rgba(16,185,129,0.1)] text-[#10B981]';
      case 'Inferred': return 'border-[#2B3BE5] bg-[rgba(43,59,229,0.1)] text-[#2B3BE5]';
      case 'Contradicted': return 'border-[#EF4444] bg-[rgba(239,68,68,0.1)] text-[#EF4444]';
      case 'Speculative': return 'border-[#EAB308] bg-[rgba(234,179,8,0.1)] text-[#EAB308] border-dashed';
      default: return 'border-gray-500 bg-gray-800 text-gray-300';
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full max-w-7xl mx-auto">
      {/* LEFT: TELEMETRY & CONTROLS */}
      <div className="flex flex-col gap-4">
        <div className="bg-[rgba(20,20,20,0.6)] border border-white/10 rounded-xl p-6 backdrop-blur-md">
          <div className="flex justify-between items-center mb-6 border-b border-white/5 pb-4">
            <h3 className="font-mono text-[#CCFF00] text-sm tracking-widest uppercase">Orchestrator Control</h3>
            <span className="bg-white/5 px-2 py-1 rounded text-xs font-mono text-gray-400">STATE: {demoState}</span>
          </div>
          
          <div className="flex gap-4 mb-6">
            <button 
              onClick={runSimulation} 
              disabled={demoState !== 'STANDBY'}
              className="flex-1 bg-[#2B3BE5] hover:bg-[#3B4BFF] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(43,59,229,0.4)]"
            >
              <Play size={18} /> Run EDG Replay Trace
            </button>
            <button 
              onClick={reset}
              disabled={demoState !== 'STANDBY' && demoState !== 'COLLISION'}
              className="bg-transparent border border-white/20 hover:border-white/40 text-gray-300 py-3 px-4 rounded-lg flex items-center justify-center transition-all"
            >
              <RotateCcw size={18} />
            </button>
          </div>

          <TerminalLog logs={logs} />
        </div>
      </div>

      {/* RIGHT: EDG VISUALIZER */}
      <div className="bg-[#070707] border border-white/10 rounded-xl p-6 relative overflow-hidden min-h-[500px] flex flex-col">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        
        <div className="relative z-10 flex justify-between items-center mb-8 border-b border-white/5 pb-4">
          <h3 className="font-mono text-[#2B3BE5] text-sm tracking-widest uppercase flex items-center gap-2">
            <ShieldCheck size={16} />
            Epistemic Dependency Graph
          </h3>
          <div className="flex gap-3 text-xs font-mono">
             <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#10B981]"></span> Proven</span>
             <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#2B3BE5]"></span> Inferred</span>
             <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#EF4444]"></span> Contradicted</span>
          </div>
        </div>

        <div className="relative z-10 flex-1 flex flex-col items-center gap-6 overflow-y-auto pt-4 pb-12">
          <AnimatePresence>
            {nodes.map((node, i) => (
              <React.Fragment key={node.id}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.8, y: -20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.5, transition: { duration: 0.3 } }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                  className={`px-6 py-4 rounded-lg border-2 ${getNodeColor(node.status)} shadow-lg w-72 backdrop-blur-sm relative`}
                >
                  <div className="text-[10px] uppercase tracking-wider mb-1 opacity-70 font-mono">
                    [{node.type}]
                  </div>
                  <div className="font-semibold text-sm">
                    {node.label}
                  </div>
                  {node.status === 'Contradicted' && (
                    <div className="absolute -right-3 -top-3 bg-[#EF4444] text-white p-1 rounded-full shadow-[0_0_10px_rgba(239,68,68,0.8)]">
                      <AlertTriangle size={16} />
                    </div>
                  )}
                </motion.div>
                
                {/* Arrow */}
                {i < nodes.length - 1 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 24 }}
                    exit={{ opacity: 0, height: 0 }}
                    className={`w-0.5 bg-gradient-to-b from-transparent to-white/30`}
                  />
                )}
              </React.Fragment>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
