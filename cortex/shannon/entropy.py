"""Shannon Entropy Module — Corpus-Level Information Measurement (Ω₁₃).

Computes Shannon entropy H(X) = -Σ p(x) log₂ p(x) over the fact corpus.
Produces actionable diagnostics: redundancy detection, stagnation warning,
and exergy ratio estimation.

Status: IMPLEMENTED (upgraded from DECORATIVE).
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field

import aiosqlite

__all__ = [
    "ShannonReport",
    "compute_corpus_entropy",
    "compute_fact_entropy",
    "diagnose_health",
]

logger = logging.getLogger("cortex.shannon.entropy")

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "and",
        "or",
        "not",
        "but",
        "this",
        "that",
        "it",
        "its",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "en",
        "un",
        "una",
        "y",
        "o",
        "que",
        "con",
        "por",
        "para",
        "se",
        "es",
        "no",
        "al",
        "su",
        "más",
        "como",
        "pero",
        "sin",
        "sobre",
    }
)

_TOKEN_RE = re.compile(r"[a-záéíóúñü]{3,}", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    """Extract meaningful tokens, excluding stop words."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP_WORDS]


@dataclass
class ShannonReport:
    """Corpus-level Shannon entropy report.

    Attributes:
        total_facts: Number of active facts analyzed.
        total_tokens: Total token count across corpus.
        unique_tokens: Number of distinct semantic tokens.
        entropy_bits: Shannon entropy H(X) in bits.
        max_entropy_bits: Maximum possible entropy (log₂ of unique tokens).
        redundancy_score: 1 - (H / H_max). 0.0 = no redundancy, 1.0 = all identical.
        exergy_ratio: Fraction of information that is non-redundant useful work.
        top_redundant_tokens: Most repeated tokens (potential noise).
    """

    total_facts: int
    total_tokens: int
    unique_tokens: int
    entropy_bits: float
    max_entropy_bits: float
    redundancy_score: float
    exergy_ratio: float
    top_redundant_tokens: list[tuple[str, int]] = field(default_factory=list)


def compute_fact_entropy(content: str) -> float:
    """Compute Shannon entropy for a single fact's content.

    Returns:
        Entropy in bits. Higher = more information diversity.
        0.0 for empty or single-token content.
    """
    tokens = _tokenize(content)
    if len(tokens) < 2:
        return 0.0

    counts = Counter(tokens)
    total = len(tokens)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


async def compute_corpus_entropy(
    conn: aiosqlite.Connection,
    *,
    project: str | None = None,
    tenant_id: str = "default",
    limit: int = 5000,
) -> ShannonReport:
    """Compute Shannon entropy over the active fact corpus.

    Args:
        conn: Active database connection.
        project: Optional project filter.
        tenant_id: Tenant isolation.
        limit: Maximum facts to analyze (performance bound).

    Returns:
        ShannonReport with entropy metrics and diagnostics.
    """
    query = "SELECT content FROM facts " "WHERE valid_until IS NULL AND tenant_id = ?"
    params: list = [tenant_id]

    if project:
        query += " AND project = ?"
        params.append(project)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    try:
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
    except Exception as e:
        logger.warning("Corpus entropy query failed: %s", e)
        return ShannonReport(
            total_facts=0,
            total_tokens=0,
            unique_tokens=0,
            entropy_bits=0.0,
            max_entropy_bits=0.0,
            redundancy_score=0.0,
            exergy_ratio=0.0,
        )

    # Aggregate all tokens
    all_tokens: list[str] = []
    for (content,) in rows:
        if content:
            all_tokens.extend(_tokenize(content))

    total_facts = len(rows)
    total_tokens = len(all_tokens)

    if total_tokens < 2:
        return ShannonReport(
            total_facts=total_facts,
            total_tokens=total_tokens,
            unique_tokens=len(set(all_tokens)),
            entropy_bits=0.0,
            max_entropy_bits=0.0,
            redundancy_score=0.0,
            exergy_ratio=1.0,
        )

    counts = Counter(all_tokens)
    unique = len(counts)
    entropy = 0.0
    for count in counts.values():
        p = count / total_tokens
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(unique) if unique > 1 else 1.0
    redundancy = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.0
    exergy = entropy / max_entropy if max_entropy > 0 else 1.0

    top_redundant = counts.most_common(10)

    report = ShannonReport(
        total_facts=total_facts,
        total_tokens=total_tokens,
        unique_tokens=unique,
        entropy_bits=round(entropy, 4),
        max_entropy_bits=round(max_entropy, 4),
        redundancy_score=round(max(0.0, min(1.0, redundancy)), 4),
        exergy_ratio=round(max(0.0, min(1.0, exergy)), 4),
        top_redundant_tokens=top_redundant,
    )

    logger.info(
        "Shannon corpus analysis: %d facts, H=%.2f bits, redundancy=%.1f%%, exergy=%.1f%%",
        total_facts,
        entropy,
        redundancy * 100,
        exergy * 100,
    )
    return report


def diagnose_health(report: ShannonReport) -> list[str]:
    """Produce actionable recommendations from a ShannonReport.

    Returns:
        List of diagnostic strings.
    """
    diagnostics: list[str] = []

    if report.total_facts == 0:
        diagnostics.append("EMPTY_CORPUS: No active facts found. System has no knowledge.")
        return diagnostics

    if report.redundancy_score > 0.7:
        diagnostics.append(
            f"HIGH_REDUNDANCY ({report.redundancy_score:.0%}): "
            "Corpus contains heavily repeated information. "
            "Run compaction or consolidation to reduce entropy."
        )

    if report.redundancy_score < 0.1 and report.total_facts > 50:
        diagnostics.append(
            f"LOW_REDUNDANCY ({report.redundancy_score:.0%}): "
            "Very diverse corpus — verify that key axioms are sufficiently represented. "
            "Low redundancy may indicate insufficient reinforcement of critical knowledge."
        )

    if report.entropy_bits < 2.0 and report.total_facts > 20:
        diagnostics.append(
            f"LOW_ENTROPY ({report.entropy_bits:.1f} bits): "
            "Knowledge appears stagnant or heavily concentrated. "
            "Consider ingesting diverse sources."
        )

    if report.exergy_ratio < 0.5:
        diagnostics.append(
            f"LOW_EXERGY ({report.exergy_ratio:.0%}): "
            "More than half the stored information is redundant. "
            "Significant waste in storage and retrieval cost."
        )

    # Check for dominant tokens
    if report.top_redundant_tokens:
        top_token, top_count = report.top_redundant_tokens[0]
        dominance = top_count / max(report.total_tokens, 1)
        if dominance > 0.05:
            diagnostics.append(
                f"TOKEN_DOMINANCE: '{top_token}' appears {top_count} times "
                f"({dominance:.1%} of corpus). May indicate topic bias."
            )

    if not diagnostics:
        diagnostics.append("HEALTHY: Corpus entropy within normal parameters.")

    return diagnostics
