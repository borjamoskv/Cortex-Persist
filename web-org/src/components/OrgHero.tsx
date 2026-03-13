import { motion } from 'framer-motion';
import { Shield, Github, Star, BookOpen, ArrowRight } from 'lucide-react';

const ease = [0.16, 1, 0.3, 1] as const;

export function OrgHero() {
  return (
    <section className="relative min-h-screen flex items-center pt-20 overflow-hidden">
      <div className="absolute inset-0 dot-grid opacity-30" />

      {/* Cyber Lime glow orbs - Hardware Accelerated (Sovereign 200) */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-60">
        <div 
          className="absolute top-[20%] right-[15%] w-[600px] h-[600px] animate-pulse-slow object-contain"
          style={{
            background: 'radial-gradient(circle, rgba(204,255,0,0.06) 0%, rgba(204,255,0,0) 70%)',
            willChange: 'transform, opacity'
          }} 
        />
        <div 
          className="absolute bottom-[10%] left-[10%] w-[700px] h-[700px] animate-pulse-slow object-contain" 
          style={{ 
            animationDelay: '2s',
            background: 'radial-gradient(circle, rgba(204,255,0,0.04) 0%, rgba(204,255,0,0) 70%)',
            willChange: 'transform, opacity'
          }} 
        />
      </div>

      {/* Watermark */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full flex justify-center pointer-events-none z-[1] opacity-50">
        <motion.h1
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.5, ease }}
          className="text-watermark text-[18vw] whitespace-nowrap"
        >
          OPEN SOURCE
        </motion.h1>
      </div>

      <div className="relative z-10 w-full max-w-5xl mx-auto px-6 text-center">
        {/* Shield + Badge */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease }}
          className="flex justify-center mb-8"
        >
          <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border border-cyber-lime/30 bg-cyber-lime/[0.06] text-cyber-lime text-xs font-mono uppercase tracking-[0.2em]">
            <Shield className="w-4 h-4" />
            Apache 2.0 Licensed
          </div>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 1, delay: 0.1, ease }}
          className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-sans font-black tracking-[-0.05em] leading-[0.9] mb-8"
        >
          CORTEX no es otro wrapper de ChatGPT.
          <br />
          <span className="text-gradient-lime">
            Sistema Operativo Soberano.
          </span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.25, ease }}
          className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto leading-relaxed mb-12"
        >
          Mientras OpenAI y Google intentan ser dueños de tu memoria y tu contexto en sus servidores, CORTEX te devuelve el control criptográfico absoluto sobre tu conocimiento. Es código abierto, funciona offline, sella cada decisión en un ledger inmutable, y asegura que la evolución de tu Inteligencia Artificial trabaje exclusivamente para tu patrimonio, no para el de ellos.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <a
            href="https://github.com/borjamoskv/cortex"
            target="_blank"
            rel="noopener noreferrer"
            className="group relative overflow-hidden rounded-none border border-cyber-lime/40 bg-cyber-lime/10 px-8 py-4 flex items-center gap-3 transition-all hover:border-cyber-lime hover:bg-cyber-lime/20 hover:shadow-[0_0_30px_rgba(204,255,0,0.2)]"
          >
            <Github className="w-5 h-5 text-cyber-lime" />
            <span className="font-mono text-sm font-bold text-white">Star on GitHub</span>
            <Star className="w-4 h-4 text-industrial-gold group-hover:text-industrial-gold group-hover:drop-shadow-[0_0_8px_rgba(212,175,55,0.5)] transition-all" />
          </a>

          <a
            href="https://cortexpersist.dev"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-4 text-text-secondary hover:text-white font-mono text-sm tracking-wide transition-colors group border border-white/10 hover:border-white/20"
          >
            <BookOpen className="w-4 h-4" />
            Read the Docs
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </a>
        </motion.div>
      </div>

      <div className="absolute bottom-0 inset-x-0 h-40 bg-gradient-to-t from-abyssal-900 to-transparent z-[2] pointer-events-none" />
    </section>
  );
}
