import { motion, useInView } from 'framer-motion';
import { Terminal, Copy, Check } from 'lucide-react';
import { useRef, useState } from 'react';

const ease = [0.16, 1, 0.3, 1] as const;

function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-abyssal-700/40">
        <span className="text-[10px] font-mono uppercase tracking-widest text-text-tertiary">{lang}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[10px] font-mono text-text-tertiary hover:text-cyber-lime transition-colors"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-5 overflow-x-auto text-sm font-mono leading-relaxed text-text-secondary">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function QuickStart() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section id="quickstart" className="py-32 relative overflow-hidden" ref={ref}>
      <div className="absolute inset-0 bg-abyssal-900" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      <div className="max-w-4xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.06] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8"
          >
            <Terminal className="w-3.5 h-3.5" />
            Quick Start
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease }}
            className="text-4xl md:text-5xl font-sans font-black tracking-[-0.04em] mb-6"
          >
            Up and running in{' '}
            <span className="text-gradient-lime">60 seconds.</span>
          </motion.h2>
        </div>

        <div className="space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.2, ease }}
            className="glass-strong rounded-none overflow-hidden"
          >
            <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5">
              <div className="flex items-center justify-center w-6 h-6 rounded-full bg-cyber-lime/10 border border-cyber-lime/30 text-cyber-lime text-xs font-mono font-bold">1</div>
              <span className="text-sm font-bold">Install</span>
            </div>
            <CodeBlock lang="bash" code={`pip install cortex-persist[all]`} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.3, ease }}
            className="glass-strong rounded-none overflow-hidden"
          >
            <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5">
              <div className="flex items-center justify-center w-6 h-6 rounded-full bg-cyber-lime/10 border border-cyber-lime/30 text-cyber-lime text-xs font-mono font-bold">2</div>
              <span className="text-sm font-bold">Store your first fact</span>
            </div>
            <CodeBlock lang="python" code={`from cortex import CortexEngine

engine = CortexEngine()

# Store a decision with cryptographic integrity
await engine.store(
    content="Migrated auth from JWT to Ed25519 signatures",
    fact_type="decision",
    project="my-agent",
    confidence="C4",
    source="agent:architect",
    meta={"impact": "security", "files_touched": 3}
)`} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.4, ease }}
            className="glass-strong rounded-none overflow-hidden"
          >
            <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5">
              <div className="flex items-center justify-center w-6 h-6 rounded-full bg-cyber-lime/10 border border-cyber-lime/30 text-cyber-lime text-xs font-mono font-bold">3</div>
              <span className="text-sm font-bold">Search with semantic understanding</span>
            </div>
            <CodeBlock lang="python" code={`# Hybrid search: vector similarity + text matching
results = await engine.hybrid_search(
    query="authentication security decisions",
    project="my-agent",
    limit=5
)

for fact in results:
    print(f"[{fact.confidence}] {fact.content}")`} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.5, ease }}
            className="glass-strong rounded-none overflow-hidden"
          >
            <div className="flex items-center gap-3 px-5 py-3 border-b border-white/5">
              <div className="flex items-center justify-center w-6 h-6 rounded-full bg-cyber-lime/10 border border-cyber-lime/30 text-cyber-lime text-xs font-mono font-bold">4</div>
              <span className="text-sm font-bold">Verify ledger integrity</span>
            </div>
            <CodeBlock lang="python" code={`# Cryptographic verification of the entire chain
report = await engine.verify_ledger()
print(f"Chain valid: {report.valid}")
print(f"Facts verified: {report.facts_checked}")
print(f"Hash algorithm: SHA-256")`} />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
