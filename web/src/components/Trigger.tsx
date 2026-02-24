import { motion, useInView } from 'framer-motion';
import { AlertOctagon, Clock, Shield, Skull } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1];

function CountdownBlock() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: 40, filter: 'blur(10px)' }}
      animate={isInView ? { opacity: 1, x: 0, filter: 'blur(0px)' } : {}}
      transition={{ duration: 1, delay: 0.2, ease }}
      className="relative z-20 group"
    >
      <div className="absolute inset-0 bg-industrial-gold/[0.02] -skew-x-12 transform group-hover:bg-industrial-gold/[0.05] transition-colors duration-700" />
      
      <div className="glass-strong rounded-none border border-industrial-gold/15 p-8 relative overflow-hidden backdrop-blur-3xl shadow-[0_0_50px_rgba(212,175,55,0.05)]">
        {/* Corner accents */}
        <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-industrial-gold/40" />
        <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-industrial-gold/40" />

        <div className="relative z-10 space-y-8 font-mono">
          {/* Deadline Header */}
          <div className="flex items-center gap-4">
            <div className="relative">
              <Clock className="w-10 h-10 text-industrial-gold" />
              <div className="absolute inset-0 bg-industrial-gold/40 rounded-full blur-xl animate-pulse-slow" />
            </div>
            <div>
              <div className="text-[10px] text-industrial-gold/60 uppercase tracking-[0.4em] mb-1">Enforcement Deadline</div>
              <div className="text-3xl font-black text-industrial-gold tracking-tighter">AUGUST 2026</div>
            </div>
          </div>

          {/* Status Rows */}
          <div className="space-y-3">
            {[
              { label: 'STANDARD LLM MEMORY', status: 'NON-COMPLIANT', icon: <Skull className="w-4 h-4" />, color: 'text-red-500', bg: 'bg-red-500/[0.05]', border: 'border-red-500/20' },
              { label: 'RAG / VECTOR DB', status: 'HEARSAY', icon: <AlertOctagon className="w-4 h-4" />, color: 'text-orange-400', bg: 'bg-orange-400/[0.05]', border: 'border-orange-400/20' },
              { label: 'CORTEX LEDGER', status: 'VERIFIED ✓', icon: <Shield className="w-4 h-4" />, color: 'text-cyber-lime', bg: 'bg-cyber-lime/[0.05]', border: 'border-cyber-lime/30' },
            ].map((row, i) => (
              <motion.div
                key={row.label}
                initial={{ opacity: 0, x: -20 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.6, delay: 0.5 + i * 0.15, ease }}
                className={`flex items-center justify-between p-4 ${row.bg} border-l-2 ${row.border} group/row hover:translate-x-1 transition-transform duration-300`}
              >
                <div className="flex items-center gap-3">
                  <span className={row.color}>{row.icon}</span>
                  <span className="text-xs text-text-secondary tracking-widest">{row.label}</span>
                </div>
                <span className={`text-xs font-black ${row.color} tracking-widest`}>{row.status}</span>
              </motion.div>
            ))}
          </div>

          {/* Fine amount */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 1.2 }}
            className="pt-6 border-t border-white/[0.05] flex justify-between items-end"
          >
            <div>
              <span className="text-[10px] text-red-500/80 uppercase tracking-[0.3em] font-bold">Maximum Infraction Penalty</span>
              <div className="text-red-500 text-sm mt-1">Under Article 12 Log Requirements</div>
            </div>
            <div className="text-5xl font-black text-industrial-gold tracking-tighter animate-count-pulse drop-shadow-[0_0_15px_rgba(212,175,55,0.3)]">
              €30M
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

export function Trigger() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-40 relative overflow-hidden" ref={ref}>
      {/* Background */}
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-30" />
      
      {/* Massive Typographic Watermark */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-20">
        <h1 className="text-watermark text-[25vw] whitespace-nowrap text-industrial-gold mix-blend-overlay">
          ARTICLE 12
        </h1>
      </div>

      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[600px] bg-industrial-gold/[0.03] rounded-[100%] blur-[150px]" />
      </div>

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="grid lg:grid-cols-2 gap-20 items-center">
          <motion.div
            initial={{ opacity: 0, x: -60, filter: 'blur(10px)' }}
            animate={isInView ? { opacity: 1, x: 0, filter: 'blur(0px)' } : {}}
            transition={{ duration: 1, ease }}
            className="relative"
          >
            {/* Structural line */}
            <div className="absolute -left-6 top-10 bottom-0 w-px bg-industrial-gold/20 hidden md:block" />

            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-industrial-gold bg-industrial-gold/[0.08] text-industrial-gold font-mono text-[10px] uppercase tracking-[0.3em] mb-12">
              <AlertOctagon className="w-3.5 h-3.5" />
              European Union AI Act
            </div>

            <h2 className="text-5xl md:text-6xl lg:text-7xl font-sans font-black tracking-[-0.04em] leading-[0.95] mb-10">
              August 2026.<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-industrial-gold to-white">
                €30,000,000
              </span><br />
              at stake.
            </h2>

            <div className="relative pl-8 mb-10">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-industrial-gold to-industrial-gold/10" />
              <p className="text-xl md:text-2xl text-text-primary leading-tight font-medium font-serif italic opacity-90">
                "High-risk AI systems must possess capabilities that enable the automatic recording of events ('logs') over the lifetime of the system."
              </p>
            </div>

            <p className="text-lg text-text-secondary leading-relaxed font-sans max-w-xl">
              Are you confident your agent's logs haven't been hallucinated? Altered? Deleted? 
              Standard vector databases provide virtually zero cryptographic guarantees against structural amnesia.
            </p>
          </motion.div>

          <CountdownBlock />
        </div>
      </div>
    </section>
  );
}
