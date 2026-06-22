# [C5-REAL] Exergy-Maximized
"""
Git-as-a-Database (GaaD) Arbitrage Engine.
Bypasses SQLite WAL by writing directly to the underlying Git Object DAG.
Used for ultra-high-throughput swarm telemetry that would lock SQLite.
"""

import json
import logging
import subprocess
from typing import Any, Optional

logger = logging.getLogger(__name__)

class GaaDEngine:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        
    def write_blob(self, data: dict[str, Any]) -> Optional[str]:
        """
        Writes a dictionary as a JSON blob directly into .git/objects.
        Returns the SHA-1 hash of the blob.
        """
        try:
            payload = json.dumps(data, sort_keys=True).encode('utf-8')
            # Using git hash-object to write directly to the object database
            process = subprocess.Popen(
                ["git", "hash-object", "-w", "--stdin"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.repo_path
            )
            stdout, stderr = process.communicate(input=payload)
            
            if process.returncode != 0:
                logger.error(f"GaaD Error: {stderr.decode('utf-8')}")
                return None
                
            blob_hash = stdout.decode('utf-8').strip()
            return blob_hash
            
        except Exception as e:
            logger.error(f"GaaD Exception: {str(e)}")
            return None
            
    def read_blob(self, blob_hash: str) -> Optional[dict[str, Any]]:
        """
        Reads a JSON blob from .git/objects given its SHA-1 hash.
        """
        try:
            process = subprocess.Popen(
                ["git", "cat-file", "-p", blob_hash],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.repo_path
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"GaaD Error: {stderr.decode('utf-8')}")
                return None
                
            return json.loads(stdout.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"GaaD Exception: {str(e)}")
            return None
