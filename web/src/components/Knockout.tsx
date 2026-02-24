import { motion, useInView } from 'framer-motion';
import { Check, X, Minus } from 'lucide-react';
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
  if (status === 'no') return <X className="w-4 h-4 text-red-500/60" />;
  return <Minus className="w-4 h-4 text-text-tertiary" />;
}

export function Knockout() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="comparison" className="py-32 relative overflow-hidden noise" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-800" />
      <div className="absolute inset-0 dot-grid animate-grid-fade opacity-50" />

      {/* Gradient borders */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      <div className="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      <div className="max-w-5xl mx-auto px-6 relative z-10">
        {/* Header */}
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, ease }}
            className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border border-cyber-lime/20 bg-cyber-lime/[0.04] text-cyber-lime text-xs font-mono uppercase tracking-[0.2em] mb-8"
          >
            Competitive Analysis
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-4xl md:text-5xl font-sans font-bold tracking-[-0.03em] mb-4"
          >
            The Kill <span className="text-cyber-lime">Matrix</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.2 }}
            className="text-text-secondary"
          >
            Stop building toys. Start building sovereign systems.
          </motion.p>
        </div>

        {/* Table */}
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={isInView ? { opacity: 1, y: 0, scale: 1 } : {}}
          transition={{ duration: 0.8, delay: 0.2, ease }}
          className="glass-strong rounded-2xl overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="py-5 px-6 text-text-tertiary font-normal text-xs uppercase tracking-[0.2em]">Capability</th>
                  <th className="py-5 px-6 text-cyber-lime font-bold text-base bg-cyber-lime/[0.03] border-x border-cyber-lime/10 relative">
                    <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-cyber-lime/0 via-cyber-lime to-cyber-lime/0" />
                    CORTEX
                  </th>
                  <th className="py-5 px-6 text-text-tertiary font-normal">Mem0</th>
                  <th className="py-5 px-6 text-text-tertiary font-normal">Zep</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, idx) => (
                  <motion.tr
                    key={row.feature}
                    initial={{ opacity: 0, x: -10 }}
                    animate={isInView ? { opacity: 1, x: 0 } : {}}
                    transition={{ duration: 0.5, delay: 0.3 + idx * 0.07, ease }}
                    className="border-b border-white/[0.03] hover:bg-white/[0.015] transition-colors group"
                  >
                    <td className="py-4 px-6 font-sans text-text-secondary text-sm group-hover:text-white transition-colors">{row.feature}</td>
                    <td className="py-4 px-6 text-white bg-cyber-lime/[0.02] border-x border-cyber-lime/5">
                      <div className="flex items-center gap-2.5">
                        <StatusIcon status={row.cortexStatus} />
                        <span className="font-semibold">{row.cortex}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-text-tertiary">
                      <div className="flex items-center gap-2.5">
                        <StatusIcon status={row.mem0Status} />
                        {row.mem0}
                      </div>
                    </td>
                    <td className="py-4 px-6 text-text-tertiary">
                      <div className="flex items-center gap-2.5">
                        <StatusIcon status={row.zepStatus} />
                        {row.zep}
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
