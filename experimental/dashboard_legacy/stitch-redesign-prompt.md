# CortexPersist — Google Stitch Redesign Prompt

> Pega el bloque de abajo en **Google Stitch** (https://stitch.withgoogle.com/) en una nueva sesión. Stitch trabaja mejor en inglés, así que el prompt está en inglés. Las notas en español están solo para ti.

---

## 🇪🇸 Notas para ti antes de pegar

- **Dirección visual elegida**: *Neural Noir* — fondo oscuro casi negro, acentos de un único verde fósforo, tipografía editorial grande mezclada con monoespaciada, micro-grids tipo blueprint. La idea es que parezca "infraestructura seria para devs de IA" sin caer en el cliché de gradientes morados.
- Si Stitch te genera algo demasiado plano, pídele en el siguiente turno: *"more editorial, bigger type, more whitespace asymmetry, add a subtle terminal/code block"*.
- Stitch suele dar mejor resultado si lo iteras: primero genera la home completa, luego pídele que rehaga **una sola sección** a la vez.

---

## 📋 Prompt para pegar en Stitch

```
ROLE
You are a senior product designer specialising in developer-tool landing pages
(think Linear, Cloudflare, Anthropic, Modal, Resend, Clerk). Design a desktop
landing page for an AI-infrastructure product called "CortexPersist".

PRODUCT
CortexPersist is a persistent memory layer for LLM agents. It lets developers
give their AI agents long-term, queryable memory that survives across sessions,
processes and model swaps — without standing up their own vector DB, schema,
eviction policy or recall pipeline. Think "Postgres for agent memory".

AUDIENCE
AI engineers and backend developers who are already building with LLMs
(LangChain, LlamaIndex, custom agents, MCP servers). They are technical,
skeptical of marketing fluff, and want to see code, latency numbers and
architecture before they trust a new dependency.

VOICE & TONE
- Confident, technical, slightly understated.
- No emoji. No "revolutionise". No "unleash".
- Short sentences. Verbs first.
- Treat the reader like a peer engineer, not a buyer.

VISUAL DIRECTION — "Neural Noir"
- Background: near-black #0A0A0B with a faint blueprint grid (#FFFFFF at 3%
  opacity, 32px cells).
- Primary accent: phosphor green #B6FF3C used SPARINGLY — only on one CTA per
  screen, key numbers, and the cursor in code blocks.
- Text: #F4F4F5 for primary, #8A8A93 for secondary.
- Type system:
  - Display: a large editorial sans (Söhne / Inter Display / Geist) at 72–96px,
    tight tracking, mixed weight (Regular + Medium in the same headline).
  - Body: Inter / Geist 16–18px, 1.55 line-height.
  - Mono: JetBrains Mono / Geist Mono for code, version tags, latency numbers,
    and "kicker" labels above headlines.
- Layout: 12-col grid, generous whitespace, intentionally asymmetric. Some
  sections break the grid with a full-bleed code block or a single oversized
  number.
- Motion hints (describe in the design, no animation needed): subtle scanline
  on hover, monospace text that types in, soft phosphor glow on the primary CTA.
- NO purple gradients. NO glassmorphism. NO 3D blobs. NO stock dev illustrations.

PAGE STRUCTURE (in this order)

1. NAV BAR (sticky, transparent on top)
   - Left: wordmark "cortexpersist" in mono lowercase, with a tiny phosphor dot.
   - Center: Docs · SDK · Benchmarks · Pricing · Changelog
   - Right: GitHub star count pill, "Sign in" ghost link, "Get an API key"
     phosphor button.

2. HERO (full viewport)
   - Mono kicker top-left: "v0.9 — memory layer for agents"
   - Headline (display, 2 lines, mixed weight):
     "Give your agents
      a memory that **persists**."
   - Sub (max 18 words):
     "Drop-in long-term memory for LLM apps. Sub-50ms recall, schema-free,
      model-agnostic. Stop rebuilding RAG every Friday."
   - Two CTAs side by side:
     · Primary (phosphor): "Get an API key →"
     · Secondary (ghost, mono): "$ pip install cortexpersist"  (clickable to copy)
   - Right side of hero: a realistic terminal / code block, ~22 lines, showing:
     ```python
     from cortexpersist import Memory

     mem = Memory("agent-42")
     mem.remember("user prefers metric units")
     mem.recall("what units does the user like?")
     # → "metric"  (3.1 KB · 41 ms)
     ```
     The terminal has a soft phosphor caret blinking.
   - Bottom of hero: a thin row of 5–6 grayscale logos labelled "Trusted by
     teams shipping agents at —"

3. PROOF STRIP (one row, 4 oversized numbers)
   - 41ms p99 recall
   - 14B+ memories stored
   - 99.99% durability
   - 1 line of code to integrate
   Each number in the editorial display font, label below in mono caps.

4. THE PROBLEM (asymmetric, 2 cols)
   - Left col: a short essay (max 80 words) titled "Agents forget. That's the
     bug." — explain in plain language why session memory and RAG aren't enough.
   - Right col: a small annotated diagram of "what devs build today" —
     boxes for Pinecone + LangChain Memory + Postgres + cron job for eviction —
     with red dashed lines showing the duct tape. Make it look like a whiteboard.

5. THE SOLUTION — three feature cards (horizontal, equal width)
   Each card: mono kicker, short headline, 2-line description, tiny inline
   code snippet at the bottom. No icons.
   - Card 1: "PERSISTENT" — Memory that survives restarts, deploys and model swaps.
   - Card 2: "QUERYABLE" — Recall by meaning, time, agent or arbitrary metadata.
   - Card 3: "OBSERVABLE" — Inspect, edit and replay every memory write.

6. HOW IT WORKS (full-bleed dark section)
   A horizontal 4-step diagram: write → embed → store → recall.
   Each step shows the underlying primitive (e.g. "write" → JSON event,
   "store" → tiered storage hot/warm/cold). Use the blueprint grid as background.

7. CODE-FIRST SECTION (the centerpiece)
   Headline: "Built for people who'd rather read code than docs."
   A large tabbed code block with 4 tabs: Python · TypeScript · Go · curl.
   Each tab shows the same end-to-end example (init → write → recall → audit).
   Below the block, three tiny links: "Full quickstart", "API reference",
   "Self-host guide".

8. BENCHMARKS (data-dense)
   A clean table OR bar chart comparing CortexPersist vs. "DIY Postgres+pgvector"
   vs. "Pinecone + LangChain Memory" on:
   - p99 recall latency
   - lines of code to integrate
   - cost per 1M memories / month
   Make the CortexPersist row glow phosphor. Footnote with link to methodology.

9. ARCHITECTURE (optional, for credibility)
   A simple line-art diagram of the system: SDK → ingest → tiered storage →
   recall API. Keep it monochrome with one phosphor highlight on the
   "deterministic recall" component.

10. SOCIAL PROOF — one big quote
    A single oversized testimonial from an AI engineer (genesis name +
    title + company logo). No carousel, no avatars grid.

11. PRICING (3 tiers, minimal)
    Hobby (free) · Pro ($X/mo) · Enterprise (contact).
    Each tier: one-line description, 4 bullet points max, monospace prices.
    The Pro card is the only one with the phosphor border.

12. FINAL CTA
    Centered, full-bleed dark.
    Headline: "Ship the agent. We'll remember the rest."
    Single phosphor button: "Get an API key →"
    Below in mono small: "No credit card. 10k memories free forever."

13. FOOTER
    4 columns: Product · Developers · Company · Legal.
    Bottom row: wordmark, "© 2026 CortexPersist", status pill ("All systems
    operational" with a phosphor dot), GitHub / X / Discord icons in mono style.

CONSTRAINTS
- Desktop first, 1440px wide.
- No carousels. No accordions. No modals.
- Every section must fit on one screen height except the hero and the code
  section.
- Use real-looking code, not lorem ipsum.
- The phosphor green appears AT MOST 6 times on the entire page.

DELIVERABLE
A single high-fidelity desktop landing page in Stitch, with components named
semantically (Hero, ProofStrip, ProblemEssay, FeatureCards, HowItWorks,
CodeTabs, BenchmarkTable, Architecture, Quote, Pricing, FinalCTA, Footer).
```

---

## 🔁 Iteraciones sugeridas (después del primer render)

Si Stitch te devuelve algo que no convence, pega cualquiera de estos prompts de seguimiento:

1. **"Make the hero more editorial: increase the display headline to 96px, mix Regular and Medium weights inside the same line, and push the terminal block 80px lower so it breaks the baseline grid."**
2. **"Replace all icons in the feature cards with mono-style numerals (01, 02, 03) and tighten the cards' vertical rhythm."**
3. **"Redesign the benchmark section as a single dense table with monospace numbers, right-aligned, and make the CortexPersist row's background a 6% phosphor tint instead of a glow."**
4. **"The page feels too dark. Add ONE light section (only the 'How it works' diagram) on a #F4F4F5 background to break the rhythm. Keep everything else dark."**
5. **"Generate a mobile version of the hero only — keep the same headline and code block, but stack vertically and shrink the terminal to 12 lines."**

---

## ✅ Checklist de calidad

Antes de dar por bueno lo que Stitch genere, valida que:

- [ ] El headline del hero se entiende en 1 segundo y no usa la palabra "AI" más de una vez.
- [ ] Hay código real visible **above the fold** (no solo en una sección posterior).
- [ ] Los números de la proof strip son creíbles, no redondos sospechosos (41ms ✅, 50ms ❌).
- [ ] Solo hay **un** CTA primario por sección.
- [ ] No aparece ningún gradiente morado, ningún blob 3D, ningún stock dev con auriculares.
- [ ] El verde fósforo aparece como mucho 6 veces en toda la página.
- [ ] La sección de benchmarks tiene un footnote con metodología (aunque sea un link genesis).
