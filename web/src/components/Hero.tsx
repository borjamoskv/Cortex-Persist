import { motion } from 'framer-motion';
import { Terminal, Copy, Check, ArrowRight, ShieldCheck } from 'lucide-react';
import { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';

const ease = [0.16, 1, 0.3, 1] as const;

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
            Sovereign Compliance Layer
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 1, delay: 0.1, ease }}
            className="text-5xl sm:text-6xl md:text-7xl lg:text-[7rem] font-sans font-black tracking-[-0.05em] leading-[0.9] relative group italic"
          >
            End AI <br />
            <span className="text-gradient relative">
              Amnesia.
              <span className="absolute inset-0 bg-cyber-lime/10 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.25, ease }}
            className="text-lg md:text-2xl text-text-secondary max-w-2xl font-sans leading-relaxed tracking-tight"
          >
            Cryptographic proof for every agent decision.<br />
            <span className="text-white font-black">Article 12 compliance in 10 minutes.</span>
          </motion.p>

            {/* Action Buttons — SaaS-first hierarchy */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 pt-6">
              {/* PRIMARY: SaaS entry point */}
              <button
                onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })}
                className="group relative overflow-hidden rounded-none border border-cyber-lime bg-cyber-lime text-black px-8 py-5 flex items-center justify-center gap-3 transition-all hover:shadow-[0_0_50px_rgba(204,255,0,0.5)] hover:scale-[1.02] flex-1 sm:flex-none font-mono font-black text-sm uppercase tracking-widest"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                Stop the €30M Risk
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>

              {/* SECONDARY: Compliance Audit */}
              <Link
                to="/audit"
                className="group relative overflow-hidden rounded-none border border-industrial-gold bg-industrial-gold/10 text-white px-8 py-5 flex items-center justify-center gap-3 transition-all hover:bg-industrial-gold/20 flex-1 sm:flex-none font-mono font-black text-sm uppercase tracking-widest shadow-[0_0_30px_rgba(212,175,55,0.1)] hover:shadow-[0_0_40px_rgba(212,175,55,0.2)]"
              >
                <ShieldCheck className="w-5 h-5 text-industrial-gold" />
                Analyze Compliance
              </Link>

              {/* TERTIARY: CLI for power users */}
              <button
                onClick={handleCopy}
                className="group relative overflow-hidden rounded-none border border-white/10 bg-black/30 backdrop-blur-md px-8 py-5 flex items-center gap-3 transition-all hover:border-cyber-lime/40 hover:shadow-[0_0_20px_rgba(204,255,0,0.08)] flex-1 sm:flex-none text-left"
              >
                <Terminal className="w-4 h-4 text-text-tertiary group-hover:text-cyber-lime transition-colors flex-shrink-0" />
                <span className="font-mono text-sm text-text-tertiary group-hover:text-white transition-colors">
                  curl -sL <span className="text-white/40 group-hover:text-cyber-lime/60 transition-colors">cortex.sovereign | bash</span>
                </span>
                <div className="ml-auto pl-3 border-l border-white/[0.06] flex-shrink-0">
                  {copied ? (
                    <Check className="w-4 h-4 text-cyber-lime" />
                  ) : (
                    <Copy className="w-4 h-4 text-white/20 group-hover:text-text-tertiary transition-colors" />
                  )}
                </div>
              </button>
            </div>

            <div className="flex items-center gap-8 pt-4">
              <div className="flex -space-x-2">
                {[1,2,3,4].map(i => (
                  <div key={i} className="w-7 h-7 rounded-full border-2 border-abyssal-900 bg-abyssal-700 flex items-center justify-center">
                    <div className="w-full h-full rounded-full bg-gradient-to-br from-white/10 to-transparent" />
                  </div>
                ))}
              </div>
              <div className="text-[10px] font-mono text-text-tertiary uppercase tracking-widest">
                Trusted by 40+ <span className="text-white">Compliance Officers</span>
              </div>
            </div>

        </div>

        {/* Right Column: THE ASSET */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.9, rotate: 2 }}
          animate={{ opacity: 1, scale: 1, rotate: 0 }}
          transition={{ duration: 1.2, delay: 0.5, ease }}
          className="lg:col-span-4 hidden lg:block relative"
        >
          <div className="relative group">
            {/* Image Container with Glow */}
            <div className="absolute -inset-4 bg-cyber-lime/20 blur-[60px] opacity-20 group-hover:opacity-40 transition-opacity" />
            <div className="relative border border-white/10 overflow-hidden bg-abyssal-800">
               <img 
                 src="/assets/cortex_hero.png" 
                 alt="CORTEX Trust Vault" 
                 className="w-full h-auto grayscale-[0.2] hover:grayscale-0 transition-all duration-700 scale-105 group-hover:scale-100" 
               />
               <div className="absolute inset-0 bg-gradient-to-t from-abyssal-900/80 via-transparent to-transparent" />
               
               {/* Metadata overlay */}
               <div className="absolute bottom-4 left-4 right-4 flex justify-between items-end font-mono text-[9px] text-cyber-lime/60">
                 <div className="space-y-1">
                   <div>SHA-256: 7hHq/zJj...</div>
                   <div>STATUS: SEALED</div>
                 </div>
                 <div className="text-right">
                   VERIFIED BY<br />WBFT CONSENSUS
                 </div>
               </div>
            </div>

            {/* Floating UI Card */}
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="absolute -top-10 -right-10 glass-strong p-4 border border-cyber-lime/30 glow-lime shadow-2xl hidden xl:block"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="w-2 h-2 rounded-full bg-cyber-lime animate-pulse" />
                <span className="text-[10px] font-mono text-white tracking-widest">ART. 12 COMPLIANT</span>
              </div>
              <div className="text-xs text-text-tertiary">99.9% Verification Rate</div>
            </motion.div>
          </div>
        </motion.div>
      </div>


      {/* Bottom Gradient Overlay */}
      <div className="absolute bottom-0 inset-x-0 h-40 bg-gradient-to-t from-abyssal-900 to-transparent z-[2] pointer-events-none" />
    </section>
  );
}
