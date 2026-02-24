import { Shield, Github, ExternalLink } from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';

export function Navbar() {
  const { scrollY } = useScroll();
  const yOffset = useTransform(scrollY, [0, 100], [0, 12]);
  const scale = useTransform(scrollY, [0, 100], [1, 0.98]);

  return (
    <div className="fixed top-6 left-0 right-0 z-50 flex justify-center pointer-events-none px-4">
      <motion.nav
        style={{ y: yOffset, scale }}
        className="glass-pill rounded-full pointer-events-auto w-full max-w-5xl"
      >
        <div className="px-6 h-16 flex items-center justify-between">
          <motion.a
            href="#"
            className="flex items-center gap-2.5 group"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <div className="relative">
              <Shield className="w-5 h-5 text-cyber-lime transition-all group-hover:drop-shadow-[0_0_8px_rgba(204,255,0,0.6)]" />
              <div className="absolute inset-0 bg-cyber-lime/40 rounded-full blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <span className="font-mono font-bold tracking-tight text-base">
              CORTEX<span className="text-text-tertiary">_os</span>
            </span>
          </motion.a>

          <div className="flex items-center gap-1 text-sm font-sans">
            <a href="#architecture" className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-full hover:bg-white/5">
              Architecture
            </a>
            <a href="#comparison" className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-full hover:bg-white/5">
              Compare
            </a>
            <a href="https://docs.cortex.moskv.dev" className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-full hover:bg-white/5 flex items-center gap-1.5">
              Docs <ExternalLink className="w-3 h-3" />
            </a>
            <a
              href="https://github.com/borjamoskv/cortex"
              target="_blank"
              rel="noreferrer"
              className="ml-2 flex items-center gap-2 bg-white/[0.04] hover:bg-cyber-lime/10 px-4 py-2 rounded-full transition-all border border-white/10 hover:border-cyber-lime/40 group"
            >
              <Github className="w-4 h-4 group-hover:text-cyber-lime transition-colors" />
              <span className="group-hover:text-cyber-lime transition-colors">Star</span>
            </a>
          </div>
        </div>
      </motion.nav>
    </div>
  );
}
