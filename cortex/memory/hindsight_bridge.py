"""hindsight_bridge — L4 Episodic Memory Bridge to Hindsight.

DECISION: Ω₃ (Byzantine Default) + Ω₅ (Antifragile by Default)
Hindsight validated independently (Virginia Tech + WaPo, arXiv:2512.12818).
MIT license. Auditable. Forkable.

Architecture:
    CORTEX L1-L3 (existing) ←→ HindsightBridge ←→ Hindsight Server/Embedded

    - Retain: Each cortex.store() also pushes to Hindsight for entity extraction
    - Recall: Hindsight recall fuses with CORTEX RRF for superior retrieval
    - Reflect: Hindsight reflect generates mental models unavailable in CORTEX

Dependencies:
    pip install hindsight-client  (client-only, for remote server)
    pip install hindsight-all     (embedded, includes PG + server)
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("cortex.memory.hindsight")

__all__ = ["HindsightBridge", "HindsightConfig"]


class HindsightConfig:
    """Configuration for the Hindsight bridge.

    Reads from environment variables with CORTEX_HINDSIGHT_ prefix,
    falling back to Hindsight's own HINDSIGHT_API_ vars.
    """

    def __init__(
        self,
        base_url: str | None = None,
        bank_id: str | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        llm_api_key: str | None = None,
        embedded: bool = False,
    ) -> None:
        self.base_url = base_url or os.getenv("CORTEX_HINDSIGHT_URL", "http://localhost:8888")
        self.bank_id = bank_id or os.getenv("CORTEX_HINDSIGHT_BANK", "cortex-sovereign")
        self.llm_provider = llm_provider or os.getenv(
            "CORTEX_HINDSIGHT_LLM_PROVIDER",
            os.getenv("HINDSIGHT_API_LLM_PROVIDER", "gemini"),
        )
        self.llm_model = llm_model or os.getenv(
            "CORTEX_HINDSIGHT_LLM_MODEL",
            os.getenv("HINDSIGHT_API_LLM_MODEL", "gemini-2.5-flash"),
        )
        self.llm_api_key = llm_api_key or os.getenv(
            "CORTEX_HINDSIGHT_LLM_API_KEY",
            os.getenv("HINDSIGHT_API_LLM_API_KEY", ""),
        )
        self.embedded = embedded


class HindsightBridge:
    """Bridge between CORTEX memory and Hindsight agent memory.

    Provides a thin, sovereign interface that:
    1. Wraps Hindsight's retain/recall/reflect as CORTEX-compatible calls
    2. Maps CORTEX fact_types to Hindsight memory networks
    3. Falls back gracefully if Hindsight is unavailable (Ω₅ antifragile)
    """

    _CORTEX_TYPE_MAP: dict[str, str] = {
        # CORTEX fact_type → Hindsight context hint
        "knowledge": "world-fact",
        "decision": "agent-experience",
        "error": "agent-experience",
        "ghost": "observation",
        "bridge": "world-fact",
    }

    def __init__(self, config: HindsightConfig | None = None) -> None:
        self._config = config or HindsightConfig()
        self._client: Any | None = None
        self._server: Any | None = None
        self._available = False

    def connect(self) -> bool:
        """Initialize Hindsight connection. Returns True if available."""
        try:
            if self._config.embedded:
                return self._connect_embedded()
            return self._connect_remote()
        except (ImportError, OSError, ValueError, ConnectionError) as exc:
            logger.warning("Hindsight unavailable — operating in CORTEX-only mode: %s", exc)
            self._available = False
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hindsight unexpected connect error: %s", exc)
            self._available = False
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

            ErrorGhostPipeline().capture_sync(
                exc, source="hindsight:connect", project="CORTEX_SYSTEM"
            )
            return False

    def _connect_remote(self) -> bool:
        """Connect to a running Hindsight server."""
        try:
            from hindsight_client import Hindsight  # type: ignore[import-untyped]

            self._client = Hindsight(base_url=self._config.base_url)
            self._available = True
            logger.info(
                "Hindsight bridge connected (remote: %s, bank: %s)",
                self._config.base_url,
                self._config.bank_id,
            )
            return True
        except ImportError:
            logger.warning("hindsight-client not installed. pip install hindsight-client")
            return False

    def _connect_embedded(self) -> bool:
        """Start an embedded Hindsight server (no Docker required)."""
        try:
            from hindsight import HindsightClient, HindsightServer  # type: ignore[import-untyped]

            self._server = HindsightServer(
                llm_provider=self._config.llm_provider,
                llm_model=self._config.llm_model,
                llm_api_key=self._config.llm_api_key,
            )
            self._server.__enter__()
            self._client = HindsightClient(base_url=self._server.url)
            self._available = True
            logger.info(
                "Hindsight bridge connected (embedded, bank: %s)",
                self._config.bank_id,
            )
            return True
        except ImportError:
            logger.warning("hindsight-all not installed. pip install hindsight-all")
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    # ─── RETAIN ─────────────────────────────────────────────

    def retain(
        self,
        content: str,
        *,
        fact_type: str = "knowledge",
        project: str = "",
        source: str | None = None,
        timestamp: str | None = None,
    ) -> bool:
        """Push a CORTEX fact into Hindsight's episodic memory.

        Maps CORTEX fact_type to a Hindsight context for proper
        routing into World/Experience/Observation networks.
        """
        if not self._available or self._client is None:
            return False

        context = self._CORTEX_TYPE_MAP.get(fact_type, "world-fact")
        full_context = f"{context}|project:{project}" if project else context
        if source:
            full_context += f"|source:{source}"

        try:
            kwargs: dict[str, Any] = {
                "bank_id": self._config.bank_id,
                "content": content,
                "context": full_context,
            }
            if timestamp:
                kwargs["timestamp"] = timestamp

            self._client.retain(**kwargs)
            logger.debug("Hindsight retain OK: %.80s...", content)
            return True
        except (ValueError, TypeError, ConnectionError, OSError) as exc:
            logger.warning("Hindsight retain failed (non-blocking): %s", exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hindsight retain unexpected error (non-blocking): %s", exc)
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

            ErrorGhostPipeline().capture_sync(
                exc, source="hindsight:retain", project="CORTEX_SYSTEM"
            )
            return False

    # ─── RECALL ─────────────────────────────────────────────

    def recall(
        self,
        query: str,
        *,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant memories from Hindsight.

        Returns list of dicts compatible with CORTEX's fact_to_dict format
        for seamless RRF fusion with existing L2 results.
        """
        if not self._available or self._client is None:
            return []

        try:
            results = self._client.recall(
                bank_id=self._config.bank_id,
                query=query,
            )
            # Normalize to CORTEX-compatible format
            normalized: list[dict[str, Any]] = []
            if isinstance(results, list):
                for i, r in enumerate(results[:max_results]):
                    text = r.get("content", str(r)) if isinstance(r, dict) else str(r)
                    mtype = r.get("memory_type", "unknown") if isinstance(r, dict) else "unknown"
                    entry: dict[str, Any] = {
                        "content": text,
                        "source": "hindsight",
                        "rrf_score": 1.0 / (i + 1),
                        "memory_type": mtype,
                    }
                    normalized.append(entry)
            return normalized
        except (ValueError, TypeError, ConnectionError, OSError) as exc:
            logger.warning("Hindsight recall failed (non-blocking): %s", exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hindsight recall unexpected error (non-blocking): %s", exc)
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

            ErrorGhostPipeline().capture_sync(
                exc, source="hindsight:recall", project="CORTEX_SYSTEM"
            )
            return []

    # ─── REFLECT ────────────────────────────────────────────

    def reflect(
        self,
        query: str,
    ) -> str | None:
        """Generate a Hindsight mental model reflection.

        This is the operation CORTEX lacks: disposition-aware reasoning
        over accumulated episodic memory to form beliefs with confidence
        scores that evolve over time.
        """
        if not self._available or self._client is None:
            return None

        try:
            result = self._client.reflect(
                bank_id=self._config.bank_id,
                query=query,
            )
            return str(result) if result else None
        except (ValueError, TypeError, ConnectionError, OSError) as exc:
            logger.warning("Hindsight reflect failed (non-blocking): %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hindsight reflect unexpected error (non-blocking): %s", exc)
            from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

            ErrorGhostPipeline().capture_sync(
                exc, source="hindsight:reflect", project="CORTEX_SYSTEM"
            )
            return None

    # ─── LIFECYCLE ──────────────────────────────────────────

    def close(self) -> None:
        """Shutdown embedded server if running."""
        if self._server is not None:
            try:
                self._server.__exit__(None, None, None)
            except (OSError, RuntimeError):
                pass
            except Exception as e:  # noqa: BLE001
                from cortex.swarm.error_ghost_pipeline import ErrorGhostPipeline

                ErrorGhostPipeline().capture_sync(
                    e, source="hindsight:close", project="CORTEX_SYSTEM"
                )
            self._server = None
        self._client = None
        self._available = False
        logger.info("Hindsight bridge closed.")
