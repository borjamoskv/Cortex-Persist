import { motion, useInView } from 'framer-motion';
import { Check, X, Minus, Crosshair } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1];

type Status = 'yes' | 'no' | 'partial';

interface Row {
  feature: string;
  cortex: string;
  cortexStatus: Status;
  mem0: string;
  mem0Status: Status;
  zep: string;
  zepStatus: Status;
}

const data: Row[] = [
  {
    feature: "Cryptographic Ledger",
    cortex: "SHA-256 + Merkle", cortexStatus: 'yes',
    mem0: "None", mem0Status: 'no',
    zep: "None", zepStatus: 'no',
  },
  {
    feature: "EU AI Act Ready",
    cortex: "Verifiable", cortexStatus: 'yes',
    mem0: "No guarantees", mem0Status: 'no',
    zep: "No guarantees", zepStatus: 'no',
  },
  {
    feature: "Data Lineage",
    cortex: "100% Deterministic", cortexStatus: 'yes',
    mem0: "Heuristic", mem0Status: 'partial',
    zep: "Heuristic", zepStatus: 'partial',
  },
  {
    feature: "Consensus Protocol",
    cortex: "WBFT", cortexStatus: 'yes',
    mem0: "None", mem0Status: 'no',
    zep: "None", zepStatus: 'no',
  },
  {
    feature: "Local-First",
    cortex: "Embedded SQLite", cortexStatus: 'yes',
    mem0: "Cloud API", mem0Status: 'no',
    zep: "Self-host option", zepStatus: 'partial',
  },
  {
    feature: "Open Source",
    cortex: "Apache 2.0", cortexStatus: 'yes',
    mem0: "Partial", mem0Status: 'partial',
    zep: "BSL", zepStatus: 'partial',
  },
];

function StatusIcon({ status }: { status: Status }) {
  if (status === 'yes') return <Check className="w-4 h-4 text-cyber-lime" />;
  if (status === 'no') return <X className="w-4 h-4 text-red-500/50" />;
  return <Minus className="w-4 h-4 text-text-tertiary" />;
}

export function Knockout() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="comparison" className="py-32 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-20" />

      {/* Massive Typographic Watermark */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-10">
        <h1 className="text-watermark text-[20vw] whitespace-nowrap text-red-500 mix-blend-overlay">
          MATRIX
        </h1>
      </div>

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        {/* Header */}
        <div className="mb-20">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, ease }}
            className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-none border-l-2 border-red-500 bg-red-500/[0.05] text-red-500 text-[10px] font-mono uppercase tracking-[0.3em] mb-6"
          >
            <Crosshair className="w-3.5 h-3.5" />
            Competitive Analysis
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-5xl md:text-6xl font-sans font-black tracking-[-0.04em] mb-4"
          >
            The Kill <span className="text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.3)]">Matrix.</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-text-secondary text-lg max-w-xl font-sans"
          >
            Stop building toys. Start building sovereign systems that can withstand extreme scrutiny and adversarial conditions.
          </motion.p>
        </div>

        {/* Tactical Data Table */}
        <motion.div
          initial={{ opacity: 0, y: 40, filter: 'blur(10px)' }}
          animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
          transition={{ duration: 1, delay: 0.2, ease }}
          className="relative group"
        >
          {/* Border accent frame */}
          <div className="absolute -inset-0.5 bg-gradient-to-b from-white/10 to-transparent opacity-50 pointer-events-none" />
          
          <div className="bg-[#050505] border border-white/10 relative overflow-hidden">
             {/* CRT Scanline overlay specifically for the table */}
             <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_50%,rgba(0,0,0,0.4)_51%)] bg-[length:100%_4px] pointer-events-none z-20 opacity-40 mix-blend-overlay" />
             
             <div className="overflow-x-auto relative z-10">
              <table className="w-full text-left font-mono text-sm border-collapse">
                <thead>
                  <tr className="border-b border-white/10 bg-white/[0.02]">
                    <th className="py-6 px-6 text-text-tertiary font-normal text-xs uppercase tracking-[0.3em] w-1/4">Capability</th>
                    
                    {/* CORTEX Highlighted Header */}
                    <th className="py-6 px-6 text-cyber-lime font-bold text-base bg-cyber-lime/[0.08] border-x border-cyber-lime/20 relative w-1/4">
                      <div className="absolute top-0 inset-x-0 h-1 bg-cyber-lime shadow-[0_0_10px_rgba(204,255,0,0.8)]" />
                      CORTEX<span className="text-cyber-lime/50 text-xs ml-1">v7</span>
                    </th>
                    
                    <th className="py-6 px-6 text-text-tertiary font-normal w-1/4">Mem0</th>
                    <th className="py-6 px-6 text-text-tertiary font-normal w-1/4">Zep</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((row, idx) => (
                    <motion.tr
                      key={row.feature}
                      initial={{ opacity: 0, x: -10 }}
                      animate={isInView ? { opacity: 1, x: 0 } : {}}
                      transition={{ duration: 0.5, delay: 0.4 + idx * 0.05, ease }}
                      className="border-b border-white/5 hover:bg-white/[0.02] transition-colors group/row"
                    >
                      <td className="py-5 px-6 font-sans text-text-secondary text-sm group-hover/row:text-white transition-colors border-r border-white/5">
                        {row.feature}
                      </td>
                      
                      {/* CORTEX Highlighted Cell */}
                      <td className="py-5 px-6 text-white bg-cyber-lime/[0.04] border-x border-cyber-lime/10 group-hover/row:bg-cyber-lime/[0.06] transition-colors relative">
                        {row.cortexStatus === 'yes' && (
                          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-1/2 bg-cyber-lime opacity-50" />
                        )}
                        <div className="flex items-center justify-between gap-2.5">
                          <span className="font-semibold text-cyber-lime drop-shadow-[0_0_8px_rgba(204,255,0,0.3)]">{row.cortex}</span>
                          <StatusIcon status={row.cortexStatus} />
                        </div>
                      </td>
                      
                      <td className="py-5 px-6 text-text-tertiary border-r border-white/5">
                        <div className="flex items-center justify-between gap-2.5">
                          {row.mem0}
                          <StatusIcon status={row.mem0Status} />
                        </div>
                      </td>
                      
                      <td className="py-5 px-6 text-text-tertiary">
                        <div className="flex items-center justify-between gap-2.5">
                          {row.zep}
                          <StatusIcon status={row.zepStatus} />
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
