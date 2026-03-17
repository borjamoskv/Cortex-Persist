import { motion, useInView } from 'framer-motion';
import { Terminal } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

const commands = [
  { cmd: 'cortex store', args: '--type decision --source agent:gemini PROJECT "content"', desc: 'Store a fact' },
  { cmd: 'cortex search', args: '"query" --limit 10', desc: 'Semantic search' },
  { cmd: 'cortex recall', args: 'PROJECT --last 5', desc: 'Recent facts' },
  { cmd: 'cortex verify', args: '--full', desc: 'Ledger integrity' },
  { cmd: 'cortex export', args: '--format json', desc: 'Export context' },
  { cmd: 'cortex graph', args: 'PROJECT --depth 3', desc: 'Knowledge graph' },
  { cmd: 'cortex shannon', args: 'PROJECT', desc: 'Entropy report' },
  { cmd: 'cortex status', args: '', desc: 'System health' },
];

export function CliReference() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="cli" className="py-32 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      <div className="max-w-4xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.06] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Terminal className="w-3.5 h-3.5" />
            CLI Reference
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-4xl md:text-5xl font-sans font-black tracking-[-0.04em] mb-6"
          >
            38 commands.{' '}
            <span className="text-gradient-lime">Zero GUI required.</span>
          </motion.h2>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.2, ease }}
          className="glass-strong rounded-none overflow-hidden"
        >
          {/* Terminal header */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5 bg-abyssal-700/40">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/60" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
              <div className="w-3 h-3 rounded-full bg-green-500/60" />
            </div>
            <span className="text-[10px] font-mono text-text-tertiary ml-2">terminal — cortex</span>
          </div>

          <div className="p-5 space-y-1.5 font-mono text-sm">
            {commands.map((c, idx) => (
              <motion.div
                key={c.cmd}
                initial={{ opacity: 0, x: -10 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.4, delay: 0.3 + idx * 0.06, ease }}
                className="flex items-start gap-3 py-1.5 hover:bg-white/[0.02] px-2 -mx-2 transition-colors group"
              >
                <span className="text-cyber-lime select-none flex-shrink-0">$</span>
                <div className="flex-1 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4">
                  <span className="text-white whitespace-nowrap">
                    <span className="font-bold">{c.cmd}</span>{' '}
                    <span className="text-text-tertiary">{c.args}</span>
                  </span>
                  <span className="text-text-tertiary text-xs sm:ml-auto flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    # {c.desc}
                  </span>
                </div>
              </motion.div>
            ))}
            <div className="flex items-center gap-3 pt-2">
              <span className="text-cyber-lime select-none">$</span>
              <span className="animate-pulse text-white">▊</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
