import { motion, useInView } from 'framer-motion';
import { ArrowRight, Github, Shield } from 'lucide-react';
import { useRef } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

export function Footer() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });

  return (
    <footer className="relative overflow-hidden noise" ref={ref}>
      {/* CTA Section */}
      <div className="py-32 relative">
        <div className="absolute inset-0 bg-abyssal-900" />
        <div className="absolute inset-0 dot-grid animate-grid-fade" />

        {/* Central glow — brighter, more urgent */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyber-lime/[0.04] rounded-full blur-[200px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[200px] h-[200px] bg-cyber-lime/[0.08] rounded-full blur-[80px]" />

        <div className="max-w-3xl mx-auto px-6 relative z-10 text-center">
          {/* Eyebrow */}
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.04] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyber-lime opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyber-lime" />
            </span>
            Now in early access
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, ease }}
            className="text-4xl md:text-6xl font-sans font-black tracking-[-0.04em] mb-6 leading-[0.95]"
          >
            Your AI memory,{' '}
            <span className="text-gradient">mathematically verified</span>.
          </motion.h2>

          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.1 }}
            className="text-text-secondary mb-12 text-lg max-w-xl mx-auto leading-relaxed"
          >
            Join the teams using CORTEX to build agents that can't lie, forget, or hallucinate without a cryptographic trace.
          </motion.p>

          {/* Dual CTA — SaaS hierarchy */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.2, ease }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <a
              href="https://cortexpersist.com/signup"
              className="group relative overflow-hidden rounded-none border border-cyber-lime bg-cyber-lime text-black px-10 py-5 flex items-center justify-center gap-3 transition-all hover:shadow-[0_0_60px_rgba(204,255,0,0.5)] hover:scale-[1.02] font-mono font-black text-sm uppercase tracking-widest w-full sm:w-auto"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/25 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
              Start Compliance Check
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </a>
          </motion.div>

          {/* Trust signals */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 0.5 }}
            className="flex items-center justify-center gap-6 mt-10 text-[11px] font-mono text-text-tertiary uppercase tracking-widest flex-wrap"
          >
            <span>No credit card required</span>
            <span className="w-1 h-1 rounded-full bg-white/20" />
            <span>Cancel anytime</span>
            <span className="w-1 h-1 rounded-full bg-white/20" />
            <span>Apache 2.0 core</span>
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
            <div className="flex gap-8 text-sm font-mono">
              <a href="https://github.com/borjamoskv/cortex" target="_blank" rel="noopener noreferrer" className="text-text-tertiary hover:text-cyber-lime transition-colors flex items-center gap-1.5 px-3 py-1 bg-white/[0.03] rounded-md border border-white/5">
                <Github className="w-3.5 h-3.5" /> GITHUB
              </a>
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
