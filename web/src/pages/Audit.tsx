import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ShieldCheck, 
  AlertTriangle, 
  FileText, 
  Zap, 
  ArrowRight, 
  ArrowLeft, 
  CheckCircle2, 
  Lock, 
  Users, 
  Clock,
  Terminal,
  Scale
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { BackgroundEffects } from '../components/BackgroundEffects';
import { Navbar } from '../components/Navbar';

interface Option {
  label: string;
  score: number;
  hint: string;
}

interface Question {
  id: number;
  dimension: string;
  euArticle: string;
  icon: React.ReactNode;
  text: string;
  hint: string;
  options: Option[];
}

const QUESTIONS: Question[] = [
  {
    id: 0,
    dimension: "Automatic Logging",
    euArticle: "Art. 12(1)",
    icon: <FileText className="w-5 h-5" />,
    text: "When your AI system takes an action or stores a decision — is it automatically logged?",
    hint: "Art. 12(1) EU AI Act: 'High-risk AI systems shall technically allow for the automatic recording of events.' Every operation must create an immutable record. Manual logging does not satisfy this clause.",
    options: [
      { label: "No logging — actions happen with no record created", score: 0, hint: "DIRECT VIOLATION — Art. 12(1)" },
      { label: "We log manually when we remember to", score: 1, hint: "NON-COMPLIANT — manual ≠ automatic" },
      { label: "Automatic logs exist but have gaps (not every event)", score: 2, hint: "PARTIAL — coverage gaps = liability windows" },
      { label: "Every AI operation triggers an automatic, timestamped log entry", score: 3, hint: "ART. 12(1) COMPLIANT" }
    ]
  },
  {
    id: 1,
    dimension: "Log Content",
    euArticle: "Art. 12(2)",
    icon: <Terminal className="w-5 h-5" />,
    text: "What information is recorded when your AI system accesses or uses its stored knowledge?",
    hint: "Art. 12(2) requires three fields: (1) timestamp of use, (2) reference to which database was queried, (3) what inputs led to a match. A log that just says 'query executed' fails this clause.",
    options: [
      { label: "No structured log content — just raw text output", score: 0, hint: "DIRECT VIOLATION — Art. 12(2)" },
      { label: "Timestamps only — no source reference or input data", score: 1, hint: "INSUFFICIENT — 2 of 3 required fields missing" },
      { label: "Timestamps + data source, but inputs are not recorded", score: 2, hint: "PARTIAL — Art. 12(2) input tracing gap" },
      { label: "Full record: timestamp, source DB reference, input data, match ID", score: 3, hint: "ART. 12(2) COMPLIANT" }
    ]
  },
  {
    id: 2,
    dimension: "Agent Traceability",
    euArticle: "Art. 12(2)(d)",
    icon: <Users className="w-5 h-5" />,
    text: "If multiple AI agents contributed to a decision — can you identify which one did what?",
    hint: "Art. 12(2)(d): Logs must identify 'persons who participated in the verification.' For multi-agent systems: each agent must be tagged and its contribution traceable in the audit record.",
    options: [
      { label: "Impossible — we have no agent identity system", score: 0, hint: "DIRECT VIOLATION — Art. 12(2)(d)" },
      { label: "Agents are named but individual actions aren’t linked", score: 1, hint: "NON-COMPLIANT — attribution without traceability" },
      { label: "Agent IDs on logs, but no weighting or verification record", score: 2, hint: "PARTIAL — consensus evidence missing" },
      { label: "Every agent tagged; votes, weights, and verdicts recorded per decision", score: 3, hint: "ART. 12(2)(d) COMPLIANT" }
    ]
  },
  {
    id: 3,
    dimension: "Tamper-Proof Storage",
    euArticle: "Art. 12(3)",
    icon: <Lock className="w-5 h-5" />,
    text: "Could someone — including a system admin — silently alter or delete your AI’s logs?",
    hint: "Art. 12(3): Logs must be 'tamper-evident' for the system’s entire operational lifetime. If a database row can be UPDATE’d without a trace, you fail this clause. Access policy is not tamper-evidence.",
    options: [
      { label: "Yes — our DB allows direct updates and deletes with no trace", score: 0, hint: "DIRECT VIOLATION — Art. 12(3)" },
      { label: "We have access controls but no cryptographic integrity proof", score: 1, hint: "NON-COMPLIANT — policy ≠ tamper-evidence" },
      { label: "Soft-deletes only, but no hash chain linking records", score: 2, hint: "PARTIAL — deletion prevented, mutation not" },
      { label: "SHA-256 hash chain: each record includes prev_hash. Mutation = detectable break", score: 3, hint: "ART. 12(3) COMPLIANT" }
    ]
  },
  {
    id: 4,
    dimension: "Periodic Verification",
    euArticle: "Art. 12(4)",
    icon: <ShieldCheck className="w-5 h-5" />,
    text: "How do you prove — on demand, to a regulator — that your AI logs haven’t been corrupted?",
    hint: "Art. 12(4): 'Providers shall implement means for periodic integrity verification.' Backups don’t count. You need a cryptographic mechanism (e.g. Merkle checkpoints) that proves integrity efficiently.",
    options: [
      { label: "We can’t — no integrity verification mechanism exists", score: 0, hint: "DIRECT VIOLATION — Art. 12(4)" },
      { label: "We do manual spot-checks occasionally", score: 1, hint: "NON-COMPLIANT — manual ≠ periodic automated" },
      { label: "Individual record checksums but no chain proof for full history", score: 2, hint: "PARTIAL — no checkpoint mechanism" },
      { label: "Merkle tree checkpoints on schedule; results stored in integrity_checks table", score: 3, hint: "ART. 12(4) COMPLIANT" }
    ]
  }
];

const VERDICTS = [
  { min: 0,  max: 30, label: "Non-Compliant", color: "text-red-500", bg: "bg-red-500/10", border: "border-red-500/20", penalty: "€30M or 6% revenue" },
  { min: 31, max: 55, label: "Significant Gaps", color: "text-orange-500", bg: "bg-orange-500/10", border: "border-orange-500/20", penalty: "€15M or 3% revenue" },
  { min: 56, max: 75, label: "Partial Compliance", color: "text-industrial-gold", bg: "bg-industrial-gold/10", border: "border-industrial-gold/20", penalty: "€5M or 1% revenue" },
  { min: 76, max: 89, label: "Near-Compliant", color: "text-cyber-lime/80", bg: "bg-cyber-lime/5", border: "border-cyber-lime/10", penalty: "Low residual risk" },
  { min: 90, max: 100, label: "Article 12 Compliant ✦", color: "text-cyber-lime", bg: "bg-cyber-lime/10", border: "border-cyber-lime/20", penalty: "Demonstrable compliance" }
];

const ease = [0.16, 1, 0.3, 1] as const;

export default function Audit() {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState<(number | null)[]>(new Array(QUESTIONS.length).fill(null));
  const [stage, setStage] = useState<'hero' | 'quiz' | 'processing' | 'results'>('hero');
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const startAudit = () => {
    setStage('quiz');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const selectOption = (optIdx: number) => {
    const newAnswers = [...answers];
    newAnswers[currentIdx] = optIdx;
    setAnswers(newAnswers);
  };

  const nextQ = () => {
    if (currentIdx < QUESTIONS.length - 1) {
      setCurrentIdx(currentIdx + 1);
    } else {
      setStage('processing');
      setTimeout(() => setStage('results'), 3000);
    }
  };

  const prevQ = () => {
    if (currentIdx > 0) setCurrentIdx(currentIdx - 1);
  };

  const scoreData = useMemo(() => {
    if (stage !== 'results') return { percentage: 0, verdict: VERDICTS[0] };
    const totalRaw = answers.reduce((acc: number, ansIdx, qIdx) => {
      if (ansIdx === null) return acc;
      return acc + QUESTIONS[qIdx].options[ansIdx].score;
    }, 0);
    const totalMax = QUESTIONS.length * 3;
    const percentage = Math.round((totalRaw / totalMax) * 100);
    const verdict = VERDICTS.find(v => percentage >= v.min && percentage <= v.max) || VERDICTS[0];
    return { percentage, verdict };
  }, [answers, stage]);

  const progressPct = (answers.filter(a => a !== null).length / QUESTIONS.length) * 100;

  return (
    <div className="min-h-screen selection:bg-cyber-lime selection:text-black">
      <BackgroundEffects />
      <Navbar onBuy={() => window.location.hash = 'pricing'} />

      <main className="max-w-4xl mx-auto px-6 py-32 relative z-10">
        <AnimatePresence mode="wait">
          {stage === 'hero' && (
            <motion.div
              key="hero"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="text-center"
            >
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.04] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8">
                <ShieldCheck className="w-3.5 h-3.5" />
                Structural Audit
              </div>
              <h1 className="text-5xl md:text-7xl font-sans font-black tracking-tight mb-8">
                Is Your AI Memory <br />
                <span className="text-gradient">Architecturally Compliant?</span>
              </h1>
              <p className="text-text-secondary text-lg md:text-xl max-w-2xl mx-auto mb-12 leading-relaxed">
                5 dimensions. 3 minutes. One-to-one mapping to the <strong className="text-cyber-lime font-bold">EU AI Act Article 12</strong> — the law taking effect August 2026 with fines up to €30M.
              </p>

              <div className="grid grid-cols-3 gap-8 max-w-lg mx-auto mb-16">
                <div className="text-center">
                  <div className="text-2xl font-black font-mono text-cyber-lime mb-1">5</div>
                  <div className="text-[10px] text-text-tertiary uppercase tracking-widest font-mono">Dimensions</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-black font-mono text-cyber-lime mb-1">&lt;3m</div>
                  <div className="text-[10px] text-text-tertiary uppercase tracking-widest font-mono">To Complete</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-black font-mono text-red-500 mb-1">€30M</div>
                  <div className="text-[10px] text-text-tertiary uppercase tracking-widest font-mono">Max Penalty</div>
                </div>
              </div>

              <button
                onClick={startAudit}
                className="bg-cyber-lime text-black px-10 py-5 font-black text-sm uppercase tracking-widest hover:shadow-[0_0_40px_rgba(204,255,0,0.3)] transition-all duration-300 group"
              >
                Launch Article 12 Audit
                <ArrowRight className="inline-block ml-3 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </motion.div>
          )}

          {stage === 'quiz' && (
            <motion.div
              key="quiz"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              className="space-y-8"
            >
              {/* Progress */}
              <div className="glass-strong p-6 rounded-none border-b-2 border-cyber-lime/20 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none group-hover:opacity-10 transition-opacity">
                  <Scale className="w-24 h-24" />
                </div>
                <div className="flex justify-between items-end mb-4 relative z-10">
                  <div>
                    <h2 className="text-xs font-mono font-bold tracking-[0.2em] text-text-tertiary uppercase mb-1">Audit Mission</h2>
                    <div className="text-lg font-bold font-mono text-text-primary">EU AI Act · Article 12 Verification</div>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-black font-mono text-cyber-lime">{Math.round(progressPct)}%</span>
                  </div>
                </div>
                <div className="h-1 bg-abyssal-600 relative overflow-hidden">
                  <motion.div 
                    className="absolute inset-y-0 left-0 bg-cyber-lime shadow-[0_0_10px_rgba(204,255,0,0.5)]"
                    initial={{ width: 0 }}
                    animate={{ width: `${progressPct}%` }}
                    transition={{ duration: 0.5, ease }}
                  />
                </div>
              </div>

              {/* Card */}
              <div className="glass-strong p-10 md:p-16 relative overflow-hidden">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentIdx}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.4, ease }}
                  >
                    <div className="flex items-center gap-4 mb-8">
                      <div className="w-12 h-12 glass border border-cyber-lime/20 flex items-center justify-center text-cyber-lime">
                        {QUESTIONS[currentIdx].icon}
                      </div>
                      <div>
                        <div className="text-[10px] font-mono font-bold tracking-widest text-cyber-lime uppercase">Dimension {currentIdx + 1} / {QUESTIONS.length}</div>
                        <div className="text-xl font-bold tracking-tight">{QUESTIONS[currentIdx].dimension}</div>
                      </div>
                      <div className="ml-auto glass px-3 py-1 text-[10px] font-mono font-bold border border-white/5 text-text-tertiary">
                        {QUESTIONS[currentIdx].euArticle}
                      </div>
                    </div>

                    <h3 className="text-2xl md:text-3xl font-black tracking-tight mb-4 leading-tight">
                      {QUESTIONS[currentIdx].text}
                    </h3>
                    
                    <p className="text-text-secondary mb-12 leading-relaxed border-l-2 border-white/5 pl-6 italic text-sm">
                      {QUESTIONS[currentIdx].hint}
                    </p>

                    <div className="space-y-4 mb-16">
                      {QUESTIONS[currentIdx].options.map((opt, i) => (
                        <button
                          key={i}
                          onClick={() => selectOption(i)}
                          className={`w-full text-left p-6 transition-all duration-300 border flex items-center gap-6 group ${
                            answers[currentIdx] === i 
                              ? 'bg-cyber-lime/10 border-cyber-lime ring-1 ring-cyber-lime/30' 
                              : 'bg-white/[0.02] border-white/5 hover:border-white/20 hover:bg-white/[0.04]'
                          }`}
                        >
                          <div className={`w-6 h-6 rounded-none border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                            answers[currentIdx] === i ? 'bg-cyber-lime border-cyber-lime' : 'border-white/10 group-hover:border-white/20'
                          }`}>
                            {answers[currentIdx] === i && <CheckCircle2 className="w-4 h-4 text-black" />}
                          </div>
                          <div className="flex-1">
                            <div className={`font-bold transition-colors ${answers[currentIdx] === i ? 'text-cyber-lime' : 'text-text-primary'}`}>
                              {opt.label}
                            </div>
                            <div className="text-xs text-text-tertiary mt-1 font-mono tracking-tight uppercase">
                              {opt.hint}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>

                    <div className="flex justify-between items-center">
                      <button
                        onClick={prevQ}
                        disabled={currentIdx === 0}
                        className="text-text-tertiary hover:text-white disabled:opacity-0 transition-all font-mono text-xs uppercase tracking-widest flex items-center gap-2"
                      >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                      </button>
                      <button
                        onClick={nextQ}
                        disabled={answers[currentIdx] === null}
                        className="bg-white text-black px-8 py-4 font-black text-xs uppercase tracking-widest hover:bg-cyber-lime transition-all duration-300 disabled:opacity-20 disabled:hover:bg-white"
                      >
                        {currentIdx === QUESTIONS.length - 1 ? 'Analyze Results' : 'Next Dimension'}
                        <ArrowRight className="inline-block ml-3 w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                </AnimatePresence>
              </div>
            </motion.div>
          )}

          {stage === 'processing' && (
            <motion.div
              key="processing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center py-20"
            >
              <div className="relative w-24 h-24 mx-auto mb-12">
                <div className="absolute inset-0 border-2 border-cyber-lime/20 rounded-none animate-ping" />
                <div className="absolute inset-0 border-4 border-cyber-lime border-t-transparent animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center text-cyber-lime">
                  <Terminal className="w-8 h-8" />
                </div>
              </div>
              <h2 className="text-3xl font-black tracking-tight mb-4">Neural Compliance Analysis</h2>
              <div className="font-mono text-xs text-text-tertiary uppercase tracking-[0.3em] space-y-2">
                <div className="animate-pulse">Mapping persistence topology...</div>
                <div className="animate-pulse delay-700">Evaluating Article 12 gap vectors...</div>
                <div className="animate-pulse delay-1000">Synthesizing sovereign risk report...</div>
              </div>
            </motion.div>
          )}

          {stage === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-8"
            >
              {/* Score Tile */}
              <div className="grid md:grid-cols-2 gap-8">
                <div className="glass-strong p-12 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                  <div className="absolute inset-0 bg-gradient-to-br from-cyber-lime/[0.02] to-transparent pointer-events-none" />
                  <div className="text-xs font-mono font-black tracking-[0.4em] text-text-tertiary uppercase mb-8">Sovereign Score</div>
                  <div className="relative">
                    <svg className="w-48 h-48 -rotate-90">
                      <circle cx="96" cy="96" r="88" className="fill-none stroke-white/5 stroke-[12]" />
                      <motion.circle 
                        cx="96" 
                        cy="96" 
                        r="88" 
                        className={`fill-none ${scoreData.verdict.color.replace('text-', 'stroke-')} stroke-[12]`}
                        strokeDasharray={2 * Math.PI * 88}
                        initial={{ strokeDashoffset: 2 * Math.PI * 88 }}
                        animate={{ strokeDashoffset: 2 * Math.PI * 88 * (1 - scoreData.percentage / 100) }}
                        transition={{ duration: 2, ease }}
                        strokeLinecap="square"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center flex-col">
                      <span className={`text-6xl font-black font-mono tracking-tighter ${scoreData.verdict.color}`}>
                        {scoreData.percentage}
                      </span>
                      <span className="text-[10px] text-text-tertiary font-mono font-black uppercase tracking-widest mt-1">PERCENT</span>
                    </div>
                  </div>
                  <div className={`mt-8 px-6 py-2 border ${scoreData.verdict.border} ${scoreData.verdict.bg} ${scoreData.verdict.color} font-mono text-[10px] font-black uppercase tracking-[0.2em]`}>
                    {scoreData.verdict.label}
                  </div>
                </div>

                <div className={`p-12 border ${scoreData.verdict.border} bg-gradient-to-br from-abyssal-900 to-red-500/5 flex flex-col justify-center`}>
                  <div className="text-xs font-mono font-black tracking-[0.3em] text-red-500 uppercase mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    Penalty Risk Exposure
                  </div>
                  <div className="text-5xl font-black font-mono text-red-500 tracking-tighter mb-4 leading-none">
                    {scoreData.verdict.penalty}
                  </div>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    Based on Article 12 compliance gaps detected in your memory architecture. Enforcement begins <strong className="text-white">August 2026</strong>.
                  </p>
                  <div className="mt-8 flex items-center gap-3 text-[10px] font-mono font-bold text-text-tertiary uppercase tracking-widest">
                    <Clock className="w-4 h-4" />
                    {Math.max(0, Math.ceil((new Date('2026-08-01').getTime() - new Date().getTime()) / (1000*60*60*24*30)))} Months Remaining
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              <div className="glass-strong p-10">
                <h3 className="text-xs font-mono font-black tracking-[0.3em] text-text-tertiary uppercase mb-8">Engineering Remediation</h3>
                <div className="space-y-6">
                  {QUESTIONS.map((q, i) => {
                    const ansIdx = answers[i] || 0;
                    const score = q.options[ansIdx].score;
                    if (score === 3) return null;

                    return (
                      <div key={i} className="group border-l-2 border-red-500/20 pl-6 py-2 hover:border-red-500/50 transition-all duration-500">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-red-500"><AlertTriangle className="w-4 h-4" /></span>
                          <span className="text-sm font-bold tracking-tight">{q.dimension}</span>
                          <span className="text-[10px] font-mono text-text-tertiary bg-white/5 px-2 py-0.5">{q.euArticle}</span>
                        </div>
                        <p className="text-xs text-text-secondary leading-relaxed mb-4">
                          Current implementation: <span className="text-white/80 italic">"{q.options[ansIdx].label}"</span>. This creates a critical audit gap under {q.euArticle}.
                        </p>
                        <div className="bg-cyber-lime/[0.03] border border-cyber-lime/10 p-4 relative group-hover:border-cyber-lime/30 transition-all duration-500">
                          <div className="text-[10px] font-mono font-black text-cyber-lime uppercase tracking-widest mb-1 flex items-center gap-2">
                            <Zap className="w-3 h-3" /> CORTEX Patch Available
                          </div>
                          <div className="text-xs text-text-primary leading-relaxed">
                            CORTEX's {q.dimension === "Tamper-Proof Storage" ? 'SHA-256 Ledger' : q.dimension === "Automatic Logging" ? 'Hook Ingress' : 'B-WFT Consensus'} closes this gap with zero custom code.
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Lead Capture */}
              <div className="glass-strong p-12 md:p-16 text-center border-t-4 border-cyber-lime">
                {!submitted ? (
                  <>
                    <h3 className="text-3xl font-black tracking-tight mb-4">Fix Your Compliance in 72 Hours</h3>
                    <p className="text-text-secondary mb-12 max-w-xl mx-auto">
                      Enter your address to receive the <strong className="text-white italic">"Sovereign Memory Architecture"</strong> PDF report + the engineering playbook to reach 100% Article 12 compliance.
                    </p>
                    <div className="flex flex-col md:flex-row gap-4 max-w-md mx-auto">
                      <input 
                        type="email" 
                        placeholder="cto@company.com" 
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="flex-1 bg-abyssal-600 border border-white/5 px-6 py-4 font-mono text-sm outline-none focus:border-cyber-lime transition-colors"
                      />
                      <button 
                        onClick={() => setSubmitted(true)}
                        className="bg-cyber-lime text-black px-8 py-4 font-black text-xs uppercase tracking-widest hover:shadow-[0_0_30px_rgba(204,255,0,0.3)] transition-all"
                      >
                        Claim Report
                      </button>
                    </div>
                  </>
                ) : (
                  <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
                    <div className="w-16 h-16 bg-cyber-lime text-black mx-auto mb-6 flex items-center justify-center">
                      <CheckCircle2 className="w-8 h-8" />
                    </div>
                    <h3 className="text-2xl font-black mb-2">Check Your Inbox</h3>
                    <p className="text-text-secondary">Your sovereign compliance playbook is on the way.</p>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="max-w-4xl mx-auto px-6 py-20 text-center border-t border-white/5 opacity-50">
        <div className="text-[10px] font-mono uppercase tracking-[0.4em] mb-4">
          © 2026 CORTEX AI · Sovereign Memory Layer
        </div>
        <div className="flex justify-center gap-8 text-[10px] font-mono uppercase tracking-widest">
          <Link to="/" className="hover:text-cyber-lime transition-colors">Home</Link>
          <a href="#" className="hover:text-cyber-lime transition-colors">Privacy</a>
          <a href="#" className="hover:text-cyber-lime transition-colors">Security</a>
        </div>
      </footer>
    </div>
  );
}
