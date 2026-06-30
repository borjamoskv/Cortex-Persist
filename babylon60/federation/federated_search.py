from decimal import Decimal
# [C5-REAL] Exergy-Maximized
# federated_search.py — Hybrid Cross-Tenant Search Layer
# Operator: borjamoskv | Kernel: MOSKV-1 APEX

import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Optional


class SearchBackend(Enum):
    SQLITE_MERGE = "sqlite_merge"
    QDRANT_FEDERATED = "qdrant_federated"


@dataclass(frozen=True)
class SearchResult:
    tenant_id: str
    doc_id: str
    score: Decimal
    text_snippet: str
    source_hash: str


@dataclass
class FederationConfig:
    """
    Configuración del switch de federación.
    """
    qps_threshold: int = 50
    tenant_threshold: int = 500
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "cortex_federated_index"
    consistency_lag_ms: int = 500
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_s: int = 30


class CircuitBreaker:
    """
    Patrón Circuit Breaker para aislar fallos de Qdrant.
    """

    def __init__(self, threshold: int = 5, recovery_timeout: int = 30):
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "closed"  # "closed" | "open" | "half-open"
        self.last_failure_time: float = 0.0
        self._lock = Lock()

    def record_success(self) -> None:
        with self._lock:
            self.failures = 0
            self.state = "closed"

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            self.last_failure_time = time.monotonic()
            if self.failures >= self.threshold:
                self.state = "open"

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == "closed":
                return True
            now = time.monotonic()
            if self.state == "open" and now - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return True
            return self.state == "half-open"


class QdrantAdapter:
    """
    Adaptador para Qdrant como índice federado con Circuit Breaker integrado.
    """

    def __init__(self, config: FederationConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            threshold=config.circuit_breaker_failure_threshold,
            recovery_timeout=config.circuit_breaker_recovery_timeout_s
        )

    def search(
        self,
        query_embedding: list[float],
        tenant_filter: Optional[list[str]] = None,
        limit: int = 20
    ) -> list[SearchResult]:
        if not self.circuit_breaker.allow_request():
            # Devuelve vacío si el Circuit Breaker está abierto para forzar el fallback
            return []

        try:
            # Simulación de llamada de búsqueda en Qdrant
            # En producción: results = self.client.search(...)
            results: list[SearchResult] = []
            self.circuit_breaker.record_success()
            return results
        except Exception:  # noqa: BLE001
            self.circuit_breaker.record_failure()
            return []

    def upsert_document(
        self,
        tenant_id: str,
        doc_id: str,
        embedding: list[float],
        text: str,
        source_hash: str
    ) -> bool:
        """Inyecta o actualiza un documento en el índice."""
        if not self.circuit_breaker.allow_request():
            return False

        try:
            # Simulación de inserción con idempotencia
            self.circuit_breaker.record_success()
            return True
        except Exception:  # noqa: BLE001
            self.circuit_breaker.record_failure()
            return False


class SQLiteMergeSearch:
    """
    Fallback: Búsqueda por merge-sort sobre N bases SQLite.
    """

    def __init__(self, db_paths: dict[str, str]):
        self.db_paths = db_paths  # tenant_id -> path

    def search(
        self,
        query: str,
        tenant_filter: Optional[list[str]] = None,
        limit: int = 20
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        targets = tenant_filter or list(self.db_paths.keys())

        for tenant_id in targets:
            path = self.db_paths.get(tenant_id)
            if not path:
                continue
            conn = sqlite3.connect(path)
            try:
                cur = conn.execute(
                    "SELECT doc_id, snippet(fts_facts, 0, '', '', '...', 32), "
                    "rank, source_hash "
                    "FROM fts_facts WHERE fts_facts MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (query, limit)
                )
                for row in cur:
                    results.append(SearchResult(
                        tenant_id=tenant_id,
                        doc_id=row[0],
                        score=abs(row[2]),
                        text_snippet=row[1],
                        source_hash=row[3]
                    ))
            except sqlite3.OperationalError:
                continue
            finally:
                conn.close()

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


class FederatedSearchRouter:
    """
    Router inteligente con mitigación de race conditions en telemetría.
    """

    def __init__(
        self,
        config: FederationConfig,
        sqlite_search: SQLiteMergeSearch,
        qdrant_search: QdrantAdapter
    ):
        self.config = config
        self.sqlite = sqlite_search
        self.qdrant = qdrant_search
        self._query_timestamps: list[float] = []
        self._lock = Lock()

    @property
    def current_qps(self) -> float:
        with self._lock:
            now = time.monotonic()
            self._query_timestamps = [
                t for t in self._query_timestamps if now - t < 10.0
            ]
            return len(self._query_timestamps) / 10.0

    def _select_backend(self, tenant_count: int) -> SearchBackend:
        # Si el Circuit Breaker de Qdrant está abierto, forzar SQLiteMerge
        if not self.qdrant.circuit_breaker.allow_request():
            return SearchBackend.SQLITE_MERGE

        if (self.current_qps > self.config.qps_threshold
                or tenant_count > self.config.tenant_threshold):
            return SearchBackend.QDRANT_FEDERATED
        return SearchBackend.SQLITE_MERGE

    def search(
        self,
        query: str,
        query_embedding: Optional[list[float]],
        tenant_count: int,
        tenant_filter: Optional[list[str]] = None,
        limit: int = 20
    ) -> tuple[list[SearchResult], SearchBackend]:
        with self._lock:
            self._query_timestamps.append(time.monotonic())

        backend = self._select_backend(tenant_count)

        if backend == SearchBackend.QDRANT_FEDERATED:
            if query_embedding is None:
                raise ValueError("Qdrant backend requires query_embedding")
            results = self.qdrant.search(
                query_embedding=query_embedding,
                tenant_filter=tenant_filter,
                limit=limit
            )
            # Fallback en caliente si Qdrant no devolvió resultados por fallo o CB
            if not results:
                results = self.sqlite.search(
                    query=query,
                    tenant_filter=tenant_filter,
                    limit=limit
                )
                backend = SearchBackend.SQLITE_MERGE
        else:
            results = self.sqlite.search(
                query=query,
                tenant_filter=tenant_filter,
                limit=limit
            )

        return results, backend


class CDCPipeline:
    """
    Sincronización incremental (Change Data Capture) y Backfill.
    """

    def __init__(self, db_paths: dict[str, str], qdrant: QdrantAdapter):
        self.db_paths = db_paths
        self.qdrant = qdrant

    def execute_backfill(self, tenant_id: str) -> int:
        """
        Ejecuta el backfill completo de un tenant hacia Qdrant.
        """
        path = self.db_paths.get(tenant_id)
        if not path:
            return 0

        conn = sqlite3.connect(path)
        count = 0
        try:
            cur = conn.execute("SELECT doc_id, text, source_hash FROM fts_facts")
            for row in cur:
                doc_id, text, source_hash = row
                # Simular generación de embedding
                embedding = [0.0] * 1536
                success = self.qdrant.upsert_document(
                    tenant_id=tenant_id,
                    doc_id=doc_id,
                    embedding=embedding,
                    text=text,
                    source_hash=source_hash
                )
                if success:
                    count += 1
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
        return count
