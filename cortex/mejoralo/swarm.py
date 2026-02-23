"""MEJORAlo v9.0 — Swarm of Specialized Subagents.

Uses ThoughtOrchestra to deploy multiple specialists in parallel,
synthesizing their insights into a single sovereign refactor.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path

from cortex.thinking.fusion import FusionStrategy
from cortex.thinking.orchestra import ThoughtOrchestra
from cortex.thinking.presets import OrchestraConfig, ThinkingMode

logger = logging.getLogger("cortex.mejoralo.swarm")

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
}


class MejoraloSwarm:
    """Orchestrates a swarm of specialists to refactor a file."""

    def __init__(self, level: int = 1):
        self.level = level
        # Configuración agresiva para el enjambre
        self.config = OrchestraConfig(
            min_models=3,
            max_models=6,
            default_strategy=FusionStrategy.SYNTHESIS,
            temperature=0.1 + (level * 0.1),
            timeout_seconds=240.0,  # A bit more time for complex synthesis
        )

    async def refactor_file(
        self, file_path: Path, findings: list[str], iteration: int = 0
    ) -> str | None:
        """Refactor code using a parallel swarm of specialists."""
        try:
            content = file_path.read_text(errors="replace")
        except Exception as e:
            logger.error("Failed to read %s: %s", file_path, e)
            return None

        findings_str = "- " + "\n- ".join(findings)

        # Prompt base para los especialistas
        base_prompt = (
            f"REFAC-TASK: Fix findings in {file_path.name}. Maintain EXACT functionality.\n"
            f"Findings:\n{findings_str}\n\n"
            f"Current Code:\n```python\n{content}\n```"
        )

        logger.info("🐝 Launching Swarm (Level %d) for %s", self.level, file_path.name)

        # Dynamically build the specialist squad based on context
        if self.level <= 1:
            squad_size = 3
        elif self.level == 2:
            squad_size = 5
        else:
            squad_size = 6

        # Always include the core architects
        active_specialists = ["ArchitectPrime", "CodeNinja"]

        fs_lower = findings_str.lower()

        # Contextual summoning
        if any(w in fs_lower for w in ["securit", "inject", "leak", "auth"]):
            active_specialists.append("SecurityWarden")

        if any(w in fs_lower for w in ["perform", "slow", "loop", "complex"]):
            active_specialists.append("PerformanceGhost")

        if any(w in fs_lower for w in ["error", "fail", "type", "except"]):
            active_specialists.append("RobustnessGuardian")

        if any(w in fs_lower for w in ["format", "lint", "style", "aesthetic"]):
            active_specialists.append("AestheticShiva")

        # Fill the rest if we haven't reached squad size, or trim if exceeded
        remaining = [s for s in SPECIALISTS_PROMPTS if s not in active_specialists]
        while len(active_specialists) < squad_size and remaining:
            active_specialists.append(remaining.pop(0))

        active_specialists = active_specialists[:squad_size]

        items = [f"- {name}: {SPECIALISTS_PROMPTS[name]}" for name in active_specialists]
        specialists_info = "\n".join(items)

        swarm_system = (
            f"You are the SOVEREIGN SWARM (Level {self.level}/3). Current iteration: {iteration}.\n"
            "Your objective: Achieve 130/100 quality score for the provided file.\n"
            f"Active Specialists:\n{specialists_info}\n\n"
            "Refactor the file by integrating ALL specialist insights. "
            "Return ONLY code between ```python and ```. Zero meta-commentary."
        )

        # Execute Refactor
        try:
            async with ThoughtOrchestra(config=self.config) as orchestra:
                result = await orchestra.think(
                    prompt=base_prompt,
                    mode=ThinkingMode.CODE,
                    system=swarm_system,
                    strategy=FusionStrategy.SYNTHESIS,
                )
        except Exception as e:
            logger.error("Swarm orchestration failed: %s", e)
            return None

        if result is None or not result.content:
            logger.error("Swarm produced no content.")
            return None

        return self._extract_code(result.content)

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
                        result = await orchestra.think(
                            prompt, mode=ThinkingMode.CODE, system=system
                        )
                        if result and result.content:
                            for line in result.content.splitlines():
                                clean = line.strip().lstrip("-*•0123456789. ")
                                if clean and len(clean) > 10:
                                    findings.append(f"{fp.name} → {clean}")
                    except Exception as e:
                        logger.error("Audit failed for %s: %s", fp.name, e)
        except Exception as e:
            logger.error("Audit orchestra failed: %s", e)
        return findings
