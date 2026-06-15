# [C5-REAL] Exergy-Maximized
"""
Sovereign Sharded Translation Daemon (Translator Daemon)
Listens to 'translation:request' signals on the sharded signal bus,
performs LLM-based technical translation, and emits 'translation:completed' signals.
Supports partition-based concurrency mapping (running separate workers for separate shard ranges).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from google import genai
from google.genai import types

from cortex.compaction.lang_compress import detect_language, estimate_token_savings
from cortex.extensions.signals.bus import _build_query
from cortex.extensions.signals.models import Signal, signal_from_row
from cortex.extensions.signals.sharded_bus import NUM_SHARDS, ShardedAsyncSignalBus

logger = logging.getLogger("cortex.extensions.daemon.translator")


class PartitionedAsyncSignalBus(ShardedAsyncSignalBus):
    """
    Sharded Signal Bus allowing partition-aware polling.
    Allows a worker instance to poll only a specific subset of database shards.
    """

    def __init__(
        self,
        base_dir: Path | str,
        num_shards: int = NUM_SHARDS,
        active_shards: list[int] | None = None,
    ) -> None:
        super().__init__(base_dir, num_shards)
        self.active_shards = active_shards

    async def poll_partition(
        self,
        *,
        tenant_id: str = "default",
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        consumer: str = "default",
        limit: int = 50,
    ) -> list[Signal]:
        if not self._ready:
            await self.initialize()

        query, params = _build_query(
            event_type=event_type,
            source=source,
            project=project,
            tenant_id=tenant_id,
            unconsumed_by=consumer,
            limit=limit,
        )

        shard_indices = (
            self.active_shards if self.active_shards is not None else range(self.num_shards)
        )
        polled_signals = []

        for idx in shard_indices:
            if len(polled_signals) >= limit:
                break

            if idx not in self._shards:
                logger.error(f"Shard connection at index {idx} not initialized")
                continue

            conn = self._shards[idx]
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

            batch = [signal_from_row(tuple(r)) for r in rows][: limit - len(polled_signals)]

            for sig in batch:
                new_consumed = sig.consumed_by + [consumer]
                await conn.execute(
                    "UPDATE signals SET consumed_by = ? WHERE id = ? AND tenant_id = ?",
                    (json.dumps(new_consumed), sig.id, tenant_id),
                )
            if batch:
                await conn.commit()
                polled_signals.extend(batch)

        return polled_signals


class ShardedTranslationDaemon:
    """
    Sovereign Daemon orchestrating distributed translation workers.
    """

    def __init__(
        self,
        shards_dir: Path | str,
        worker_id: str = "translation_worker_0",
        shard_indices: list[int] | None = None,
        poll_interval_s: float = 3.0,
        model: str = "gemini-2.0-flash",
    ):
        self.shards_dir = Path(shards_dir)
        self.worker_id = worker_id
        self.shard_indices = shard_indices
        self.poll_interval_s = poll_interval_s
        self.model = model
        self.bus = PartitionedAsyncSignalBus(self.shards_dir, active_shards=shard_indices)
        self._client: genai.Client | None = None
        self._shutdown = False

    def _get_client(self) -> genai.Client:
        if self._client is None:
            try:
                self._client = genai.Client()
            except Exception as e:
                logger.error(
                    "Failed to initialize google-genai client. Ensure GOOGLE_API_KEY is set."
                )
                raise RuntimeError("Failed to initialize GenAI client") from e
        return self._client

    async def translate_text(
        self, text: str, target_lang: str, source_lang: str | None = None
    ) -> str:
        """Translate text with robust three-tier fallback logic (Gemini -> LLMManager -> Heuristic)."""
        # Tier 1: Gemini API
        try:
            client = self._get_client()
            system_instruction = (
                "You are a precise technical translator for a distributed AI agent ecosystem (CORTEX).\n"
                f"Translate the provided text into '{target_lang}'.\n"
                "Rules:\n"
                "1. Preserve all technical variables, symbols, markdown elements, and identifiers unchanged.\n"
                "2. Preserve code blocks and file paths exactly as in the source.\n"
                "3. Use concise, professional, and dense translation (no conversational fluff).\n"
                "4. Output ONLY the translated content, with absolutely no preamble or explanation."
            )
            if source_lang:
                system_instruction += f"\nSource language: {source_lang}"

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                ),
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"Tier 1 (Gemini API) failed: {e}. Trying Tier 2 (LLMManager)...")

        # Tier 2: Local LLMManager (Ollama / vLLM / OpenRouter)
        try:
            from cortex.extensions.llm.manager import LLMManager

            llm = LLMManager()
            if llm.available:
                prompt = f"Translate the following text to '{target_lang}'. Output ONLY the translation without any preamble:\n\n{text}"
                system = "You are a precise technical translator. Translate and preserve variables/code as-is."
                res = await llm.complete(prompt=prompt, system=system, temperature=0.1)
                if res:
                    return res.strip()
        except Exception as e:
            logger.warning(f"Tier 2 (LLMManager) failed: {e}. Falling back to Tier 3 Heuristic...")

        # Tier 3: Sovereign Heuristic Fallback
        return self.local_heuristic_translate(text, target_lang, source_lang)

    def local_heuristic_translate(
        self, text: str, target_lang: str, source_lang: str | None = None
    ) -> str:
        """Sovereign local heuristic translation fallback."""
        mapping = {
            "es": {
                "en": {
                    "hola": "hello",
                    "mundo": "world",
                    "adiós": "goodbye",
                    "gracias": "thanks",
                    "error": "error",
                    "éxito": "success",
                    "servidor": "server",
                    "demonio": "daemon",
                    "sistema": "system",
                    "distribuido": "distributed",
                    "memoria": "memory",
                    "hecho": "fact",
                    "hechos": "facts",
                }
            },
            "en": {
                "es": {
                    "hello": "hola",
                    "world": "mundo",
                    "goodbye": "adiós",
                    "thanks": "gracias",
                    "error": "error",
                    "success": "éxito",
                    "server": "servidor",
                    "daemon": "demonio",
                    "system": "sistema",
                    "distributed": "distribuido",
                    "memory": "memoria",
                    "fact": "hecho",
                    "facts": "hechos",
                }
            },
        }

        source = (source_lang or "es").lower()
        target = target_lang.lower()

        import re

        words = text.split()
        translated_words = []
        lang_map = mapping.get(source, {}).get(target, {})

        for w in words:
            clean_w = w.lower().strip(".,!?()[]{}:;\"'")
            if clean_w in lang_map:
                sub = lang_map[clean_w]
                if w.istitle():
                    sub = sub.title()
                elif w.isupper():
                    sub = sub.upper()

                # Case-insensitive replacement of clean_w
                pattern = re.compile(re.escape(clean_w), re.IGNORECASE)
                translated_words.append(pattern.sub(sub, w) if clean_w else w)
            else:
                translated_words.append(w)

        return "[OFFLINE FALLBACK]: " + " ".join(translated_words)

    async def process_request(self, signal: Signal) -> None:
        """Process a single translation:request signal."""
        start_time = time.perf_counter()
        payload = signal.payload
        text = payload.get("text", "")
        target_lang = payload.get("target_lang", "en")
        source_lang = payload.get("source_lang")
        correlation_id = payload.get("correlation_id", f"corr-{signal.id}")

        logger.info(
            f"[{self.worker_id}] Processing request for correlation_id={correlation_id} (len={len(text)} chars)"
        )

        if not text:
            await self.emit_failure(correlation_id, "Empty text payload in request")
            return

        # Fallback to language detection if source_lang is not provided
        if not source_lang:
            try:
                source_lang = detect_language(text)
            except Exception:
                source_lang = "unknown"

        try:
            translated_text = await self.translate_text(text, target_lang, source_lang)
            is_offline_fallback = "[OFFLINE FALLBACK]:" in translated_text
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Estimate token savings if translating to English
            tokens_saved = 0
            savings_pct = 0.0
            if target_lang.lower() == "en" and source_lang != "en":
                try:
                    savings = estimate_token_savings(text, source_lang)
                    tokens_saved = savings.get("est_token_savings", 0)
                    savings_pct = savings.get("savings_pct", 0.0)
                except Exception as e:
                    logger.debug(f"Failed to estimate token savings: {e}")

            # Emit completion signal back to the bus using correlation_id as routing key
            await self.bus.emit(
                event_type="translation:completed",
                payload={
                    "translated_text": translated_text,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "correlation_id": correlation_id,
                    "duration_ms": duration_ms,
                    "tokens_saved": tokens_saved,
                    "savings_pct": savings_pct,
                    "worker_id": self.worker_id,
                    "offline_fallback": is_offline_fallback,
                },
                source=self.worker_id,
                project=signal.project,
                routing_key=correlation_id,
            )
            logger.info(
                f"[{self.worker_id}] Successfully translated and emitted completed signal (duration={duration_ms:.1f}ms)"
            )
        except Exception as e:
            logger.exception(f"[{self.worker_id}] Failed to translate text: {e}")
            await self.emit_failure(correlation_id, str(e), signal.project)

    async def emit_failure(
        self, correlation_id: str, error_msg: str, project: str | None = None
    ) -> None:
        try:
            await self.bus.emit(
                event_type="translation:failed",
                payload={
                    "correlation_id": correlation_id,
                    "error": error_msg,
                    "worker_id": self.worker_id,
                },
                source=self.worker_id,
                project=project,
                routing_key=correlation_id,
            )
        except Exception as e:
            logger.error(f"Failed to emit translation:failed signal: {e}")

    async def run_loop(self) -> None:
        """Core execution loop for the daemon with adaptive polling."""
        logger.info(
            f"🚀 {self.worker_id} starting. Shards path={self.shards_dir}, partition_indices={self.shard_indices}"
        )
        await self.bus.initialize()

        current_interval = self.poll_interval_s
        while not self._shutdown:
            try:
                # Poll translation requests using partitioned polling
                signals = await self.bus.poll_partition(
                    event_type="translation:request",
                    consumer=self.worker_id,
                    limit=10,
                )

                if signals:
                    logger.info(f"[{self.worker_id}] Polled {len(signals)} new request(s)")
                    # Process signals concurrently in parallel tasks
                    tasks = [asyncio.create_task(self.process_request(sig)) for sig in signals]
                    await asyncio.gather(*tasks)
                    # Adaptive polling: if we just processed signals, set a tiny poll interval
                    current_interval = 0.1
                else:
                    # No signals: back to standard poll interval
                    current_interval = self.poll_interval_s

            except Exception as e:
                logger.error(f"[{self.worker_id}] Error in translation poll cycle: {e}")
                current_interval = self.poll_interval_s

            await asyncio.sleep(current_interval)

    def stop(self) -> None:
        logger.info(f"Shutting down translator worker {self.worker_id}...")
        self._shutdown = True
