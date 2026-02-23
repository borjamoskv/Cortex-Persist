"use client";

import { useState } from "react";

export default function OmniTranslateLanding() {
  const [inputText, setInputText] = useState("");
  const [outputResult, setOutputResult] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [languages] = useState(["es", "fr"]);
  const [isRedirecting, setIsRedirecting] = useState(false);

  const handleSubscribe = async () => {
    setIsRedirecting(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/v1/stripe/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: "pro" }) // Defaults to Pro plan
      });
      const data = await response.json();
      if (data.url) {
        globalThis.location.href = data.url;
      } else {
        throw new Error("No URL returned");
      }
    } catch (e) {
      alert("Billing connection failed. Ensure CORTEX backend and Stripe keys are active.");
      setIsRedirecting(false);
    }
  };

  const handleTranslate = async () => {
    if (!inputText) return;
    
    setIsLoading(true);
    try {
      // Mocking the text to a key-value format for the API
      const texts = { "raw": inputText };
      
      const response = await fetch("http://127.0.0.1:8000/v1/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          texts,
          target_languages: languages
        })
      });

      if (!response.ok) throw new Error("Translation failed");
      
      const data = await response.json();
      setOutputResult(JSON.stringify(data.translations, null, 2));
    } catch (error: any) {
      setOutputResult(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[var(--color-noir-900)] text-[var(--color-text-primary)] font-sans relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-[var(--color-accent-yinmn)] opacity-20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[40%] bg-[var(--color-accent-violet)] opacity-10 blur-[100px] rounded-full pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6 py-24 relative z-10 flex flex-col lg:flex-row gap-16 items-center">
        
        {/* Left: Copy & Value Prop */}
        <div className="flex-1 space-y-8">
          <div className="inline-block px-3 py-1 text-xs font-mono tracking-widest text-[var(--color-accent-lime)] border border-[var(--color-accent-lime)] rounded-full mb-4 opacity-80 uppercase">
            Sovereign B2B API
          </div>
          <h1 className="text-5xl lg:text-7xl font-bold tracking-tight leading-[1.1]">
            Localize<br/>
            <span className="text-glow-lime text-[var(--color-accent-lime)]">With Intent.</span>
          </h1>
          <p className="text-xl text-[var(--color-text-secondary)] max-w-lg leading-relaxed">
            OMNI-TRANSLATE is the API layer for scaling global SaaS. Send your JSON structured data, receive culturally-aware translations in 50+ languages in milliseconds.
          </p>
          
          <div className="flex gap-4 pt-4">
            <button 
              onClick={handleSubscribe}
              disabled={isRedirecting}
              className="px-8 py-4 bg-[var(--color-text-primary)] text-[var(--color-noir-900)] font-semibold rounded-md hover:scale-105 transition-transform disabled:opacity-50"
            >
              {isRedirecting ? "Connecting..." : "Start Building"}
            </button>
            <button className="px-8 py-4 glass-panel text-[var(--color-text-primary)] font-semibold rounded-md hover:bg-[rgba(255,255,255,0.05)] transition-colors">
              View Documentation
            </button>
          </div>
        </div>

        {/* Right: Interactive Demo */}
        <div className="flex-1 w-full max-w-lg">
          <div className="glass-panel rounded-2xl p-8 flex flex-col gap-6 relative shadow-2xl shadow-black/50">
            
            <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.1)] pb-4">
              <h3 className="font-mono text-sm tracking-widest uppercase text-[var(--color-text-secondary)]">Terminal Demo</h3>
              <div className="flex gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500/50" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                <div className="w-3 h-3 rounded-full bg-green-500/50" />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="translateInput" className="text-xs font-mono text-[var(--color-accent-lime)] uppercase">Input (JSON payload)</label>
              <textarea 
                id="translateInput"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Enter string to translate..."
                className="w-full bg-[rgba(0,0,0,0.5)] border border-[rgba(255,255,255,0.1)] rounded-lg p-4 font-mono text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent-lime)] transition-colors resize-none h-32"
              />
            </div>

            <button 
              onClick={handleTranslate}
              disabled={isLoading}
              className="w-full py-3 bg-[var(--color-accent-violet)] text-white font-mono uppercase tracking-widest text-sm rounded-lg hover:bg-opacity-80 transition-all disabled:opacity-50"
            >
              {isLoading ? 'Translating...' : 'Execute Translation ->'}
            </button>

            <div className="space-y-2">
              <label htmlFor="translateOutput" className="text-xs font-mono text-[var(--color-accent-violet)] uppercase">CORTEX Output</label>
              <div id="translateOutput" className="w-full bg-[rgba(0,0,0,0.5)] border border-[rgba(255,255,255,0.1)] rounded-lg p-4 h-48 overflow-auto">
                {outputResult ? (
                  <pre className="font-mono text-sm text-gray-300 whitespace-pre-wrap">{outputResult}</pre>
                ) : (
                  <span className="text-gray-600 font-mono text-sm">Waiting for payload...</span>
                )}
              </div>
            </div>

          </div>
        </div>

      </div>
    </main>
  );
}
