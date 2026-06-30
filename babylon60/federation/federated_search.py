# [C5-REAL] Exergy-Maximized
# federated_search.py — Hybrid Cross-Tenant Search Layer
# Operator: borjamoskv | Kernel: MOSKV-1 APEX

from dataclasses import dataclass
from typing import List, Optional, Protocol
from enum import Enum
import time
import sqlite3


class SearchBackend(Enum):
    SQLITE_MERGE = "sqlite_merge"
    QDRANT_FEDERATED = "qdrant_federated"


@dataclass(frozen=True)
class SearchResult:
    tenant_id: str
    doc_id: str
    score: float
    text_snippet: str
    source_hash: str


@dataclass
class FederationConfig:
    """
    Configuración del switch de federación.
    
    El sistema opera en modo SQLite merge-sort hasta que se
    superan los umbrales. Entonces activa Qdrant automáticamente.
    """
    qps_threshold: int = 50
    tenant_threshold: int = 500
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "cortex_federated_index"
    consistency_lag_ms: int = 500


class QdrantAdapter:
    """
    Adaptador para Qdrant como índice federado.
    
    Responsabilidades:
    - Upsert de documentos desde CDC pipeline
    - Búsqueda vectorial + FTS con filtro por tenant
    - Verificación de consistencia contra SQLite source-of-truth
    """

    def __init__(self, config: FederationConfig):
        self.config = config
        # from qdrant_client import QdrantClient
        # self.client = QdrantClient(url=config.qdrant_url)

    def search(
        self,
        query_embedding: List[float],
        tenant_filter: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Búsqueda vectorial federada.
        
        Si tenant_filter es None, busca en TODOS los tenants.
        Si se especifica, filtra solo esos tenants (ACL check previo).
        """
        # TODO: Implementar con qdrant_client
        # filter_conditions = {}
        # if tenant_filter:
        #     filter_conditions = {
        #         "must": [{"key": "tenant_id",
        #                   "match": {"any": tenant_filter}}]
        #     }
        # results = self.client.search(
        #     collection_name=self.config.collection_name,
        #     query_vector=query_embedding,
        #     query_filter=filter_conditions,
        #     limit=limit
        # )
        return []

    def upsert_document(
        self,
        tenant_id: str,
        doc_id: str,
        embedding: List[float],
        text: str,
        source_hash: str
    ) -> None:
        """Inyecta o actualiza un documento en el índice."""
        # TODO: Implementar upsert con verificación de idempotencia
        pass


class SQLiteMergeSearch:
    """
    Fallback: Búsqueda por merge-sort sobre N bases SQLite.
    O(N) pero funcional para bajo volumen.
    """

    def __init__(self, db_paths: dict[str, str]):
        self.db_paths = db_paths  # tenant_id -> path

    def search(
        self,
        query: str,
        tenant_filter: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
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
    Router inteligente que decide qué backend usar
    basándose en métricas operacionales en tiempo real.
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

    @property
    def current_qps(self) -> float:
        now = time.monotonic()
        # Ventana de 10 segundos
        self._query_timestamps = [
            t for t in self._query_timestamps if now - t < 10.0
        ]
        return len(self._query_timestamps) / 10.0

    def _select_backend(self, tenant_count: int) -> SearchBackend:
        if (self.current_qps > self.config.qps_threshold
                or tenant_count > self.config.tenant_threshold):
            return SearchBackend.QDRANT_FEDERATED
        return SearchBackend.SQLITE_MERGE

    def search(
        self,
        query: str,
        query_embedding: Optional[List[float]],
        tenant_count: int,
        tenant_filter: Optional[List[str]] = None,
        limit: int = 20
    ) -> tuple[List[SearchResult], SearchBackend]:
        self._query_timestamps.append(time.monotonic())
        backend = self._select_backend(tenant_count)

        if backend == SearchBackend.QDRANT_FEDERATED:
            if query_embedding is None:
                raise ValueError(
                    "Qdrant backend requires query_embedding"
                )
            results = self.qdrant.search(
                query_embedding=query_embedding,
                tenant_filter=tenant_filter,
                limit=limit
            )
        else:
            results = self.sqlite.search(
                query=query,
                tenant_filter=tenant_filter,
                limit=limit
            )

        return results, backend
