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
      initial={{ opacity: 0, scale: 0.9, filter: 'blur(10px)' }}
      animate={isInView ? { opacity: 1, scale: 1, filter: 'blur(0px)' } : {}}
      transition={{ duration: 0.8, delay: 0.2, ease }}
      className="glass-strong rounded-2xl p-8 relative overflow-hidden group"
    >
      {/* Noise overlay */}
      <div className="absolute inset-0 noise opacity-50" />

      {/* Corner glow */}
      <div className="absolute -top-20 -right-20 w-40 h-40 bg-industrial-gold/20 rounded-full blur-[80px] group-hover:bg-industrial-gold/30 transition-colors duration-700" />

      <div className="relative z-10 space-y-6 font-mono">
        {/* Deadline Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="relative">
            <Clock className="w-8 h-8 text-industrial-gold" />
            <div className="absolute inset-0 bg-industrial-gold/30 rounded-full blur-lg animate-pulse-slow" />
          </div>
          <div>
            <div className="text-xs text-industrial-gold/60 uppercase tracking-[0.3em]">Deadline</div>
            <div className="text-2xl font-bold text-industrial-gold">August 2026</div>
          </div>
        </div>

        {/* Status Rows */}
        {[
          { label: 'Standard LLM Memory', status: 'NON-COMPLIANT', icon: <Skull className="w-4 h-4" />, color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/20' },
          { label: 'RAG / Vector DB', status: 'HEARSAY', icon: <AlertOctagon className="w-4 h-4" />, color: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/20' },
          { label: 'CORTEX Ledger', status: 'VERIFIED ✓', icon: <Shield className="w-4 h-4" />, color: 'text-cyber-lime', bg: 'bg-cyber-lime/10', border: 'border-cyber-lime/20' },
        ].map((row, i) => (
          <motion.div
            key={row.label}
            initial={{ opacity: 0, x: -20 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.4 + i * 0.15, ease }}
            className={`flex items-center justify-between p-4 rounded-xl ${row.bg} border ${row.border} group/row hover:scale-[1.02] transition-transform duration-300`}
          >
            <div className="flex items-center gap-3">
              <span className={row.color}>{row.icon}</span>
              <span className="text-sm text-text-secondary">{row.label}</span>
            </div>
            <span className={`text-sm font-bold ${row.color} tracking-wider`}>{row.status}</span>
          </motion.div>
        ))}

        {/* Fine amount */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 1 }}
          className="pt-4 border-t border-white/5 text-center"
        >
          <span className="text-xs text-text-tertiary uppercase tracking-[0.3em]">Maximum Fine</span>
          <div className="text-4xl font-black text-industrial-gold mt-2 animate-count-pulse">€30,000,000</div>
        </motion.div>
      </div>
    </motion.div>
  );
}

export function Trigger() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="py-32 relative overflow-hidden noise" ref={ref}>
      {/* Background */}
      <div className="absolute inset-0 bg-abyssal-800" />
      <div className="absolute inset-0 dot-grid animate-grid-fade opacity-50" />
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-industrial-gold/[0.04] rounded-full blur-[200px]" />
      </div>

      {/* Top/Bottom borders */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-industrial-gold/30 to-transparent" />
      <div className="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-industrial-gold/30 to-transparent" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, x: -50, filter: 'blur(10px)' }}
            animate={isInView ? { opacity: 1, x: 0, filter: 'blur(0px)' } : {}}
            transition={{ duration: 0.8, ease }}
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-industrial-gold/[0.06] text-industrial-gold border border-industrial-gold/15 font-mono text-xs uppercase tracking-[0.2em] mb-10">
              <AlertOctagon className="w-3.5 h-3.5" />
              EU AI ACT — ARTICLE 12
            </div>

            <h2 className="text-4xl md:text-5xl lg:text-6xl font-sans font-bold tracking-[-0.03em] leading-[1.1] mb-8">
              August 2026.{' '}
              <br />
              <span className="text-industrial-gold">€30M at stake.</span>
            </h2>

            <blockquote className="border-l-2 border-industrial-gold/30 pl-6 mb-8">
              <p className="text-lg text-text-secondary leading-relaxed italic">
                "High-risk AI systems must possess capabilities that enable the automatic recording of events ('logs') over the lifetime of the system."
              </p>
            </blockquote>

            <p className="text-base text-text-secondary leading-relaxed">
              Are you confident your logs haven't been hallucinated? Altered? Deleted?
              Standard databases provide{' '}
              <span className="text-white font-semibold border-b border-dashed border-white/30">zero cryptographic guarantees</span>.
            </p>
          </motion.div>

          <CountdownBlock />
        </div>
      </div>
    </section>
  );
}
