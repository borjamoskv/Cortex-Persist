import { motion } from 'framer-motion';
import { FileCode, Terminal, BookOpen, Github } from 'lucide-react';

const ease = [0.16, 1, 0.3, 1] as const;

export function DocsHero() {
  return (
    <section className="relative min-h-[85vh] flex items-center pt-20 overflow-hidden">
      <div className="absolute inset-0 dot-grid opacity-30" />

      <div className="absolute inset-0 z-0 pointer-events-none opacity-50">
        <div className="absolute top-[15%] right-[20%] w-[500px] h-[500px] animate-pulse-slow object-contain bg-[image:radial-gradient(circle,rgba(204,255,0,0.04)_0%,transparent_70%)] [will-change:transform,opacity]" />
        <div className="absolute bottom-[20%] left-[10%] w-[600px] h-[600px] animate-pulse-slow object-contain [animation-delay:2s] bg-[image:radial-gradient(circle,rgba(46,80,144,0.04)_0%,transparent_70%)] [will-change:transform,opacity]" />
      </div>

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-50">
        <motion.h1
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.5, ease }}
          className="text-watermark text-[18vw] whitespace-nowrap"
        >
          DOCS
        </motion.h1>
      </div>

      <div className="relative z-10 w-full max-w-5xl mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease }}
          className="flex justify-center mb-8"
        >
          <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border border-cyber-lime/30 bg-cyber-lime/[0.06] text-cyber-lime text-xs font-mono uppercase tracking-[0.2em]">
            <FileCode className="w-4 h-4" />
            v0.3.0b1
          </div>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 1, delay: 0.1, ease }}
          className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-sans font-black tracking-[-0.05em] leading-[0.9] mb-8"
        >
          Developer{' '}
          <br />
          <span className="text-gradient-lime">
            Documentation.
          </span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.25, ease }}
          className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto leading-relaxed mb-12"
        >
          Everything you need to integrate CORTEX Persist into your AI agent stack.
          Getting started, API reference, architecture deep-dives, and CLI reference.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <a
            href="#quickstart"
            className="group relative overflow-hidden rounded-none border border-cyber-lime/40 bg-cyber-lime/10 px-8 py-4 flex items-center gap-3 transition-all hover:border-cyber-lime hover:bg-cyber-lime/20 hover:shadow-[0_0_30px_rgba(204,255,0,0.15)]"
          >
            <Terminal className="w-5 h-5 text-cyber-lime" />
            <span className="font-mono text-sm font-bold text-white">Get Started</span>
          </a>

          <a
            href="https://github.com/borjamoskv/cortex"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-4 text-text-secondary hover:text-white font-mono text-sm tracking-wide transition-colors group border border-white/10 hover:border-white/20"
          >
            <Github className="w-4 h-4" />
            View Source
            <BookOpen className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </a>
        </motion.div>
      </div>

      <div className="absolute bottom-0 inset-x-0 h-40 bg-gradient-to-t from-abyssal-900 to-transparent z-[2] pointer-events-none" />
    </section>
  );
}
