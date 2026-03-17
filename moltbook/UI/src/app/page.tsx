"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const SovereignSplineInterface = dynamic(() => import("./SplineSovereign"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-screen bg-[#0A0A0A] flex items-center justify-center">
      <div className="w-12 h-12 border-t-2 border-[#CCFF00] rounded-full animate-spin" />
    </div>
  ),
});

const CortexNotebook = dynamic(() => import("./CortexNotebook"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-screen bg-[#0A0A0A] flex items-center justify-center">
      <div className="w-12 h-12 border-t-2 border-[#CCFF00] rounded-full animate-spin" />
    </div>
  ),
});

type View = "SPLINE" | "NOTEBOOK";

export default function Home() {
  const [view, setView] = useState<View>("NOTEBOOK");

  return (
    <main className="min-h-screen bg-[#0A0A0A] relative">
      {/* Tab Navigation */}
      <nav className="fixed top-0 right-0 z-50 flex gap-1 p-3">
        {(["NOTEBOOK", "SPLINE"] as View[]).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`text-[9px] font-mono tracking-[0.2em] px-4 py-2 rounded-md transition-all duration-200 backdrop-blur-md ${
              view === v
                ? "bg-[#CCFF00]/15 text-[#CCFF00] border border-[#CCFF00]/30 shadow-[0_0_12px_rgba(204,255,0,0.08)]"
                : "bg-black/40 text-white/30 border border-white/[0.06] hover:text-white/50 hover:border-white/15"
            }`}
          >
            {v}
          </button>
        ))}
      </nav>

      {/* Views */}
      {view === "SPLINE" && <SovereignSplineInterface />}
      {view === "NOTEBOOK" && <CortexNotebook />}
    </main>
  );
}
