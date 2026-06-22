globalThis.process ??= {};
globalThis.process.env ??= {};
import { c as createComponent } from "./astro-component_DEaCX7dm.mjs";
import { n as renderComponent, h as renderTemplate, m as maybeRenderHead, g as addAttribute } from "./worker-entry_DFUcbWB_.mjs";
import { $ as $$SiteLayout } from "./SiteLayout_DduZsl0t.mjs";
const $$Index = createComponent(($$result, $$props, $$slots) => {
  const articles = [
    {
      title: "Te digo tó y no te digo ná: Termodinámica + Teoría de la Información",
      date: "June 2026",
      description: "El 0.002% de la población mundial domina la intersección entre Boltzmann y Shannon. Una estimación Fermi, el Criterio Técnico y la matemática detrás de la equivalencia física de la información.",
      href: "/blog/te_digo_to_y_no_te_digo_na",
      featured: true,
      tag: "ensayo"
    },
    {
      title: "La Máquina de Credibilidad: Consenso, Exergía y la Muerte del Vibe Coding",
      date: "June 2026",
      description: "Cómo escapar del caos probabilístico de los LLMs. La arquitectura de la Máquina de Credibilidad en CORTEX-Persist: firmas Ed25519, snapshots atómicos y replay determinista.",
      href: "/blog/maquina-credibilidad",
      featured: false,
      tag: "técnica"
    },
    {
      title: "La Mutación Causal del Genoma: AST, Autopoiesis y Exergía Pura",
      date: "June 2026",
      description: "La transición de evolución estocástica a deducción causal. Cómo CORTEX-Persist aplica cirugía determinista sobre nodos fallidos mutando su propio genoma AST/ISA.",
      href: "/blog/la_mutacion_causal_del_genoma",
      featured: false,
      tag: "técnica"
    },
    {
      title: "La Paradoja del Contexto Infinito: Por Qué Más Memoria No Es Más Inteligencia",
      date: "May 2026",
      description: "Google ofrece 2M de tokens de contexto. Anthropic, 200K. OpenAI, 128K. Y sin embargo, tu agente sigue olvidando todo al día siguiente. El problema nunca fue el tamaño de la ventana.",
      href: "/blog/la_paradoja_del_contexto_infinito",
      featured: false,
      tag: "análisis"
    },
    {
      title: "La Extinción de las Formas de Pensar: Lenguas Muertas, Agentes Amnésicos y el Último Acto de la Memoria",
      date: "May 2026",
      description: "Cada lengua que muere destruye un experimento cognitivo irrepetible de 10.000 años. Cada sesión de IA que se pierde replica el mismo patrón. Un ensayo sobre lingüística, entropía y persistencia soberana.",
      href: "/blog/la_extincion_de_las_formas_de_pensar",
      featured: false,
      tag: "ensayo"
    },
    {
      title: "La Muerte del Editor: La IA Agéntica como Modelo de Extracción de Renta",
      date: "May 2026",
      description: "Google desmanteló el editor local en Antigravity 2.0. ¿Por qué a la industria le interesa forzar interfaces conversacionales y cómo ataca esto a la soberanía del programador?",
      href: "/blog/la_muerte_del_editor.html",
      featured: false,
      tag: "ensayo"
    },
    {
      title: "La Economía de la Mentira: Los Influencers de IA y la Industria del Humo Digital",
      date: "May 2026",
      description: "En un mercado donde un avatar sin pulmones gana 40 veces más que un creador humano, la pregunta no es si la IA es el futuro, sino quién se está quedando con el presente.",
      href: "/blog/economia_mentira_industrial.html",
      featured: false,
      tag: "análisis"
    },
    {
      title: "Why Your AI Agent Has Alzheimer's",
      date: "Feb 2026",
      description: "You spent 3 hours teaching your AI agent the codebase. Next session? Gone. 100% amnesia. This is the most expensive bug in AI — and nobody's talking about it.",
      href: "/blog/why-your-ai-agent-has-alzheimers.html",
      featured: false,
      tag: "técnica"
    }
  ];
  return renderTemplate`${renderComponent($$result, "SiteLayout", $$SiteLayout, { "title": "CORTEX Persist | Intelligence Hub", "description": "Technical intelligence, sovereign engineering insights, and the operational reality of autonomous AI agents.", "data-astro-cid-5tznm7mj": true }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<main class="noir-blog-shell" data-astro-cid-5tznm7mj> <header class="masthead" data-astro-cid-5tznm7mj> <a class="brand" href="/" aria-label="CORTEX Persist home" data-astro-cid-5tznm7mj> <span class="brand-mark" data-astro-cid-5tznm7mj>CP</span> <span class="brand-copy" data-astro-cid-5tznm7mj> <strong data-astro-cid-5tznm7mj>CORTEX Persist</strong> <span data-astro-cid-5tznm7mj>Verifiable memory for AI agents</span> </span> </a> <nav class="site-nav" aria-label="Primary" data-astro-cid-5tznm7mj> <a class="nav-link" href="/#problem" data-astro-cid-5tznm7mj>Problem</a> <a class="nav-link" href="/#fit" data-astro-cid-5tznm7mj>Fit</a> <a class="nav-link" href="/#pilot" data-astro-cid-5tznm7mj>Pilot</a> <a class="nav-link active" href="/blog" data-astro-cid-5tznm7mj>Blog</a> </nav> <div class="masthead-actions" data-astro-cid-5tznm7mj> <a class="button-tertiary" href="https://github.com/borjamoskv/Cortex-Persist" target="_blank" rel="noreferrer" data-astro-cid-5tznm7mj>
Open Source
</a> <a class="button-primary" href="/async-demo" data-astro-cid-5tznm7mj>
Async Demo
</a> </div> </header> <!-- Hero Section --> <section class="noir-hero" data-astro-cid-5tznm7mj> <div class="noir-hero-label" data-astro-cid-5tznm7mj>INTELLIGENCE LOG</div> <h1 class="noir-hero-title" data-astro-cid-5tznm7mj>SOVEREIGN <span data-astro-cid-5tznm7mj>OPERATIONS</span></h1> <p class="noir-hero-sub" data-astro-cid-5tznm7mj>Technical essays and state-of-the-art research on memory, autonomy, and the economics of verifiable AI.</p> </section> <!-- Blog Grid --> <section class="noir-grid-section" data-astro-cid-5tznm7mj> <div class="noir-blog-grid" data-astro-cid-5tznm7mj> ${articles.map((article, i) => renderTemplate`<a${addAttribute(article.href, "href")}${addAttribute(`noir-blog-card ${article.featured ? "noir-card-featured" : "noir-card-standard"}`, "class")} data-astro-cid-5tznm7mj> <div class="noir-card-meta" data-astro-cid-5tznm7mj> <span class="noir-card-tag" data-astro-cid-5tznm7mj>${article.tag || "intelligence"}</span> <span class="noir-card-date" data-astro-cid-5tznm7mj>${article.date}</span> </div> <h3 class="noir-card-title" data-astro-cid-5tznm7mj>${article.title}</h3> <p class="noir-card-excerpt" data-astro-cid-5tznm7mj>${article.description}</p> <div class="noir-card-cta" data-astro-cid-5tznm7mj>Access Log ➔</div> </a>`)} </div> </section> <footer class="site-footer noir-footer" data-astro-cid-5tznm7mj> <p class="footer-note" data-astro-cid-5tznm7mj>CORTEX Persist / The swarm verifies. The hardware remembers.</p> <div class="footer-links" data-astro-cid-5tznm7mj> <a href="https://github.com/borjamoskv/Cortex-Persist" target="_blank" rel="noreferrer" data-astro-cid-5tznm7mj>GitHub</a> <a href="https://github.com/borjamoskv/Cortex-Persist/tree/main/docs" target="_blank" rel="noreferrer" data-astro-cid-5tznm7mj>Docs</a> <a href="/certificaciones" data-astro-cid-5tznm7mj>Certificaciones</a> <a href="/vsa" data-astro-cid-5tznm7mj>Public Shell</a> </div> </footer> </main> ` })}`;
}, "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/blog/index.astro", void 0);
const $$file = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/frontend/src/pages/blog/index.astro";
const $$url = "/blog";
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
