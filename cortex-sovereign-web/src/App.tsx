import React, { Suspense } from 'react';
import { motion } from 'framer-motion';
import { Activity, Zap, Shield, Brain, ChevronRight, Github } from 'lucide-react';
import NeuralHive from './components/NeuralHive';

export default function App() {
  return (
    <div className="min-h-screen bg-[#050505] text-white selection:bg-cyber-lime selection:text-black overflow-x-hidden">
      {/* Hero Section */}
      <div className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Animated Background Elements */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-cyber-lime/5 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute top-[20%] right-[10%] w-[400px] h-[400px] bg-electric-violet/5 blur-[100px] rounded-full pointer-events-none" />
        
        <div className="max-w-7xl mx-auto relative z-10">
          <nav className="flex justify-between items-center mb-32">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-cyber-lime rounded-sm" />
              <span className="text-xl font-bold tracking-tighter font-outfit uppercase">Cortex v6</span>
            </div>
            <div className="flex gap-8 items-center text-sm font-mono tracking-widest text-white/40 uppercase">
              <a href="#hive" className="hover:text-cyber-lime transition-colors">Neural Hive</a>
              <a href="#features" className="hover:text-cyber-lime transition-colors">Architecture</a>
              <a href="https://github.com/borjamoskv/cortex" title="GitHub Repository" className="p-2 bg-white/5 rounded-full hover:bg-white/10 transition-colors">
                <Github className="w-5 h-5" />
              </a>
            </div>
          </nav>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              <div className="inline-block px-4 py-1.5 bg-cyber-lime/10 rounded-full border border-cyber-lime/20 text-cyber-lime text-[10px] font-mono tracking-widest uppercase mb-8">
                The Sovereign Standard v6.0.0
              </div>
              <motion.h1 
                className="text-7xl md:text-8xl font-black tracking-tighter leading-[0.9] mb-8 font-outfit uppercase"
              >
                {["Cognitive", "Infrastructure"].map((word, i) => (
                  <motion.span 
                    key={i} 
                    className="block"
                    initial={{ y: 50, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.2 + i * 0.1, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                  >
                    {word === "Infrastructure" ? <span className="text-white/20">{word}</span> : word}
                  </motion.span>
                ))}
              </motion.h1>
              <p className="text-white/40 text-xl leading-relaxed mb-12 font-light">
                The open-source state layer for the agentic era. Store decisions, recall context, and synchronize consciousness across multi-agent swarms.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <button className="btn btn-primary group px-8 py-4 bg-cyber-lime text-black font-bold uppercase tracking-widest text-xs flex items-center justify-center gap-2">
                  Initialize Node <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button className="btn btn-outline px-8 py-4 border border-white/10 hover:bg-white/5 transition-colors uppercase tracking-widest text-xs">
                  View Protocol
                </button>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.2 }}
              className="relative aspect-square glass-panel rounded-3xl border-white/5 overflow-hidden group"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyber-lime/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
              <div className="absolute inset-0 flex items-center justify-center p-12">
                <div className="w-full h-full relative">
                  <div className="absolute inset-0 border border-white/5 rounded-full animate-[spin_20s_linear_infinite]" />
                  <div className="absolute inset-4 border border-white/5 rounded-full animate-[spin_15s_linear_infinite_reverse]" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Brain className="w-32 h-32 text-cyber-lime/20" />
                  </div>
                </div>
              </div>
              <div className="absolute bottom-8 left-8 right-8">
                <div className="flex justify-between items-end">
                  <div>
                    <div className="text-[10px] font-mono text-white/20 uppercase tracking-[0.3em] mb-2">Status</div>
                    <div className="text-cyber-lime font-mono text-xs flex items-center gap-2">
                       <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyber-lime opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-cyber-lime"></span>
                      </span>
                      ACTIVE_GHOST_COUNT: 0
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-mono text-white/20 uppercase tracking-[0.3em] mb-2">Factor</div>
                    <div className="text-white font-mono text-xl tracking-tighter">130.00</div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Hero Section Extension (Parallax Target) */}
      <section className="relative h-[20vh] pointer-events-none" />

      {/* Axioms Scrolling Bar */}
      <div className="relative z-20 py-8 bg-black/40 backdrop-blur-3xl border-y border-white/5 overflow-hidden">
        <div className="flex animate-marquee gap-12 whitespace-nowrap">
          {[
            { id: "consensus", text: "BYZANTINE consensus v4.0" },
            { id: "latency", text: "LATENCY < 5MS" },
            { id: "leaks", text: "ZERO DATA PERSISTENCE LEAKS" },
            { id: "sovereign", text: "SOVEREIGN INFRASTRUCTURE" },
            { id: "compaction", text: "AUTONOMOUS MEMORY RECLAMATION" },
            { id: "search", text: "SEMANTIC SEARCH (MINILM-L6-V2)" }
          ].map((axiom) => (
            <span key={axiom.id} className="text-[10px] font-mono tracking-[0.4em] uppercase text-white/20 flex items-center gap-4">
              <div className="w-1.5 h-1.5 rounded-full bg-cyber-lime" /> {axiom.text}
            </span>
          ))}
          {/* Repeat for seamless loop */}
          {[
            { id: "consensus-2", text: "BYZANTINE consensus v4.0" },
            { id: "latency-2", text: "LATENCY < 5MS" },
            { id: "leaks-2", text: "ZERO DATA PERSISTENCE LEAKS" },
            { id: "sovereign-2", text: "SOVEREIGN INFRASTRUCTURE" },
            { id: "compaction-2", text: "AUTONOMOUS MEMORY RECLAMATION" },
            { id: "search-2", text: "SEMANTIC SEARCH (MINILM-L6-V2)" }
          ].map((axiom) => (
            <span key={axiom.id} className="text-[10px] font-mono tracking-[0.4em] uppercase text-white/20 flex items-center gap-4">
              <div className="w-1.5 h-1.5 rounded-full bg-cyber-lime" /> {axiom.text}
            </span>
          ))}
        </div>
      </div>

      {/* Neural Hive Demo */}
      <section id="demo" className="relative py-32 px-6 z-10 max-w-7xl mx-auto scanlines">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          <div>
            <h2 className="text-6xl font-bold tracking-tighter mb-8 font-outfit uppercase">Cognitive Visibility</h2>
            <p className="text-white/40 text-xl leading-relaxed mb-12">
              Real-time visualization of the CORTEX knowledge graph. See how agents store facts, resolve ghosts, and achieve consensus through our proprietary Neural Hive engine.
            </p>
            <div className="space-y-6">
              {[
                "Real-time Fact-Binding",
                "Ghost Persistence Detection",
                "Consensus Pulse Visualization"
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-4 text-white/60">
                  <div className="w-6 h-[1px] bg-cyber-lime" />
                  <span className="font-mono text-xs uppercase tracking-widest">{item}</span>
                </div>
              ))}
            </div>
          </div>
          <Suspense fallback={<div className="h-[600px] glass-panel animate-pulse rounded-3xl" />}>
            <div className="h-[600px] relative">
              <div className="absolute -inset-4 bg-cyber-lime/5 blur-3xl rounded-full" />
              <NeuralHive />
            </div>
          </Suspense>
        </div>
      </section>

      {/* Comparison Section */}
      <section className="relative py-32 px-6 z-10 max-w-5xl mx-auto">
        <div className="text-center mb-24">
          <h2 className="text-2xl font-mono tracking-[0.5em] text-cyber-lime mb-4 uppercase">Sovereign Protocol</h2>
          <h2 className="text-6xl font-bold tracking-tighter mb-4 font-outfit uppercase">Built for Production</h2>
        </div>

        <div className="glass-panel rounded-3xl overflow-hidden border-white/5 shadow-2xl">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.01]">
                <th className="p-10 text-[10px] uppercase tracking-widest text-white/20 font-mono">Feature_ID</th>
                <th className="p-10 text-[10px] uppercase tracking-widest text-white/20 font-mono text-center">Standard</th>
                <th className="p-10 text-[10px] uppercase tracking-widest text-cyber-lime font-mono text-center bg-cyber-lime/[0.03]">CORTEX_S_V6</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {[
                { f: "Multi-Agent Consensus (⅔)", o: "Manual", c: "Autonomous" },
                { f: "Latency (High-Concurrency)", o: "Variable", c: "< 5ms Fix" },
                { f: "Task Persistence", o: "Ephemeral", c: "Immutable" },
                { f: "Self-Hostable", o: "Restricted", c: "100% Sovereign" },
                { f: "Memory Reclamation", o: "None", c: "Sidecar-Monitor" }
              ].map((row, i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/[0.01] transition-colors">
                  <td className="p-10 font-bold text-white/70 tracking-tight">{row.f}</td>
                  <td className="p-10 text-center text-white/20 font-mono text-xs">{row.o}</td>
                  <td className="p-10 text-center text-cyber-lime font-bold bg-cyber-lime/[0.01] font-mono text-xs">{row.c}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Features Bento Grid */}
      <section id="features" className="relative py-32 px-6 z-10 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          <BentoCard 
            className="md:col-span-8"
            title="Byzantine Consensus" 
            subtitle="CORTEX implements a modified PBFT protocol where agents must reach ⅔ consensus before a fact is considered 'Sovereign Truth'."
            icon={<Shield className="text-cyber-lime" />}
          />
          <BentoCard 
            className="md:col-span-4"
            title="Ghost Resolution" 
            subtitle="Active ghost monitoring prevents task decomposition during high-entropy sessions."
            icon={<Activity className="text-electric-violet" />}
          />
          <BentoCard 
            className="md:col-span-4" 
            title="Compaction Sidecar" 
            subtitle="Production-grade memory reclamation via our autonomous sidecar monitor."
            icon={<Zap className="text-cyber-lime" />}
          />
          <BentoCard 
            className="md:col-span-8"
            title="Sovereign Ontology" 
            subtitle="Self-documenting knowledge graphs that evolve with your agent's understanding, stored locally in encrypted vaults."
            icon={<Brain className="text-yinmn-blue" />}
          />
        </div>
      </section>
      {/* Pricing Section */}
      <section id="pricing" className="relative py-32 px-6 z-10 max-w-7xl mx-auto">
        <div className="text-center mb-20">
          <h2 className="text-5xl font-bold tracking-tighter font-outfit uppercase mb-4">Licensing</h2>
          <p className="text-white/40 font-light">Select your level of sovereignty.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { 
              name: "Nucleus", 
              price: "Free", 
              desc: "For independent agents and researchers.",
              features: ["Local-only persistence", "Byzantine Consensus (v1)", "Sovereign Ontology (Basic)"]
            },
            { 
              name: "Sovereign", 
              price: "$99/mo", 
              desc: "For production-grade agent swarms.",
              features: ["Multi-cloud sync", "Ghost Resolution Engine", "Autonomous Memory Reclamation", "PBFT Consensus v4.0"],
              featured: true
            },
            { 
              name: "Galaxy", 
              price: "Custom", 
              desc: "For enterprise-level cognitive clusters.",
              features: ["Dedicated Sidecar Fleet", "Zero-Knowledge Fact Verification", "Psi-Level Telemetry", "Priority Forge Access"]
            }
          ].map((tier, i) => (
            <motion.div
              key={i}
              whileHover={{ y: -10 }}
              className={`glass-panel p-10 rounded-3xl border-white/5 flex flex-col ${tier.featured ? 'border-cyber-lime/20 bg-cyber-lime/[0.02]' : ''}`}
            >
              {tier.featured && (
                <div className="text-[10px] font-mono text-cyber-lime tracking-widest uppercase mb-6 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyber-lime animate-pulse" /> RECOMMENDED_ARCHITECTURE
                </div>
              )}
              <h3 className="text-2xl font-bold mb-2 font-outfit uppercase">{tier.name}</h3>
              <div className="text-4xl font-black mb-6 font-outfit">{tier.price}</div>
              <p className="text-white/40 text-sm mb-8 font-light min-h-[40px]">{tier.desc}</p>
              
              <ul className="space-y-4 mb-10 flex-grow">
                {tier.features.map((f, j) => (
                  <li key={j} className="flex items-center gap-3 text-xs text-white/60">
                    <Activity className="w-3 h-3 text-cyber-lime/50" /> {f}
                  </li>
                ))}
              </ul>

              <button className={`btn w-full ${tier.featured ? 'btn-primary' : 'btn-outline'}`}>
                {tier.price === "Custom" ? "Contact Forge" : "Deploy Now"}
              </button>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative py-20 px-6 z-10 border-t border-white/5 bg-black">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-12">
          <div className="flex flex-col items-center md:items-start gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-cyber-lime rounded-sm" />
              <span className="text-xl font-bold tracking-tighter font-outfit uppercase">Cortex v6</span>
            </div>
            <p className="text-[10px] font-mono text-white/20 uppercase tracking-widest">
              © 2026 MOSKV-1 SOVEREIGN SYSTEMS. ALL RIGHTS RESERVED.
            </p>
          </div>
          
          <div className="flex gap-12 text-[10px] font-mono tracking-widest uppercase text-white/40">
            <a href="#" className="hover:text-cyber-lime transition-colors">Manifesto</a>
            <a href="#" className="hover:text-cyber-lime transition-colors">Security</a>
            <a href="#" className="hover:text-cyber-lime transition-colors">Forge</a>
            <a href="#" className="hover:text-cyber-lime transition-colors">Status</a>
          </div>

          <div className="flex gap-4">
            <a href="#" title="GitHub" className="p-3 bg-white/5 rounded-full hover:bg-white/10 transition-colors border border-white/5">
              <Github className="w-4 h-4" />
            </a>
            <a href="#" title="Activity Monitor" className="p-3 bg-white/5 rounded-full hover:bg-white/10 transition-colors border border-white/5">
              <Activity className="w-4 h-4" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

interface BentoCardProps {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  className?: string;
}

function BentoCard({ title, subtitle, icon, className = "" }: BentoCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      whileHover={{ scale: 1.01 }}
      className={`glass-panel p-8 rounded-3xl relative overflow-hidden group cursor-default transition-all duration-500 hover:border-white/10 ${className}`}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.01] to-transparent pointer-events-none" />
      <motion.div 
        className="absolute top-0 left-0 w-full h-1 bg-cyber-lime/20 shadow-[0_0_15px_rgba(204,255,0,0.5)] opacity-0 group-hover:opacity-100 transition-opacity"
        animate={{ top: ["0%", "100%", "0%"] }}
        transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
      />
      <div className="h-12 w-12 rounded-2xl bg-black/40 flex items-center justify-center border border-white/5 mb-6 group-hover:border-cyber-lime/30 transition-colors">
        {React.isValidElement(icon) ? React.cloneElement(icon as React.ReactElement<{ className?: string }>, { className: "w-6 h-6" }) : icon}
      </div>
      <div>
        <h3 className="text-2xl font-bold mb-2 font-outfit">{title}</h3>
        <p className="text-white/40 font-light leading-relaxed">{subtitle}</p>
      </div>
    </motion.div>
  );
}
