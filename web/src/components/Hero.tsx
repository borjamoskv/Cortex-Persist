import { motion } from 'framer-motion';
import { Terminal, Copy, Check, ChevronRight } from 'lucide-react';
import { useState, useCallback, useEffect } from 'react';

const ease = [0.16, 1, 0.3, 1];

export function Hero() {
  const [copied, setCopied] = useState(false);
  const [mouseY, setMouseY] = useState(0);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMouseY(e.clientY / globalThis.innerHeight);
    };
    globalThis.addEventListener('mousemove', handleMouseMove);
    return () => globalThis.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText('pip install cortex-engine');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  return (
    <section className="relative min-h-screen flex items-center pt-20 overflow-hidden noise">
      {/* Dot Grid Background */}
      <div className="absolute inset-0 dot-grid animate-grid-fade" />

      {/* Radial Glow Orbs - More dynamic and asymmetrical */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-60">
        <motion.div 
          animate={{ y: mouseY * -50 }}
          className="absolute top-[20%] right-[10%] w-[600px] h-[600px] bg-cyber-lime/[0.04] rounded-full blur-[150px] animate-pulse-slow" 
        />
        <motion.div 
          animate={{ y: mouseY * 50 }}
          className="absolute bottom-[10%] left-[5%] w-[800px] h-[800px] bg-cyber-violet/[0.05] rounded-full blur-[200px] animate-pulse-slow" 
          style={{ animationDelay: '2s' }} 
        />
      </div>

      {/* Massive Typographic Watermark */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-50">
        <motion.h1 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.5, ease }}
          className="text-watermark text-[20vw] whitespace-nowrap"
        >
          CORTEX
        </motion.h1>
      </div>

      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 grid lg:grid-cols-12 gap-12 items-center">
        {/* Left Column (Main Content) */}
        <div className="lg:col-span-8 space-y-10 relative">
          {/* Vertical tracking line */}
          <div className="absolute -left-6 top-4 bottom-0 w-px bg-gradient-to-b from-cyber-lime/50 via-cyber-lime/10 to-transparent hidden md:block" />
          
          <motion.div
            initial={{ opacity: 0, x: -20, filter: 'blur(10px)' }}
            animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
            transition={{ duration: 0.8, ease }}
            className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border border-cyber-lime/20 bg-cyber-lime/[0.04] text-cyber-lime text-xs font-mono uppercase tracking-[0.2em]"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyber-lime opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyber-lime" />
            </span>
            The SSL/TLS of AI Memory
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 1, delay: 0.1, ease }}
            className="text-5xl sm:text-6xl md:text-7xl lg:text-[6rem] font-sans font-black tracking-[-0.04em] leading-[0.95]"
          >
            Proof over <br />
            <span className="text-gradient">Probabilities.</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.25, ease }}
            className="text-lg md:text-2xl text-text-secondary max-w-2xl font-sans leading-relaxed tracking-tight"
          >
            CORTEX is a sovereign cryptographic ledger for AI memory.
            Convert stochastic LLM hallucinations into{' '}
            <span className="text-white font-medium">mathematically verifiable facts</span>.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease }}
            className="flex flex-col sm:flex-row items-start sm:items-center gap-6 pt-4"
          >
            {/* Pip Install Bespoke Button */}
            <button
              onClick={handleCopy}
              className="group relative overflow-hidden rounded-none border border-cyber-lime/30 bg-black/40 backdrop-blur-md px-8 py-5 flex items-center gap-4 transition-all hover:border-cyber-lime hover:shadow-[0_0_30px_rgba(204,255,0,0.15)] w-full sm:w-auto text-left"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-cyber-lime/0 via-cyber-lime/[0.05] to-cyber-lime/0 -translate-x-full group-hover:animate-shimmer" />
              <Terminal className="w-5 h-5 text-cyber-lime flex-shrink-0" />
              <div className="flex flex-col">
                <span className="text-xs text-text-tertiary font-mono uppercase tracking-[0.2em] mb-1">Install Engine</span>
                <span className="font-mono text-sm text-white">
                  pip install <span className="text-cyber-lime">cortex-engine</span>
                </span>
              </div>
              <div className="ml-4 pl-4 border-l border-white/10 flex-shrink-0">
                {copied ? (
                  <Check className="w-5 h-5 text-cyber-lime" />
                ) : (
                  <Copy className="w-5 h-5 text-text-tertiary group-hover:text-cyber-lime transition-colors" />
                )}
              </div>
            </button>

            <a
              href="https://github.com/borjamoskv/cortex"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 group font-mono text-sm tracking-wide text-text-secondary hover:text-white transition-colors py-2"
            >
              View Repository
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform text-cyber-lime" />
            </a>
          </motion.div>
        </div>

        {/* Right Column (Data/Stats HUD) */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, delay: 0.5, ease }}
          className="lg:col-span-4 hidden lg:flex flex-col gap-6 relative"
        >
          {/* Decorative bracket */}
          <div className="absolute -left-8 top-0 bottom-0 w-4 border-l border-y border-white/10 rounded-l-xl opacity-50" />
          
          {[
            { value: 'SHA-256', label: 'Hash Chain Core', desc: 'Immutable ledger' },
            { value: 'WBFT', label: 'Swarm Consensus', desc: 'Zero-trust voting' },
            { value: '<5ms', label: 'Verify Latency', desc: 'Overhead per fact' },
            { value: '100%', label: 'Deterministic', desc: 'Lineage tracking' },
          ].map((stat, i) => (
            <div key={stat.label} className="pl-6 group">
              <div className="font-mono text-3xl font-bold text-white tracking-tighter group-hover:text-cyber-lime transition-colors">
                {stat.value}
              </div>
              <div className="text-sm text-text-secondary font-mono mt-1 flex items-center justify-between">
                <span>{stat.label}</span>
                <span className="text-[10px] uppercase text-text-tertiary">{stat.desc}</span>
              </div>
              {i !== 3 && <div className="h-px w-full bg-white/5 mt-6" />}
            </div>
          ))}
        </motion.div>
      </div>

      {/* Bottom Gradient Overlay */}
      <div className="absolute bottom-0 inset-x-0 h-40 bg-gradient-to-t from-abyssal-900 to-transparent z-[2] pointer-events-none" />
    </section>
  );
}
