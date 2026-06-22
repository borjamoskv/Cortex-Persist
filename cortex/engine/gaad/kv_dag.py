# [C5-REAL] Exergy-Maximized
"""
Git-as-a-Database (GaaD) KV-DAG Engine.
Bypasses SQLite WAL under massive Swarm load (10k+ concurrent agents).
Uses the local `.git/objects` structure as a content-addressable graph database.
"""

import os
import zlib
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path

class GaaDKVDAG:
    """
    Git KV-DAG structure for O(1) content-addressable storage.
    """
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.objects_dir = self.repo_path / ".git" / "objects"
        
        if not self.objects_dir.exists():
            raise RuntimeError("[C5-REAL] GaaD requires an initialized Git repository.")

    def _hash_object(self, content: bytes, obj_type: str = "blob") -> str:
        header = f"{obj_type} {len(content)}\0".encode("utf-8")
        store = header + content
        return hashlib.sha1(store).hexdigest()

    def put_blob(self, content: bytes) -> str:
        """
        Injects raw fact into Git objects bypassing `git add`.
        """
        header = f"blob {len(content)}\0".encode("utf-8")
        store = header + content
        sha1 = hashlib.sha1(store).hexdigest()
        
        dir_name = sha1[:2]
        file_name = sha1[2:]
        obj_dir = self.objects_dir / dir_name
        
        obj_dir.mkdir(parents=True, exist_ok=True)
        obj_path = obj_dir / file_name
        
        if not obj_path.exists():
            compressed = zlib.compress(store)
            with open(obj_path, "wb") as f:
                f.write(compressed)
                
        return sha1

    def get_blob(self, sha1: str) -> Optional[bytes]:
        """
        O(1) resolution from KV-DAG.
        """
        dir_name = sha1[:2]
        file_name = sha1[2:]
        obj_path = self.objects_dir / dir_name / file_name
        
        if not obj_path.exists():
            return None
            
        with open(obj_path, "rb") as f:
            compressed = f.read()
            store = zlib.decompress(compressed)
            
        # Split header and content
        null_idx = store.find(b"\0")
        if null_idx == -1:
            return None
            
        return store[null_idx + 1:]
