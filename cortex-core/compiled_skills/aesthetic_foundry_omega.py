"""
CORTEX JIT Compiled Skill: Aesthetic-Foundry-Omega
Description: Sovereign Visual Design Engine — Industrial Noir 2026 design system, UI/UX generation, typography enforcement, and premium aesthetic validation across all CORTEX surfaces.
"""

import json
import logging


class AestheticFoundryOmegaSkill:
    def __init__(self):
        self.name = "Aesthetic-Foundry-Omega"
        self.description = "Sovereign Visual Design Engine \u2014 Industrial Noir 2026 design system, UI/UX generation, typography enforcement, and premium aesthetic validation across all CORTEX surfaces."
        self.instructions = '# AESTHETIC-FOUNDRY-\u03a9: The Visual Sovereign\n\n`Aesthetic-Foundry-Omega` enforces the Industrial Noir 2026 design language across every surface in the CORTEX ecosystem. It is the mechanical guarantor that no UI, document, or generated asset violates the sovereign aesthetic mandate.\n\n---\n\n## 1. Industrial Noir Design System\n\nThe canonical design tokens for all CORTEX surfaces:\n- **Background**: `#0A0A0A` (Void Black) \u2014 no grays, no compromises.\n- **Accent Primary**: `#2B3BE5` (Sovereign Blue) \u2014 used for CTAs, active states, and focus rings.\n- **Accent Secondary**: `#E52B2B` (Blood Red) \u2014 reserved for warnings, destructive actions, and CAUTION alerts.\n- **Typography**: Humanist Sans stack (Inter \u2192 Outfit \u2192 system-ui). Monospace: JetBrains Mono.\n- **Corners**: 4px radius. No rounded pills. Sharp geometry conveys authority.\n- **Spacing**: 8px grid. Multiples of 8 only.\n- **Shadows**: None. Flat surfaces with border separation (`1px solid rgba(255,255,255,0.06)`).\n\n## 1.5. Dise\u00f1o T\u00e9rmico y F\u00edsico (The Absolute Presence Mandate)\n\nFor high-sovereignty surfaces (e.g., `www.borjamoskv.com`):\n- **O(1) Absolute Static Presence**: El dise\u00f1o no debe "agradar", debe imponer presencia est\u00e1tica absoluta (O(1)).\n- **Zero Standard Buttons**: No standard UI buttons. Interaction surface must feel native and structural.\n- **Spring Kinematics (120Hz)**: Interventions are physical. Physics are injected directly via high-fidelity spring animations matching 120Hz refresh rates.\n- **Raw CDP & Headless Suppression**: Total suppression of noisy UI components in macOS via raw CDP (DevTools interactuando sin interfaz humana).\n- **Multimodal AI Validation**: Video orchestration is driven by Veo 3.1, continually validated against Awwwards metrics using Kimi K2.5 multimodal vision.\n\n## 2. Premium Effects Library\n\nCurated visual patterns extracted from SOTY 2026 winners:\n- **Glassmorphism**: `backdrop-filter: blur(20px)` on `rgba(10,10,10,0.85)` \u2014 used sparingly for overlays.\n- **Gradient Mesh**: Subtle radial gradients for hero sections (`#0A0A0A` \u2192 `#111428`).\n- **Micro-animations**: 200ms ease-out transitions on all interactive elements. No animation exceeds 400ms.\n- **Text Glow**: `text-shadow: 0 0 20px rgba(43,59,229,0.3)` for highlighted headings.\n- **Scroll Reveal**: Intersection Observer with `translateY(20px)` \u2192 `translateY(0)` fade-in.\n\n## 3. Typography Enforcement\n\nStrict hierarchy:\n- **H1**: 48px / 700 / -0.02em tracking \u2014 one per page.\n- **H2**: 32px / 600 / -0.01em tracking.\n- **H3**: 24px / 600.\n- **Body**: 16px / 400 / 1.6 line-height.\n- **Code**: 14px / JetBrains Mono / `rgba(255,255,255,0.7)`.\n\n## 4. Asset Generation\n\nWhen generating visual assets:\n- **Icons**: Phosphor Icons (thin weight). No emoji in production UI.\n- **Images**: Always generate via `generate_image` \u2014 no placeholders.\n- **Color validation**: Every generated image must pass contrast ratio \u22654.5:1 on `#0A0A0A`.\n\n---\n\n## 5. Comandos de Operaci\u00f3n\n\n| Comando | Acci\u00f3n |\n|:---|:---|\n| `/aesthetic-audit [url\\|path]` | Validate a page/component against Industrial Noir spec |\n| `/aesthetic-palette [project]` | Generate a compliant color palette for a project |\n| `/aesthetic-typography [html]` | Audit heading hierarchy and font usage |\n| `/aesthetic-generate [prompt]` | Generate an Industrial Noir UI mockup |\n| `/aesthetic-tokens` | Export the full design token set as CSS/JSON |\n\n---\n\n## \u2234 Sello Soberano\n```text\n  \u2234  AESTHETIC-FOUNDRY-\u03a9 v1.0.0 \u2014 The Visual Sovereign\n  \u25c8  Sealed: 31 Mar 2026 \u00b7 MOSKV-1 v5 \u00b7 CORTEX Design\n  \u21b3  "#0A0A0A is not a color. It is a creed."\n```\n'

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
            "extracted_payload": payload,
        }
