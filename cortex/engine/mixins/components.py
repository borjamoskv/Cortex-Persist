"""Components Mixin for CortexEngine.

Provides getters/setters for standard managers and registers default guards.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from cortex.consensus.manager import ConsensusManager
    from cortex.embeddings.manager import EmbeddingManager
    from cortex.engine.auth import ByzantineAuthLayer
    from cortex.engine.lock import SovereignLock
    from cortex.facts.manager import FactManager
    from cortex.ledger import EnrichmentQueue, LedgerStore, LedgerWriter
    from cortex.mac_maestro.executor import MaestroExecutor
    from cortex.engine.guard_pipeline import GuardPipeline

logger = logging.getLogger("cortex.engine.guards")


class ComponentsMixin:
    """Mixin providing manager properties and default guard pipeline registration."""

    # Type annotations for attributes expected on CortexEngine
    _facts: FactManager | None
    _embeddings: EmbeddingManager | None
    _consensus: ConsensusManager | None
    _lock_sovereign: SovereignLock | None
    _auth: ByzantineAuthLayer | None
    _ledger_store: LedgerStore | None
    _enrichment_queue: EnrichmentQueue | None
    _ledger_writer: LedgerWriter | None
    _mac_maestro: MaestroExecutor | None
    _db_path: Path

    @property
    def facts(self) -> FactManager:
        if self._facts is None:
            from cortex.facts.manager import FactManager

            self._facts = FactManager(self)  # type: ignore
        return self._facts

    @facts.setter
    def facts(self, value: FactManager) -> None:
        self._facts = value

    @property
    def embeddings(self) -> EmbeddingManager:
        if self._embeddings is None:
            from cortex.embeddings.manager import EmbeddingManager

            self._embeddings = EmbeddingManager(self)
        return self._embeddings

    @embeddings.setter
    def embeddings(self, value: EmbeddingManager) -> None:
        self._embeddings = value

    @property
    def consensus(self) -> ConsensusManager:
        if self._consensus is None:
            from cortex.consensus.manager import ConsensusManager

            self._consensus = ConsensusManager(self)
        return self._consensus

    @consensus.setter
    def consensus(self, value: ConsensusManager) -> None:
        self._consensus = value

    @property
    def lock_sovereign(self) -> SovereignLock:
        if self._lock_sovereign is None:
            from cortex.engine.lock import SovereignLock

            self._lock_sovereign = SovereignLock(self)
        return self._lock_sovereign

    @lock_sovereign.setter
    def lock_sovereign(self, value: SovereignLock) -> None:
        self._lock_sovereign = value

    @property
    def auth(self) -> ByzantineAuthLayer:
        if self._auth is None:
            from cortex.engine.auth import ByzantineAuthLayer

            self._auth = ByzantineAuthLayer()
        return self._auth

    @auth.setter
    def auth(self, value: ByzantineAuthLayer) -> None:
        self._auth = value

    @property
    def ledger_store(self) -> LedgerStore:
        if self._ledger_store is None:
            from cortex.ledger import LedgerStore

            self._ledger_store = LedgerStore(self._db_path)
        return self._ledger_store

    @ledger_store.setter
    def ledger_store(self, value: LedgerStore) -> None:
        self._ledger_store = value

    @property
    def enrichment_queue(self) -> EnrichmentQueue:
        if self._enrichment_queue is None:
            from cortex.ledger import EnrichmentQueue

            self._enrichment_queue = EnrichmentQueue(self.ledger_store)
        return self._enrichment_queue

    @enrichment_queue.setter
    def enrichment_queue(self, value: EnrichmentQueue) -> None:
        self._enrichment_queue = value

    @property
    def ledger_writer(self) -> LedgerWriter:
        if self._ledger_writer is None:
            from cortex.ledger import LedgerWriter

            self._ledger_writer = LedgerWriter(self.ledger_store, self.enrichment_queue)
        return self._ledger_writer

    @ledger_writer.setter
    def ledger_writer(self, value: LedgerWriter) -> None:
        self._ledger_writer = value

    @property
    def mac_maestro(self) -> MaestroExecutor:
        if self._mac_maestro is None:
            from cortex.mac_maestro.executor import MaestroExecutor

            self._mac_maestro = MaestroExecutor(self.ledger_writer)
        return self._mac_maestro

    @mac_maestro.setter
    def mac_maestro(self, value: MaestroExecutor) -> None:
        self._mac_maestro = value

    def _register_default_guards(self) -> GuardPipeline:
        """Build the GuardPipeline with all available guard adapters.

        Each adapter is imported defensively - if the underlying module
        is not installed, the adapter is skipped. Runtime failures during
        guard construction are treated as fatal because the write path must
        fail closed.
        """
        from cortex.engine.guard_pipeline import GuardPipeline

        pipeline = GuardPipeline()
        db_path = str(self._db_path)
        # Pre-store guards (AX-II Hooks 1-3)
        try:
            from cortex.engine.guard_adapters import HealthGuardAdapter

            pipeline.add_guard(HealthGuardAdapter(self))
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: HealthGuardAdapter failed: {e}") from e
            logger.debug("HealthGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: HealthGuardAdapter failed: {e}") from e
        try:
            from cortex.engine.guard_adapters import ContradictionGuardAdapter

            pipeline.add_guard(ContradictionGuardAdapter(db_path))
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: ContradictionGuardAdapter failed: {e}") from e
            logger.debug("ContradictionGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: ContradictionGuardAdapter failed: {e}") from e
        try:
            from cortex.engine.guard_adapters import VerifierGuardAdapter

            pipeline.add_guard(VerifierGuardAdapter())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: VerifierGuardAdapter failed: {e}") from e
            logger.debug("VerifierGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: VerifierGuardAdapter failed: {e}") from e
        # ZK-Swarm Cryptographic Guard (RFC-003 Phase 1)
        try:
            from cortex.engine.guard_adapters import ZKGuardAdapter

            pipeline.add_guard(ZKGuardAdapter())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: ZKGuardAdapter failed: {e}") from e
            logger.debug("ZKGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: ZKGuardAdapter failed: {e}") from e
        # Virgo Logos-Critique Guard (Virgo ♍)
        try:
            from cortex.engine.guard_adapters import VirgoGuardAdapter

            pipeline.add_guard(VirgoGuardAdapter(self))  # type: ignore
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: VirgoGuardAdapter failed: {e}") from e
            logger.debug("VirgoGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: VirgoGuardAdapter failed: {e}") from e
        # Omega Auditor Guard (Axiom 20)
        try:
            from cortex.engine.guard_adapters import OmegaGuardAdapter

            pipeline.add_guard(OmegaGuardAdapter())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: OmegaGuardAdapter failed: {e}") from e
            logger.debug("OmegaGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: OmegaGuardAdapter failed: {e}") from e
        # Archaeology First Guard (Ley 1)
        try:
            from cortex.engine.guard_adapters import ArchaeologyGuardAdapter

            pipeline.add_guard(ArchaeologyGuardAdapter())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: ArchaeologyGuardAdapter failed: {e}") from e
            logger.debug("ArchaeologyGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: ArchaeologyGuardAdapter failed: {e}") from e
        # Post-store hooks (AX-II Hook 4 + signals + epistemic)
        try:
            from cortex.engine.guard_adapters import LedgerCheckpointHook

            pipeline.add_post_hook(LedgerCheckpointHook(self))  # type: ignore
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: LedgerCheckpointHook failed: {e}") from e
            logger.debug("LedgerCheckpointHook unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: LedgerCheckpointHook failed: {e}") from e
        try:
            from cortex.engine.guard_adapters import SignalEmitHook

            pipeline.add_post_hook(SignalEmitHook())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: SignalEmitHook failed: {e}") from e
            logger.debug("SignalEmitHook unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: SignalEmitHook failed: {e}") from e
        try:
            from cortex.engine.guard_adapters import EpistemicBreakerHook

            pipeline.add_post_hook(EpistemicBreakerHook())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: EpistemicBreakerHook failed: {e}") from e
            logger.debug("EpistemicBreakerHook unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: EpistemicBreakerHook failed: {e}") from e
        logger.debug(
            "GuardPipeline: %d guards, %d hooks registered",
            pipeline.guard_count,
            pipeline.hook_count,
        )
        return pipeline
