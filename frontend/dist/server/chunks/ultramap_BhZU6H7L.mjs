globalThis.process ??= {};
globalThis.process.env ??= {};
import { c as createComponent } from "./astro-component_DEaCX7dm.mjs";
import { n as renderComponent, h as renderTemplate, m as maybeRenderHead } from "./worker-entry_DFUcbWB_.mjs";
import { r as renderScript } from "./script_CjiNhLUW.mjs";
import { $ as $$SiteLayout } from "./SiteLayout_DduZsl0t.mjs";
const $$Ultramap = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "SiteLayout", $$SiteLayout, { "title": "CORTEX | Ultramap-Ω Sovereign Visualizer", "description": "Topological memory substrate explorer for the K-0 Swarm. Real-time C5-REAL spatial grid and endocrine telemetry.", "canonical": "https://cortexpersist.com/ultramap", "bodyClass": "ultramap-body" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<div id="ultramap-stage"> <video class="sota-video-bg" src="/assets/ultramap_bg.mp4" autoplay loop muted playsinline></video> <div id="ultramap-canvas-container"></div> <div id="ultramap-overlay"> <header class="ultramap-topbar surface"> <div class="ultramap-brand"> <a class="brand" href="/" aria-label="Return to landing"> <span class="brand-mark">UΩ</span> <span class="brand-copy"> <strong>ULTRAMAP-Ω</strong> <span>K-0 Swarm / lock-free memory mapped</span> </span> </a> </div> <div class="ultramap-heading"> <p class="eyebrow">Topological Substrate Visualizer</p> <h1>Matrix persistance plane</h1> </div> <div class="ultramap-actions"> <div class="status-badge" data-mode="standby" role="status">
STANDBY
</div> <a class="button-tertiary compact" href="/vsa">
VSA Shell
</a> </div> </header> <div class="ultramap-grid"> <!-- Left Panel: Agent Inspector --> <aside class="surface ultramap-inspector"> <div class="surface-head"> <span class="surface-label">Agent Inspector</span> <span class="surface-state" id="inspect-state">No selection</span> </div> <div id="inspector-content"> <div class="empty-inspector-state"> <p>Click on any agent in the 3D space to inspect its topological coordinates, endocrine signals, and exergy metrics.</p> </div> </div> <div class="exergy-calculator-panel hidden" id="exergy-calc"> <span class="surface-label">Exergy calculator</span> <div class="calc-row"> <input type="text" id="target-input" placeholder="TARGET_DARKPOOL_0x1" value="TARGET_DARKPOOL_0x1"> <button id="calc-exergy-btn" class="button-primary compact">Compute</button> </div> <div class="calc-results" id="calc-results"> <!-- Dynamic exergy math --> </div> </div> </aside> <!-- Right Panel: Swarm Overview & Telemetry --> <main class="ultramap-main-panel"> <section class="surface-sunken ultramap-overview"> <div class="surface-head"> <span class="surface-label">Swarm telemetry</span> <span class="surface-copy" id="reality-indicator">C4-SIM (LOCAL)</span> </div> <div class="swarm-stats"> <div class="stat-card"> <span class="stat-label">Active Swarm size</span> <strong id="active-agents-count">8</strong> </div> <div class="stat-card"> <span class="stat-label">System exergy index</span> <strong id="system-exergy-value">92.4%</strong> </div> <div class="stat-card"> <span class="stat-label">Mean entropy</span> <strong id="mean-entropy-value">0.892</strong> </div> <div class="stat-card"> <span class="stat-label">Telemetry latency</span> <strong id="bridge-latency">0ms</strong> </div> </div> </section> <section class="surface-sunken log-panel"> <div class="surface-head"> <span class="surface-label">Signal log stream</span> <span class="surface-copy">Real-time telemetry feeds</span> </div> <div id="log-monitor"> <div class="log-entry"><span class="log-tag">[BOOT]</span> Ultramap-Ω Dashboard mounted successfully.</div> </div> </section> </main> </div> </div> </div> ${renderScript($$result2, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/ultramap.astro?astro&type=script&index=0&lang.ts")} ` })}`;
}, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/ultramap.astro", void 0);
const $$file = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/ultramap.astro";
const $$url = "/ultramap";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$Ultramap,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
