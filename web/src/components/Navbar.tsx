import { Shield, Github, ExternalLink } from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';

export function Navbar() {
  const { scrollY } = useScroll();
  const bgOpacity = useTransform(scrollY, [0, 100], [0, 0.8]);
  const borderOpacity = useTransform(scrollY, [0, 100], [0, 0.05]);

  return (
    <motion.nav
      className="fixed top-0 w-full z-50 backdrop-blur-xl border-b"
      style={{
        backgroundColor: useTransform(bgOpacity, (v) => `rgba(10, 10, 10, ${v})`),
        borderBottomColor: useTransform(borderOpacity, (v) => `rgba(255, 255, 255, ${v})`),
      }}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <motion.a
          href="#"
          className="flex items-center gap-2.5 group"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <div className="relative">
            <Shield className="w-6 h-6 text-cyber-lime transition-all group-hover:drop-shadow-[0_0_8px_rgba(204,255,0,0.4)]" />
            <div className="absolute inset-0 bg-cyber-lime/20 rounded-full blur-lg opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <span className="font-mono font-bold tracking-tight text-lg">
            CORTEX<span className="text-text-tertiary">_os</span>
          </span>
        </motion.a>

        <div className="flex items-center gap-1 text-sm font-sans">
          <a href="#architecture" className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-lg hover:bg-white/5">
            Architecture
          </a>
          <a href="#comparison" className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-lg hover:bg-white/5">
            Compare
          </a>
          <a href="https://docs.cortex.moskv.dev" className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-lg hover:bg-white/5 flex items-center gap-1.5">
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
  );
}
