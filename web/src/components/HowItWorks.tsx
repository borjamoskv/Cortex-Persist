import { motion, useInView } from 'framer-motion';
import { Terminal, ShieldCheck, FileCheck, ArrowRight } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const steps = [
  {
    number: '01',
    title: 'Connect',
    subtitle: 'Hook into any AI agent',
    icon: <Terminal className="w-6 h-6" />,
    code: `cortex connect my-agent --port 8080`,
    detail: 'Seamlessly link CORTEX to your existing agent workflows. Zero trust, cryptographic identity established instantly.',
  },
  {
    number: '02',
    title: 'Verify',
    subtitle: 'Cryptographic audit trails',
    icon: <ShieldCheck className="w-6 h-6" />,
    code: `cortex verify --deep \\
# -> ✅ INTEGRITY VALIDATED
# Hash: 0x8f2...ae1
# Trails: 1,240 immutable entries`,
    detail: 'Every memory entry is SHA-256 hash-chained. Any tamper attempt is mathematically impossible to hide.',
  },
  {
    number: '03',
    title: 'Export',
    subtitle: 'EU AI Act Compliance Report',
    icon: <FileCheck className="w-6 h-6" />,
    code: `cortex export --format pdf \\
# -> Compliance Score: 100/100
# AI Act Article 12: PASSED`,
    detail: 'Generate deterministic compliance reports in seconds. Ready for legal and regulatory audit.',
  },
];

function StepCard({ step, index }: { step: typeof steps[0]; index: number }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50, filter: 'blur(10px)' }}
      animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
      transition={{ duration: 0.8, delay: index * 0.15, ease }}
      className="relative group"
    >
      {/* Connection line to next step */}
      {index < 2 && (
        <div className="absolute -bottom-16 left-1/2 -translate-x-1/2 h-16 w-px bg-gradient-to-b from-cyber-lime/30 to-transparent hidden lg:block" />
      )}

      <div className="glass-strong rounded-none border border-white/[0.06] p-8 relative overflow-hidden hover:border-cyber-lime/20 transition-colors duration-500">
        {/* Corner accents */}
        <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-cyber-lime/30 opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-cyber-lime/30 opacity-0 group-hover:opacity-100 transition-opacity" />

        <div className="relative z-10">
          {/* Step number + icon */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <span className="text-5xl font-black text-white/[0.06] font-mono tracking-tighter group-hover:text-cyber-lime/10 transition-colors">
                {step.number}
              </span>
              <div className="w-12 h-12 rounded-none border border-cyber-lime/20 flex items-center justify-center text-cyber-lime bg-cyber-lime/[0.04] group-hover:bg-cyber-lime/[0.08] transition-colors">
                {step.icon}
              </div>
            </div>
            {index < 2 && (
              <ArrowRight className="w-5 h-5 text-text-tertiary hidden lg:block group-hover:text-cyber-lime group-hover:translate-x-1 transition-all" />
            )}
          </div>

          {/* Title */}
          <h3 className="text-2xl font-black tracking-tight mb-1 group-hover:text-cyber-lime transition-colors">
            {step.title}
          </h3>
          <p className="text-sm text-text-tertiary font-mono uppercase tracking-[0.2em] mb-6">
            {step.subtitle}
          </p>

          {/* Code block */}
          <div className="bg-[#050505] border border-white/5 p-5 mb-6 relative overflow-hidden">
            <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_50%,rgba(0,0,0,0.3)_51%)] bg-[length:100%_4px] pointer-events-none z-10 opacity-20" />
            <div className="font-mono text-[10px] text-text-tertiary uppercase tracking-widest mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-cyber-lime rounded-full animate-pulse" />
              terminal
            </div>
            <pre className="font-mono text-xs text-cyber-lime/80 whitespace-pre-wrap leading-relaxed relative z-20">
              {step.code}
            </pre>
          </div>

          {/* Detail */}
          <p className="text-sm text-text-secondary leading-relaxed">
            {step.detail}
          </p>
        </div>
      </div>
    </motion.div>
  );
}

export function HowItWorks() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section id="how-it-works" className="py-40 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-20" />

      {/* Watermark */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-10">
        <h1 className="text-watermark text-[18vw] whitespace-nowrap">
          PROTOCOL
        </h1>
      </div>

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Header */}
        <div className="mb-24">
          <div className="absolute -left-6 top-4 bottom-0 w-px bg-gradient-to-b from-cyber-lime/40 via-cyber-lime/10 to-transparent hidden md:block" />

          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, ease }}
            className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.04] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Verification Flow
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
            animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-5xl md:text-6xl lg:text-7xl font-sans font-black tracking-[-0.04em] leading-[0.95] mb-8"
          >
            Connect. Verify.{' '}
            <span className="text-gradient">Audit.</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.2, ease }}
            className="text-lg md:text-xl text-text-secondary max-w-2xl font-sans leading-relaxed"
          >
            From raw LLM output to EU AI Act compliance in three deterministic steps.
            Local-first execution with elective cloud synchronization. No trust required.
          </motion.p>
        </div>

        {/* Steps Grid */}
        <div className="grid lg:grid-cols-3 gap-8 lg:gap-6">
          {steps.map((step, idx) => (
            <StepCard key={step.number} step={step} index={idx} />
          ))}
        </div>
      </div>
    </section>
  );
}
