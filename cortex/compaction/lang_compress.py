"""Language Compression Engine — Tokenization Tax Eliminator.

Ω₂: Entropic Asymmetry — The tokenizer doesn't care about culture.
Optimize for its physics. Auto-translates non-English memos to English
for storage, preserving the original language tag for retrieval rendering.

Token savings (cl100k_base / o200k_base):
  - Spanish (es) → English: ~30-50% token reduction
  - Basque (eu)  → English: ~60-75% token reduction
  - Other langs  → English: variable, typically 20-40%

Design:
  - Detection: lightweight heuristic + optional langdetect fallback
  - Translation: Gemini 2.0 Flash (cheap, fast, 1M context)
  - Storage: original content preserved in meta._orig_content
  - Language tag: meta._orig_lang (ISO 639-1)
  - Retrieval: rendering layer checks _orig_lang and can display original
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("cortex.lang_compress")

__all__ = [
    "LangCompressor",
    "CompressionResult",
    "detect_language",
    "estimate_token_savings",
]

# ─── Language Detection (Zero-Dep Heuristic) ─────────────────────────

# Common Spanish stopwords/patterns (high entropy markers)
_ES_MARKERS: frozenset[str] = frozenset({
    "que", "los", "las", "del", "para", "con", "por", "una", "como",
    "más", "pero", "fue", "son", "está", "todo", "también", "cuando",
    "sobre", "entre", "después", "desde", "donde", "cada", "puede",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
    "aquel", "aquella", "muy", "hay", "tiene", "hace", "siendo",
    "otro", "otra", "otros", "otras", "mismo", "misma", "hacia",
    "sino", "según", "durante", "aunque", "porque", "mientras",
    "además", "así", "mejor", "algún", "ningún", "parte",
    "decisión", "error", "proyecto", "memoria", "sesión",
})

# Common Basque markers (agglutinative morphology = high token tax)
_EU_MARKERS: frozenset[str] = frozenset({
    "eta", "bat", "da", "ere", "hau", "bere", "dago", "dira",
    "gara", "beste", "baino", "hori", "hura", "baina", "nola",
    "zer", "zein", "nahi", "egin", "izan", "dut", "dugu",
    "duzu", "dute", "zuen", "gure", "nire", "haien",
    "bertan", "gainera", "beraz", "orduan", "orain", "gero",
    "lehen", "aurrera", "atzera", "goian", "behean",
    "bakoitzak", "guztiak", "batzuk", "gehiago", "gutxiago",
    "azkar", "poliki", "ondo", "gaizki", "berri", "zahar",
})

# Minimum word count for reliable detection
_MIN_WORDS_FOR_DETECTION = 4

# Token ratio estimates (non-English tokens / English tokens for same meaning)
_TOKEN_TAX_RATIOS: dict[str, float] = {
    "es": 1.35,   # Spanish: ~35% more tokens
    "eu": 2.50,   # Basque: ~150% more tokens (agglutinative)
    "fr": 1.25,   # French: ~25% more
    "de": 1.30,   # German: ~30% more (compounds)
    "pt": 1.30,   # Portuguese: ~30% more
    "it": 1.25,   # Italian: ~25% more
    "ja": 1.80,   # Japanese: ~80% more
    "zh": 1.50,   # Chinese: ~50% more
    "ko": 1.70,   # Korean: ~70% more
    "ar": 1.60,   # Arabic: ~60% more
    "ru": 1.50,   # Russian: ~50% more
}


def detect_language(text: str) -> str:
    """Detect language using zero-dependency heuristic.

    Returns ISO 639-1 code. Falls back to 'en' if uncertain.
    O(N) where N = word count, but bounded by first 200 words.
    """
    # Quick reject: very short text or code-like content
    if len(text) < 20:
        return "en"

    # Code detection: skip anything that looks like code
    code_indicators = (
        "def ", "class ", "import ", "from ", "return ",
        "func ", "fn ", "pub ", "let ", "const ", "var ",
        "SELECT ", "INSERT ", "CREATE ", "```",
    )
    if any(indicator in text for indicator in code_indicators):
        return "en"

    # Normalize and tokenize (first 200 words)
    words = re.findall(r"[a-z\u00e0-\u00ff]+", text.lower())[:200]
    if len(words) < _MIN_WORDS_FOR_DETECTION:
        return "en"

    word_set = set(words)

    # Score each language by marker overlap
    es_hits = len(word_set & _ES_MARKERS)
    eu_hits = len(word_set & _EU_MARKERS)

    total = len(words)
    es_ratio = es_hits / total if total > 0 else 0
    eu_ratio = eu_hits / total if total > 0 else 0

    # Basque has priority (higher token tax, distinct morphology)
    if eu_ratio > 0.08 and eu_hits >= 3:
        return "eu"
    if es_ratio > 0.06 and es_hits >= 3:
        return "es"

    # Try optional langdetect if available
    try:
        from langdetect import detect as _detect  # type: ignore[import-untyped]
        detected = _detect(text[:500])
        if detected in _TOKEN_TAX_RATIOS:
            return detected
    except ImportError:
        pass

    return "en"


def estimate_token_savings(text: str, lang: str) -> dict[str, Any]:
    """Estimate token savings from compressing to English.

    Returns dict with estimated metrics. Does NOT actually tokenize.
    """
    ratio = _TOKEN_TAX_RATIOS.get(lang, 1.0)
    word_count = len(text.split())

    # Rough token estimate: ~1.3 tokens per word for English
    est_tokens_original = int(word_count * 1.3 * ratio)
    est_tokens_english = int(word_count * 1.3)
    savings = est_tokens_original - est_tokens_english
    pct = (1 - (1 / ratio)) * 100 if ratio > 1 else 0

    return {
        "lang": lang,
        "token_tax_ratio": ratio,
        "est_tokens_original": est_tokens_original,
        "est_tokens_english": est_tokens_english,
        "est_token_savings": savings,
        "savings_pct": round(pct, 1),
        "word_count": word_count,
    }


# ─── Compression Result ─────────────────────────────────────────────


@dataclass
class CompressionResult:
    """Result of a language compression operation."""

    fact_id: int
    original_lang: str
    original_content: str
    compressed_content: str
    token_savings_est: int
    savings_pct: float
    was_compressed: bool = True
    error: str | None = None


@dataclass
class BatchCompressionResult:
    """Aggregate result of a batch compression run."""

    project: str
    total_facts: int = 0
    compressed: int = 0
    skipped_english: int = 0
    skipped_already: int = 0
    failed: int = 0
    total_token_savings_est: int = 0
    avg_savings_pct: float = 0.0
    results: list[CompressionResult] = field(default_factory=list)
    dry_run: bool = False


# ─── Core Compressor ─────────────────────────────────────────────────


class LangCompressor:
    """Sovereign Language Compression Engine.

    Translates non-English CORTEX facts to English for storage,
    preserving original content and language tag in metadata.
    """

    def __init__(self, model: str = "gemini-2.0-flash"):
        self._model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-init Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client()
            except (ImportError, ValueError, OSError, RuntimeError) as e:
                raise RuntimeError(
                    f"Gemini client initialization failed: {e}. "
                    "Ensure google-genai is installed and GOOGLE_API_KEY is set."
                ) from e
        return self._client

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """Translate text to English using Gemini Flash.

        The prompt is engineered for maximum fidelity:
        - Preserves technical terms, variable names, project references
        - Maintains the semantic density of the original
        - Uses concise English (further reducing tokens)
        """
        from google.genai import types

        client = self._get_client()

        system_prompt = (
            "You are a precise technical translator for an AI memory system. "
            "Translate the following text to concise English. "
            "Rules:\n"
            "1. Preserve ALL technical terms, variable names, and project names as-is\n"
            "2. Preserve code snippets and file paths unchanged\n"
            "3. Use concise, dense English — no fluff or padding\n"
            "4. Maintain the exact meaning and all details\n"
            "5. Output ONLY the translation, no commentary\n"
            f"Source language: {source_lang}"
        )

        response = client.models.generate_content(
            model=self._model,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1,
            ),
        )

        if not response.text:
            raise ValueError("Empty translation response from LLM")

        return response.text.strip()

    def compress_fact(
        self,
        fact_id: int,
        content: str,
        meta: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> CompressionResult:
        """Compress a single fact by translating to English.

        In dry_run mode, skips the LLM call entirely and returns
        estimated savings based on language detection alone.
        """
        meta = meta or {}

        # Already compressed?
        if meta.get("_orig_lang"):
            return CompressionResult(
                fact_id=fact_id,
                original_lang=meta["_orig_lang"],
                original_content=content,
                compressed_content=content,
                token_savings_est=0,
                savings_pct=0.0,
                was_compressed=False,
            )

        # Detect language
        lang = detect_language(content)

        # Already English → skip
        if lang == "en":
            return CompressionResult(
                fact_id=fact_id,
                original_lang="en",
                original_content=content,
                compressed_content=content,
                token_savings_est=0,
                savings_pct=0.0,
                was_compressed=False,
            )

        # Estimate savings
        savings_info = estimate_token_savings(content, lang)

        # Dry run: skip LLM call, return estimate only
        if dry_run:
            return CompressionResult(
                fact_id=fact_id,
                original_lang=lang,
                original_content=content,
                compressed_content="[DRY RUN — not translated]",
                token_savings_est=savings_info["est_token_savings"],
                savings_pct=savings_info["savings_pct"],
                was_compressed=True,
            )

        try:
            translated = self.translate_to_english(content, lang)
        except (RuntimeError, ValueError, OSError) as e:
            logger.error("Translation failed for fact #%d: %s", fact_id, e)
            return CompressionResult(
                fact_id=fact_id,
                original_lang=lang,
                original_content=content,
                compressed_content=content,
                token_savings_est=0,
                savings_pct=0.0,
                was_compressed=False,
                error=str(e),
            )

        return CompressionResult(
            fact_id=fact_id,
            original_lang=lang,
            original_content=content,
            compressed_content=translated,
            token_savings_est=savings_info["est_token_savings"],
            savings_pct=savings_info["savings_pct"],
            was_compressed=True,
        )

    def _decode_fact_row(
        self, row: tuple,
    ) -> tuple[int, str, dict[str, Any]]:
        """Decode a raw DB row into (fact_id, content, meta)."""
        fact_id, raw_content, meta_json = row[0], row[1], row[2]
        try:
            from cortex.crypto import get_default_encrypter
            enc = get_default_encrypter()
            content = enc.decrypt_str(raw_content, tenant_id="default") if raw_content else ""
            meta = enc.decrypt_json(meta_json, tenant_id="default") if meta_json else {}
        except (ImportError, ValueError, TypeError):
            content = raw_content or ""
            meta = json.loads(meta_json) if meta_json else {}
        return fact_id, content, meta if isinstance(meta, dict) else {}

    async def _apply_compression(
        self,
        engine: Any,
        result: CompressionResult,
        meta: dict[str, Any],
    ) -> str | None:
        """Apply compressed content to the engine. Returns error string or None."""
        new_meta = dict(meta)
        new_meta["_orig_lang"] = result.original_lang
        new_meta["_orig_content"] = result.original_content
        new_meta["_lang_compressed"] = True
        try:
            await engine.update(
                fact_id=result.fact_id,
                content=result.compressed_content,
                meta=new_meta,
            )
        except (ValueError, RuntimeError, OSError) as e:
            logger.error("Failed to update fact #%d: %s", result.fact_id, e)
            return str(e)
        return None

    async def compress_project(
        self,
        engine: Any,
        project: str,
        dry_run: bool = False,
        limit: int = 500,
    ) -> BatchCompressionResult:
        """Compress all non-English facts in a project.

        - Detects language for each active fact
        - Translates to English
        - Updates fact content, preserving original in meta._orig_content
        - Tags with meta._orig_lang for retrieval rendering
        """
        batch = BatchCompressionResult(project=project, dry_run=dry_run)

        async with engine.session() as conn:
            cursor = await conn.execute(
                "SELECT id, content, meta FROM facts "
                "WHERE project = ? AND valid_until IS NULL "
                "AND is_tombstoned = 0 ORDER BY id DESC LIMIT ?",
                (project, limit),
            )
            rows = await cursor.fetchall()

        batch.total_facts = len(rows)

        for row in rows:
            fact_id, content, meta = self._decode_fact_row(row)

            if meta.get("_orig_lang"):
                batch.skipped_already += 1
                continue

            result = self.compress_fact(fact_id, content, meta, dry_run=dry_run)

            if not result.was_compressed:
                if result.original_lang == "en":
                    batch.skipped_english += 1
                elif result.error:
                    batch.failed += 1
                continue

            if not dry_run:
                err = await self._apply_compression(engine, result, meta)
                if err:
                    result.was_compressed = False
                    result.error = err
                    batch.failed += 1
                    continue

            batch.compressed += 1
            batch.total_token_savings_est += result.token_savings_est
            batch.results.append(result)

        if batch.compressed > 0:
            batch.avg_savings_pct = sum(
                r.savings_pct for r in batch.results if r.was_compressed
            ) / batch.compressed

        return batch

