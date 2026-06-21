# [C5-REAL] Exergy-Maximized
"""Maxwell's Token Demon (L1 Router / Cognitive Heat Sink).

Implements Hypothesis [H-THERMO-01]: An algorithmic gatekeeper that selectively
sorts high-signal (exergy) vs low-signal (entropy) tokens before they enter
the APEX model's context window. Discards conversational filler and boilerplate.

Status: IMPLEMENTED (C5-REAL)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from cortex.shannon.entropy import compute_fact_entropy

# Markers that indicate high exergy (structural data, code, YAML, logic)
_HIGH_EXERGY_MARKERS = re.compile(
    r"(```|def |class |import |from |\{|\}|\[|\]|<|>|yaml|json|C5-REAL|C4-SIM|# |->|=>|::)",
    re.IGNORECASE,
)

# Common conversational filler (high entropy noise)
_LOW_EXERGY_FILLER = re.compile(
    r"^(I think|Maybe|Perhaps|I understand|As an AI|I am an AI|Sure|Here is|Here are|Let me know|"
    r"Please note|It's important to remember|In conclusion|To summarize|As mentioned earlier)",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class MaxwellDemonResult:
    original_length: int
    filtered_length: int
    exergy_density: float
    filtered_content: str
    tokens_discarded: int


def filter_context(content: str, entropy_threshold: float = 1.5) -> MaxwellDemonResult:
    """Passes content through Maxwell's Demon to discard thermodynamic noise.

    Args:
        content: The raw prompt or context string.
        entropy_threshold: The minimum entropy bits required to preserve non-structural lines.

    Returns:
        MaxwellDemonResult containing the optimized string and metrics.
    """
    if not content:
        return MaxwellDemonResult(0, 0, 0.0, "", 0)

    lines = content.split("\n")
    preserved_lines = []

    inside_code_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            preserved_lines.append(line)
            continue

        if stripped.startswith("```"):
            inside_code_block = not inside_code_block
            preserved_lines.append(line)
            continue

        # 1. Structural Bypass (Demon lets fast particles through)
        if inside_code_block or _HIGH_EXERGY_MARKERS.search(line):
            preserved_lines.append(line)
            continue

        # 2. Filler Annihilation (Demon blocks slow particles)
        if _LOW_EXERGY_FILLER.search(line):
            continue

        # 3. Entropy-Based Evaluation (Demon measures kinetic energy)
        line_entropy = compute_fact_entropy(line)
        if line_entropy >= entropy_threshold:
            preserved_lines.append(line)

    filtered_content = "\n".join(preserved_lines)

    orig_len = len(content)
    filt_len = len(filtered_content)
    discarded = orig_len - filt_len

    # Calculate density = structural signal / total length
    density = (filt_len / orig_len) if orig_len > 0 else 0.0

    return MaxwellDemonResult(
        original_length=orig_len,
        filtered_length=filt_len,
        exergy_density=density,
        filtered_content=filtered_content,
        tokens_discarded=discarded,
    )
