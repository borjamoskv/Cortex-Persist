"""
CORTEX — Contradiction Guard (Axiom 20: Epistemic Consistency).

Every new decision must explicitly invalidate its predecessors or confirm
compatibility.  This guard runs at store-time and returns potential
conflicts so the agent can disambiguate before persisting.

Strategy (3-layer, O(N) bounded):
  1. FTS5 keyword overlap — fast, coarse.
  2. Project+topic co-occurrence — medium precision.
  3. Negation / supersession detection — high precision.

Returns a ConflictReport with scored candidates.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import aiosqlite

logger = logging.getLogger("cortex.guards.contradiction")

# ── Defaults ────────────────────────────────────────────────────────
from cortex.core.paths import CORTEX_DB as DEFAULT_DB_PATH  # noqa: E402

MAX_CANDIDATES = 10
MIN_OVERLAP_SCORE = 0.10  # Jaccard threshold for keyword overlap


# ── Data classes ────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class ConflictCandidate:
    """A single potentially contradicting decision."""

    fact_id: int
    project: str
    content: str
    date: str
    overlap_score: float
    conflict_type: str  # 'keyword_overlap' | 'negation' | 'version_supersede'

    def __str__(self) -> str:
        return (
            f"[#{self.fact_id}|{self.project}|{self.date}] "
            f"({self.conflict_type}, score={self.overlap_score:.2f}) "
            f"{self.content[:120]}"
        )


@dataclass(slots=True)
class ConflictReport:
    """Result of a contradiction scan."""

    new_content: str
    new_project: str
    candidates: list[ConflictCandidate] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return len(self.candidates) > 0

    @property
    def severity(self) -> str:
        if not self.candidates:
            return "clean"
        max_score = max(c.overlap_score for c in self.candidates)
        if max_score >= 0.6:
            return "high"
        if max_score >= 0.4:
            return "medium"
        return "low"

    def format(self) -> str:
        if not self.has_conflicts:
            return "✅ No contradictions detected."
        lines = [
            f"⚠️ {len(self.candidates)} potential contradiction(s) (severity: {self.severity}):",
        ]
        for c in sorted(self.candidates, key=lambda x: -x.overlap_score):
            lines.append(f"  {c}")
        lines.append("")
        lines.append(
            "ACTION REQUIRED: Add 'Supersedes #ID' or "
            "'Compatible with #ID' to your decision content."
        )
        return "\n".join(lines)


# ── Noise filter ────────────────────────────────────────────────────
_NOISE_PREFIXES = ("MAILTV-1: ARCHIVE",)
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
    }
)

_NEGATION_MARKERS = frozenset(
    {
        "no usar",
        "never use",
        "prohibido",
        "eliminado",
        "forbidden",
        "deprecated",
        "removed",
        "replaced",
        "reemplazado",
        "obsolete",
        "no utilizar",
        "don't use",
        "do not use",
        "eliminamos",
        "matado",
        "killed",
        "purged",
        "deleted",
    }
)

_SUPERSESSION_MARKERS = re.compile(
    r"supersed|replac|obsolet|invalidat|deprecat|"
    r"eliminad|reemplaz|upgrade|migrat|refactor",
    re.IGNORECASE,
)

_VERSION_PATTERN = re.compile(r"\b[vV](\d+(?:\.\d+)*)\b")


# ── Core functions ──────────────────────────────────────────────────
def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from content."""
    tokens = set(re.findall(r"[a-záéíóúñ]{3,}", text.lower()))
    return tokens - _STOP_WORDS


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity coefficient."""
    if not a or not b:
        return 0.0
    intersection = a & b
    union = a | b
    return len(intersection) / len(union) if union else 0.0


def _detect_negation(content: str) -> bool:
    """Check if content contains negation/prohibition language."""
    content_lower = content.lower()
    return any(marker in content_lower for marker in _NEGATION_MARKERS)


def _detect_supersession(content: str) -> bool:
    """Check if content contains supersession language."""
    return bool(_SUPERSESSION_MARKERS.search(content))


def _extract_versions(content: str) -> list[str]:
    """Extract version numbers from content."""
    return _VERSION_PATTERN.findall(content)


def _is_noise(content: str) -> bool:
    """Filter out noise decisions like MAILTV archives."""
    return any(content.startswith(prefix) for prefix in _NOISE_PREFIXES)


# ── Main detector ───────────────────────────────────────────────────
async def detect_contradictions(
    new_content: str,
    new_project: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    decrypt_fn: callable | None = None,  # type: ignore[reportGeneralTypeIssues]
    max_candidates: int = MAX_CANDIDATES,
    min_score: float = MIN_OVERLAP_SCORE,
) -> ConflictReport:
    """
    Scan existing decisions for potential contradictions with new_content.

    Args:
        new_content: The new decision text to check.
        new_project: The project this decision belongs to.
        db_path: Path to the CORTEX database.
        decrypt_fn: Optional decryption function for encrypted content.
        max_candidates: Maximum number of conflict candidates to return.
        min_score: Minimum Jaccard overlap score to consider.

    Returns:
        ConflictReport with ranked candidates.
    """
    if _is_noise(new_content):
        return ConflictReport(new_content, new_project)

    report = ConflictReport(new_content, new_project)
    new_tokens = _tokenize(new_content)

    if len(new_tokens) < 3:
        # Too short to meaningfully compare
        return report

    async with aiosqlite.connect(str(db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        try:
            # Chronos Sniper Guard: Timeout for heavy FTS/Decryption scanning
            if decrypt_fn:
                # Prioritize same-project decisions, then cross-project
                cursor = await conn.execute(
                    """
                    SELECT id, project, content, created_at
                    FROM facts
                    WHERE fact_type = 'decision'
                    ORDER BY
                        CASE WHEN project = ? THEN 0 ELSE 1 END,
                        id DESC
                    LIMIT 400
                    """,
                    (new_project,),
                )
            else:
                # FTS5 path for unencrypted DBs
                fts_terms = " OR ".join(list(new_tokens)[:8])
                cursor = await conn.execute(
                    """
                    SELECT f.id, f.project, f.content, f.created_at
                    FROM facts f
                    JOIN facts_fts fts ON fts.rowid = f.id
                    WHERE fts.facts_fts MATCH ?
                      AND f.fact_type = 'decision'
                    ORDER BY rank
                    LIMIT 200
                    """,
                    (fts_terms,),
                )
            rows = await cursor.fetchall()

            # ── Layer 2: Jaccard scoring + project boosting ─────────
            candidates: list[ConflictCandidate] = []

            for row in rows:
                content = row["content"]

                # Decrypt if needed
                if decrypt_fn and content.startswith("v6_aesgcm:"):
                    try:
                        content = decrypt_fn(content)
                    except Exception:
                        # InvalidTag, cross-tenant, corrupted — skip silently
                        continue

                if not content or _is_noise(content):
                    continue

                existing_tokens = _tokenize(content)
                base_score = _jaccard(new_tokens, existing_tokens)

                # Project boost: same project = 1.3x score
                if row["project"] == new_project:
                    base_score *= 1.3

                if base_score < min_score:
                    continue

                # ── Layer 3: Conflict type classification ───────────
                conflict_type = "keyword_overlap"

                if _detect_negation(new_content) or _detect_negation(content):
                    conflict_type = "negation"
                    base_score *= 1.5  # Boost negation conflicts

                if _detect_supersession(new_content) or _detect_supersession(content):
                    conflict_type = "version_supersede"
                    base_score *= 1.2

                # Version conflict detection
                new_versions = _extract_versions(new_content)
                old_versions = _extract_versions(content)
                if new_versions and old_versions:
                    # Same module but different versions = high conflict potential
                    common_tokens = new_tokens & existing_tokens
                    if len(common_tokens) > 5:
                        conflict_type = "version_supersede"
                        base_score *= 1.4

                candidates.append(
                    ConflictCandidate(
                        fact_id=row["id"],
                        project=row["project"],
                        content=content[:300],
                        date=row["created_at"][:10],
                        overlap_score=min(base_score, 1.0),
                        conflict_type=conflict_type,
                    )
                )

            # Sort by score, keep top N
            candidates.sort(key=lambda c: -c.overlap_score)
            report.candidates = candidates[:max_candidates]

        except (aiosqlite.OperationalError, Exception) as e:
            logger.warning("Contradiction scan failed: %s", e)

    return report


# ── CLI-friendly batch scanner ──────────────────────────────────────
async def scan_all_contradictions(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    decrypt_fn: callable | None = None,  # type: ignore[reportGeneralTypeIssues]
    min_score: float = 0.45,
    limit: int = 50,
) -> list[tuple[ConflictCandidate, ConflictCandidate]]:
    """
    Batch scanner: find pairs of potentially contradicting decisions.
    
    Returns list of (decision_a, decision_b) pairs ordered by overlap.
    """
    async with aiosqlite.connect(str(db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        try:
            cursor = await conn.execute(
                """
                SELECT id, project, content, created_at
                FROM facts
                WHERE fact_type = 'decision'
                ORDER BY id
                """
            )
            rows = await cursor.fetchall()

            # Decrypt and tokenize all
            decisions: list[dict] = []
            for row in rows:
                content = row["content"]
                if decrypt_fn and content.startswith("v6_aesgcm:"):
                    try:
                        content = decrypt_fn(content)
                    except Exception:
                        continue
                if not content or _is_noise(content):
                    continue
                tokens = _tokenize(content)
                if len(tokens) < 3:
                    continue
                decisions.append(
                    {
                        "id": row["id"],
                        "project": row["project"],
                        "content": content,
                        "date": row["created_at"][:10],
                        "tokens": tokens,
                    }
                )

            # ── LSH Bucketing: O(N·logN) ───────────────────────────────
            # Group by project first (cross-project conflicts are rare),
            # then bucket by top-K tokens within each project.
            by_project: dict[str, list[dict]] = defaultdict(list)
            for d in decisions:
                by_project[d["project"]].append(d)

            # Token → decision indices within project (inverted index)
            pairs: list[tuple[float, ConflictCandidate, ConflictCandidate]] = []
            seen_pairs: set[tuple[int, int]] = set()

            for _project, group in by_project.items():
                # Build inverted index: token → list of decision indices
                token_index: dict[str, list[int]] = defaultdict(list)
                for idx, d in enumerate(group):
                    # Use top-8 tokens by length (more specific = better signal)
                    top_tokens = sorted(
                        d["tokens"], key=len, reverse=True
                    )[:8]
                    for token in top_tokens:
                        token_index[token].append(idx)

                # Only compare decisions that share bucket membership
                for _token, indices in token_index.items():
                    if len(indices) < 2 or len(indices) > 50:
                        # Skip tokens that are too common (noise)
                        # or singleton (no comparison possible)
                        continue
                    for i_pos in range(len(indices)):
                        for j_pos in range(i_pos + 1, len(indices)):
                            i, j = indices[i_pos], indices[j_pos]
                            pair_key = (
                                min(group[i]["id"], group[j]["id"]),
                                max(group[i]["id"], group[j]["id"]),
                            )
                            if pair_key in seen_pairs:
                                continue
                            seen_pairs.add(pair_key)

                            a, b = group[i], group[j]
                            score = _jaccard(a["tokens"], b["tokens"])
                            if score < min_score:
                                continue

                            ctype = "keyword_overlap"
                            if _detect_negation(
                                a["content"]
                            ) or _detect_negation(b["content"]):
                                ctype = "negation"
                                score *= 1.3

                            if _detect_supersession(
                                a["content"]
                            ) or _detect_supersession(b["content"]):
                                ctype = "version_supersede"
                                score *= 1.2

                            ca = ConflictCandidate(
                                a["id"],
                                a["project"],
                                a["content"][:200],
                                a["date"],
                                min(score, 1.0),
                                ctype,
                            )
                            cb = ConflictCandidate(
                                b["id"],
                                b["project"],
                                b["content"][:200],
                                b["date"],
                                min(score, 1.0),
                                ctype,
                            )
                            pairs.append((score, ca, cb))

            pairs.sort(key=lambda x: -x[0])
            return [(a, b) for _, a, b in pairs[:limit]]

        except (aiosqlite.OperationalError, Exception) as e:
            logger.warning("Batch contradiction scan failed: %s", e)
            return []
