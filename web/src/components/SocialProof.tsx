import { motion, useInView } from 'framer-motion';
import { useRef, useState, useEffect } from 'react';
import { Code2, TestTube, Scale, ShieldCheck, Layers, Cpu, Globe, Plug } from 'lucide-react';

const ease = [0.16, 1, 0.3, 1] as const;

const stats = [
  { value: 45500, suffix: '+', label: 'Lines of Code', icon: <Code2 className="w-4 h-4" /> },
  { value: 1162, suffix: '+', label: 'Test Functions', icon: <TestTube className="w-4 h-4" /> },
  { value: 444, suffix: '', label: 'Python Modules', icon: <Layers className="w-4 h-4" /> },
  { value: 38, suffix: '', label: 'CLI Commands', icon: <Cpu className="w-4 h-4" /> },
];

const integrations = [
  'LangChain', 'CrewAI', 'AutoGen', 'Google ADK',
  'Claude Code', 'Cursor', 'Windsurf', 'Stripe',
  'Slack', 'Salesforce', 'SQLite', 'AlloyDB',
  'Qdrant', 'Docker', 'AWS', 'Vercel',
];

const badges = [
  { label: 'Apache 2.0', icon: <Scale className="w-3.5 h-3.5" />, color: 'text-cyber-lime' },
  { label: 'EU AI Act Ready', icon: <ShieldCheck className="w-3.5 h-3.5" />, color: 'text-industrial-gold' },
  { label: 'Cross-Platform', icon: <Globe className="w-3.5 h-3.5" />, color: 'text-cyber-violet' },
  { label: 'MCP Native', icon: <Plug className="w-3.5 h-3.5" />, color: 'text-white' },
];

function AnimatedCounter({ target, suffix, inView }: { target: number; suffix: string; inView: boolean }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const duration = 2000;
    const steps = 60;
    const increment = target / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [inView, target]);

  return (
    <span className="tabular-nums">
      {count.toLocaleString()}{suffix}
    </span>
  );
}

export function SocialProof() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="py-28 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-800/50" />
      <div className="absolute inset-0 dot-grid opacity-10" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-white/5 mb-20">
          {stats.map((stat, idx) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: idx * 0.1, ease }}
              className="bg-abyssal-900 p-8 text-center group hover:bg-abyssal-800/50 transition-colors"
            >
              <div className="flex justify-center mb-3 text-text-tertiary group-hover:text-cyber-lime transition-colors">
                {stat.icon}
              </div>
              <div className="text-3xl md:text-4xl font-black font-mono tracking-tighter text-white group-hover:text-cyber-lime transition-colors mb-2">
                <AnimatedCounter target={stat.value} suffix={stat.suffix} inView={isInView} />
              </div>
              <div className="text-xs text-text-tertiary font-mono uppercase tracking-[0.2em]">
                {stat.label}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Trust Badges */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.4, ease }}
          className="flex flex-wrap justify-center gap-4 mb-20"
        >
          {badges.map((badge) => (
            <div
              key={badge.label}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-none border border-white/10 bg-white/[0.02] ${badge.color} font-mono text-xs tracking-wider`}
            >
              {badge.icon}
              {badge.label}
            </div>
          ))}
        </motion.div>

        {/* Integrations Marquee */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="relative"
        >
          <div className="text-center mb-8">
            <span className="text-[10px] text-text-tertiary font-mono uppercase tracking-[0.4em]">
              Integrates With Your Stack
            </span>
          </div>

          {/* Gradient masks */}
          <div className="relative overflow-hidden">
            <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-abyssal-900 to-transparent z-10 pointer-events-none" />
            <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-abyssal-900 to-transparent z-10 pointer-events-none" />

            <div className="flex gap-6 animate-marquee">
              {[...integrations, ...integrations].map((name, idx) => (
                <div
                  key={`${name}-${idx}`}
                  className="flex-shrink-0 px-6 py-3 border border-white/5 bg-white/[0.01] text-text-tertiary font-mono text-sm hover:text-cyber-lime hover:border-cyber-lime/20 transition-colors whitespace-nowrap"
                >
                  {name}
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
