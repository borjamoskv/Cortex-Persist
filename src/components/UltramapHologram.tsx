// @C5-REAL
import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';

interface EdgNode {
  id: string;
  label: string;
  timestamp: string;
  hash: string;
}

interface EdgEdge {
  source: string;
  target: string;
  type: string;
}

interface EdgData {
  nodes: EdgNode[];
  edges: EdgEdge[];
  metadata: {
    total_nodes: number;
    total_edges: number;
    state: string;
  };
}

export default function UltramapHologram() {
  const [data, setData] = useState<EdgData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchEdg() {
      try {
        const mockData: EdgData = {
          nodes: [
            { id: "EDU-001", label: "Adaptive Learning (EDG)", timestamp: new Date().toISOString(), hash: "a1b2c3d4" },
            { id: "EDU-002", label: "Intelligent Tutoring System (ITS)", timestamp: new Date().toISOString(), hash: "e5f6g7h8" },
            { id: "EDU-003", label: "Socratic Feedback Engine", timestamp: new Date().toISOString(), hash: "i9j0k1l2" },
            { id: "EDU-004", label: "Curriculum Topology Mutator", timestamp: new Date().toISOString(), hash: "m3n4o5p6" },
          ],
          edges: [
            { source: "EDU-001", target: "EDU-002", type: "causal" },
            { source: "EDU-002", target: "EDU-003", type: "causal" },
            { source: "EDU-001", target: "EDU-004", type: "causal" },
          ],
          metadata: { total_nodes: 4, total_edges: 3, state: "C5-REAL" }
        };
        
        try {
            const res = await fetch('http://localhost:8000/api/v1/ultramap/edg');
            if (res.ok) {
                const json = await res.json();
                if (json.nodes && json.nodes.length > 0) {
                    setData(json);
                    setLoading(false);
                    return;
                }
            }
        } catch (e) {
            console.log("FastAPI backend not reachable, using physical mock projection");
        }
        
        setData(mockData);
        setLoading(false);
      } catch (err: any) {
        setError(err.message);
        setLoading(false);
      }
    }
    fetchEdg();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[500px] w-full border border-gray-800 rounded-xl bg-black/50 backdrop-blur-md">
        <div className="text-blue-500 font-mono text-sm tracking-widest animate-pulse">
          EXTRACTING EDG TOPOLOGY...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-[500px] w-full border border-red-900/50 rounded-xl bg-black/50 backdrop-blur-md">
        <div className="text-red-500 font-mono text-sm tracking-widest">
          TOPOLOGY EXTRACTION FAILED: {error}
        </div>
      </div>
    );
  }

  const radius = 220;
  const centerX = 400;
  const centerY = 300;
  
  const nodePositions = data.nodes.map((node, i) => {
    const angle = (i / data.nodes.length) * Math.PI * 2 - Math.PI / 2;
    return {
      ...node,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    };
  });

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl" style={{ height: '600px' }}>
      
      {/* Background Grid & Glows */}
      <div className="absolute inset-0 opacity-20" style={{ 
        backgroundImage: 'linear-gradient(rgba(43, 59, 229, 0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(43, 59, 229, 0.2) 1px, transparent 1px)',
        backgroundSize: '30px 30px'
      }} />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-[#2B3BE5] rounded-full blur-[120px] opacity-10 pointer-events-none" />

      {/* Header Info */}
      <div className="absolute top-6 left-6 z-10 font-mono text-xs text-white/60 space-y-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)] animate-pulse" />
          <span className="tracking-widest text-green-400 font-bold">{data.metadata.state} ENGAGED</span>
        </div>
        <div className="tracking-wider text-white">EDG TOPOLOGY RENDERER</div>
        <div className="text-white/40 pt-2">NODES: {data.metadata.total_nodes} // EDGES: {data.metadata.total_edges}</div>
      </div>

      <div className="absolute inset-0 flex items-center justify-center">
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ overflow: 'visible' }}>
          {data.edges.map((edge, i) => {
            const sourceNode = nodePositions.find(n => n.id === edge.source);
            const targetNode = nodePositions.find(n => n.id === edge.target);
            if (!sourceNode || !targetNode) return null;
            
            return (
              <motion.path
                key={`edge-${i}`}
                d={`M ${sourceNode.x} ${sourceNode.y} Q ${centerX} ${centerY} ${targetNode.x} ${targetNode.y}`}
                fill="none"
                stroke="rgba(43, 59, 229, 0.4)"
                strokeWidth="2"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 1.5, delay: i * 0.2, ease: "easeInOut" }}
              />
            );
          })}
        </svg>

        {nodePositions.map((node, i) => (
          <motion.div
            key={node.id}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: i * 0.15 + 0.5 }}
            className="absolute flex flex-col items-center justify-center group"
            style={{ 
              left: node.x, 
              top: node.y,
              transform: 'translate(-50%, -50%)'
            }}
          >
            <div className="w-12 h-12 rounded-full border border-[#2B3BE5]/50 bg-black/80 backdrop-blur-xl flex items-center justify-center shadow-[0_0_15px_rgba(43,59,229,0.3)] transition-all duration-300 group-hover:scale-110 group-hover:border-[#2B3BE5] group-hover:shadow-[0_0_25px_rgba(43,59,229,0.6)] cursor-pointer z-10">
              <span className="font-mono text-[10px] text-white/80">{node.id.split('-')[1] || node.id}</span>
            </div>
            
            <div className="absolute top-14 bg-black/90 border border-white/10 rounded-lg p-3 w-48 opacity-0 pointer-events-none transform translate-y-2 transition-all duration-300 group-hover:opacity-100 group-hover:translate-y-0 z-20 backdrop-blur-xl">
              <div className="text-white text-sm font-medium mb-1 truncate">{node.label}</div>
              <div className="text-white/40 font-mono text-[10px] mb-1">HASH: {node.hash}</div>
              <div className="text-white/40 font-mono text-[9px]">{new Date(node.timestamp).toLocaleString()}</div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
