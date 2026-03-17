import { motion } from 'framer-motion';
import { Terminal, Copy, Check, ArrowRight, ShieldCheck } from 'lucide-react';
import { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import SovereignCanvas from './SovereignCanvas';

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
    navigator.clipboard.writeText('pip install cortex-persist');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  return (
    <section className="relative min-h-screen flex items-center pt-20 overflow-hidden noise">
      {/* Dot Grid Background */}
      <div className="absolute inset-0 dot-grid animate-grid-fade" />

      {/* 3D WebGL Nivel Igloo Canvas */}
      <SovereignCanvas />

      {/* Radial Glow Orbs - More dynamic, biological, asymmetric, and warm */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-40">
        <motion.div 
          animate={{ y: mouseY * -30, x: mouseY * 15 }}
          className="absolute top-[10%] right-[10%] w-[700px] h-[500px] rounded-[100%] animate-pulse-slow bg-[image:radial-gradient(ellipse,rgba(204,255,0,0.03)_0%,transparent_70%)] will-change-transform opacity-70" 
        />
        <motion.div 
          animate={{ y: mouseY * 40, x: mouseY * -20 }}
          className="absolute bottom-[5%] left-[5%] w-[900px] h-[600px] rounded-[100%] animate-pulse-slow [animation-delay:2s] bg-[image:radial-gradient(ellipse,rgba(255,107,0,0.04)_0%,transparent_70%)] will-change-transform" 
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
            transition={{ duration: 1, ease }}
            className="inline-flex items-center gap-2.5 px-4 py-2 rounded-sm border border-cyber-lime/10 bg-cyber-lime/[0.02] text-text-primary text-xs font-mono uppercase tracking-[0.2em]"
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
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-5 pt-8">
              {/* PRIMARY: SaaS entry point */}
              <button
                onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })}
                className="group relative overflow-hidden rounded-[4px] border border-cyber-lime/80 bg-cyber-lime text-abyssal-900 px-8 py-5 flex items-center justify-center gap-3 transition-transform duration-500 ease-out glow-lime hover:scale-[0.98] active:scale-[0.96] flex-1 sm:flex-none font-sans font-semibold text-[15px] tracking-wide"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-out" />
                Stop the €30M Risk
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1.5 transition-transform duration-500 ease-out" />
              </button>

              {/* SECONDARY: Compliance Audit */}
              <Link
                to="/audit"
                className="group relative overflow-hidden rounded-none border border-industrial-gold bg-industrial-gold/10 text-white px-8 py-5 flex items-center justify-center gap-3 transition-all duration-300 hover:bg-industrial-gold/20 flex-1 sm:flex-none font-mono font-black text-sm uppercase tracking-widest shadow-[0_0_30px_rgba(212,175,55,0.1)] hover:shadow-[0_0_40px_rgba(212,175,55,0.2)] active:scale-[0.98]"
              >
                <ShieldCheck className="w-5 h-5 text-industrial-gold" />
                Analyze Compliance
              </Link>

              {/* TERTIARY: CLI for power users */}
              <button
                onClick={handleCopy}
                className="group relative overflow-hidden rounded-none border border-white/10 bg-black/30 backdrop-blur-md px-8 py-5 flex items-center gap-3 transition-all duration-300 hover:border-cyber-lime/40 hover:shadow-[0_0_20px_rgba(204,255,0,0.08)] active:scale-[0.98] flex-1 sm:flex-none text-left"
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

            <div className="flex items-center gap-8 pt-6">
              <div className="flex -space-x-3">
                {[1,2,3,4].map(i => (
                  <div key={i} className="w-8 h-8 rounded-sm border-2 border-abyssal-900 bg-abyssal-700 flex items-center justify-center opacity-80 hover:opacity-100 hover:-translate-y-1 transition-all duration-500">
                    <div className="w-full h-full rounded-sm bg-gradient-to-br from-white/5 to-transparent" />
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
            <div className="absolute -inset-4 opacity-20 group-hover:opacity-40 transition-opacity bg-[image:radial-gradient(circle,rgba(204,255,0,0.2)_0%,transparent_60%)]" />
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

            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
              className="absolute -top-10 -right-10 glass-strong p-5 rounded-[4px] border-t border-[rgba(255,107,0,0.15)] border-l border-[rgba(255,255,255,0.05)] shadow-[0_12px_40px_rgba(0,0,0,0.8)] glow-tungsten hidden xl:block z-20"
            >
              <div className="flex items-center gap-3 mb-2 opacity-90">
                <div className="w-1.5 h-1.5 rounded-full bg-tungsten-glow animate-pulse-slow shadow-[0_0_10px_rgba(255,107,0,0.8)]" />
                <span className="text-[10px] font-mono text-text-primary tracking-widest uppercase">ART. 12 COMPLIANT</span>
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
