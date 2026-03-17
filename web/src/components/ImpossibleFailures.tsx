import { motion, useInView } from 'framer-motion';
import { BrainCircuit, History, AlertTriangle, Ghost, GitMerge, ShieldCheck } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const FAILURES = [
  {
    id: '01',
    icon: BrainCircuit,
    title: 'Session Amnesia',
    without: 'Every session is T₀. Months of accumulated decisions vanish. The agent reconstructs from hallucination.',
    guarantee: 'STRUCTURAL',
    guaranteeColor: 'text-cyber-lime border-cyber-lime/30 bg-cyber-lime/[0.04]',
    detail: 'Boot protocol enforces context load before ANY action. No code path exists where an agent begins without structural memory.',
  },
  {
    id: '02',
    icon: History,
    title: 'Repeated Errors',
    without: 'The same architectural mistake, re-diagnosed from scratch. The learning curve resets every conversation.',
    guarantee: 'BEHAVIORAL',
    guaranteeColor: 'text-cyber-lime border-cyber-lime/30 bg-cyber-lime/[0.04]',
    detail: 'Error memory layer persists root cause + resolution. Every session queries it before acting. A resolved error cannot be invisible.',
  },
  {
    id: '03',
    icon: AlertTriangle,
    title: 'Fabricated History',
    without: 'The LLM invents coherent rationale for decisions never made. Indistinguishable from truth under casual review.',
    guarantee: 'CRYPTOGRAPHIC',
    guaranteeColor: 'text-cyber-lime border-cyber-lime/30 bg-cyber-lime/[0.04]',
    detail: 'SHA-256 hash chain + Merkle checkpoints. Tamper is mathematically detectable. Unverified = did not happen.',
  },
  {
    id: '04',
    icon: Ghost,
    title: 'Ghost Accumulation',
    without: 'Incomplete work is invisible. Each session starts "clean." Projects silently accumulate abandoned half-implementations.',
    guarantee: 'STRUCTURAL',
    guaranteeColor: 'text-cyber-lime border-cyber-lime/30 bg-cyber-lime/[0.04]',
    detail: 'Ghost taxonomy surfaces at boot. >10 ghosts: operator is notified. No incomplete work is invisible to a future session.',
  },
  {
    id: '05',
    icon: GitMerge,
    title: 'Multi-Agent Divergence',
    without: 'Two agents build different versions of reality. Conflict is silent until production — then non-deterministic.',
    guarantee: 'CONSENSUS',
    guaranteeColor: 'text-cyber-lime border-cyber-lime/30 bg-cyber-lime/[0.04]',
    detail: 'All agents read from the same structural ground truth. WBFT consensus verifies agreement before critical writes.',
  },
  {
    id: '06',
    icon: ShieldCheck,
    title: 'Regulatory Failure',
    without: 'Manual audits of millions of agent decisions. €30M fine risk under EU AI Act Art. 12. Corporate amnesia.',
    guarantee: 'COMPLIANCE',
    guaranteeColor: 'text-cyber-lime border-cyber-lime/30 bg-cyber-lime/[0.04]',
    detail: 'Automated compliance reports. Every decision is hash-verified and indexed in real-time. Meeting Art. 12 is a constant.',
  },
];

export function ImpossibleFailures() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="py-40 relative overflow-hidden" ref={ref}>
      {/* Background */}
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-20" />

      {/* Radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1200px] h-[600px] rounded-full pointer-events-none bg-[image:radial-gradient(circle,rgba(204,255,0,0.02)_0%,transparent_70%)]" />

      {/* Watermark */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-[0.03]">
        <span className="text-watermark text-[22vw] whitespace-nowrap text-cyber-lime">
          IMPOSSIBLE
        </span>
      </div>

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
          animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
          transition={{ duration: 1, ease }}
          className="max-w-3xl mb-24"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 border-l-2 border-cyber-lime bg-cyber-lime/[0.06] text-cyber-lime font-mono text-[10px] uppercase tracking-[0.3em] mb-10">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyber-lime opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyber-lime" />
            </span>
            Structural Guarantees
          </div>

          <h2 className="text-5xl md:text-6xl lg:text-[5.5rem] font-sans font-black tracking-[-0.04em] leading-[0.92] mb-8">
            Failures we make{' '}
            <span className="text-gradient">impossible.</span>
          </h2>

          <p className="text-xl text-text-secondary leading-relaxed max-w-2xl font-sans">
            The most valuable guarantee of a system is not what it does —
            it's what it makes{' '}
            <span className="text-white font-medium">structurally unreachable</span>.
            Not unlikely. Not difficult. Architecturally excluded.
          </p>
        </motion.div>

        {/* Failure Cards */}
        <div className="space-y-px">
          {FAILURES.map((failure, i) => {
            const Icon = failure.icon;
            return (
              <motion.div
                key={failure.id}
                initial={{ opacity: 0, x: -40, filter: 'blur(8px)' }}
                animate={isInView ? { opacity: 1, x: 0, filter: 'blur(0px)' } : {}}
                transition={{ duration: 0.8, delay: i * 0.1, ease }}
                className="group relative"
              >
                <div className="glass border border-white/[0.05] group-hover:border-cyber-lime/20 transition-colors duration-500 p-8 md:p-10 relative overflow-hidden">
                  {/* Hover scan line */}
                  <div className="absolute inset-x-0 top-0 h-px bg-cyber-lime/0 group-hover:bg-cyber-lime/20 transition-colors duration-500" />

                  <div className="grid md:grid-cols-12 gap-8 items-start">
                    {/* Number + Icon */}
                    <div className="md:col-span-1 flex md:flex-col items-center md:items-start gap-4">
                      <span className="font-mono text-[10px] text-text-tertiary tracking-[0.3em] opacity-60">
                        {failure.id}
                      </span>
                      <div className="w-10 h-10 border border-white/10 group-hover:border-cyber-lime/30 transition-colors flex items-center justify-center bg-white/[0.02]">
                        <Icon className="w-5 h-5 text-text-tertiary group-hover:text-cyber-lime transition-colors" />
                      </div>
                    </div>

                    {/* Title + Without */}
                    <div className="md:col-span-4">
                      <h3 className="text-xl font-sans font-bold text-white tracking-tight mb-3">
                        {failure.title}
                      </h3>
                      <p className="text-sm text-text-tertiary leading-relaxed font-mono">
                        <span className="text-red-500/60 text-[10px] uppercase tracking-widest block mb-1">
                          without cortex
                        </span>
                        {failure.without}
                      </p>
                    </div>

                    {/* Detail */}
                    <div className="md:col-span-5">
                      <p className="text-sm text-text-secondary leading-relaxed">
                        <span className="text-cyber-lime/60 text-[10px] uppercase tracking-widest font-mono block mb-1">
                          how it's prevented
                        </span>
                        {failure.detail}
                      </p>
                    </div>

                    {/* Guarantee Badge */}
                    <div className="md:col-span-2 flex md:justify-end items-start">
                      <span className={`px-3 py-1 border font-mono text-[10px] uppercase tracking-widest ${failure.guaranteeColor}`}>
                        {failure.guarantee}
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Bottom Statement */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.7, ease }}
          className="mt-20 pt-16 border-t border-white/[0.05]"
        >
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <blockquote className="relative pl-8">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-cyber-lime to-cyber-lime/10" />
              <p className="text-2xl md:text-3xl font-serif italic text-text-primary leading-relaxed opacity-90">
                "An agent with CORTEX cannot hallucinate its own history.
                The hash chain is the proof."
              </p>
            </blockquote>

            <div className="space-y-4 font-mono text-sm">
              {[
                { label: 'Guarantee Model', value: 'Static Analysis — not runtime behavior' },
                { label: 'Hash Algorithm', value: 'SHA-256 (FIPS 180-4)' },
                { label: 'Verification', value: 'Merkle checkpoint + WBFT consensus' },
                { label: 'Audit Trail', value: 'EU AI Act Art. 12 compliant' },
              ].map((row) => (
                <div key={row.label} className="flex justify-between items-center border-b border-white/[0.04] pb-3">
                  <span className="text-text-tertiary text-xs">{row.label}</span>
                  <span className="text-text-secondary">{row.value}</span>
                </div>
              ))}
              <div className="pt-2">
                <code className="text-xs text-cyber-lime/70 bg-cyber-lime/[0.04] px-3 py-2 block">
                  cortex verify --full → ✅ All invariants hold
                </code>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
