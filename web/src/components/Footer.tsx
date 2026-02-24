import { motion, useInView } from 'framer-motion';
import { Terminal, Copy, Check, Github, FileText, Shield } from 'lucide-react';
import { useRef, useState, useCallback } from 'react';

const ease = [0.16, 1, 0.3, 1];

export function Footer() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText('pip install cortex-engine');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  return (
    <footer className="relative overflow-hidden noise" ref={ref}>
      {/* CTA Section */}
      <div className="py-32 relative">
        <div className="absolute inset-0 bg-abyssal-900" />
        <div className="absolute inset-0 dot-grid animate-grid-fade" />

        {/* Central glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-cyber-lime/[0.03] rounded-full blur-[200px]" />

        <div className="max-w-3xl mx-auto px-6 relative z-10 text-center">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, ease }}
            className="text-4xl md:text-5xl font-sans font-bold tracking-[-0.03em] mb-4"
          >
            Don't outsource <span className="text-gradient">your brain</span>.
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.1 }}
            className="text-text-secondary mb-12 text-lg"
          >
            Three lines. Zero cloud dependency. Total sovereignty.
          </motion.p>

          {/* Terminal Block */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={isInView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.8, delay: 0.2, ease }}
            className="max-w-lg mx-auto"
          >
            <div className="glass-strong rounded-xl overflow-hidden glow-lime">
              {/* Terminal header */}
              <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/60" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                  <div className="w-3 h-3 rounded-full bg-green-500/60" />
                </div>
                <span className="text-xs text-text-tertiary font-mono ml-2">terminal</span>
              </div>
              {/* Terminal body */}
              <button
                onClick={handleCopy}
                className="w-full px-6 py-5 flex items-center justify-between group cursor-pointer hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-3 font-mono text-sm">
                  <Terminal className="w-4 h-4 text-cyber-lime" />
                  <span>
                    <span className="text-text-tertiary">$</span>{' '}
                    pip install <span className="text-cyber-lime font-semibold">cortex-engine</span>
                  </span>
                </div>
                {copied ? (
                  <Check className="w-4 h-4 text-cyber-lime" />
                ) : (
                  <Copy className="w-4 h-4 text-text-tertiary group-hover:text-cyber-lime transition-colors" />
                )}
              </button>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="border-t border-white/5 bg-abyssal-800/50 backdrop-blur-xl relative z-10">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            {/* Logo */}
            <div className="flex items-center gap-2.5 font-mono text-sm">
              <Shield className="w-4 h-4 text-cyber-lime" />
              <span className="font-bold">CORTEX</span>
              <span className="text-text-tertiary">v0.3.0</span>
              <span className="mx-2 text-text-tertiary">·</span>
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyber-lime opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-cyber-lime" />
                </span>
                <span className="text-text-tertiary text-xs uppercase tracking-wider">Operational</span>
              </div>
            </div>

            {/* Links */}
            <div className="flex gap-6 text-sm font-mono">
              <a href="https://github.com/borjamoskv/cortex" target="_blank" rel="noopener noreferrer" className="text-text-tertiary hover:text-cyber-lime transition-colors flex items-center gap-1.5">
                <Github className="w-3.5 h-3.5" /> GitHub
              </a>
              <a href="https://docs.cortex.moskv.dev" target="_blank" rel="noopener noreferrer" className="text-text-tertiary hover:text-white transition-colors flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5" /> Docs
              </a>
              <span className="text-text-tertiary">Apache 2.0</span>
            </div>

            {/* Copyright */}
            <div className="text-xs text-text-tertiary font-mono">
              © 2026 MOSKV-1 SOVEREIGN SYSTEMS
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
