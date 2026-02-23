import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, Shield, Cpu, Database, AlertTriangle, Zap, Github, LucideIcon } from 'lucide-react';

interface CardProps {
  children: React.ReactNode;
  title: string;
  icon: LucideIcon;
  color?: string;
}

const Card = ({ children, title, icon: Icon, color = "lime" }: CardProps) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    whileHover={{ scale: 1.02 }}
    className="glass-panel p-6 rounded-2xl relative overflow-hidden group border-white/5"
  >
    <div className={`absolute top-0 right-0 w-24 h-24 bg-${color}-500/5 blur-3xl -mr-12 -mt-12 group-hover:bg-${color}-500/10 transition-all`} />
    <div className="flex items-start justify-between mb-4">
      <Icon className={`w-5 h-5 text-${color}-400`} />
      <div className={`w-2 h-2 rounded-full bg-${color}-500 shadow-[0_0_10px_rgba(204,255,0,0.5)] animate-pulse`} />
    </div>
    <h3 className="text-white/40 text-xs font-mono uppercase tracking-widest mb-1">{title}</h3>
    <div className="text-2xl font-bold tracking-tighter">{children}</div>
  </motion.div>
);

export default function Dashboard() {
  const [stats] = useState({
    modules: 444,
    latency: "4.2ms",
    threats: 0,
    entropy: "low"
  });

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white p-8 font-outfit selection:bg-cyber-lime selection:text-black">
      {/* HUD Header */}
      <header className="flex justify-between items-center mb-12 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl font-bold tracking-tighter flex items-center gap-3">
            <div className="w-8 h-8 bg-cyber-lime rounded flex items-center justify-center">
              <div className="w-4 h-1 bg-black rotate-45" />
            </div>
            CORTEX <span className="text-white/20 font-light">v6.0.0</span>
          </h1>
          <p className="text-white/40 text-sm font-mono mt-1 tracking-widest uppercase">Sovereign Cloud Core // Operational</p>
        </div>
        <div className="flex gap-4">
          <div className="px-4 py-2 bg-white/5 rounded-full border border-white/10 text-xs font-mono flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-cyber-lime" />
            130/100 STANDARD ACTIVE
          </div>
          <a
            href="https://github.com/borjamoskv/cortex"
            target="_blank"
            rel="noopener noreferrer"
            title="View Source on GitHub"
            className="p-2 hover:bg-white/5 rounded-lg transition-colors border border-white/5"
          >
            <Github className="w-5 h-5" />
          </a>
        </div>
      </header>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        <Card title="System Integrity" icon={Shield} color="lime">
          Sovereign
        </Card>
        <Card title="Knowledge Density" icon={Database} color="lime">
          {stats.modules} Modules
        </Card>
        <Card title="Operational Latency" icon={Zap} color="lime">
          {stats.latency}
        </Card>
        <Card title="Neural Load" icon={Cpu} color="blue">
          {stats.entropy}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Active Daemons */}
        <div className="lg:col-span-2 glass-panel rounded-3xl p-8 border-white/5">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-bold tracking-tight">Active Daemon Monitors</h2>
            <div className="px-3 py-1 bg-cyber-lime/10 rounded-md text-[10px] text-cyber-lime font-mono">13 ACTIVE</div>
          </div>
          
          <div className="space-y-4">
            {[
              { name: "SovereignSecurity", load: "0.2%", status: "Nominal" },
              { name: "CompactionEngine", load: "1.4%", status: "Optimizing" },
              { name: "ConsensusOrchestrator", load: "0.8%", status: "Voting" },
              { name: "IdentityWarden", load: "0.1%", status: "Guarding" }
            ].map((daemon) => (
              <div key={daemon.name} className="flex items-center justify-between p-4 bg-white/5 rounded-2xl border border-white/5 hover:border-white/10 transition-all">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center">
                    <Activity className="w-4 h-4 text-white/40" />
                  </div>
                  <div>
                    <div className="font-bold text-sm tracking-tight">{daemon.name}</div>
                    <div className="text-[10px] font-mono text-white/20">LOAD: {daemon.load}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-white/40 uppercase tracking-tighter">{daemon.status}</span>
                  <div className="w-1.5 h-1.5 rounded-full bg-cyber-lime shadow-[0_0_8px_rgba(204,255,0,0.4)]" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Security Alerts HUD */}
        <div className="glass-panel rounded-3xl p-8 border-red-500/10 bg-red-500/5">
          <div className="flex items-center gap-3 mb-8 text-red-500">
            <AlertTriangle className="w-6 h-6" />
            <h2 className="text-2xl font-bold tracking-tight">Threat Intel</h2>
          </div>

          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
              <Shield className="w-8 h-8 text-red-500/40" />
            </div>
            <p className="text-white/40 text-sm font-light">
              No active threats detected.<br/>
              <span className="font-mono text-[10px] uppercase mt-2 block tracking-widest">Perimeter Secure</span>
            </p>
          </div>

          <div className="mt-8 pt-8 border-t border-red-500/10">
            <div className="flex justify-between items-center text-xs font-mono uppercase tracking-widest text-red-500/60">
              <span>Kill Switch Status</span>
              <span>disarmed</span>
            </div>
            <div className="h-1 bg-red-500/10 rounded-full mt-4 overflow-hidden">
              <div className="h-full w-2 bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
