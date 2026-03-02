import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { motion } from 'framer-motion';
import { ShieldCheck, Check, Terminal, ExternalLink, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const ease = [0.16, 1, 0.3, 1] as const;

export function Success() {
  return (
    <div className="min-h-screen bg-abyssal-900 flex flex-col">
      <Navbar />
      
      <main className="flex-1 flex items-center justify-center pt-24 pb-20 relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 dot-grid opacity-20" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyber-lime/[0.04] rounded-[100%] blur-[150px] pointer-events-none" />
        
        <div className="w-full max-w-3xl mx-auto px-6 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 0.8, ease }}
            className="glass-strong rounded-none border border-cyber-lime/30 p-10 md:p-14 text-center relative overflow-hidden"
          >
            {/* Success indicator */}
            <div className="absolute -top-20 -right-20 w-64 h-64 bg-gradient-to-br from-cyber-lime/20 to-transparent blur-[60px] pointer-events-none" />
            
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.6, type: 'spring' }}
              className="w-20 h-20 mx-auto rounded-none border border-cyber-lime/40 bg-cyber-lime/[0.05] flex items-center justify-center mb-8"
            >
              <ShieldCheck className="w-10 h-10 text-cyber-lime" />
            </motion.div>

            <h1 className="text-4xl md:text-5xl font-sans font-black tracking-[-0.04em] mb-4 text-white">
              Protocol Initiated.
            </h1>
            <p className="text-xl text-text-secondary font-medium tracking-tight mb-10 max-w-lg mx-auto">
              Transaction verified. Your deployment is now armed with Sovereign AI compliance tools.
            </p>

            <div className="grid md:grid-cols-2 gap-6 text-left mb-12">
              <div className="glass bg-abyssal-800/80 p-6 border-l-4 border-cyber-lime">
                <div className="flex items-center gap-2 text-cyber-lime font-mono text-sm tracking-widest uppercase mb-4">
                  <Terminal className="w-4 h-4" /> Start Building
                </div>
                <div className="bg-abyssal-900 border border-white/5 p-4 font-mono text-xs text-text-secondary select-all mb-4">
                  <div className="flex gap-2">
                    <span className="text-cyber-lime">$</span>
                    <span>pip install cortex-engine</span>
                  </div>
                  <div className="flex gap-2 mt-1">
                    <span className="text-cyber-lime">$</span>
                    <span>cortex auth --token &lt;YOUR_API_KEY&gt;</span>
                  </div>
                </div>
                <a href="https://cortexpersist.dev" target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-sm font-semibold text-white hover:text-cyber-lime transition-colors">
                  Open Documentation <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              <div className="glass bg-abyssal-800/80 p-6 border-white/5 space-y-4">
                <h3 className="font-bold text-white mb-2">Next Steps</h3>
                <ul className="space-y-3">
                  <li className="flex gap-3 text-sm text-text-secondary items-start">
                    <Check className="w-4 h-4 text-cyber-lime flex-shrink-0 mt-0.5" />
                    <span>Check your email for access credentials and billing receipts.</span>
                  </li>
                  <li className="flex gap-3 text-sm text-text-secondary items-start">
                    <Check className="w-4 h-4 text-cyber-lime flex-shrink-0 mt-0.5" />
                    <span>Generate your Sovereign production keys in the dashboard.</span>
                  </li>
                  <li className="flex gap-3 text-sm text-text-secondary items-start">
                    <Check className="w-4 h-4 text-cyber-lime flex-shrink-0 mt-0.5" />
                    <span>Join the private Discord channel for premium support.</span>
                  </li>
                </ul>
              </div>
            </div>

            <Link
              to="/"
              className="inline-flex items-center gap-3 px-8 py-4 bg-white/[0.03] border border-white/10 hover:border-white/30 text-white font-mono text-sm tracking-wide transition-all group"
            >
              Return Home
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
          </motion.div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
