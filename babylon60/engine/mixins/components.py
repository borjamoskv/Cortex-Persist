# [C5-REAL] Exergy-Maximized
"""Components Mixin for CortexEngine.

Provides getters/setters for standard managers and registers default guards.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from babylon60.consensus.manager import ConsensusManager
    from babylon60.embeddings.manager import EmbeddingManager
    from babylon60.engine.flow.guard_pipeline import GuardPipeline
    from babylon60.engine.flow.lock import SovereignLock
    from babylon60.facts.manager import FactManager
    from babylon60.ledger import EnrichmentQueue, LedgerStore, LedgerWriter
    from babylon60.mac_maestro.executor import MaestroExecutor
    from babylon60.swarm.auth import ByzantineAuthLayer

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
            from babylon60.facts.manager import FactManager

            self._facts = FactManager(self)  # type: ignore
        return self._facts

    @facts.setter
    def facts(self, value: FactManager) -> None:
        self._facts = value

    @property
    def embeddings(self) -> EmbeddingManager | None:
        if self._embeddings is None:
            try:
                from babylon60.embeddings.manager import EmbeddingManager

                self._embeddings = EmbeddingManager(self)
            except ImportError:
                return None
        return self._embeddings

    @embeddings.setter
    def embeddings(self, value: EmbeddingManager) -> None:
        self._embeddings = value

    @property
    def consensus(self) -> ConsensusManager:
        if self._consensus is None:
            from babylon60.consensus.manager import ConsensusManager

            self._consensus = ConsensusManager(self)
        return self._consensus

    @consensus.setter
    def consensus(self, value: ConsensusManager) -> None:
        self._consensus = value

    @property
    def lock_sovereign(self) -> SovereignLock:
        if self._lock_sovereign is None:
            from babylon60.engine.flow.lock import SovereignLock

            self._lock_sovereign = SovereignLock(self)
        return self._lock_sovereign

    @lock_sovereign.setter
    def lock_sovereign(self, value: SovereignLock) -> None:
        self._lock_sovereign = value

    @property
    def auth(self) -> ByzantineAuthLayer:
        if self._auth is None:
            from babylon60.swarm.auth import ByzantineAuthLayer

            self._auth = ByzantineAuthLayer()
        return self._auth

    @auth.setter
    def auth(self, value: ByzantineAuthLayer) -> None:
        self._auth = value

    @property
    def ledger_store(self) -> LedgerStore:
        if self._ledger_store is None:
            from babylon60.ledger import LedgerStore

            self._ledger_store = LedgerStore(self._db_path)
        return self._ledger_store

    @ledger_store.setter
    def ledger_store(self, value: LedgerStore) -> None:
        self._ledger_store = value

    @property
    def enrichment_queue(self) -> EnrichmentQueue:
        if self._enrichment_queue is None:
            from babylon60.ledger import EnrichmentQueue

            self._enrichment_queue = EnrichmentQueue(self.ledger_store)
        return self._enrichment_queue

    @enrichment_queue.setter
    def enrichment_queue(self, value: EnrichmentQueue) -> None:
        self._enrichment_queue = value

    @property
    def ledger_writer(self) -> LedgerWriter:
        if self._ledger_writer is None:
            from babylon60.ledger import LedgerWriter

            self._ledger_writer = LedgerWriter(self.ledger_store, self.enrichment_queue)
        return self._ledger_writer

    @ledger_writer.setter
    def ledger_writer(self, value: LedgerWriter) -> None:
        self._ledger_writer = value

    @property
    def mac_maestro(self) -> MaestroExecutor:
        if self._mac_maestro is None:
            from babylon60.mac_maestro.executor import MaestroExecutor

            self._mac_maestro = MaestroExecutor(self.ledger_writer)
        return self._mac_maestro

    @mac_maestro.setter
    def mac_maestro(self, value: MaestroExecutor) -> None:
        self._mac_maestro = value

    def _register_default_guards(self) -> GuardPipeline:
        """Build the GuardPipeline with all available guard adapters."""
        from babylon60.engine.flow.guard_pipeline import GuardPipeline

        pipeline = GuardPipeline()
        db_path = str(self._db_path)

        def _health():
            from babylon60.engine.flow.guard_adapters import HealthGuardAdapter

            return HealthGuardAdapter(self)

        def _contradiction():
            from babylon60.engine.flow.guard_adapters import ContradictionGuardAdapter

            return ContradictionGuardAdapter(db_path)

        def _verifier():
            from babylon60.engine.flow.guard_adapters import VerifierGuardAdapter

            return VerifierGuardAdapter()

        def _zk():
            from babylon60.engine.flow.guard_adapters import ZKGuardAdapter

            return ZKGuardAdapter()

        def _virgo():
            from babylon60.engine.flow.guard_adapters import VirgoGuardAdapter

            return VirgoGuardAdapter(self)  # type: ignore

        def _omega():
            from babylon60.engine.flow.guard_adapters import OmegaGuardAdapter

            return OmegaGuardAdapter()

        def _arch():
            from babylon60.engine.flow.guard_adapters import ArchaeologyGuardAdapter

            return ArchaeologyGuardAdapter()

        def _ouroboros_entropy():
            from babylon60.engine.flow.guard_adapters import OuroborosEntropyGuardAdapter

            return OuroborosEntropyGuardAdapter()

        self._try_add(pipeline, "HealthGuardAdapter", _health, is_hook=False)
        self._try_add(pipeline, "ContradictionGuardAdapter", _contradiction, is_hook=False)
        self._try_add(pipeline, "VerifierGuardAdapter", _verifier, is_hook=False)
        self._try_add(pipeline, "ZKGuardAdapter", _zk, is_hook=False)
        self._try_add(pipeline, "VirgoGuardAdapter", _virgo, is_hook=False)
        self._try_add(pipeline, "OmegaGuardAdapter", _omega, is_hook=False)
        self._try_add(pipeline, "ArchaeologyGuardAdapter", _arch, is_hook=False)
        self._try_add(pipeline, "OuroborosEntropyGuardAdapter", _ouroboros_entropy, is_hook=False)

        def _ledger():
            from babylon60.engine.flow.guard_adapters import LedgerCheckpointHook

            return LedgerCheckpointHook(self)  # type: ignore

        def _signal():
            from babylon60.engine.flow.guard_adapters import SignalEmitHook

            return SignalEmitHook()

        def _epistemic():
            from babylon60.engine.flow.guard_adapters import EpistemicBreakerHook

            return EpistemicBreakerHook()

        self._try_add(pipeline, "LedgerCheckpointHook", _ledger, is_hook=True)
        self._try_add(pipeline, "SignalEmitHook", _signal, is_hook=True)
        self._try_add(pipeline, "EpistemicBreakerHook", _epistemic, is_hook=True)

        logger.debug(
            "GuardPipeline: %d guards, %d hooks registered",
            pipeline.guard_count,
            pipeline.hook_count,
        )
        return pipeline

    def _try_add(self, pipeline, name: str, factory, is_hook: bool) -> None:
        try:
            component = factory()
            if is_hook:
                pipeline.add_post_hook(component)
            else:
                pipeline.add_guard(component)
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: {name} failed: {e}") from e
            logger.debug("%s unavailable: %s", name, e)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            raise RuntimeError(f"FAIL-CLOSED: {name} failed: {e}") from e
