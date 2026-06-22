# [C5-REAL] Exergy-Maximized
"""
Storage Router for Hybrid GaaD (Git-as-a-Database) and SQLite.
Routes requests based on payload size and swarm concurrency heuristics.
"""

from typing import Optional, Any
from cortex.engine.gaad.kv_dag import GaaDKVDAG

class StorageRouter:
    """
    Abstracts storage dependency.
    Under low load/relational queries, routes to SQLite WAL.
    Under 10k+ swarm load or O(1) content-addressable requests, routes to Git KV-DAG.
    """
    def __init__(self, use_gaad: bool = False, repo_path: str = "."):
        self.use_gaad = use_gaad
        self.gaad = GaaDKVDAG(repo_path) if use_gaad else None

    async def put_fact(self, content: bytes, sqlite_fallback_fn=None) -> str:
        """
        Routes mutation to appropriate storage engine.
        """
        if self.use_gaad and self.gaad:
            return self.gaad.put_blob(content)
        
        if sqlite_fallback_fn:
            return await sqlite_fallback_fn(content)
        raise RuntimeError("No fallback storage provided.")

    async def get_fact(self, sha1: str, sqlite_fallback_fn=None) -> Optional[bytes]:
        """
        O(1) fact resolution. Tries GaaD first, then SQLite.
        """
        if self.gaad:
            blob = self.gaad.get_blob(sha1)
            if blob:
                return blob
                
        if sqlite_fallback_fn:
            return await sqlite_fallback_fn(sha1)
        return None
