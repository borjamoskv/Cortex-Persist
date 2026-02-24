import { motion } from 'framer-motion';
import { Terminal, Copy, Check, ChevronRight } from 'lucide-react';
import { useState, useCallback } from 'react';

const ease = [0.16, 1, 0.3, 1];

export function Hero() {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText('pip install cortex-engine');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  return (
    <section className="relative min-h-screen flex items-center justify-center pt-20 overflow-hidden noise">
      {/* Dot Grid Background */}
      <div className="absolute inset-0 dot-grid animate-grid-fade" />

      {/* Radial Glow Orbs */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/4 w-[500px] h-[500px] bg-cyber-lime/[0.07] rounded-full blur-[150px] animate-pulse-slow" />
        <div className="absolute bottom-1/4 right-1/5 w-[600px] h-[600px] bg-cyber-violet/[0.08] rounded-full blur-[180px] animate-pulse-slow" style={{ animationDelay: '2s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-yinmn-blue/[0.06] rounded-full blur-[120px] animate-float" />
      </div>

      {/* Top Gradient Fade */}
      <div className="absolute top-0 inset-x-0 h-40 bg-gradient-to-b from-abyssal-900 to-transparent z-[2]" />

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center space-y-8">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20, filter: 'blur(10px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 0.8, ease }}
          className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border border-cyber-lime/20 bg-cyber-lime/[0.04] text-cyber-lime text-xs font-mono uppercase tracking-[0.2em]"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyber-lime opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyber-lime" />
          </span>
          The SSL/TLS of AI Memory
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 1, delay: 0.1, ease }}
          className="text-5xl sm:text-6xl md:text-7xl lg:text-[5.5rem] font-sans font-bold tracking-[-0.03em] leading-[1.05]"
        >
          Can your AI agent{' '}
          <span className="text-gradient">PROVE</span>
          <br />
          its decisions are correct?
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.25, ease }}
          className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto font-sans leading-relaxed"
        >
          CORTEX is a sovereign cryptographic ledger for AI memory.
          It converts probabilistic LLM outputs into{' '}
          <span className="text-white font-medium">mathematically verifiable facts</span>.
        </motion.p>

        {/* Trust Signal */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4, ease }}
          className="text-sm text-text-tertiary font-mono tracking-wide"
        >
          Architected by senior specialists · 15+ years experience · Open Source
        </motion.p>

        {/* Install CTA */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.5, ease }}
          className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          {/* Pip Install */}
          <button
            onClick={handleCopy}
            className="glass-strong rounded-xl px-6 py-4 flex items-center gap-4 group hover:border-cyber-lime/30 transition-all cursor-pointer relative overflow-hidden glow-lime w-full sm:w-auto"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-cyber-lime/0 via-cyber-lime/[0.04] to-cyber-lime/0 animate-shimmer" />
            <Terminal className="w-4 h-4 text-cyber-lime relative z-10" />
            <span className="font-mono text-sm relative z-10">
              pip install <span className="text-cyber-lime font-semibold">cortex-engine</span>
            </span>
            <div className="relative z-10 ml-2">
              {copied ? (
                <Check className="w-4 h-4 text-cyber-lime" />
              ) : (
                <Copy className="w-4 h-4 text-text-tertiary group-hover:text-cyber-lime transition-colors" />
              )}
            </div>
          </button>

          {/* GitHub CTA */}
          <a
            href="https://github.com/borjamoskv/cortex"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-6 py-4 rounded-xl border border-white/10 hover:border-white/20 bg-white/[0.02] hover:bg-white/[0.05] transition-all text-sm font-sans group"
          >
            View on GitHub
            <ChevronRight className="w-4 h-4 text-text-tertiary group-hover:text-white group-hover:translate-x-0.5 transition-all" />
          </a>
        </motion.div>

        {/* Stats Row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.7, ease }}
          className="flex items-center justify-center gap-8 mt-12 pt-8 border-t border-white/5"
        >
          {[
            { value: 'SHA-256', label: 'Hash Chain' },
            { value: 'WBFT', label: 'Consensus' },
            { value: '<5ms', label: 'Verify Latency' },
            { value: '100%', label: 'Lineage' },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 + i * 0.1 }}
              className="text-center"
            >
              <div className="font-mono text-lg font-bold text-white">{stat.value}</div>
              <div className="text-xs text-text-tertiary font-mono uppercase tracking-widest mt-1">{stat.label}</div>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Bottom Gradient */}
      <div className="absolute bottom-0 inset-x-0 h-40 bg-gradient-to-t from-abyssal-900 to-transparent z-[2]" />
    </section>
  );
}
