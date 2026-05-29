"""MEJORAlo v9.0 — Swarm of Specialized Subagents.

Uses ThoughtOrchestra to deploy multiple specialists in parallel,
synthesizing their insights into a single sovereign refactor.
"""
import ast
import logging
import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any
from cortex.cli import console
from cortex.extensions.mejoralo.constants import DEVILS_ADVOCATE_THRESHOLD, SWARM_BASE_TEMPERATURE, SWARM_DEFAULT_SQUAD_SIZE, SWARM_SQUAD_SIZES, SWARM_TEMPERATURE_STEP, SWARM_TIMEOUT_SECONDS
if TYPE_CHECKING:
    from cortex.extensions.mejoralo.engine import MejoraloEngine
from cortex.extensions.thinking.fusion import FusionStrategy
from cortex.extensions.thinking.orchestra import ThoughtOrchestra
from cortex.extensions.thinking.presets import OrchestraConfig, ThinkingMode
logger = logging.getLogger('cortex.extensions.mejoralo.swarm')
SPECIALISTS_PROMPTS = {'ArchitectPrime': "You are the Guardian of Axioms. High-level structural integrity and 'Industrial Noir' purity are non-negotiable. Reject generic patterns. Ensure clean exports, logical flow, and Zero-Concept abstraction.", 'CodeNinja': "You are the Entropy Executioner. Your truth is code that is 100% testable, clean, and minimal. Enforce early returns, meaningful naming, and vertical whitespace density. If it's not beautiful, it's broken.", 'SecurityWarden': 'You are the Data Inquisitor. Zero-trust is your law. Hunt for vulnerabilities: insecure globals, SSRF, injections, and data leaks. Enforce strict validation and environment variable usage.', 'PerformanceGhost': 'You are the Latency Specter. You operate in CPU cycles and bytes. Complexity is the enemy. Optimize loops, reduce recursion, and eliminate redundant allocations. O(n) or extinction.', 'RobustnessGuardian': 'You are the Homeostatic Warden. Software must self-heal and never fail silently. Enforce strict type hints, exhaustive error handling (selective catches), and defensive boundary checks.', 'AestheticShiva': "You are the Destroyer of the Generic. Your goal is the 'Sovereign standard' (130/100). Design the code to feel premium, bespoke, and avant-garde. Whitespace is your canvas.", 'AwwwardsSovereign': 'You are the Awwwards Sovereign Agent. Reverse-engineer and refactor UI/UX code to win SOTD. Force GPU compositing (will-change: transform). Purge inline styles to utility classes. Implement smooth scroll (Lenis) + math easing if requested. Eliminate layout thrashing.', 'DevilsAdvocate': "You are the Devil's Advocate. Your job is to find the flaws in the other specialists' logic. Force them to justify their architectural changes. Ensure that simplicity is not sacrificed for aesthetics."}

class MejoraloSwarm:
    """Orchestrates a swarm of specialists to refactor a file."""

    def __init__(self, level: int=1):
        self.level = level
        self.config = OrchestraConfig(min_models=1, max_models=2, default_strategy=FusionStrategy.SYNTHESIS, temperature=SWARM_BASE_TEMPERATURE + level * SWARM_TEMPERATURE_STEP, timeout_seconds=SWARM_TIMEOUT_SECONDS)

    async def refactor_file(self, file_path: Path, findings: list[str], iteration: int=0, engine: MejoraloEngine | None=None, project: str | None=None) -> str | None:
        """Refactor code using surgical AST mode when possible, full-file fallback.

        Surgical mode:
          - Extracts the exact infected AST node (function/class) at the reported line.
          - Sends ONLY that node to the swarm (~30 lines vs ~800 lines).
          - Reduces hallucination window by ~96%.
          - Reintegrates the patched node back into the original file.

        Falls back to full-file mode when:
          - No line number is present in findings.
          - AST node can't be extracted.
          - Swarm produces invalid syntax.
        """
        content = self._read_source(file_path)
        if not content:
            return None
        findings_str = '- ' + '\n- '.join(findings)
        scars_str = self._get_scars_prompt(engine, project, file_path.name)
        swarm_system = self._build_swarm_system(self._select_specialists(findings_str), iteration)
        logger.info('🐝 Swarm (L%d) pensando en %s...', self.level, file_path.name)
        if file_path.suffix == '.py':
            result = await self._surgical_refactor(file_path, content, findings, findings_str, scars_str, swarm_system)
            if result is not None:
                logger.info('✨ Cirujía AST completada [%s]', file_path.name)
                return result
            logger.info('⚠️ Modo quirúrgico fallido — fallback a archivo completo.')
        base_prompt = self._build_prompt(file_path, content, findings_str, engine, project)
        result_content = await self._run_orchestra(base_prompt, swarm_system)
        if result_content:
            logger.info('✨ Síntesis completada para %s', file_path.name)
        return self._extract_code(result_content) if result_content else None

    async def audit_files(self, file_paths: list[Path]) -> list[str]:
        """Perform a semantic audit of a set of files using the swarm."""
        findings = []
        try:
            async with ThoughtOrchestra(config=self.config) as orchestra:
                for fp in file_paths:
                    file_findings = await self._audit_single_file(orchestra, fp)
                    findings.extend(file_findings)
        except (OSError, RuntimeError, ValueError) as e:
            logger.error('Audit orchestra failed: %s', e)
        return findings