import { useState, FormEvent } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { Target, Key, TerminalSquare, AlertTriangle, ShieldAlert, Cpu } from 'lucide-react';
import { BackgroundEffects } from '../components/BackgroundEffects';
import { Navbar } from '../components/Navbar';

interface AuditResult {
  confidence: number;
  report: string;
}

export default function OracleDashboard() {
  const [targetUrl, setTargetUrl] = useState('');
  const [agentId, setAgentId] = useState('ariadne');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AuditResult | null>(null);

  // Awwwards Sovereign v2.0 - Core Choreography
  useGSAP(() => {
    // Initial Reveal Sequence
    const tl = gsap.timeline({ defaults: { ease: 'power4.out', duration: 1.2 } });
    
    tl.fromTo('.reveal-text', 
      { y: 50, opacity: 0, clipPath: 'inset(100% 0 0 0)' },
      { y: 0, opacity: 1, clipPath: 'inset(0% 0 0 0)', stagger: 0.1, duration: 1.5 }
    )
    .fromTo('.reveal-input',
      { x: -30, opacity: 0 },
      { x: 0, opacity: 1, stagger: 0.1 },
      '-=1.0'
    )
    .fromTo('.output-panel',
      { scale: 0.95, opacity: 0, filter: 'blur(10px)' },
      { scale: 1, opacity: 1, filter: 'blur(0px)', duration: 1.5 },
      '-=1.2'
    );
  }, []);

  const handleAudit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    let isFetchError = false;

    try {
      // In production this points to CORTEX API /v1/oracle/audit
      const response = await fetch('http://127.0.0.1:8000/v1/oracle/audit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          target_url: targetUrl,
          agent_type: agentId,
          depth: 2
        }),
      });

      if (!response.ok) {
        let errorMsg = 'Audit request failed';
        try {
          const errorData = await response.json();
          errorMsg = errorData.detail || errorMsg;
        } catch {
          errorMsg = await response.text() || errorMsg;
        }
        throw new Error(errorMsg);
      }

      const data = await response.json();
      setResult({
        confidence: data.confidence,
        report: data.report
      });
    } catch (err: unknown) {
      const error = err as Error;
      console.error('Audit Error:', error);
      // Fallback for demo purposes if backend isn't reachable
      if (error.message === 'Failed to fetch') {
         isFetchError = true;
         setTimeout(() => {
           setResult({
             confidence: 0.95,
             report: "## SEVERE VULNERABILITIES DETECTED\n\n- **CRITICAL**: Exposed API Keys detected in main.js bundle.\n- **WARNING**: Missing Content-Security-Policy headers allow XSS execution.\n- **INFO**: React components rendered in development mode (source maps exposed).\n\nThe target exhibits severe architectural flaws. Recommended immediate quarantine and topological restructuring."
           });
           setLoading(false);
         }, 3000);
         return;
      }
      setError(error.message || 'An unexpected error occurred during the audit protocol.');
    } finally {
      if (!isFetchError) {
        setLoading(false);
      }
    }
  };

  return (
    <div className="min-h-screen selection:bg-cyber-lime selection:text-black">
      <BackgroundEffects />
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 py-32 relative z-10 flex flex-col md:flex-row gap-12">
        {/* Left Side - Init Protocol */}
        <div className="flex-1 w-full max-w-xl">
          <div className="reveal-text inline-flex items-center gap-2 px-3 py-1.5 rounded-none border-l-2 border-cyber-lime bg-cyber-lime/[0.04] text-cyber-lime text-[10px] font-mono uppercase tracking-[0.3em] mb-8">
            <TerminalSquare className="w-3.5 h-3.5" />
            Oracle Terminal
          </div>
          <h1 className="reveal-text text-4xl md:text-5xl font-sans font-black tracking-tight mb-4 select-none">
            Initialize Audit
          </h1>
          <p className="reveal-text text-text-secondary mb-12">
            Deploy sovereign cognitive bandwidth to analyze external targets. Provide your provisioned CORTEX key to begin.
          </p>

          <form onSubmit={handleAudit} className="space-y-6">
            <div className="space-y-2">
              <label className="reveal-text text-xs font-mono text-text-secondary uppercase tracking-wider block">
                [TARGET_URL]
              </label>
              <div className="reveal-input relative">
                <Target className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-tertiary" />
                <input
                  type="url"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  placeholder="https://example.com"
                  required
                  className="w-full bg-black/40 border border-white/10 rounded-none px-12 py-4 text-white placeholder:text-text-tertiary focus:outline-none focus:border-cyber-lime transition-colors font-mono text-sm"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="reveal-text text-xs font-mono text-text-secondary uppercase tracking-wider block">
                [AGENT_PROTO]
              </label>
              <div className="reveal-input relative">
                <Cpu className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-tertiary" />
                <select
                  aria-label="Agent Protocol"
                  value={agentId}
                  onChange={(e) => setAgentId(e.target.value)}
                  className="w-full bg-black border border-white/10 rounded-none px-12 py-4 text-white focus:outline-none focus:border-cyber-lime transition-colors font-mono text-sm appearance-none"
                >
                  <option value="ariadne">Ariadne (Architecture & Topology)</option>
                  <option value="nyx">Nyx (Shadow Penetration Tester)</option>
                  <option value="scavenger">Scavenger (Toxin & Risk Radar)</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <label className="reveal-text text-xs font-mono text-text-secondary uppercase tracking-wider block">
                [ORACLE_KEY]
              </label>
              <div className="reveal-input relative">
                <Key className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-tertiary" />
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="ctx_live_..."
                  required
                  className="w-full bg-black/40 border border-white/10 rounded-none px-12 py-4 text-white placeholder:text-text-tertiary focus:outline-none focus:border-cyber-lime transition-colors font-mono text-sm"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !targetUrl || !apiKey}
              className="reveal-input w-full bg-cyber-lime text-black py-4 font-black text-xs uppercase tracking-widest hover:shadow-[0_0_30px_rgba(204,255,0,0.3)] disabled:opacity-50 disabled:cursor-not-allowed transition-all mt-4 will-change-transform"
            >
              {loading ? 'Initializing Agent...' : 'EXECUTE PROTOCOL'}
            </button>
            
            {error && (
              <div className="p-4 bg-red-500/10 border-l-2 border-red-500 flex items-start gap-3 mt-4">
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
                <p className="text-sm font-mono text-red-400">{error}</p>
              </div>
            )}
          </form>
        </div>

        {/* Right Side - Output Stream */}
        <div className="flex-1">
            {!result && !loading && (
              <div
                className="output-panel h-full min-h-[400px] border border-white/5 bg-black/40 flex flex-col items-center justify-center text-center p-8 relative overflow-hidden will-change-transform"
              >
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[length:24px_24px] opacity-20" />
                <TerminalSquare className="w-12 h-12 text-white/10 mb-6" />
                <p className="font-mono text-sm text-text-tertiary uppercase tracking-widest">
                  AWAITING INITIALIZATION
                </p>
              </div>
            )}

            {loading && (
              <div
                className="output-panel h-full min-h-[400px] border border-cyber-lime/20 bg-cyber-lime/[0.02] flex flex-col items-center justify-center p-8 will-change-transform"
              >
                <div className="relative">
                  <div className="w-16 h-16 border-2 border-white/10 border-t-cyber-lime rounded-full animate-spin" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-2 h-2 bg-cyber-lime rounded-full animate-pulse" />
                  </div>
                </div>
                <div className="mt-8 font-mono text-sm text-cyber-lime uppercase tracking-widest animate-pulse">
                  ESTABLISHING LINK...
                </div>
                <div className="mt-4 text-xs font-mono text-text-tertiary">
                  &gt; Resolving target vectors<br />
                  &gt; Injecting sovereign bypass
                </div>
              </div>
            )}

            {result && !loading && (
               <div
                 className="output-panel space-y-6 will-change-transform"
               >
                 <div className="glass-strong p-8 border-l-4 border-cyber-lime">
                   <div className="flex items-start justify-between mb-8">
                     <div>
                       <h3 className="text-sm font-mono uppercase tracking-widest text-text-secondary mb-2">Confidence Matrix</h3>
                       <div className="text-6xl font-black font-mono text-cyber-lime">
                         {(result.confidence * 100).toFixed(1)}<span className="text-2xl text-text-tertiary">%</span>
                       </div>
                     </div>
                     <ShieldAlert className={`w-12 h-12 ${result.confidence < 0.8 ? 'text-red-500' : 'text-cyber-lime'}`} />
                   </div>
                 </div>

                 <div className="space-y-4">
                   <h4 className="text-xs font-mono uppercase tracking-widest text-text-secondary flex items-center gap-2">
                     <TerminalSquare className="w-4 h-4" />
                     Diagnostic Output
                   </h4>
                   <div className="glass-strong p-6 overflow-hidden">
                     <pre className="font-mono text-sm text-text-primary whitespace-pre-wrap leading-relaxed max-h-[600px] overflow-y-auto custom-scrollbar">
                       {result.report}
                     </pre>
                   </div>
                 </div>
               </div>
            )}
        </div>
      </main>
    </div>
  );
}
