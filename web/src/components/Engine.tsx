import { motion, useInView } from 'framer-motion';
import { Database, Lock, Search, Network, Activity } from 'lucide-react';
import { useRef, useState } from 'react';

const ease = [0.16, 1, 0.3, 1];

const features = [
  {
    title: "SHA-256 Memory Ledger",
    description: "Every fact cryptographically hashed. A single altered byte breaks the chain. Total chronological integrity enforced at the protocol level.",
    icon: <Lock className="w-5 h-5" />,
    accent: 'cyber-lime',
    code: `hash = sha256(fact.content + prev_hash)\nledger.append(Hash(value=hash, seq=n))`,
  },
  {
    title: "Zero-Trust Consensus",
    description: "Weighted Byzantine Fault Tolerance for agent swarms. No single agent corrupts the global state. Mathematically provable safety.",
    icon: <Network className="w-5 h-5" />,
    accent: 'cyber-violet',
    code: `consensus = wbft.propose(fact, quorum=0.67)\nif consensus.verified: ledger.commit(fact)`,
  },
  {
    title: "Hybrid Vector + SQL",
    description: "Strictly structured SQLite with native vector embeddings. Lightning semantic retrieval with relational guarantees. Zero cloud dependency.",
    icon: <Database className="w-5 h-5" />,
    accent: 'cyber-lime',
    code: `results = engine.search("auth pattern",\n  project="api", top_k=5)  # <5ms`,
  },
  {
    title: "Deterministic Lineage",
    description: "100% attribute traceability. Know which agent, at what millisecond, with what confidence, originated any fact. Full provenance.",
    icon: <Search className="w-5 h-5" />,
    accent: 'cyber-violet',
    code: `fact.source    # "agent:gemini"\nfact.created   # "2026-02-24T09:03:22Z"\nfact.confidence # "C5" (verified)`,
  }
];

function FeatureCard({ feature, index }: { feature: typeof features[0], index: number }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const [hovered, setHovered] = useState(false);

  // Dynamic colors mapped to Tailwind classes for borders/text
  const borderColor = feature.accent === 'cyber-lime' ? 'border-cyber-lime' : 'border-cyber-violet';
  const textColor = feature.accent === 'cyber-lime' ? 'text-cyber-lime' : 'text-cyber-violet';
  const bgColor = feature.accent === 'cyber-lime' ? 'bg-cyber-lime' : 'bg-cyber-violet';
  
  // Asymmetrical staggered layout
  const alignLeft = index % 2 === 0;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: alignLeft ? -50 : 50, filter: 'blur(10px)' }}
      animate={isInView ? { opacity: 1, x: 0, filter: 'blur(0px)' } : {}}
      transition={{ duration: 0.8, delay: 0.1, ease }}
      className={`relative w-full lg:w-[85%] ${alignLeft ? 'mr-auto' : 'ml-auto'}`}
    >
      {/* Node connection to center line */}
      <div className={`absolute top-1/2 -mt-px h-px w-20 hidden lg:block ${alignLeft ? '-right-20 bg-gradient-to-r' : '-left-20 bg-gradient-to-l'} from-${feature.accent}/50 to-transparent`} />

      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className={`glass-strong rounded-none p-10 border-l-4 ${borderColor}/50 hover:${borderColor} transition-colors duration-500 group relative overflow-hidden`}
      >
        <div className={`absolute inset-0 ${bgColor}/[0.02] group-hover:${bgColor}/[0.05] transition-colors duration-500`} />
        
        {/* Tech Corner Pattern */}
        <div className="absolute top-0 right-0 w-16 h-16 pointer-events-none opacity-20 group-hover:opacity-100 transition-opacity duration-700">
          <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id={`gridp-${index}`} width="8" height="8" patternUnits="userSpaceOnUse">
                <circle cx="2" cy="2" r="1" fill={feature.accent === 'cyber-lime' ? '#CCFF00' : '#6600FF'} />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill={`url(#gridp-${index})`} />
            <polygon points="64,0 64,64 0,0" fill="#0A0A0A" />
          </svg>
        </div>

        <div className="relative z-10 grid md:grid-cols-2 gap-8 items-center cursor-default">
          <div>
            <div className={`w-10 h-10 rounded-none border border-${feature.accent}/30 flex items-center justify-center mb-6 ${textColor} group-hover:scale-110 group-hover:rotate-3 transition-transform duration-500 bg-[#0A0A0A]`}>
              {feature.icon}
            </div>

            <h3 className="text-xl md:text-2xl font-bold mb-4 font-sans tracking-tight">{feature.title}</h3>
            <p className="text-text-secondary text-sm md:text-base leading-relaxed mb-6 font-sans">
              {feature.description}
            </p>

            <motion.div
              animate={{ opacity: hovered ? 1 : 0.5, x: hovered ? 5 : 0 }}
              className={`flex items-center gap-2 text-xs font-mono uppercase tracking-widest ${textColor} transition-all duration-300`}
            >
              <Activity className="w-3 h-3" /> System Trace
            </motion.div>
          </div>

          <div className="relative h-full min-h-[140px] flex flex-col justify-center">
            {/* Dark code block area */}
            <div className={`absolute inset-0 bg-[#050505] border border-white/5 p-4 overflow-hidden`}>
              {/* Scanline effect for code block */}
              <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_50%,rgba(0,0,0,0.5)_51%)] bg-[length:100%_4px] pointer-events-none z-10 opacity-30" />
              
              <div className="font-mono text-[10px] md:text-xs text-text-tertiary mb-3 uppercase tracking-widest flex items-center justify-between">
                <span>execution_layer</span>
                <span className={`w-2 h-2 ${bgColor} rounded-full animate-ping opacity-50`} />
              </div>
              <pre className={`font-mono textxs md:text-sm ${textColor} whitespace-pre-wrap leading-relaxed relative z-20`}>
                {feature.code}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function Engine() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="architecture" className="py-40 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-20" />

      {/* Massive Typographic Watermark */}
      <div className="absolute top-1/4 left-0 w-full flex justify-center pointer-events-none z-[1] opacity-10">
        <h1 className="text-watermark text-[20vw] whitespace-nowrap text-cyber-violet mix-blend-overlay rotate-90 transform-gpu md:rotate-0">
          ARCHITECTURE
        </h1>
      </div>

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Header Section */}
        <div className="mb-32 relative">
          <div className="absolute -left-6 top-4 bottom-0 w-px bg-gradient-to-b from-cyber-violet/50 via-cyber-violet/10 to-transparent hidden md:block" />
          
          <motion.div
            initial={{ opacity: 0, x: -20, filter: 'blur(10px)' }}
            animate={isInView ? { opacity: 1, x: 0, filter: 'blur(0px)' } : {}}
            transition={{ duration: 0.8, ease }}
            className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-none border-l-2 border-cyber-violet bg-cyber-violet/[0.04] text-cyber-violet text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Database className="w-3.5 h-3.5" />
            Under the Hood
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
            animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-5xl md:text-6xl lg:text-7xl font-sans font-black tracking-[-0.04em] leading-[0.95] mb-8"
          >
            The Sovereignty <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-violet to-white">
              Engine.
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.2, ease }}
            className="text-lg md:text-xl text-text-secondary max-w-2xl font-sans leading-relaxed"
          >
            Not a standard database. A deterministic protocol designed to force unconstrained LLMs to operate strictly within mathematically verifiable bounds.
          </motion.p>
        </div>

        {/* Structural Schematic Layout */}
        <div className="relative">
          {/* Central spine/tracking line connecting elements on larger screens */}
          <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 w-px bg-white/5 hidden lg:block" />
          
          <div className="space-y-16">
            {features.map((feature, idx) => (
              <FeatureCard key={feature.title} feature={feature} index={idx} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
