import { motion, useInView } from 'framer-motion';
import { Database, Lock, Search, Network, ArrowRight } from 'lucide-react';
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
  const isInView = useInView(ref, { once: true, margin: "-50px" });
  const [hovered, setHovered] = useState(false);

  const accentColor = feature.accent === 'cyber-lime' ? '#CCFF00' : '#6600FF';

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30, filter: 'blur(10px)' }}
      animate={isInView ? { opacity: 1, y: 0, filter: 'blur(0px)' } : {}}
      transition={{ duration: 0.7, delay: 0.1 * index, ease }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="glass-strong p-8 rounded-2xl relative overflow-hidden group cursor-default"
    >
      {/* Hover glow */}
      <motion.div
        className="absolute inset-0 rounded-2xl pointer-events-none"
        animate={{
          boxShadow: hovered
            ? `inset 0 0 80px ${accentColor}08, 0 0 40px ${accentColor}06`
            : 'inset 0 0 0px transparent, 0 0 0px transparent'
        }}
        transition={{ duration: 0.5 }}
      />

      {/* Corner accent line */}
      <div className={`absolute top-0 left-0 w-16 h-px bg-${feature.accent}`} />
      <div className={`absolute top-0 left-0 h-16 w-px bg-${feature.accent}`} />

      <div className="relative z-10">
        {/* Icon */}
        <div className={`w-12 h-12 rounded-xl bg-${feature.accent}/10 border border-${feature.accent}/20 flex items-center justify-center mb-6 text-${feature.accent} group-hover:scale-110 group-hover:rotate-3 transition-all duration-500`}>
          {feature.icon}
        </div>

        {/* Title */}
        <h3 className="text-xl font-bold mb-3 font-sans tracking-tight">{feature.title}</h3>

        {/* Description / Code toggle */}
        <div className="relative min-h-[80px]">
          <motion.p
            animate={{ opacity: hovered ? 0 : 1, y: hovered ? -10 : 0 }}
            transition={{ duration: 0.3 }}
            className="text-text-secondary text-sm leading-relaxed absolute inset-0"
          >
            {feature.description}
          </motion.p>
          <motion.pre
            animate={{ opacity: hovered ? 1 : 0, y: hovered ? 0 : 10 }}
            transition={{ duration: 0.3 }}
            className={`font-mono text-xs text-${feature.accent}/80 absolute inset-0 leading-relaxed`}
          >
            {feature.code}
          </motion.pre>
        </div>

        {/* Hover indicator */}
        <motion.div
          animate={{ opacity: hovered ? 1 : 0, x: hovered ? 0 : -5 }}
          className={`flex items-center gap-1.5 text-xs font-mono text-${feature.accent} mt-6`}
        >
          <ArrowRight className="w-3 h-3" /> view implementation
        </motion.div>
      </div>
    </motion.div>
  );
}

export function Engine() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="architecture" className="py-32 relative overflow-hidden noise" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid animate-grid-fade" />

      {/* Radial glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-cyber-violet/[0.04] rounded-full blur-[200px]" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Header */}
        <div className="text-center mb-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, ease }}
            className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border border-cyber-violet/20 bg-cyber-violet/[0.04] text-cyber-violet text-xs font-mono uppercase tracking-[0.2em] mb-8"
          >
            Under the Hood
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-4xl md:text-5xl lg:text-6xl font-sans font-bold tracking-[-0.03em] mb-6"
          >
            The Sovereignty{' '}
            <span className="text-gradient-violet">Engine</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.2, ease }}
            className="text-lg text-text-secondary max-w-2xl mx-auto"
          >
            Not a database. A deterministic protocol that forces LLMs to operate within{' '}
            <span className="text-white font-medium">mathematically verifiable constraints</span>.
          </motion.p>
        </div>

        {/* Feature Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, idx) => (
            <FeatureCard key={feature.title} feature={feature} index={idx} />
          ))}
        </div>
      </div>
    </section>
  );
}
