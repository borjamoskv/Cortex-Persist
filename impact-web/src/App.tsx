import React, { useState, useEffect, lazy, Suspense } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Database, Activity, Code2, Zap } from 'lucide-react';

const Spline = lazy(() => import('@splinetool/react-spline'));

export default function App() {
  const { scrollYProgress } = useScroll();
  const yBackground = useTransform(scrollYProgress, [0, 1], [0, 300]);
  const opacityText = useTransform(scrollYProgress, [0, 0.3], [1, 0]);

  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="min-h-[200vh] bg-background selection:bg-cyan selection:text-black">
      {/* 3D Spline Canvas Foreground/Background */}
      <div className="fixed inset-0 z-0 pointer-events-auto">
        <Suspense fallback={
          <div className="w-full h-full bg-gradient-to-br from-[#0A0A0A] via-[#1A1A1A] to-[#0A0A0A] animate-pulse flex items-center justify-center">
            <div className="text-[#CCFF00] font-mono text-sm tracking-widest animate-bounce">LOADING AETHER-Ω</div>
          </div>
        }>
          <Spline scene="https://prod.spline.design/6Wq1Q7YGyM-iab9i/scene.splinecode" />
        </Suspense>
      </div>

      {/* Dynamic Aura Background */}
      <motion.div 
        className="fixed inset-0 pointer-events-none opacity-40 mix-blend-screen z-0"
        animate={{
          background: `radial-gradient(1000px circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(102, 0, 255, 0.1), transparent 40%)`
        }}
        transition={{ type: "tween", ease: "linear", duration: 0.1 }}
      />
      <div className="fixed inset-0 pointer-events-none mix-blend-screen z-0"
           style={{ background: 'radial-gradient(circle at 50% 120%, rgba(204, 255, 0, 0.05), transparent 60%)' }} />

      {/* Hero Section */}
      <section className="relative h-screen flex flex-col justify-center items-center px-6 pointer-events-none">
        <motion.div 
          style={{ y: yBackground, opacity: opacityText }}
          className="max-w-7xl mx-auto w-full flex flex-col items-center justify-center relative z-10"
        >
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="flex items-center gap-2 mb-6 px-4 py-2 rounded-full glass-panel border border-[#CCFF00]/20 backdrop-blur-md bg-black/40"
          >
            <Activity className="w-4 h-4 text-[#CCFF00]" />
            <span className="text-xs uppercase tracking-widest font-mono text-cyan-400">YOLO_MODE: ACTIVE</span>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="text-7xl md:text-9xl font-bold font-['Outfit'] tracking-tighter text-center leading-[0.85] mix-blend-difference"
          >
            <span className="block text-white mb-2 glitch" data-text="O U R O B O R O S">O U R O B O R O S</span>
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-zinc-300 via-zinc-100 to-zinc-400">
              ARCHITECTURE
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.5 }}
            className="mt-12 text-zinc-300 max-w-xl text-center text-lg md:text-xl font-light leading-relaxed mix-blend-difference"
          >
            Aesthetic Matrix Overload. Spline Rendering on Maximum Output. <span className="text-[#CCFF00] font-medium animate-pulse">Absolute Genesis</span>.
          </motion.p>
        </motion.div>

        {/* Scroll Indicator */}
        <motion.div 
          animate={{ y: [0, 8, 0] }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
          className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-zinc-600"
        >
          <span className="text-xs font-mono uppercase tracking-[0.2em]">Engage</span>
          <div className="w-[1px] h-12 bg-gradient-to-b from-zinc-600 to-transparent" />
        </motion.div>
      </section>

      {/* Modular Section */}
      <section className="relative px-6 py-32 z-20">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <BentoCard 
              title="Hyper-Responsive" 
              subtitle="Latency is a crime."
              icon={<Zap className="w-6 h-6 text-[#CCFF00]" />}
              delay={0}
            />
            <BentoCard 
              title="Recursive Evolution" 
              subtitle="Self-improving architecture."
              icon={<Code2 className="w-6 h-6 text-[#6600FF]" />}
              delay={0.1}
            />
            <BentoCard 
              title="Aesthetic Matrix" 
              subtitle="Uncompromising visuals."
              icon={<Database className="w-6 h-6 text-[#D4AF37]" />}
              delay={0.2}
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function BentoCard({ title, subtitle, icon, delay }: { title: string, subtitle: string, icon: React.ReactNode, delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
      className="glass-panel p-8 rounded-3xl flex flex-col justify-between aspect-square group cursor-pointer relative overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent pointer-events-none" />
      <div className="h-12 w-12 rounded-2xl bg-zinc-900/50 flex items-center justify-center border border-white/5 group-hover:border-[#CCFF00]/30 transition-colors">
        {icon}
      </div>
      <div>
        <h3 className="text-2xl font-bold font-['Outfit'] mb-2">{title}</h3>
        <p className="text-zinc-500 font-sans">{subtitle}</p>
      </div>
    </motion.div>
  );
}
