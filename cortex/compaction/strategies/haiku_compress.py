"""CORTEX v8 — Haiku Poet-Compactor (Swarm-Driven Semantic Compression).

3-agent swarm for distilling facts into 5-7-5 English haikus:
  - Poet Agent:  Generates N candidate haikus (creative, temp=0.9)
  - Critic Agent: Scores semantic fidelity of each candidate (analytical, temp=0.1)
  - Judge Agent:  Validates 5-7-5 structure, selects best candidate

Design:
  - Retroactive batch mode is configurable
  - Additive: haiku stored in metadata, original content stays intact
  - English-only output by default regardless of source language
  - Zero data loss (Ω₃ cycle safety)
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.compaction.haiku")

__all__ = [
    "HaikuCompressConfig",
    "HaikuSwarm",
    "ComposeHaikuResult",
    "HaikuResult",
    "BatchHaikuResult",
    "execute_haiku_compress",
    "SwarmCollapseError",
    "ExergyExhaustionError",
]

class SwarmCollapseError(RuntimeError):
    """Raised when the swarm hits the Thermal Fuse due to semantic or API collapse."""
    pass

class ExergyExhaustionError(RuntimeError):
    """Raised when the maximum LLM call limit is breached."""
    pass



# ─── Config ──────────────────────────────────────────────────────────


@dataclass(slots=True)
class HaikuCompressConfig:
    """Runtime configuration for the haiku compaction strategy."""

    enabled: bool = False
    retroactive: bool = False
    model: str = "gemini-2.5-pro"
    num_candidates: int = 3
    min_content_len: int = 30
    limit: int = 500
    strict_575: bool = True
    min_fidelity: float = 0.60
    language: str = "English"
    store_key: str = "_haiku"
    store_fidelity_key: str = "_haiku_fidelity"
    store_candidates_key: str = "_haiku_candidates"
    max_llm_calls_per_batch: int = 1500


# ─── Result Dataclasses ──────────────────────────────────────────────


@dataclass(slots=True)
class ComposeHaikuResult:
    """Outcome of the internal Poet → Critic → Judge pipeline."""

    haiku: str
    fidelity_score: float
    candidates_generated: int
    was_composed: bool = True
    error: str | None = None


@dataclass(slots=True)
class HaikuResult:
    """Outcome of a single fact haiku compression."""

    fact_id: int
    haiku: str
    fidelity_score: float
    candidates_generated: int
    was_composed: bool = True
    error: str | None = None


@dataclass(slots=True)
class BatchHaikuResult:
    """Aggregate result of a haiku batch."""

    project: str
    total_facts: int = 0
    composed: int = 0
    skipped_existing: int = 0
    skipped_short: int = 0
    failed: int = 0
    dry_run: bool = False
    aborted: bool = False
    results: list[HaikuResult] = field(default_factory=list)


@dataclass(slots=True)
class _ScoredCandidate:
    """Internal: a haiku candidate with its fidelity score."""

    haiku: str
    fidelity: float


# ─── Agent System Prompts ────────────────────────────────────────────


_POET_SYSTEM = (
    "You are a sovereign poet. Your art is compression — distilling knowledge "
    "into haiku (5-7-5 syllable structure). You write in {language} only.\n\n"
    "Rules:\n"
    "1. Each haiku MUST have exactly 3 lines: 5 syllables, 7 syllables, 5 syllables\n"
    "2. Preserve the semantic essence of the input — the core meaning must survive\n"
    "3. Be beautiful. Be sharp. No filler words. Every syllable earns its place\n"
    "4. Write in {language} regardless of the input language\n"
    "5. Output ONLY the haiku lines, nothing else — no titles, no commentary\n"
    "6. Separate each haiku with a blank line\n\n"
    "Generate exactly {n} different haiku candidates for the given content. "
    "Each must capture the same core meaning from a different aesthetic angle."
)

_CRITIC_SYSTEM = (
    "You are a semantic fidelity analyst. Given an original text and several haiku "
    "candidates, score each haiku's semantic fidelity to the original on a scale "
    "of 0.0 to 1.0.\n\n"
    "Scoring criteria:\n"
    "- 1.0 = Perfect semantic compression — all essential meaning preserved\n"
    "- 0.7 = Good — core meaning intact, minor nuance lost\n"
    "- 0.4 = Partial — captures theme but misses key details\n"
    "- 0.1 = Poor — tangentially related at best\n\n"
    'Respond with a JSON array of objects: [{"haiku": "...", "fidelity": 0.X}, ...]\n'
    "Output ONLY the JSON array, no commentary."
)

_JUDGE_SYSTEM = (
    "You are a structural judge for haiku validation. Given scored haiku candidates, "
    "select the single best one that:\n"
    "1. Has the highest semantic fidelity score\n"
    "2. Follows valid 5-7-5 syllable structure\n"
    "3. Is aesthetically compelling\n\n"
    "If a top candidate has questionable syllable count, prefer the next-best "
    "structurally valid one.\n\n"
    "Respond with ONLY the selected haiku (3 lines), nothing else."
)


# ─── HaikuSwarm ──────────────────────────────────────────────────────


class HaikuSwarm:
    """3-agent swarm for haiku generation via LLM."""

    def __init__(self, config: HaikuCompressConfig | None = None) -> None:
        self.config = config or HaikuCompressConfig()
        self._model = self.config.model
        self._client: Any = None
        self._llm_calls_made = 0

    def _get_client(self) -> Any:
        """Lazy-init Gemini client."""
        if self._client is None:
            try:
                from google import genai  # type: ignore[attr-defined]

                self._client = genai.Client()
            except (ImportError, ValueError, OSError, RuntimeError) as e:
                raise RuntimeError(
                    f"Gemini client init failed: {e}. "
                    "Ensure google-genai is installed and GOOGLE_API_KEY is set."
                ) from e
        return self._client

    def _call_llm(self, system: str, user: str, temperature: float = 0.5) -> str:
        """Single LLM invocation with system + user prompt and Viscosity Backoff."""
        import time

        from google.genai import types

        client = self._get_client()
        
        for attempt in range(1, 4):  # max 3 tries
            if self._llm_calls_made >= self.config.max_llm_calls_per_batch:
                raise ExergyExhaustionError("Max LLM call ceiling reached")
            
            self._llm_calls_made += 1
            try:
                response = client.models.generate_content(
                    model=self._model,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=temperature,
                    ),
                )
                if not response.text:
                    raise ValueError("Empty LLM response")
                return response.text.strip()
            except Exception as e:
                if attempt == 3:
                    raise RuntimeError(f"LLM call failed after 3 attempts: {e}") from e
                
                wait_time = (2 ** (attempt - 1)) * 1.5
                logger.warning(
                    "LLM thermal backoff triggered. Attempt %d failed (%s). "
                    "Waiting %.1fs...",
                    attempt,
                    type(e).__name__,
                    wait_time,
                )
                time.sleep(wait_time)
        
        raise RuntimeError("LLM call failed unexpectedly")

    # ─── Agent: Poet ─────────────────────────────────────────────────

    def _poet_agent(self, content: str, fact_type: str) -> list[str]:
        """Generate N haiku candidates from fact content."""
        system = _POET_SYSTEM.format(
            n=self.config.num_candidates,
            language=self.config.language,
        )
        user = (
            f"Fact type: {fact_type}\n"
            f"Content to compress into haiku:\n\n{content}"
        )
        raw = self._call_llm(system, user, temperature=0.9)

        candidates = [c.strip() for c in re.split(r"\n\s*\n", raw) if c.strip()]

        if len(candidates) < 2:
            lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
            regrouped: list[str] = []
            for i in range(0, len(lines), 3):
                chunk = lines[i : i + 3]
                if len(chunk) == 3 and all(chunk):
                    regrouped.append("\n".join(chunk))
            candidates = regrouped

        trimmed = candidates[: self.config.num_candidates]
        logger.info("Poet agent generated %d candidates", len(trimmed))
        return trimmed

    # ─── Agent: Critic ───────────────────────────────────────────────

    def _critic_agent(
        self, original: str, candidates: list[str]
    ) -> list[_ScoredCandidate]:
        """Score each candidate for semantic fidelity against original."""
        candidates_text = "\n\n".join(
            f"Candidate {i + 1}:\n{c}" for i, c in enumerate(candidates)
        )
        user = (
            f"Original text:\n{original}\n\n"
            f"Haiku candidates:\n{candidates_text}"
        )
        raw = self._call_llm(_CRITIC_SYSTEM, user, temperature=0.1)
        scored = self._parse_critic_response(raw, candidates)

        logger.info(
            "Critic agent scored %d candidates: %s",
            len(scored),
            [(s.fidelity, s.haiku[:20]) for s in scored],
        )
        return scored

    @staticmethod
    def _parse_critic_response(
        raw: str, fallback_candidates: list[str]
    ) -> list[_ScoredCandidate]:
        """Extract scored candidates from critic JSON response.

        Only accepts haikus that match the supplied candidate set.
        Falls back to uniform 0.5 scores on parse failure or empty valid output.
        """
        if not raw or not raw.strip():
            return [
                _ScoredCandidate(haiku=c, fidelity=0.5)
                for c in fallback_candidates
            ]

        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        allowed = set(fallback_candidates)

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                out: list[_ScoredCandidate] = []
                for item in parsed:
                    if not isinstance(item, dict):
                        continue

                    haiku = str(item.get("haiku", "")).strip()
                    if not haiku or haiku not in allowed:
                        continue

                    try:
                        fidelity = float(item.get("fidelity", 0.5))
                    except (TypeError, ValueError):
                        fidelity = 0.5

                    fidelity = max(0.0, min(1.0, fidelity))
                    out.append(_ScoredCandidate(haiku=haiku, fidelity=fidelity))

                if out:
                    return out
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Critic response parse failed, using uniform scores")

        return [
            _ScoredCandidate(haiku=c, fidelity=0.5) for c in fallback_candidates
        ]

    # ─── Agent: Judge ────────────────────────────────────────────────

    def _judge_agent(self, scored: list[_ScoredCandidate]) -> str | None:
        """Select the best structurally valid haiku."""
        from cortex.immune.haiku import HaikuGuard

        ranked = sorted(scored, key=lambda s: s.fidelity, reverse=True)

        if self.config.strict_575:
            for candidate in ranked:
                if HaikuGuard.validate(candidate.haiku):
                    logger.info(
                        "Judge selected haiku (fidelity=%.2f): %s",
                        candidate.fidelity,
                        candidate.haiku.replace("\n", " / "),
                    )
                    return candidate.haiku

            logger.warning("No candidate passed HaikuGuard, invoking LLM judge")
            candidates_text = "\n\n".join(
                f"[fidelity={s.fidelity:.2f}]\n{s.haiku}" for s in ranked
            )
            try:
                selected = self._call_llm(
                    _JUDGE_SYSTEM, candidates_text, temperature=0.1
                )
                if HaikuGuard.validate(selected):
                    return selected
            except (ValueError, RuntimeError) as e:
                logger.warning("Judge LLM fallback failed: %s", e)

        if ranked:
            logger.warning("Accepting best candidate without strict validation")
            return ranked[0].haiku
        return None

    # ─── Full Pipeline ───────────────────────────────────────────────

    def compose(
        self, content: str, fact_type: str = "knowledge"
    ) -> ComposeHaikuResult:
        """Run the full Poet → Critic → Judge pipeline for a single fact."""
        candidates = self._poet_agent(content, fact_type)
        if not candidates:
            return ComposeHaikuResult(
                haiku="",
                fidelity_score=0.0,
                candidates_generated=0,
                was_composed=False,
                error="Poet agent produced no candidates",
            )

        scored = self._critic_agent(content, candidates)
        best = self._judge_agent(scored)
        if not best:
            return ComposeHaikuResult(
                haiku="",
                fidelity_score=0.0,
                candidates_generated=len(candidates),
                was_composed=False,
                error="Judge could not select a valid haiku",
            )

        fidelity = next((s.fidelity for s in scored if s.haiku == best), 0.5)

        if fidelity < self.config.min_fidelity:
            return ComposeHaikuResult(
                haiku="",
                fidelity_score=fidelity,
                candidates_generated=len(candidates),
                was_composed=False,
                error=(
                    f"Selected haiku fidelity {fidelity:.2f} "
                    f"below minimum {self.config.min_fidelity:.2f}"
                ),
            )

        return ComposeHaikuResult(
            haiku=best,
            fidelity_score=fidelity,
            candidates_generated=len(candidates),
            was_composed=True,
        )

    # ─── Single Fact Compression ─────────────────────────────────────

    def compress_fact(
        self,
        fact_id: int,
        content: str,
        meta: dict[str, Any] | str | None = None,
        dry_run: bool = False,
    ) -> HaikuResult:
        """Compress a single fact into a haiku."""
        decoded_meta = self._decode_meta(meta)

        if decoded_meta.get(self.config.store_key):
            return HaikuResult(
                fact_id=fact_id,
                haiku=str(decoded_meta[self.config.store_key]),
                fidelity_score=1.0,
                candidates_generated=0,
                was_composed=False,
            )

        if len(content) < self.config.min_content_len:
            return HaikuResult(
                fact_id=fact_id,
                haiku="",
                fidelity_score=0.0,
                candidates_generated=0,
                was_composed=False,
                error="Content too short for haiku compression",
            )

        if dry_run:
            return HaikuResult(
                fact_id=fact_id,
                haiku="[DRY RUN — not composed]",
                fidelity_score=0.0,
                candidates_generated=0,
                was_composed=True,
            )

        try:
            fact_type = str(decoded_meta.get("fact_type", "knowledge"))
            composed = self.compose(content, fact_type)
            return HaikuResult(
                fact_id=fact_id,
                haiku=composed.haiku,
                fidelity_score=composed.fidelity_score,
                candidates_generated=composed.candidates_generated,
                was_composed=composed.was_composed,
                error=composed.error,
            )
        except (RuntimeError, ValueError, OSError) as e:
            logger.error("Haiku composition failed for fact #%d: %s", fact_id, e)
            return HaikuResult(
                fact_id=fact_id,
                haiku="",
                fidelity_score=0.0,
                candidates_generated=0,
                was_composed=False,
                error=str(e),
            )

    # ─── Retroactive Batch ───────────────────────────────────────────

    async def compress_project(
        self,
        engine: CortexEngine,
        project: str,
        dry_run: bool = False,
        limit: int | None = None,
    ) -> BatchHaikuResult:
        """Retroactively compress all facts in a project into haikus."""
        batch = BatchHaikuResult(project=project, dry_run=dry_run)
        row_limit = limit if limit is not None else self.config.limit

        conn = await engine.get_conn()
        async with conn.execute(
            "SELECT id, content, metadata, fact_type FROM facts "
            "WHERE project = ? AND valid_until IS NULL "
            "ORDER BY id DESC LIMIT ?",
            (project, row_limit),
        ) as cursor:
            rows = await cursor.fetchall()

        batch.total_facts = len(rows)
        consecutive_failures = 0

        for row in rows:
            fact_id = row[0]
            content = row[1] or ""
            meta = self._decode_meta(row[2])
            fact_type = row[3] or "knowledge"
            meta.setdefault("fact_type", fact_type)

            result = self.compress_fact(
                fact_id=fact_id,
                content=content,
                meta=meta,
                dry_run=dry_run,
            )

            if not result.was_composed:
                if meta.get(self.config.store_key):
                    batch.skipped_existing += 1
                elif result.error and "too short" in result.error.lower():
                    batch.skipped_short += 1
                else:
                    batch.failed += 1
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        logger.error("Swarm Thermal Fuse snapped: 5 consecutive failures. Aborting batch.")
                        batch.aborted = True
                        break
                continue
            
            consecutive_failures = 0

            if not dry_run and result.haiku:
                new_meta = dict(meta)
                new_meta[self.config.store_key] = result.haiku
                new_meta[self.config.store_fidelity_key] = result.fidelity_score
                new_meta[self.config.store_candidates_key] = (
                    result.candidates_generated
                )

                try:
                    await engine.update(
                        fact_id=fact_id,
                        meta=new_meta,
                    )
                except (ValueError, RuntimeError, OSError) as e:
                    logger.error(
                        "Failed to persist haiku for fact #%d: %s",
                        fact_id,
                        e,
                    )
                    result.was_composed = False
                    result.error = str(e)
                    batch.failed += 1
                    continue

            batch.composed += 1
            batch.results.append(result)

        return batch

    @staticmethod
    def _decode_meta(raw: Any) -> dict[str, Any]:
        """Decode metadata from DB row or callsite input."""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, TypeError, ValueError):
                return {}
        return {}


# ─── Strategy Adapter ────────────────────────────────────────────────


async def execute_haiku_compress(
    engine: CortexEngine,
    project: str,
    result: Any,
    dry_run: bool,
    config: HaikuCompressConfig | None = None,
) -> None:
    """Strategy adapter for compactor.py integration.

    Unlike destructive strategies, haiku_compress enriches metadata.
    """
    cfg = config or HaikuCompressConfig()

    if not cfg.enabled:
        result.details.append("haiku_compress: disabled")
        return

    swarm = HaikuSwarm(cfg)

    if not cfg.retroactive:
        result.details.append("haiku_compress: enabled but retroactive=false")
        return

    try:
        batch = await swarm.compress_project(
            engine=engine,
            project=project,
            dry_run=dry_run,
            limit=cfg.limit,
        )
    except (RuntimeError, ValueError, OSError) as e:
        logger.error("Haiku swarm failed for project %s: %s", project, e)
        result.details.append(f"haiku_compress: FAILED — {e}")
        return

    detail = (
        f"haiku_compress: {batch.composed} haikus composed, "
        f"{batch.skipped_existing} already had haiku, "
        f"{batch.skipped_short} too short, "
        f"{batch.failed} failed"
    )
    if batch.aborted:
        detail += " [ABORTED BY THERMAL FUSE]"
        
    result.details.append(detail)
    logger.info("Compactor [%s] %s", project, detail)
