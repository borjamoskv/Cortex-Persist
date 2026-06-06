# [C5-REAL] Exergy-Maximized
"""CORTEX Level 3 Copilot - Context Window Manager.

Intelligent prefix/suffix extraction for LLM context windows.
Handles token budget management, smart truncation, and FIM formatting.

Token estimation: ~4 chars per token (tiktoken-free approximation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

# ── Constants ─────────────────────────────────────────────────────

CHARS_PER_TOKEN = 4  # Conservative approximation
FIM_PREFIX_TAG = "<|fim_prefix|>"
FIM_SUFFIX_TAG = "<|fim_suffix|>"
FIM_MIDDLE_TAG = "<|fim_middle|>"

# Language-specific patterns for import detection
IMPORT_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\s*(import |from .+ import )", re.MULTILINE),
    "typescript": re.compile(r"^\s*(import |export |require\()", re.MULTILINE),
    "javascript": re.compile(r"^\s*(import |export |require\()", re.MULTILINE),
    "rust": re.compile(r"^\s*(use |mod |extern crate )", re.MULTILINE),
    "go": re.compile(r"^\s*(import )", re.MULTILINE),
}

# Signature patterns (functions, classes)
SIGNATURE_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\s*(def |class |async def )", re.MULTILINE),
    "typescript": re.compile(
        r"^\s*(function |class |interface |type |const .+=.*=>|export (?:default )?(?:function|class))",
        re.MULTILINE,
    ),
    "javascript": re.compile(r"^\s*(function |class |const .+=.*=>)", re.MULTILINE),
    "rust": re.compile(r"^\s*(fn |pub fn |struct |impl |trait |enum )", re.MULTILINE),
    "go": re.compile(r"^\s*(func |type )", re.MULTILINE),
}


# ── Models ────────────────────────────────────────────────────────


class ContextWindow(BaseModel):
    """Optimized context window ready for LLM consumption."""

    prefix: str = Field(default="", description="Truncated prefix text")
    suffix: str = Field(default="", description="Truncated suffix text")
    prefix_tokens: int = Field(default=0, ge=0)
    suffix_tokens: int = Field(default=0, ge=0)
    total_budget: int = Field(default=2048, gt=0)
    tokens_used: int = Field(default=0, ge=0)

    # FIM (Fill-in-the-Middle) formatted fields
    fim_prefix: str = Field(default="", description="FIM-tagged prefix")
    fim_suffix: str = Field(default="", description="FIM-tagged suffix")
    fim_middle: str = Field(default=FIM_MIDDLE_TAG, description="FIM middle marker")

    # Metadata
    language: str = Field(default="python")
    imports_preserved: int = Field(default=0, ge=0)
    signatures_preserved: int = Field(default=0, ge=0)
    truncated: bool = Field(default=False)


@dataclass
class _LinePriority:
    """Internal: a line with its priority score for truncation decisions."""

    line_number: int
    text: str
    priority: float = 0.0  # Higher = more important to keep
    is_import: bool = False
    is_signature: bool = False
    is_cursor_adjacent: bool = False


# ── Core Builder ──────────────────────────────────────────────────


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return max(1, len(text) // CHARS_PER_TOKEN) if text else 0


def build_context_window(
    raw_prefix: str,
    raw_suffix: str,
    *,
    budget_tokens: int = 2048,
    language: str = "python",
    prefix_ratio: float = 0.75,
    cursor_adjacency_lines: int = 20,
) -> ContextWindow:
    """Build an optimized context window from raw prefix/suffix.

    Priority ranking (highest → lowest):
      1. Lines adjacent to cursor (±cursor_adjacency_lines)
      2. Import statements
      3. Function/class signatures
      4. File header (first 5 lines)
      5. Everything else

    Args:
        raw_prefix: Full text before cursor.
        raw_suffix: Full text after cursor.
        budget_tokens: Total token budget for prefix + suffix.
        language: Language ID for pattern detection.
        prefix_ratio: Fraction of budget allocated to prefix (0.0–1.0).
        cursor_adjacency_lines: Lines near cursor to prioritize.

    Returns:
        ContextWindow with truncated, prioritized text.
    """
    prefix_budget = int(budget_tokens * prefix_ratio)
    suffix_budget = budget_tokens - prefix_budget

    prefix_est = estimate_tokens(raw_prefix)
    suffix_est = estimate_tokens(raw_suffix)

    # Fast path: everything fits
    if prefix_est + suffix_est <= budget_tokens:
        return ContextWindow(
            prefix=raw_prefix,
            suffix=raw_suffix,
            prefix_tokens=prefix_est,
            suffix_tokens=suffix_est,
            total_budget=budget_tokens,
            tokens_used=prefix_est + suffix_est,
            fim_prefix=f"{FIM_PREFIX_TAG}{raw_prefix}",
            fim_suffix=f"{FIM_SUFFIX_TAG}{raw_suffix}",
            fim_middle=FIM_MIDDLE_TAG,
            language=language,
            truncated=False,
        )

    # Smart truncation needed
    truncated_prefix, imports_kept, sigs_kept = _smart_truncate_prefix(
        raw_prefix,
        budget_chars=prefix_budget * CHARS_PER_TOKEN,
        language=language,
        cursor_adjacency_lines=cursor_adjacency_lines,
    )
    truncated_suffix = _smart_truncate_suffix(
        raw_suffix,
        budget_chars=suffix_budget * CHARS_PER_TOKEN,
    )

    p_tokens = estimate_tokens(truncated_prefix)
    s_tokens = estimate_tokens(truncated_suffix)

    return ContextWindow(
        prefix=truncated_prefix,
        suffix=truncated_suffix,
        prefix_tokens=p_tokens,
        suffix_tokens=s_tokens,
        total_budget=budget_tokens,
        tokens_used=p_tokens + s_tokens,
        fim_prefix=f"{FIM_PREFIX_TAG}{truncated_prefix}",
        fim_suffix=f"{FIM_SUFFIX_TAG}{truncated_suffix}",
        fim_middle=FIM_MIDDLE_TAG,
        language=language,
        imports_preserved=imports_kept,
        signatures_preserved=sigs_kept,
        truncated=True,
    )


# ── Smart Truncation ─────────────────────────────────────────────


def _smart_truncate_prefix(
    text: str,
    *,
    budget_chars: int,
    language: str,
    cursor_adjacency_lines: int,
) -> tuple[str, int, int]:
    """Truncate prefix keeping high-priority lines.

    Returns: (truncated_text, imports_preserved, signatures_preserved)
    """
    if len(text) <= budget_chars:
        return text, 0, 0

    lines = text.split("\n")
    total_lines = len(lines)

    import_pat = IMPORT_PATTERNS.get(language)
    sig_pat = SIGNATURE_PATTERNS.get(language)

    # Score each line
    scored: list[_LinePriority] = []
    for i, line in enumerate(lines):
        lp = _LinePriority(line_number=i, text=line)

        # Priority 1: Cursor adjacency (last N lines)
        distance_from_cursor = total_lines - 1 - i
        if distance_from_cursor < cursor_adjacency_lines:
            lp.priority = 100.0 - distance_from_cursor
            lp.is_cursor_adjacent = True

        # Priority 2: Imports
        elif import_pat and import_pat.match(line):
            lp.priority = 50.0
            lp.is_import = True

        # Priority 3: Signatures
        elif sig_pat and sig_pat.match(line):
            lp.priority = 40.0
            lp.is_signature = True

        # Priority 4: File header (first 5 lines)
        elif i < 5:
            lp.priority = 30.0

        # Priority 5: Non-empty lines
        elif line.strip():
            lp.priority = 10.0

        # Priority 6: Empty lines
        else:
            lp.priority = 1.0

        scored.append(lp)

    # Sort by priority (descending), take lines within budget
    scored.sort(key=lambda x: x.priority, reverse=True)

    kept_lines: list[_LinePriority] = []
    char_count = 0
    imports_kept = 0
    sigs_kept = 0

    for lp in scored:
        line_cost = len(lp.text) + 1  # +1 for newline
        if char_count + line_cost > budget_chars:
            continue
        kept_lines.append(lp)
        char_count += line_cost
        if lp.is_import:
            imports_kept += 1
        if lp.is_signature:
            sigs_kept += 1

    # Reconstruct in original order
    kept_lines.sort(key=lambda x: x.line_number)

    # Add truncation marker if we dropped lines
    result_lines = []
    prev_line_num = -1
    for lp in kept_lines:
        if prev_line_num >= 0 and lp.line_number > prev_line_num + 1:
            result_lines.append("# ... (truncated)")
        result_lines.append(lp.text)
        prev_line_num = lp.line_number

    return "\n".join(result_lines), imports_kept, sigs_kept


def _smart_truncate_suffix(text: str, *, budget_chars: int) -> str:
    """Truncate suffix keeping lines closest to cursor."""
    if len(text) <= budget_chars:
        return text

    # For suffix, keep the beginning (closest to cursor)
    lines = text.split("\n")
    kept: list[str] = []
    char_count = 0

    for line in lines:
        line_cost = len(line) + 1
        if char_count + line_cost > budget_chars:
            break
        kept.append(line)
        char_count += line_cost

    if len(kept) < len(lines):
        kept.append("# ... (truncated)")

    return "\n".join(kept)


# ── String Safety ─────────────────────────────────────────────────


def is_inside_string(text: str, position: int, language: str = "python") -> bool:
    """Check if a position in text is inside a string literal.

    Prevents truncation at positions that would break string syntax.
    """
    if position >= len(text):
        return False

    # Simple heuristic: count unescaped quotes before position
    quote_chars = {"python": ('"', "'"), "typescript": ('"', "'", "`")}.get(language, ('"', "'"))

    in_string = False
    current_quote: str | None = None
    i = 0

    while i < position:
        ch = text[i]
        # Check for triple quotes (Python)
        if language == "python" and i + 2 < len(text):
            triple = text[i : i + 3]
            if triple in ('"""', "'''"):
                if in_string and current_quote == triple:
                    in_string = False
                    current_quote = None
                    i += 3
                    continue
                if not in_string:
                    in_string = True
                    current_quote = triple
                    i += 3
                    continue

        if ch in quote_chars and not in_string:
            in_string = True
            current_quote = ch
        elif ch == current_quote and not in_string:
            pass
        elif in_string and ch == current_quote:
            # Check for escape
            if i > 0 and text[i - 1] != "\\":
                in_string = False
                current_quote = None

        i += 1

    return in_string
