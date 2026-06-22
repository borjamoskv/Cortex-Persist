globalThis.process ??= {};
globalThis.process.env ??= {};
import { c as createComponent } from "./astro-component_DEaCX7dm.mjs";
import { n as renderComponent, h as renderTemplate, m as maybeRenderHead } from "./worker-entry_DFUcbWB_.mjs";
import { r as renderScript } from "./script_CjiNhLUW.mjs";
import { $ as $$SiteLayout } from "./SiteLayout_DduZsl0t.mjs";
const $$Vsa = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "SiteLayout", $$SiteLayout, { "title": "CORTEX Persist | VSA Sovereign Explorer", "description": "Public VSA shell for CORTEX Persist. Deterministic demo by default, localhost live mode on demand.", "canonical": "https://cortexpersist.com/vsa", "bodyClass": "vsa-body" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<div id="vsa-stage"> <div id="vsa-canvas-container"></div> <div id="vsa-overlay"> <header class="vsa-topbar surface"> <div class="vsa-brand"> <a class="brand" href="/" aria-label="Return to landing"> <span class="brand-mark">CP</span> <span class="brand-copy"> <strong>CORTEX Persist</strong> <span>Public shell / 400 dimensions</span> </span> </a> </div> <div class="vsa-heading"> <p class="eyebrow">Sovereign explorer</p> <h1>VSA shell / live only when requested</h1> </div> <div class="vsa-actions"> <div class="status-badge" data-mode="standby" role="status">
STANDBY
</div> <a class="button-secondary compact" href="/ultramap">
Ultramap-Ω
</a> <a class="button-tertiary compact" href="https://github.com/borjamoskv/Cortex-Persist" target="_blank" rel="noreferrer">
GitHub
</a> </div> </header> <section class="vsa-grid"> <article class="surface vsa-lead"> <div class="surface-head"> <span class="surface-label">Telemetry shell</span> <span class="surface-state" id="mode-source">Boot</span> </div> <div class="lead-copy"> <h2>Compact public shell. Serious signal.</h2> <p>
Deterministic demo mode is the default public path. A localhost stream is
							only attempted when you explicitly opt into <code>?live=1</code>.
</p> </div> <div class="vsa-metrics"> <div class="metric-card"> <span class="metric-label">Exergy Yield</span> <strong id="yield-count">0.00</strong> </div> <div class="metric-card"> <span class="metric-label">Agent Cycles</span> <strong id="cycle-count">0</strong> </div> <div class="metric-card"> <span class="metric-label">Active Nodes</span> <strong id="active-count">000</strong> </div> <div class="metric-card"> <span class="metric-label">VSA Dimensions</span> <strong id="vsa-count">400</strong> </div> </div> </article> <aside class="surface-sunken vsa-ops"> <div class="ops-block"> <span class="surface-label">Runtime phase</span> <strong id="phase-value">Initializing shell</strong> <p class="surface-copy">
The public route stays honest: demo by default, localhost live mode only
							on local origin.
</p> </div> <div class="ops-pairs"> <div class="ops-pair"> <span>Drift Guard</span> <strong id="drift-value">0.00</strong> </div> <div class="ops-pair"> <span>Activity</span> <strong id="activity-value">0 / 400</strong> </div> </div> <div class="meter-block"> <div class="meter-copy"> <span class="surface-label">Health Envelope</span> <strong id="health-value">0%</strong> </div> <div class="meter-rail" aria-hidden="true"> <div id="health-fill"></div> </div> </div> </aside> </section> <section class="vsa-footer"> <article class="surface-sunken log-panel"> <div class="surface-head"> <span class="surface-label">Log stream</span> <span class="surface-copy">Newest state first</span> </div> <div id="log-monitor"></div> </article> <article class="surface hint-panel"> <p class="surface-label">Operator notes</p> <ul class="hint-list"> <li>Pan is disabled. Rotate and zoom only.</li> <li>Public mode runs synthetic telemetry with deterministic cadence.</li> <li>Use <code>?live=1</code> on localhost to attach the daemon stream.</li> </ul> </article> </section> </div> </div> ${renderScript($$result2, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/vsa.astro?astro&type=script&index=0&lang.ts")} ` })}`;
}, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/vsa.astro", void 0);
const $$file = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/vsa.astro";
const $$url = "/vsa";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$Vsa,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
