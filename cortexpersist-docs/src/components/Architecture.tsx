import { motion, useInView } from 'framer-motion';
import { Layers, ArrowRight } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const layers = [
  {
    name: 'Entry Points',
    modules: ['CLI (59 files)', 'REST API (55+ endpoints)', 'MCP Server (SSE + stdio)', 'Google ADK Runner'],
    color: 'cyber-lime',
    desc: 'How data enters the system',
  },
  {
    name: 'Guards & Validation',
    modules: ['Injection Guard', 'Contradiction Guard', 'Dependency Guard', 'Intent Validator'],
    color: 'industrial-gold',
    desc: 'Zero-trust defense layer',
  },
  {
    name: 'Core Engine',
    modules: ['StoreMixin', 'QueryMixin', 'MemoryMixin', 'SearchMixin', 'TransactionMixin'],
    color: 'yinmn-light',
    desc: 'Composite orchestrator via mixin composition',
  },
  {
    name: 'Crypto & Ledger',
    modules: ['AES-256 Encryption', 'SHA-256 Hash Chain', 'Merkle Tree Checkpoints', 'Ed25519 Signatures'],
    color: 'cyber-violet',
    desc: 'Mathematical integrity guarantees',
  },
  {
    name: 'Intelligence',
    modules: ['Vector Embeddings (ONNX)', 'Hybrid Search (RRF)', 'Knowledge Graph', 'Shannon Entropy Analysis'],
    color: 'cyber-lime',
    desc: 'Semantic understanding layer',
  },
  {
    name: 'Persistence',
    modules: ['SQLite + sqlite-vec', 'AlloyDB (Cloud)', 'Qdrant (Vector)', 'Redis (L1 Cache)'],
    color: 'yinmn-light',
    desc: 'Pluggable storage backends',
  },
];

export function Architecture() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="architecture" className="py-32 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-yinmn-blue bg-yinmn-blue/[0.06] text-yinmn-light text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Layers className="w-3.5 h-3.5" />
            Architecture
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-4xl md:text-5xl font-sans font-black tracking-[-0.04em] mb-6"
          >
            Defense in{' '}
            <span className="text-gradient-blue">depth.</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.2 }}
            className="text-text-secondary max-w-xl mx-auto text-lg"
          >
            Six layers. Every fact traverses all of them. No shortcuts.
          </motion.p>
        </div>

        <div className="space-y-3">
          {layers.map((layer, idx) => (
            <motion.div
              key={layer.name}
              initial={{ opacity: 0, x: idx % 2 === 0 ? -40 : 40 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 + idx * 0.1, ease }}
              className={`glass-strong rounded-none p-6 border-l-4 border-${layer.color}/30 hover:border-${layer.color} transition-colors group`}
            >
              <div className="flex flex-col md:flex-row md:items-center gap-4">
                <div className="md:w-48 flex-shrink-0">
                  <div className={`text-[10px] font-mono uppercase tracking-[0.2em] text-${layer.color} mb-1`}>
                    Layer {idx + 1}
                  </div>
                  <h3 className="text-lg font-bold tracking-tight">{layer.name}</h3>
                  <p className="text-xs text-text-tertiary mt-1">{layer.desc}</p>
                </div>
                <div className="flex-1 flex flex-wrap gap-2">
                  {layer.modules.map((mod) => (
                    <span
                      key={mod}
                      className={`text-xs font-mono px-3 py-1.5 bg-${layer.color}/[0.04] border border-${layer.color}/10 text-text-secondary group-hover:text-white group-hover:border-${layer.color}/20 transition-colors`}
                    >
                      {mod}
                    </span>
                  ))}
                </div>
                <ArrowRight className={`w-4 h-4 text-text-tertiary group-hover:text-${layer.color} transition-colors hidden md:block`} />
              </div>
            </motion.div>
          ))}
        </div>

        {/* Data flow */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.8, ease }}
          className="mt-16 glass-strong rounded-none p-8 text-center"
        >
          <pre className="text-xs font-mono text-text-tertiary leading-loose overflow-x-auto">
{`Input → Guards → Encrypt(AES-256) → Hash Chain(SHA-256)
     → Embed(ONNX) → SQLite Insert → Audit Log → Signal Dispatch`}
          </pre>
        </motion.div>
      </div>
    </section>
  );
}
