import { motion, useInView } from 'framer-motion';
import { Shield, Lock, Globe } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const pillars = [
  {
    icon: <Shield className="w-8 h-8" />,
    title: 'Sovereign',
    description: 'Your data never leaves your machine. No cloud dependency. No vendor lock-in. SQLite at the core—the most deployed database on Earth.',
    accent: 'yinmn-blue',
  },
  {
    icon: <Lock className="w-8 h-8" />,
    title: 'Verifiable',
    description: 'Every fact is SHA-256 hash-chained. Merkle tree checkpoints. WBFT consensus for multi-agent systems. Mathematical proof, not promises.',
    accent: 'cyber-lime',
  },
  {
    icon: <Globe className="w-8 h-8" />,
    title: 'Open',
    description: 'Apache 2.0 licensed. Community-governed roadmap. Open RFCs. No proprietary APIs. The trust layer belongs to everyone.',
    accent: 'cyber-violet',
  },
];

export function Mission() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section className="py-40 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-20" />

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-10">
        <h1 className="text-watermark text-[20vw] whitespace-nowrap">MISSION</h1>
      </div>

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="text-center mb-24">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-yinmn-blue bg-yinmn-blue/[0.06] text-yinmn-light text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Shield className="w-3.5 h-3.5" />
            Foundation
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-5xl md:text-6xl font-sans font-black tracking-[-0.04em] mb-6"
          >
            Three Pillars.{' '}
            <span className="text-gradient-blue">Zero Compromise.</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.2 }}
            className="text-text-secondary max-w-xl mx-auto text-lg"
          >
            We believe AI trust infrastructure should be open, verifiable, and owned by no single entity.
          </motion.p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {pillars.map((pillar, idx) => (
            <motion.div
              key={pillar.title}
              initial={{ opacity: 0, y: 40, filter: 'blur(8px)' }}
              animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
              transition={{ duration: 0.7, delay: idx * 0.15, ease }}
              className={`glass-strong rounded-none border-t-4 border-${pillar.accent}/40 p-10 group hover:border-${pillar.accent} transition-colors duration-500`}
            >
              <div className={`w-14 h-14 rounded-none border border-${pillar.accent}/20 flex items-center justify-center mb-8 text-${pillar.accent} bg-${pillar.accent}/[0.04] group-hover:bg-${pillar.accent}/[0.08] transition-colors`}>
                {pillar.icon}
              </div>
              <h3 className="text-2xl font-black tracking-tight mb-4 group-hover:text-yinmn-light transition-colors">
                {pillar.title}
              </h3>
              <p className="text-text-secondary text-sm leading-relaxed">
                {pillar.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
