import { motion, useInView } from 'framer-motion';
import { Code, ArrowRight } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const endpoints = [
  { method: 'POST', path: '/api/v1/facts', desc: 'Store a new fact with crypto integrity', color: 'cyber-lime' },
  { method: 'GET', path: '/api/v1/facts/{id}', desc: 'Retrieve a specific fact by ID', color: 'yinmn-light' },
  { method: 'POST', path: '/api/v1/search', desc: 'Hybrid semantic + text search', color: 'cyber-lime' },
  { method: 'POST', path: '/api/v1/search/vector', desc: 'Pure vector similarity search', color: 'cyber-lime' },
  { method: 'GET', path: '/api/v1/ledger/verify', desc: 'Verify full hash chain integrity', color: 'yinmn-light' },
  { method: 'GET', path: '/api/v1/stats', desc: 'Memory metrics and entropy report', color: 'yinmn-light' },
  { method: 'POST', path: '/api/v1/graph', desc: 'Knowledge graph traversal', color: 'cyber-lime' },
  { method: 'GET', path: '/api/v1/shannon', desc: 'Information-theoretic analysis', color: 'yinmn-light' },
  { method: 'POST', path: '/api/v1/consensus', desc: 'Byzantine consensus voting', color: 'cyber-lime' },
  { method: 'DELETE', path: '/api/v1/facts/{id}', desc: 'Soft-delete with audit trail', color: 'industrial-gold' },
];

const sdks = [
  { name: 'Python', version: 'v0.3.0b1', status: 'stable', color: 'cyber-lime' },
  { name: 'MCP Server', version: 'v1.0', status: 'stable', color: 'cyber-lime' },
  { name: 'REST API', version: '55+ endpoints', status: 'stable', color: 'cyber-lime' },
  { name: 'CLI', version: '38 commands', status: 'stable', color: 'cyber-lime' },
];

export function ApiReference() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="api" className="py-32 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-10">
        <h1 className="text-watermark text-[20vw] whitespace-nowrap">API</h1>
      </div>

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.06] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Code className="w-3.5 h-3.5" />
            API Reference
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-4xl md:text-5xl font-sans font-black tracking-[-0.04em] mb-6"
          >
            One engine.{' '}
            <span className="text-gradient-lime">Every interface.</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.2 }}
            className="text-text-secondary max-w-xl mx-auto text-lg"
          >
            Python SDK, REST API, CLI, or MCP Server — same sovereign engine underneath.
          </motion.p>
        </div>

        {/* SDK badges */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2, ease }}
          className="flex flex-wrap justify-center gap-3 mb-16"
        >
          {sdks.map((sdk) => (
            <div key={sdk.name} className={`inline-flex items-center gap-2 px-4 py-2 glass-strong rounded-none border border-${sdk.color}/20`}>
              <div className={`w-2 h-2 rounded-full bg-${sdk.color}`} />
              <span className="text-xs font-mono font-bold">{sdk.name}</span>
              <span className="text-[10px] font-mono text-text-tertiary">{sdk.version}</span>
            </div>
          ))}
        </motion.div>

        {/* Endpoint list */}
        <div className="glass-strong rounded-none overflow-hidden">
          <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-widest text-text-tertiary">Core Endpoints</span>
            <span className="text-[10px] font-mono text-text-tertiary">55+ total</span>
          </div>
          <div className="divide-y divide-white/[0.03]">
            {endpoints.map((ep, idx) => (
              <motion.div
                key={ep.path + ep.method}
                initial={{ opacity: 0, x: -20 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.5, delay: 0.3 + idx * 0.05, ease }}
                className="flex items-center gap-4 px-5 py-3.5 hover:bg-white/[0.02] transition-colors group cursor-pointer"
              >
                <span className={`text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 border rounded-none min-w-[52px] text-center ${
                  ep.method === 'POST' ? 'text-cyber-lime border-cyber-lime/30 bg-cyber-lime/[0.04]' :
                  ep.method === 'DELETE' ? 'text-red-400 border-red-400/30 bg-red-400/[0.04]' :
                  'text-yinmn-light border-yinmn-blue/30 bg-yinmn-blue/[0.04]'
                }`}>
                  {ep.method}
                </span>
                <code className="text-sm font-mono text-white flex-1">{ep.path}</code>
                <span className="text-xs text-text-tertiary hidden sm:block group-hover:text-text-secondary transition-colors">{ep.desc}</span>
                <ArrowRight className="w-3.5 h-3.5 text-text-tertiary group-hover:text-cyber-lime group-hover:translate-x-1 transition-all" />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
