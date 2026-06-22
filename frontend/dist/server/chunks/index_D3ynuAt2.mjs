globalThis.process ??= {};
globalThis.process.env ??= {};
import { c as createComponent } from "./astro-component_DEaCX7dm.mjs";
import { m as maybeRenderHead, h as renderTemplate } from "./worker-entry_DFUcbWB_.mjs";
const $$Index = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${maybeRenderHead()}<h1>CortexPersist ORG Foundation</h1>`;
}, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/org/index.astro", void 0);
const $$file = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/org/index.astro";
const $$url = "/org";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$Index,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
