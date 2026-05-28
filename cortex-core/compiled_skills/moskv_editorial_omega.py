"""
CORTEX JIT Compiled Skill: moskv-editorial-omega
Description: Sovereign Editorial Pipeline — Text-in, published-site-out. Astro 6 + Sanity + Cloudflare.
"""
import json
import logging

class MoskvEditorialOmegaSkill:
    def __init__(self):
        self.name = "moskv-editorial-omega"
        self.description = "Sovereign Editorial Pipeline \u2014 Text-in, published-site-out. Astro 6 + Sanity + Cloudflare."
        self.instructions = "# MOSKV-EDITORIAL-\u03a9 \u2014 Sovereign Editorial Pipeline\n\n**Contract:** Raw text in \u2192 published on borjamoskv.com out.\n**Pipeline:** `text \u2192 classify \u2192 Sanity doc \u2192 Astro build \u2192 Cloudflare deploy`\n\n## Content Types \u2192 Sanity `_type`\n| Signal | `_type` | Route |\n|---|---|---|\n| Essay, analysis | `post` | `/post/[slug]`, `/diario`, `/archivo` |\n| External link | `linkItem` | `/enlaces` |\n| Config change | `siteSettings` | Global |\n\n## Sanity Schema (Key Fields)\n\n**`post`:** `title`(req), `slug`, `publishedAt`, `excerpt`, `body`(Portable Text), `category`(ref), `tags`, `section`(diario|ultra-think|archivo), `featured`\n\n**`linkItem`:** `title`, `url`, `description`, `category`(ref), `addedAt`\n\n**`siteSettings`:** `title`, `description`, `ogImage`, `socialLinks[]`\n\n## Astro Routes\n| Route | GROQ Filter |\n|---|---|\n| `/diario` | `_type==\"post\" && section==\"diario\"` |\n| `/ultra-think` | `_type==\"post\" && section==\"ultra-think\"` |\n| `/archivo` | `*[_type==\"post\"]` grouped by year |\n| `/enlaces` | `*[_type==\"linkItem\"]` grouped by category |\n| `/post/[slug]` | `slug.current == $slug` |\n\n## Sanity Client\n```typescript\n// src/lib/sanity.ts\nimport { createClient } from '@sanity/client';\nexport const client = createClient({\n  projectId: import.meta.env.SANITY_PROJECT_ID,\n  dataset: import.meta.env.SANITY_DATASET || 'production',\n  apiVersion: '2026-03-25',\n  useCdn: true,\n});\n```\n**Env vars:** `SANITY_PROJECT_ID`, `SANITY_DATASET`, `SANITY_API_TOKEN`\n\n## Agent Pipeline (5 Steps)\n1. **Parse & Classify** \u2192 detect `_type`, extract title/body/tags\n2. **Transform** \u2192 generate slug (kebab, no accents), convert to Portable Text, infer section\n3. **Write to Sanity** \u2192 `client.create(document)`\n4. **Trigger Rebuild** \u2192 `curl -X POST https://api.cloudflare.com/.../deploy_hooks/<HOOK_ID>`\n5. **Verify** \u2192 GROQ fetch \u2192 confirm route resolves on borjamoskv.com\n\n## Categories\n`articulo`, `set-lore`, `ultra-think`, `tecnica`, `cultura`, `politica`\n\n## Cloudflare Config\n```javascript\n// astro.config.mjs\nimport cloudflare from '@astrojs/cloudflare';\nexport default defineConfig({ output: 'static', adapter: cloudflare(), site: 'https://borjamoskv.com' });\n```\n\n## Invariants\n1. Zero HTML manual \u2014 Agent transforms text \u2192 Portable Text \u2192 Sanity \u2192 Astro \u2192 HTML\n2. Every post auto-appears in `/archivo` by year\n3. Every linkItem auto-appears in `/enlaces` by category\n4. `section` field routes to `/diario` or `/ultra-think`\n5. Sanity webhook triggers Cloudflare Pages rebuild\n\n## Migration Pending (7 HTML articles)\n`catarsis-colectiva`, `colapso-millennial`, `eclectic-electronic-analysis`, `gordacorp`, `idioma-nativo-progreso`, `la-semana-que-viene`, `termodinamica-de-agentes`\n\u2192 Extract HTML \u2192 Portable Text \u2192 Sanity documents via client SDK\n"

    def get_system_prompt(self):
        return self.instructions

    def execute(self, payload: dict) -> dict:
        """
        O(1) execution wrapper.
        In Cycle 1 (MCP), this will bind via API to Cortex Swarm.
        """
        logging.info(f"[{self.name}] Executing logic...")
        # A wrapper returning the prompt context for Frontier Models
        # or executing underlying local hooks if defined.
        return {
            "status": "success",
            "skill": self.name,
            "injected_knowledge_tokens": len(self.instructions.split()),
            "yield_impact": "O(1) Execution",
            "extracted_payload": payload
        }
