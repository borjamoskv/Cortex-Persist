globalThis.process ??= {};
globalThis.process.env ??= {};
import { c as createComponent } from "./astro-component_DEaCX7dm.mjs";
import { n as renderComponent, h as renderTemplate, m as maybeRenderHead } from "./worker-entry_DFUcbWB_.mjs";
import { r as renderScript } from "./script_CjiNhLUW.mjs";
import { $ as $$SiteLayout } from "./SiteLayout_DduZsl0t.mjs";
const $$Demo = createComponent(async ($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "SiteLayout", $$SiteLayout, { "title": "CORTEX Persist | Causal Persistence Demo", "description": "CORTEX-PERSIST DEMO v0. Causal persistence, hash-chain auditing, and recursive origin recovery.", "canonical": "https://cortexpersist.com/demo", "bodyClass": "demo-body" }, { "default": async ($$result2) => renderTemplate` ${maybeRenderHead()}<div id="demo-stage"> <header class="demo-topbar surface"> <div class="demo-brand"> <a class="brand" href="/" aria-label="Return to landing"> <span class="brand-mark">CP</span> <span class="brand-copy"> <strong>CORTEX Persist</strong> <span>Causal Persistence Ledger / Demo v0</span> </span> </a> </div> <div class="demo-heading"> <p class="eyebrow">DEMO ORCHESTRATOR</p> <h1>Sovereign Memory & Provenance</h1> </div> <div class="demo-actions"> <div class="status-badge" id="conn-status" data-mode="standby" role="status">
STANDBY
</div> <button class="button-primary compact" id="btn-toggle-mode">
SWITCH TO LIVE
</button> </div> </header> <main class="demo-grid"> <!-- CORTEX Auditor Status Card --> <section class="demo-panel"> <article class="surface auditor-card"> <div class="surface-head"> <span class="surface-label">CRYPTOGRAPHIC INTEGRITY MONITOR</span> <span class="surface-state" id="integrity-badge">SECURE</span> </div> <div class="auditor-box"> <div class="terminal-border-top">┌───────────────────────────┐</div> <div class="terminal-line">│ <span class="terminal-title">CORTEX AUDITOR</span> │</div> <div class="terminal-border-mid">├───────────────────────────┤</div> <div class="terminal-line">│ Events      : <span class="terminal-val" id="val-events">0</span> │</div> <div class="terminal-line">│ Integrity   : <span class="terminal-val" id="val-integrity">WAITING</span> │</div> <div class="terminal-line">│ Restarts    : <span class="terminal-val" id="val-restarts">0</span> │</div> <div class="terminal-line">│ Corruption  : <span class="terminal-val" id="val-corruption">0</span> │</div> <div class="terminal-line">│ Root Causes : <span class="terminal-val" id="val-root">100%</span> │</div> <div class="terminal-border-bottom">└───────────────────────────┘</div> </div> <p class="card-desc">
This panel runs continuous SHA-256 validation over the event ledger. Tampering with any historical block propagates a chain breach.
</p> </article> <!-- Controls --> <article class="surface operations-card"> <div class="surface-head"> <span class="surface-label">OPERATIONS CENTER</span> <span class="surface-state">READY</span> </div> <div class="ops-buttons"> <button class="button-primary" id="btn-init">
1. INGEST 10,000 EVENTS
</button> <button class="button-secondary btn-risk" id="btn-tamper">
2. TAMPER EVENT 9834
</button> <button class="button-secondary" id="btn-audit">
3. RUN CRYPTOGRAPHIC AUDIT
</button> <button class="button-tertiary" id="btn-repair">
4. REPAIR HASH CHAIN
</button> </div> </article> </section> <!-- Causal Chain Visualizer --> <section class="demo-panel"> <article class="surface visualizer-card"> <div class="surface-head"> <span class="surface-label">CAUSAL TRACE VISUALIZER</span> <span class="surface-state">ACTIVE</span> </div> <div class="visualizer-content"> <div class="query-prompt"> <p>Query Causal Origin of Event 9834:</p> <button class="button-primary compact" id="btn-query-causal">
Run WITH RECURSIVE Causal Query
</button> </div> <div class="causal-chain-display" id="causal-chain-display"> <div class="empty-state">No causal query executed yet. Click above to trace history.</div> </div> </div> </article> </section> <!-- Terminal / Log Log --> <section class="demo-panel full-width"> <article class="surface console-card"> <div class="surface-head"> <span class="surface-label">LEDGER TELEMETRY TERMINAL</span> <span class="surface-state">RAW</span> </div> <div class="console-body" id="console-body"> <div class="console-row">[SYSTEM] Offline demonstration mode active. Click 'SWITCH TO LIVE' to interface with the local C5-REAL server on port 8000.</div> </div> </article> </section> </main> </div> ${renderScript($$result2, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/demo.astro?astro&type=script&index=0&lang.ts")} ` })}`;
}, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/demo.astro", void 0);
const $$file = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/demo.astro";
const $$url = "/demo";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$Demo,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
