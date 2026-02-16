import { useEffect, useState } from 'react';
import { Shield, Brain, Activity, Database, Zap } from 'lucide-react';
import { searchFacts, fetchGraphData } from '../api/client';
import type { Fact, GraphData } from '../api/client';
import NeuralHive from '../components/NeuralHive';

export function CodexView() {
  const [viewMode, setViewMode] = useState<'codex' | 'hive'>('codex');
  
  // Codex Data
  const [axioms, setAxioms] = useState<Fact[]>([]);
  const [ontology, setOntology] = useState<Fact[]>([]);
  
  // Hive Data
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initNeuralLink = async () => {
      try {
        setLoading(true);
        // Phase 1: Fetch Core Axioms & Ontology
        const [axiomData, schemaData] = await Promise.all([
            searchFacts('Prime Directives', 'cortex', 20),
            searchFacts('Ontology', 'cortex', 20)
        ]);

        // Filter and ensure unique entries
        const axiomSet = axiomData.filter((f) => f.fact_type === 'axiom' || f.tags.includes('prime-directive'));
        const ontologySet = schemaData.filter((f) => f.fact_type === 'schema' || f.tags.includes('ontology') || f.tags.includes('taxonomy'));
        
        setAxioms(axiomSet);
        setOntology(ontologySet);

        // Phase 2: Pre-fetch Graph Data (Silent)
        fetchGraphData().then(setGraphData).catch(err => console.warn("Graph pre-fetch failed:", err));

      } catch (e) {
        console.error("Failed to fetch Codex:", e);
        setError("Neural Link Offline. Check Connection.");
      } finally {
        setLoading(false);
      }
    };

    initNeuralLink();
  }, []);

  if (loading) return (
    <div className="min-h-screen bg-[#020202] flex flex-col items-center justify-center font-mono">
        <div className="w-12 h-12 border-t-2 border-[#00dcb4] rounded-full animate-spin mb-4" />
        <div className="text-[#00dcb4] animate-pulse uppercase tracking-[0.3em] text-xs">Initializing Neural Link...</div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-[#020202] flex items-center justify-center p-8">
        <div className="max-w-md w-full border border-red-500/30 bg-red-950/10 p-6 rounded-lg backdrop-blur-xl">
            <h2 className="text-red-500 font-mono mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" /> SYSTEM_ERROR
            </h2>
            <p className="text-red-400/80 font-mono text-xs leading-relaxed">{error}</p>
        </div>
    </div>
  );

  return (
    <div className="relative bg-[#020202] min-h-screen text-slate-200 font-sans selection:bg-[#00dcb4]/30 overflow-hidden">
        
        {/* Cyber Overlay: Scanlines */}
        <div className="fixed inset-0 pointer-events-none z-50 opacity-[0.03] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,0,0.06))] bg-[length:100%_2px,3px_100%]" />
        
        {/* HEADER & CONTROLS */}
        <header className="fixed top-0 left-0 w-full z-20 p-8 border-b border-white/5 bg-black/40 backdrop-blur-xl flex justify-between items-center transition-all duration-500">
            <div className="group cursor-default">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-1 bg-gradient-to-r from-[#00dcb4] to-transparent" />
                    <h1 className="text-3xl font-bold tracking-tighter text-white group-hover:text-[#00dcb4] transition-colors duration-500">
                        CORTEX <span className="font-light opacity-50 text-xs tracking-[0.5em] ml-2">VERSION 4.0</span>
                    </h1>
                </div>
                <p className="text-white/20 mt-1 text-xs font-mono uppercase tracking-widest pl-11">Sovereign Neural Memory</p>
            </div>
            
            {/* VIEW TOGGLE */}
            <div className="flex bg-white/5 p-1 rounded-sm border border-white/10 shadow-2xl">
                <button 
                    onClick={() => setViewMode('codex')}
                    className={`px-6 py-2 rounded-sm flex items-center gap-2 transition-all duration-300 ${viewMode === 'codex' ? 'bg-[#00dcb4] text-black font-bold shadow-[0_0_20px_rgba(0,220,180,0.4)]' : 'text-white/40 hover:text-white/80'}`}
                >
                    <Database className="w-4 h-4" />
                    <span className="text-[10px] font-mono tracking-[0.2em] uppercase">Codex</span>
                </button>
                <button 
                    onClick={() => setViewMode('hive')}
                    className={`px-6 py-2 rounded-sm flex items-center gap-2 transition-all duration-300 ${viewMode === 'hive' ? 'bg-[#7d5fff] text-white font-bold shadow-[0_0_20px_rgba(125,95,255,0.4)]' : 'text-white/40 hover:text-white/80'}`}
                >
                    <Activity className="w-4 h-4" />
                    <span className="text-[10px] font-mono tracking-[0.2em] uppercase">Neural Hive</span>
                </button>
            </div>
        </header>

        {/* MAIN CONTENT AREA */}
        <main className="pt-32 p-8 h-screen box-border overflow-y-auto no-scrollbar">
            
            {viewMode === 'codex' ? (
                // --- CODEX VIEW ---
                <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 mt-12 animate-in fade-in slide-in-from-bottom-8 duration-700">
                    {/* PRIME DIRECTIVES */}
                    <section className="space-y-8">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 bg-[#00dcb4]/10 rounded-xl border border-[#00dcb4]/20">
                                <Shield className="w-6 h-6 text-[#00dcb4]" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold tracking-tight text-white uppercase">Prime Directives</h2>
                                <div className="h-0.5 w-12 bg-[#00dcb4] mt-1" />
                            </div>
                        </div>
                        
                        <div className="space-y-6">
                            {axioms.length === 0 && <div className="text-white/20 italic font-mono text-xs">No Prime Directives registered.</div>}
                            {axioms.map(fact => (
                                <div key={fact.id} className="relative p-8 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-[#00dcb4]/30 transition-all duration-500 group overflow-hidden">
                                    <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-20 transition-opacity">
                                        <Shield className="w-24 h-24 text-[#00dcb4]" />
                                    </div>
                                    <pre className="relative z-10 whitespace-pre-wrap font-sans text-sm text-slate-400 leading-relaxed group-hover:text-white transition-colors">
                                        {fact.content}
                                    </pre>
                                    <div className="mt-6 flex items-center justify-between">
                                        <div className="flex gap-2">
                                            <span className="px-3 py-1 text-[9px] font-bold rounded-full bg-[#00dcb4]/10 text-[#00dcb4] border border-[#00dcb4]/20 tracking-tighter uppercase font-mono">Directive</span>
                                            <span className="px-3 py-1 text-[9px] font-bold rounded-full bg-white/5 text-white/30 border border-white/5 tracking-tighter uppercase font-mono">ID::{fact.id}</span>
                                        </div>
                                        <span className="text-[10px] text-white/10 font-mono uppercase group-hover:text-[#00dcb4]/40 transition-colors">
                                            {fact.project}::PROT_LVL_0
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* ONTOLOGY & TAXONOMY */}
                    <section className="space-y-8">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 bg-[#7d5fff]/10 rounded-xl border border-[#7d5fff]/20">
                                <Brain className="w-6 h-6 text-[#7d5fff]" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold tracking-tight text-white uppercase">Sovereign Ontology</h2>
                                <div className="h-0.5 w-12 bg-[#7d5fff] mt-1" />
                            </div>
                        </div>

                        <div className="space-y-6">
                            {ontology.length === 0 && <div className="text-white/20 italic font-mono text-xs">Knowledge graph is building...</div>}
                            {ontology.map(fact => (
                                <div key={fact.id} className="relative p-8 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-[#7d5fff]/30 transition-all duration-500 group overflow-hidden">
                                     <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-20 transition-opacity">
                                        <Brain className="w-24 h-24 text-[#7d5fff]" />
                                    </div>
                                    <pre className="relative z-10 whitespace-pre-wrap font-sans text-sm text-slate-400 leading-relaxed group-hover:text-white transition-colors">
                                        {fact.content}
                                    </pre>
                                    <div className="mt-6 flex items-center justify-between">
                                        <div className="flex gap-2">
                                            <span className="px-3 py-1 text-[9px] font-bold rounded-full bg-[#7d5fff]/10 text-[#7d5fff] border border-[#7d5fff]/20 tracking-tighter uppercase font-mono">Ontology</span>
                                            <span className="px-3 py-1 text-[9px] font-bold rounded-full bg-white/5 text-white/30 border border-white/5 tracking-tighter uppercase font-mono">ID::{fact.id}</span>
                                        </div>
                                        <span className="text-[10px] text-white/10 font-mono uppercase group-hover:text-[#7d5fff]/40 transition-colors">
                                            SYST_MAP_ACTIVE
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>
            ) : (
                // --- NEURAL HIVE VIEW ---
                <div className="absolute inset-0 top-0 pt-0 z-0 h-full w-full animate-in fade-in zoom-in-95 duration-1000">
                    {graphData ? (
                        <NeuralHive 
                            data={graphData} 
                            onNodeSelect={(node) => console.log("Selected:", node)} 
                        />
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full gap-4">
                            <div className="text-[#7d5fff] animate-pulse font-mono text-xs uppercase tracking-[0.4em]">
                                Synchronizing Neural Hive Synapses
                            </div>
                            <div className="w-48 h-1 bg-white/5 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-transparent via-[#7d5fff] to-transparent animate-shimmer" />
                            </div>
                        </div>
                    )}
                </div>
            )}
        </main>
    </div>
  );
}
