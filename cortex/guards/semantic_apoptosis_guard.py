# [C5-REAL] Exergy-Maximized
"""
Semantic Apoptosis Guard (Information Bottleneck)

Terminates stochastic payloads containing low-density semantic noise (prose, apologies)
at the boundary. Forces frontier LLMs (like GPT-5.5) to communicate purely in
structural invariants (AST, YAML, JSON, diffs).
"""

import logging
import re
from typing import Any

from cortex.utils.errors import CortexError

logger = logging.getLogger("cortex.guards.semantic_apoptosis")


class SemanticApoptosisError(ValueError, CortexError):
    """Raised when a payload fails semantic density requirements."""


class SemanticApoptosisGuard:
    """
    Evaluates Shannon Density and executes semantic apoptosis on LLM slop.
    Rejects decorative prose at the boundary before SAGA execution.
    """

    def __init__(self, max_noise_ratio: float = 0.15) -> None:
        self.max_noise_ratio = max_noise_ratio

        # Heuristics for GPT-style conversational slop
        self._slop_patterns = re.compile(
            r"(?i)\b(espero que|aquí tienes|por supuesto|sin problema|en conclusión|"
            r"este script|el código anterior|como modelo de lenguaje|lo siento|"
            r"sure,|here is|i hope this helps|let me know|certainly)\b"
        )
        # Match standard code blocks
        self._code_blocks = re.compile(r"```[a-z]*\n.*?\n```", re.DOTALL)

    def assess_payload(self, proposal: Any) -> bool:
        """
        Assesses the payload.
        Returns True if the payload is purely structural (Fast-Path eligible).
        Raises SemanticApoptosisError if the payload contains too much noise.
        """
        if not isinstance(proposal, str):
            # Non-string proposals (dicts, ints) are structural by definition
            return True

        content = proposal
        total_len = len(content.strip())

        if total_len == 0:
            raise SemanticApoptosisError("Payload is empty.")

        # Extract structured blocks (markdown code, json)
        code_matches = self._code_blocks.findall(content)
        code_len = sum(len(m) for m in code_matches)

        # Assess the remainder (potential prose)
        prose_content = self._code_blocks.sub("", content).strip()
        prose_len = len(prose_content)

        # Calculate slop matches in prose
        slop_hits = len(self._slop_patterns.findall(prose_content))

        # If no code blocks and heavy slop, immediate kill
        if code_len == 0 and slop_hits > 0:
            logger.warning("Semantic Apoptosis: Payload consists entirely of conversational slop.")
            raise SemanticApoptosisError(
                "Payload consists entirely of conversational slop. Jettisoned."
            )

        # Ratio check
        noise_ratio = prose_len / total_len if total_len > 0 else 0.0

        if noise_ratio > self.max_noise_ratio and slop_hits > 0:
            logger.warning(
                f"Semantic Apoptosis: Noise ratio {noise_ratio:.2f} exceeds {self.max_noise_ratio}."
            )
            raise SemanticApoptosisError(
                f"Semantic Apoptosis: Noise ratio {noise_ratio:.2f} exceeds strict boundary {self.max_noise_ratio}. "
                "Generative prose detected. Payload jettisoned."
            )

        # Mark for Fast-Path if purely structural (noise_ratio ~ 0 or non-code text is extremely short and has no slop)
        is_perfect_exergy = (noise_ratio < 0.05 or prose_len < 30) and slop_hits == 0
        return is_perfect_exergy
