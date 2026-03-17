import { motion, useInView } from 'framer-motion';
import { Milestone, Check, Clock, Rocket } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const milestones = [
  {
    version: 'v7.0',
    title: 'Trust Engine',
    status: 'released',
    date: 'Feb 2026',
    features: [
      'SHA-256 hash-chained ledger',
      'Merkle tree checkpoints',
      'WBFT consensus protocol',
      'Privacy Shield (11 patterns)',
      '38 CLI commands',
    ],
  },
  {
    version: 'v8.0',
    title: 'Sovereign Cloud',
    status: 'current',
    date: 'Q1 2026',
    features: [
      'Multi-tenant isolation',
      'AlloyDB + Qdrant backends',
      'REST API (55+ endpoints)',
      'Biological Core (autopoiesis)',
      'AST Sandbox execution',
    ],
  },
  {
    version: 'v9.0',
    title: 'Enterprise Grade',
    status: 'planned',
    date: 'Q3 2026',
    features: [
      'GraphQL API',
      'HSM key management',
      'FedRAMP certification path',
      'Multi-region edge sync',
      'SDK: Python, TypeScript, Go, Rust',
    ],
  },
];

function StatusBadge({ status }: { status: string }) {
  if (status === 'released') return (
    <div className="flex items-center gap-1.5 text-cyber-lime text-[10px] font-mono uppercase tracking-widest">
      <Check className="w-3 h-3" /> Released
    </div>
  );
  if (status === 'current') return (
    <div className="flex items-center gap-1.5 text-yinmn-light text-[10px] font-mono uppercase tracking-widest">
      <Rocket className="w-3 h-3 animate-pulse" /> In Progress
    </div>
  );
  return (
    <div className="flex items-center gap-1.5 text-text-tertiary text-[10px] font-mono uppercase tracking-widest">
      <Clock className="w-3 h-3" /> Planned
    </div>
  );
}

export function Roadmap() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section className="py-40 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-8">
        <h1 className="text-watermark text-[22vw] whitespace-nowrap text-yinmn-blue mix-blend-overlay">ROADMAP</h1>
      </div>

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="text-center mb-24">
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-yinmn-blue bg-yinmn-blue/[0.06] text-yinmn-light text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Milestone className="w-3.5 h-3.5" />
            Product Roadmap
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-5xl md:text-6xl font-sans font-black tracking-[-0.04em] mb-6"
          >
            Where we're{' '}
            <span className="text-gradient-blue">going.</span>
          </motion.h2>
        </div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-yinmn-blue/40 via-yinmn-blue/20 to-transparent hidden lg:block" />

          <div className="space-y-12 lg:space-y-24">
            {milestones.map((milestone, idx) => {
              const isLeft = idx % 2 === 0;
              return (
                <motion.div
                  key={milestone.version}
                  initial={{ opacity: 0, x: isLeft ? -50 : 50, filter: 'blur(8px)' }}
                  animate={isInView ? { opacity: 1, x: 0, filter: 'blur(0px)' } : {}}
                  transition={{ duration: 0.7, delay: 0.2 + idx * 0.15, ease }}
                  className={`relative lg:w-[45%] ${isLeft ? 'lg:mr-auto' : 'lg:ml-auto'}`}
                >
                  {/* Node dot on timeline */}
                  <div className={`absolute top-8 hidden lg:block ${isLeft ? '-right-[calc(10%+8px)]' : '-left-[calc(10%+8px)]'}`}>
                    <div className={`w-4 h-4 rounded-full border-2 ${milestone.status === 'current' ? 'border-yinmn-blue bg-yinmn-blue/30 shadow-[0_0_12px_rgba(46,80,144,0.5)]' : milestone.status === 'released' ? 'border-cyber-lime bg-cyber-lime/20' : 'border-white/20 bg-white/5'}`} />
                  </div>

                  <div className={`glass-strong rounded-none p-8 border-l-4 ${milestone.status === 'current' ? 'border-yinmn-blue' : milestone.status === 'released' ? 'border-cyber-lime/40' : 'border-white/10'} hover:border-yinmn-blue transition-colors group`}>
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <span className={`text-2xl font-black font-mono tracking-tighter ${milestone.status === 'current' ? 'text-yinmn-light' : milestone.status === 'released' ? 'text-cyber-lime' : 'text-text-tertiary'}`}>
                          {milestone.version}
                        </span>
                        <span className="text-white font-bold">{milestone.title}</span>
                      </div>
                      <StatusBadge status={milestone.status} />
                    </div>

                    <div className="text-[10px] text-text-tertiary font-mono uppercase tracking-widest mb-5">{milestone.date}</div>

                    <ul className="space-y-2.5">
                      {milestone.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-2.5 text-sm text-text-secondary">
                          <Check className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${milestone.status === 'released' ? 'text-cyber-lime' : milestone.status === 'current' ? 'text-yinmn-light' : 'text-text-tertiary'}`} />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
