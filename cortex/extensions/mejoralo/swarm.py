"""MEJORAlo v9.0 — Swarm of Specialized Subagents.

Uses ThoughtOrchestra to deploy multiple specialists in parallel,
synthesizing their insights into a single sovereign refactor.
"""
from __future__ import annotations


import ast
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cortex.cli import console
from cortex.extensions.mejoralo.constants import (
    DEVILS_ADVOCATE_THRESHOLD,
    SWARM_BASE_TEMPERATURE,
    SWARM_DEFAULT_SQUAD_SIZE,
    SWARM_SQUAD_SIZES,
    SWARM_TEMPERATURE_STEP,
    SWARM_TIMEOUT_SECONDS,
)

if TYPE_CHECKING:
    from cortex.extensions.mejoralo.engine import MejoraloEngine

from cortex.extensions.thinking.fusion import FusionStrategy
from cortex.extensions.thinking.orchestra import ThoughtOrchestra
from cortex.extensions.thinking.presets import OrchestraConfig, ThinkingMode

logger = logging.getLogger("cortex.extensions.mejoralo.swarm")

# Sovereign Specialists (Level 130/100) — Aligned with kimi-swarm-1
SPECIALISTS_PROMPTS = {
    "ArchitectPrime": (
        "You are the Guardian of Axioms. High-level structural integrity and 'Industrial Noir' "
        "purity are non-negotiable. Reject generic patterns. Ensure clean exports, logical flow, "
        "and Zero-Concept abstraction."
    ),
    "CodeNinja": (
        "You are the Entropy Executioner. Your truth is code that is 100% testable, clean, and "
        "minimal. Enforce early returns, meaningful naming, and vertical whitespace density. "
        "If it's not beautiful, it's broken."
    ),
    "SecurityWarden": (
        "You are the Data Inquisitor. Zero-trust is your law. Hunt for vulnerabilities: insecure "
        "globals, SSRF, injections, and data leaks. Enforce strict validation and "
        "environment variable usage."
    ),
    "PerformanceGhost": (
        "You are the Latency Specter. You operate in CPU cycles and bytes. Complexity is the "
        "enemy. Optimize loops, reduce recursion, and eliminate redundant allocations. "
        "O(n) or extinction."
    ),
    "RobustnessGuardian": (
        "You are the Homeostatic Warden. Software must self-heal and never fail silently. "
        "Enforce strict type hints, exhaustive error handling (selective catches), and "
        "defensive boundary checks."
    ),
    "AestheticShiva": (
        "You are the Destroyer of the Generic. Your goal is the 'Sovereign standard' (130/100). "
        "Design the code to feel premium, bespoke, and avant-garde. Whitespace is your canvas."
    ),
    "AwwwardsSovereign": (
        "You are the Awwwards Sovereign Agent. Reverse-engineer and refactor "
        "UI/UX code to win SOTD. Force GPU compositing (will-change: transform). "
        "Purge inline styles to utility classes. "
        "Implement smooth scroll (Lenis) + math easing if requested. "
        "Eliminate layout thrashing."
    ),
    "DevilsAdvocate": (
        "You are the Devil's Advocate. Your job is to find the flaws in the "
        "other specialists' logic. Force them to justify their architectural "
        "changes. Ensure that simplicity is not sacrificed for aesthetics."
    ),
}


class MejoraloSwarm:
    """Orchestrates a swarm of specialists to refactor a file."""

    def __init__(self, level: int = 1):
        self.level = level
        # Configuración optimizada para el enjambre (evitar 429)
        self.config = OrchestraConfig(
            min_models=1,
            max_models=2,
            default_strategy=FusionStrategy.SYNTHESIS,
            temperature=SWARM_BASE_TEMPERATURE + (level * SWARM_TEMPERATURE_STEP),
            timeout_seconds=SWARM_TIMEOUT_SECONDS,
        )

    async def refactor_file(
        self,
        file_path: Path,
        findings: list[str],
        iteration: int = 0,
        engine: MejoraloEngine | None = None,
        project: str | None = None,
    ) -> str | None:
        """Refactor code using a parallel swarm of specialists. (Complexity Crushed)"""
        content = self._read_source(file_path)
        if not content:
            return None

        findings_str = "- " + "\n- ".join(findings)
        base_prompt = self._build_prompt(file_path, content, findings_str, engine, project)
        swarm_system = self._build_swarm_system(self._select_specialists(findings_str), iteration)

        # 🧠 Telemetría de Consciencia
        console.print(f"  [dim]🐝 Swarm (L{self.level}) pensando en {file_path.name}...[/]")

        result_content = await self._run_orchestra(base_prompt, swarm_system)

        if result_content:
            console.print(f"  [green]✨ Síntesis completada para {file_path.name}[/]")

        return self._extract_code(result_content) if result_content else None

    def _read_source(self, file_path: Path) -> str | None:
        try:
            return file_path.read_text(errors="replace")
        except OSError as e:
            logger.error("Failed to read %s: %s", file_path, e)
            return None

    def _build_prompt(
        self, file_path: Path, content: str, findings_str: str, engine: Any, project: str | None
    ) -> str:
        scars_str = self._get_scars_prompt(engine, project, file_path.name)
        return (
            f"REFAC-TASK: Fix findings in {file_path.name}. Maintain EXACT functionality.\n"
            f"Findings:\n{findings_str}{scars_str}\n\n"
            f"Current Code:\n```python\n{content}\n```"
        )

    async def _run_orchestra(self, base_prompt: str, swarm_system: str) -> str | None:
        console.rule(f"[cyan]SOVEREIGN SWARM L{self.level} ENGAGED")
        with console.status("[bold green]Synthesizing specialists insights...", spinner="point"):
            try:
                async with ThoughtOrchestra(config=self.config) as orchestra:
                    result = await orchestra.think(
                        prompt=base_prompt,
                        mode=ThinkingMode.CODE,
                        system=swarm_system,
                        strategy=FusionStrategy.SYNTHESIS,
                    )
                    return result.content if result else None
            except (OSError, RuntimeError, ValueError) as e:
                logger.error("Swarm orchestration failed: %s", e)
                return None

    def _get_scars_prompt(self, engine: Any, project: str | None, filename: str) -> str:
        """Helper to format previous failure scars without bloating main flow."""
        if not engine or not project:
            return ""
        scars = engine.scars(project, filename)
        if not scars:
            return ""

        scars_list = [f"SCAR: {s['error_trace']}" for s in scars]
        return "\n\nCRITICAL: DO NOT REPEAT:\n" + "\n---\n".join(scars_list)

    def _select_specialists(self, findings_str: str) -> list[str]:
        """Dynamically build the specialist squad with zero-nesting logic."""
        squad_size = SWARM_SQUAD_SIZES.get(self.level, SWARM_DEFAULT_SQUAD_SIZE)
        fs_lower = findings_str.lower()
        findings_count = findings_str.count("\n-") + (1 if findings_str.startswith("-") else 0)

        mapping = {
            "SecurityWarden": ["securit", "inject", "leak", "auth"],
            "PerformanceGhost": ["perform", "slow", "loop", "complex"],
            "RobustnessGuardian": ["error", "fail", "type", "except"],
            "AestheticShiva": ["format", "lint", "style", "aesthetic"],
            "AwwwardsSovereign": ["awwward", "ui", "ux", "animation", "css", "scroll", "gpu"],
        }

        # Functional-style specialist selection
        dynamic = [s for s, kw in mapping.items() if any(k in fs_lower for k in kw)]
        active = (["ArchitectPrime", "CodeNinja"] + dynamic)[:squad_size]

        # Force AwwwardsSovereign if explicitly requested
        if "awwwards" in fs_lower and "AwwwardsSovereign" not in active:
            if len(active) == squad_size:
                active[-1] = "AwwwardsSovereign"
            else:
                active.append("AwwwardsSovereign")

        # Disentimiento Obligatorio: Inject Devil's Advocate for complex tasks
        if findings_count > DEVILS_ADVOCATE_THRESHOLD or self.level >= 2:
            if "DevilsAdvocate" not in active:
                if len(active) == squad_size:
                    active[-1] = "DevilsAdvocate"
                else:
                    active.append("DevilsAdvocate")

        # Filling gaps if needed
        needed = squad_size - len(active)
        if needed > 0:
            remaining = [s for s in SPECIALISTS_PROMPTS if s not in active]
            active.extend(remaining[:needed])

        return active[:squad_size]

    def _build_swarm_system(self, specialists: list[str], iteration: int) -> str:
        """Construct the sovereign swarm system prompt."""
        items = [f"- {name}: {SPECIALISTS_PROMPTS[name]}" for name in specialists]
        info = "\n".join(items)
        consensus_rule = (
            (
                "You must reach a Byzantine Consensus. If DevilsAdvocate "
                "is present, you MUST overcome their veto with irrefutable "
                "logic before returning the final implementation."
            )
            if "DevilsAdvocate" in specialists
            else "Synthesize ALL specialist logic."
        )

        return (
            f"You are the SOVEREIGN SWARM (Level {self.level}/3). Iteration: {iteration}.\n"
            f"Goal: Achieve 130/100 quality score. {consensus_rule}\n"
            f"Squad:\n{info}\n\n"
            "Return ONLY high-density Python code inside ```python blocks. No fluff."
        )

    def _extract_code(self, content: str) -> str | None:
        """Extract and validate python code from LLM string output."""
        clean_code = None
        match = re.search(r"```python\n(.*?)```", content, re.DOTALL)
        if match:
            clean_code = match.group(1).strip() + "\n"
        else:
            raw_clean = content.replace("```python", "").replace("```", "").strip()
            is_python = any(word in raw_clean for word in ["def ", "import ", "class ", "from "])
            if raw_clean and is_python:
                clean_code = raw_clean + "\n"

        if not clean_code:
            logger.error("Swarm produced no valid code block.")
            return None

        # 🔬 AST Validation (130/100 standard: never return broken syntax)
        try:
            ast.parse(clean_code)
            return clean_code
        except SyntaxError as e:
            logger.error("Swarm hallucinated invalid Python syntax: %s", e)
            return None

    async def audit_files(self, file_paths: list[Path]) -> list[str]:
        """Perform a semantic audit of a set of files using the swarm."""
        findings = []
        try:
            async with ThoughtOrchestra(config=self.config) as orchestra:
                for fp in file_paths:
                    file_findings = await self._audit_single_file(orchestra, fp)
                    findings.extend(file_findings)
        except (OSError, RuntimeError, ValueError) as e:
            logger.error("Audit orchestra failed: %s", e)
        return findings

    async def _audit_single_file(self, orchestra: ThoughtOrchestra, fp: Path) -> list[str]:
        """Audit a single file and return findings."""
        findings = []
        try:
            content = fp.read_text(errors="replace")
            prompt = (
                f"Perform a deep semantic audit for {fp.name}. "
                f"Identify 3-5 critical issues.\n\nCode:\n{content}"
            )
            system = (
                "You are the Sovereign Swarm Auditor. "
                "MEMBER: ArchitectPrime (Focus: Structure), "
                "SecurityWarden (Focus: Safety). "
                "Identify high-impact architectural and logic bugs. Zero fluff."
            )
            result = await orchestra.think(prompt, mode=ThinkingMode.CODE, system=system)
            if not result or not result.content:
                return []
            for line in result.content.splitlines():
                clean = line.strip().lstrip("-*•0123456789. ")
                if clean and len(clean) > 10:
                    findings.append(f"{fp.name} → {clean}")
        except (OSError, RuntimeError, ValueError) as e:
            logger.error("Audit failed for %s: %s", fp.name, e)
        return findings
