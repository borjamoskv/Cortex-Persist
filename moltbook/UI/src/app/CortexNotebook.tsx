"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ─── Types ──────────────────────────────────────────────────────────

interface SearchFact {
  fact_id: number;
  project: string;
  content: string;
  fact_type: string;
  score: number;
  tags: string[];
  created_at: string;
  updated_at: string;
  hash?: string;
  context?: Record<string, unknown>;
}

interface AskSource {
  fact_id: number;
  content: string;
  score: number;
  project: string;
}

type QueryMode = "SEARCH" | "ASK";

// ─── Fact Type Colors ───────────────────────────────────────────────

const FACT_TYPE_COLORS: Record<string, string> = {
  decision: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  error: "bg-red-500/20 text-red-300 border-red-500/30",
  ghost: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  bridge: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  discovery: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  axiom: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  knowledge: "bg-white/10 text-white/70 border-white/20",
};

function getFactTypeStyle(factType: string): string {
  return FACT_TYPE_COLORS[factType] || FACT_TYPE_COLORS.knowledge;
}

// ─── Score Bar ──────────────────────────────────────────────────────

function ScoreBar({ score }: Readonly<{ score: number }>) {
  const pct = Math.min(100, Math.max(0, score * 100));
  const hue = Math.round(pct * 0.8 + 20); // 20=red → 100=lime
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-1 bg-white/5 rounded overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          style={{ backgroundColor: `hsl(${hue}, 80%, 55%)` }}
          className="h-full rounded"
        />
      </div>
      <span className="text-[10px] font-mono text-white/40 w-10 text-right">
        {score.toFixed(3)}
      </span>
    </div>
  );
}

// ─── Fact Card ───────────────────────────────────────────────────────

function FactCard({ fact, index }: Readonly<{ fact: SearchFact; index: number }>) {
  const [expanded, setExpanded] = useState(false);
  const isLong = fact.content.length > 200;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
      className="bg-white/[0.03] border border-white/[0.06] rounded-lg p-4 hover:border-[#CCFF00]/20 hover:bg-white/[0.05] transition-all duration-300 group"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-[#CCFF00]/50">
            #{fact.fact_id}
          </span>
          <span
            className={`text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border ${getFactTypeStyle(fact.fact_type)}`}
          >
            {fact.fact_type}
          </span>
          <span className="text-[10px] font-mono text-white/30">
            {fact.project}
          </span>
        </div>
        <span className="text-[9px] font-mono text-white/20">
          {new Date(fact.created_at).toLocaleDateString()}
        </span>
      </div>

      {/* Score */}
      <ScoreBar score={fact.score} />

      {/* Content */}
      <div className="mt-3">
        <p className="text-sm text-white/80 leading-relaxed font-mono">
          {expanded || !isLong
            ? fact.content
            : fact.content.slice(0, 200) + "…"}
        </p>
        {isLong && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[10px] text-[#CCFF00]/60 hover:text-[#CCFF00] font-mono mt-1 transition-colors"
          >
            {expanded ? "▲ COLLAPSE" : "▼ EXPAND"}
          </button>
        )}
      </div>

      {/* Tags */}
      {fact.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {fact.tags.map((tag) => (
            <span
              key={tag}
              className="text-[9px] font-mono px-1.5 py-0.5 bg-white/5 text-white/40 rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Hash */}
      {fact.hash && (
        <div className="mt-2 text-[9px] font-mono text-white/15 truncate group-hover:text-white/25 transition-colors">
          ⛓ {fact.hash}
        </div>
      )}
    </motion.div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────

export default function CortexNotebook() {
  // State
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<QueryMode>("SEARCH");
  const [isLoading, setIsLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchFact[]>([]);
  const [askAnswer, setAskAnswer] = useState("");
  const [askSources, setAskSources] = useState<AskSource[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<"online" | "offline" | "unknown">(
    "unknown"
  );
  const [totalTime, setTotalTime] = useState<number | null>(null);

  // Filters
  const [filterProject, setFilterProject] = useState("");
  const [filterK, setFilterK] = useState(10);
  const [filterGraphDepth, setFilterGraphDepth] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Health check on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/cortex/health");
        setApiStatus(res.ok ? "online" : "offline");
      } catch {
        setApiStatus("offline");
      }
    })();
  }, []);

  // Execute search
  const executeSearch = useCallback(async () => {
    if (!query.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);
    setSearchResults([]);
    setAskAnswer("");
    setAskSources([]);
    setTotalTime(null);
    const t0 = performance.now();

    try {
      if (mode === "SEARCH") {
        const res = await fetch("/api/cortex/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query.trim(),
            k: filterK,
            project: filterProject || undefined,
            graph_depth: filterGraphDepth,
            include_graph: filterGraphDepth > 0,
          }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(
            data.detail || `Search failed (${res.status})`
          );
        }

        const facts: SearchFact[] = await res.json();
        setSearchResults(facts);
        setTotalTime(performance.now() - t0);
        setApiStatus("online");
      } else {
        // ASK mode — streaming
        const res = await fetch("/api/cortex/ask/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query.trim(),
            k: filterK,
            project: filterProject || undefined,
            temperature: 0.3,
            max_tokens: 2048,
          }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(
            data.detail || `Ask failed (${res.status})`
          );
        }

        if (!res.body) throw new Error("No stream body");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let answer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") break;

            try {
              const parsed = JSON.parse(payload);
              if (parsed.type === "sources") {
                setAskSources(
                  parsed.data.map((s: { id: number; score: number; project: string }) => ({
                    fact_id: s.id,
                    content: "",
                    score: s.score,
                    project: s.project,
                  }))
                );
              } else if (parsed.type === "token") {
                answer += parsed.data;
                setAskAnswer(answer);
              } else if (parsed.type === "error") {
                throw new Error(parsed.data);
              }
            } catch (e) {
              if (e instanceof SyntaxError) continue;
              throw e;
            }
          }
        }

        setTotalTime(performance.now() - t0);
        setApiStatus("online");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setError(msg);
      if (msg.includes("unreachable") || msg.includes("503")) {
        setApiStatus("offline");
      }
    } finally {
      setIsLoading(false);
    }
  }, [query, mode, filterK, filterProject, filterGraphDepth, isLoading]);

  // Keyboard shortcut
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        executeSearch();
      }
    },
    [executeSearch]
  );

  const hasResults =
    searchResults.length > 0 || askAnswer.length > 0 || askSources.length > 0;

  return (
    <div className="w-full h-screen bg-[#0A0A0A] flex flex-col overflow-hidden font-sans text-white/90 selection:bg-[#CCFF00] selection:text-black">
      {/* ─── Header Bar ──────────────────────────────────────── */}
      <header className="flex-none flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold tracking-tighter">
            CORTEX{" "}
            <span className="text-[#CCFF00] font-light">NOTEBOOK</span>
          </h1>
          <span className="text-[10px] font-mono text-white/25 tracking-wider">
            HYBRID_SEARCH // SOVEREIGN MEMORY
          </span>
        </div>

        <div className="flex items-center gap-4">
          {/* Stats */}
          {totalTime !== null && (
            <span className="text-[10px] font-mono text-white/30">
              {totalTime.toFixed(0)}ms
            </span>
          )}
          {mode === "SEARCH" && searchResults.length > 0 && (
            <span className="text-[10px] font-mono text-[#CCFF00]/50">
              {searchResults.length} facts
            </span>
          )}

          {/* Status */}
          <div className="flex items-center gap-2">
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                apiStatus === "online"
                  ? "bg-[#CCFF00] shadow-[0_0_6px_#ccff00]"
                  : apiStatus === "offline"
                    ? "bg-red-400 shadow-[0_0_6px_#f87171]"
                    : "bg-white/30"
              }`}
            />
            <span className="text-[10px] font-mono text-white/30 uppercase">
              {apiStatus}
            </span>
          </div>
        </div>
      </header>

      {/* ─── Query Bar ───────────────────────────────────────── */}
      <div className="flex-none px-6 py-4 border-b border-white/[0.06]">
        <div className="flex gap-3 items-start">
          {/* Mode Toggle */}
          <div className="flex flex-col gap-1 pt-1">
            {(["SEARCH", "ASK"] as QueryMode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`text-[9px] font-mono tracking-[0.2em] px-3 py-1.5 rounded transition-all duration-200 ${
                  mode === m
                    ? "bg-[#CCFF00]/15 text-[#CCFF00] border border-[#CCFF00]/30"
                    : "text-white/30 border border-transparent hover:text-white/50 hover:border-white/10"
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                mode === "SEARCH"
                  ? "Search CORTEX memory… (hybrid vector + text)"
                  : "Ask CORTEX a question… (RAG synthesis)"
              }
              rows={2}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-lg px-4 py-3 text-sm font-mono text-white/90 placeholder:text-white/20 focus:outline-none focus:border-[#CCFF00]/30 focus:bg-white/[0.05] resize-none transition-all duration-200"
            />
            <div className="absolute bottom-2 right-3 flex items-center gap-2">
              <span className="text-[9px] font-mono text-white/15">
                ⌘+Enter
              </span>
            </div>
          </div>

          {/* Submit + Filters */}
          <div className="flex flex-col gap-1 pt-1">
            <button
              onClick={executeSearch}
              disabled={isLoading || !query.trim()}
              className={`px-5 py-1.5 text-[10px] font-mono tracking-[0.2em] uppercase rounded transition-all duration-200 ${
                isLoading || !query.trim()
                  ? "bg-white/5 text-white/20 cursor-not-allowed"
                  : "bg-[#CCFF00]/10 text-[#CCFF00] border border-[#CCFF00]/30 hover:bg-[#CCFF00]/20"
              }`}
            >
              {isLoading ? "…" : "EXEC"}
            </button>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-5 py-1.5 text-[10px] font-mono tracking-[0.2em] uppercase rounded transition-all duration-200 border ${
                showFilters
                  ? "border-white/20 text-white/50"
                  : "border-transparent text-white/25 hover:text-white/40"
              }`}
            >
              FILTER
            </button>
          </div>
        </div>

        {/* Filter Panel */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="flex gap-6 items-center pt-4 mt-4 border-t border-white/[0.04]">
                {/* Project */}
                <div className="flex items-center gap-2">
                  <label htmlFor="filter-project" className="text-[9px] font-mono text-white/30 uppercase tracking-wider">
                    Project
                  </label>
                  <input
                    id="filter-project"
                    value={filterProject}
                    onChange={(e) => setFilterProject(e.target.value)}
                    placeholder="all"
                    className="w-32 bg-white/[0.03] border border-white/[0.06] rounded px-2 py-1 text-xs font-mono text-white/70 placeholder:text-white/20 focus:outline-none focus:border-[#CCFF00]/20"
                  />
                </div>

                {/* K */}
                <div className="flex items-center gap-2">
                  <label htmlFor="filter-k" className="text-[9px] font-mono text-white/30 uppercase tracking-wider">
                    K
                  </label>
                  <input
                    id="filter-k"
                    type="range"
                    min={1}
                    max={50}
                    value={filterK}
                    onChange={(e) => setFilterK(Number(e.target.value))}
                    className="w-20 accent-[#CCFF00]"
                    aria-label="Number of results"
                  />
                  <span className="text-[10px] font-mono text-white/40 w-6 text-right">
                    {filterK}
                  </span>
                </div>

                {/* Graph Depth (Search only) */}
                {mode === "SEARCH" && (
                  <div className="flex items-center gap-2">
                    <label htmlFor="filter-graph" className="text-[9px] font-mono text-white/30 uppercase tracking-wider">
                      Graph
                    </label>
                    <select
                      id="filter-graph"
                      value={filterGraphDepth}
                      onChange={(e) =>
                        setFilterGraphDepth(Number(e.target.value))
                      }
                      aria-label="Graph depth"
                      className="bg-white/[0.03] border border-white/[0.06] rounded px-2 py-1 text-xs font-mono text-white/70 focus:outline-none focus:border-[#CCFF00]/20"
                    >
                      <option value={0}>OFF</option>
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                      <option value={3}>3</option>
                    </select>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ─── Results ─────────────────────────────────────────── */}
      <div ref={resultsRef} className="flex-1 overflow-y-auto px-6 py-4">
        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg"
            >
              <p className="text-xs font-mono text-red-300">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center gap-3 py-8 justify-center">
            <div className="w-4 h-4 border-t-2 border-[#CCFF00] rounded-full animate-spin" />
            <span className="text-xs font-mono text-white/30 tracking-wider">
              {mode === "SEARCH" ? "EXECUTING HYBRID_SEARCH…" : "SYNTHESIZING…"}
            </span>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !hasResults && !error && (
          <div className="flex flex-col items-center justify-center h-full text-center opacity-40">
            <div className="text-5xl mb-6">⬡</div>
            <p className="text-sm font-mono text-white/30 max-w-md leading-relaxed">
              {mode === "SEARCH"
                ? "Execute a query to search CORTEX memory. hybrid_search combines vector similarity (sqlite-vec) with FTS5 text matching via Reciprocal Rank Fusion."
                : "Ask CORTEX a question. The RAG pipeline searches memory for relevant facts, then synthesizes an answer with the configured LLM."}
            </p>
            <p className="text-[10px] font-mono text-white/15 mt-4">
              ⌘+Enter to execute · {mode === "SEARCH" ? "/v1/search" : "/v1/ask/stream"}
            </p>
          </div>
        )}

        {/* SEARCH Results */}
        {mode === "SEARCH" && searchResults.length > 0 && (
          <div className="grid gap-3">
            {searchResults.map((fact, i) => (
              <FactCard key={fact.fact_id} fact={fact} index={i} />
            ))}
          </div>
        )}

        {/* ASK Results */}
        {mode === "ASK" && (askAnswer || askSources.length > 0) && (
          <div className="space-y-4">
            {/* Answer */}
            {askAnswer && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-white/[0.03] border border-[#CCFF00]/10 rounded-lg p-5"
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#CCFF00] shadow-[0_0_6px_#ccff00]" />
                  <span className="text-[10px] font-mono text-[#CCFF00]/50 uppercase tracking-wider">
                    CORTEX SYNTHESIS
                  </span>
                </div>
                <div className="text-sm text-white/85 leading-relaxed whitespace-pre-wrap font-mono">
                  {askAnswer}
                  {isLoading && (
                    <span className="inline-block w-2 h-4 bg-[#CCFF00]/60 ml-0.5 animate-pulse" />
                  )}
                </div>
              </motion.div>
            )}

            {/* Sources */}
            {askSources.length > 0 && (
              <div>
                <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider mb-2">
                  SOURCES ({askSources.length} facts)
                </p>
                <div className="flex flex-wrap gap-2">
                  {askSources.map((s) => (
                    <div
                      key={s.fact_id}
                      className="flex items-center gap-2 px-3 py-1.5 bg-white/[0.03] border border-white/[0.06] rounded text-[10px] font-mono"
                    >
                      <span className="text-[#CCFF00]/50">
                        #{s.fact_id}
                      </span>
                      <span className="text-white/30">{s.project}</span>
                      <span className="text-white/20">
                        {s.score.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ─── Footer ──────────────────────────────────────────── */}
      <footer className="flex-none flex items-center justify-between px-6 py-2 border-t border-white/[0.04] text-[9px] font-mono text-white/15">
        <span>
          CORTEX NOTEBOOK v5.0 // MoltBook Intelligence //{'  '}
          {mode === "SEARCH" ? "hybrid_search → sqlite-vec + FTS5" : "RAG → hybrid_search + LLM"}
        </span>
        <span>SOVEREIGN MEMORY EXPLORER</span>
      </footer>
    </div>
  );
}
