import { Shield, Github, Menu, X, ArrowRight, Scale, MessageSquare } from 'lucide-react';
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion';
import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';

interface NavbarProps {
  onBuy?: () => void;
}

export function Navbar({ onBuy }: NavbarProps) {
  const { scrollY } = useScroll();
  const yOffset = useTransform(scrollY, [0, 100], [0, 12]);
  const scale = useTransform(scrollY, [0, 100], [1, 0.98]);
  const [mobileOpen, setMobileOpen] = useState(false);

  const scrollTo = useCallback((id: string) => {
    setMobileOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  return (
    <>
      <div className="fixed top-6 left-0 right-0 z-50 flex justify-center pointer-events-none px-4">
        <motion.nav
          style={{ y: yOffset, scale }}
          className="glass-pill rounded-full pointer-events-auto w-full max-w-5xl"
        >
          <div className="px-6 h-16 flex items-center justify-between">
            <Link
              to="/"
              className="flex items-center gap-2.5 group pointer-events-auto"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            >
              <div className="relative">
                <Shield className="w-5 h-5 text-cyber-lime transition-all group-hover:drop-shadow-[0_0_8px_rgba(204,255,0,0.6)]" />
                <div className="absolute inset-0 bg-cyber-lime/40 rounded-full blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <span className="font-mono font-bold tracking-tight text-base uppercase">
                CORTEX<span className="text-text-tertiary">_persist</span>
              </span>
            </Link>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center gap-1.5 text-sm font-sans">
              <button onClick={() => scrollTo('architecture')} className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-full hover:bg-white/5 font-mono text-[11px] uppercase tracking-widest">
                Architecture
              </button>
              <button onClick={() => scrollTo('pricing')} className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-full hover:bg-white/5 font-mono text-[11px] uppercase tracking-widest">
                Pricing
              </button>
              <Link 
                to="/foro" 
                className="px-4 py-2 text-text-secondary hover:text-white transition-colors rounded-full hover:bg-white/5 font-mono text-[11px] uppercase tracking-widest flex items-center gap-2"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Moltbook
              </Link>
              <Link 
                to="/audit" 
                className="px-4 py-2 text-industrial-gold hover:text-white transition-colors rounded-full hover:bg-industrial-gold/10 font-mono text-[11px] uppercase tracking-widest flex items-center gap-2"
              >
                <Scale className="w-3.5 h-3.5" />
                Compliance Audit
              </Link>

              <div className="h-4 w-px bg-white/10 mx-2" />

              <a
                href="https://github.com/borjamoskv/cortex"
                target="_blank"
                rel="noreferrer noopener"
                title="GitHub Repository"
                className="flex items-center gap-2 text-text-tertiary hover:text-white transition-colors p-2"
              >
                <Github className="w-4 h-4" />
              </a>

              <button
                onClick={onBuy ? onBuy : undefined}
                className="ml-2 flex items-center gap-2 bg-cyber-lime text-black px-6 py-2 rounded-full transition-all border border-cyber-lime group relative overflow-hidden font-mono text-[11px] font-black tracking-widest uppercase hover:shadow-[0_0_20px_rgba(204,255,0,0.4)]"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-500" />
                Get Started
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden w-10 h-10 flex items-center justify-center text-text-secondary hover:text-white transition-colors"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </motion.nav>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[45] bg-abyssal-900/95 backdrop-blur-2xl flex flex-col items-center justify-center gap-8 md:hidden p-6"
          >
            {[
              { label: 'Architecture', id: 'architecture' },
              { label: 'Pricing', id: 'pricing' },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => scrollTo(item.id)}
                className="text-4xl font-black font-sans hover:text-cyber-lime transition-colors uppercase tracking-tighter italic"
              >
                {item.label}
              </button>
            ))}

            <Link
              to="/audit"
              onClick={() => setMobileOpen(false)}
              className="text-4xl font-black font-sans text-industrial-gold hover:text-white transition-colors uppercase tracking-tighter italic"
            >
              Compliance Audit
            </Link>
            
            <button
              onClick={() => {
                setMobileOpen(false);
                onBuy?.();
              }}
              className="mt-4 w-full bg-cyber-lime text-black py-6 font-black text-xl uppercase tracking-widest italic"
            >
              Buy CORTEX
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
