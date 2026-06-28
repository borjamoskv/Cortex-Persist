# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Thermodynamic Apoptosis Daemon.

Enforces structural entropy reduction (Context Rot eradication).
Scans the cortex/ repository for thermodynamically dead modules
(0 external references & > 7 days untouched) and physically purges them via `git rm`.
"""

import ast
import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.database.core import connect_async_ctx

logger = logging.getLogger("cortex.daemon.apoptosis")

class ApoptosisDaemon:
    """The Grim Reaper of Context Rot."""
    
    def __init__(self, repo_path: Path, db_path: str = "cortex_ledger.db"):
        self.repo_path = repo_path
        self.cortex_dir = repo_path / "cortex"
        self.db_path = db_path
        self.decay_threshold_days = 7
        
    def _is_untouched(self, filepath: Path) -> bool:
        """Check if the file has been untouched for > 7 days using git."""
        try:
            # Get the Unix timestamp of the last commit modifying this file
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct", "--", str(filepath)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            timestamp_str = result.stdout.strip()
            if not timestamp_str:
                # File might be untracked. We don't apoptose untracked files automatically here.
                return False
                
            last_commit_time = int(timestamp_str)
            current_time = int(time.time())
            days_untouched = (current_time - last_commit_time) / 86400.0
            
            return days_untouched > self.decay_threshold_days
            
        except subprocess.CalledProcessError:
            return False
            
    def _extract_exports(self, filepath: Path) -> list[str]:
        """Extract all Class and Function names defined in the file using AST."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                node = ast.parse(f.read(), filename=str(filepath))
                
            exports = []
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not child.name.startswith("_"):
                        exports.append(child.name)
            return exports
        except SyntaxError:
            return []
            
    def _has_external_references(self, filepath: Path, exports: list[str]) -> bool:
        """Check if any of the exports are referenced in other files in cortex/."""
        if not exports:
            # If a file exports nothing public, it might be a script.
            # Check if its filename is imported.
            module_name = filepath.stem
            exports = [module_name]
            
        # We use a simple but rigorous heuristic: ripgrep or standard string matching
        # across all .py files.
        for py_file in self.cortex_dir.rglob("*.py"):
            if py_file.resolve() == filepath.resolve():
                continue
                
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    for exp in exports:
                        if exp in content:
                            return True
            except Exception:
                continue
                
        return False
        
    def _is_protected(self, filepath: Path) -> bool:
        """Prevent apoptosis of core system files."""
        name = filepath.name
        if name in ("__init__.py", "__main__.py", "config.py"):
            return True
        # Protect specific directories
        if "cli" in filepath.parts or "migrations" in filepath.parts:
            return True
        return False

    async def execute_purge(self) -> int:
        """
        Scan all files, find dead modules, and trigger git rm.
        Returns the number of purged files.
        """
        purged_count = 0
        
        async with connect_async_ctx(self.db_path) as conn:
            ledger = EnterpriseAuditLedger(conn)
            await ledger.ensure_table()
            
            for py_file in self.cortex_dir.rglob("*.py"):
                if self._is_protected(py_file):
                    continue
                    
                # 1. Check Age
                if not self._is_untouched(py_file):
                    continue
                    
                # 2. Extract public symbols
                exports = self._extract_exports(py_file)
                
                # 3. Check for external references
                if self._has_external_references(py_file, exports):
                    continue
                    
                # 4. Apoptosis execution
                logger.critical(f"[APOPTOSIS] Thermodynamic death of unreferenced module: {py_file.name}")
                try:
                    subprocess.run(
                        ["git", "rm", "-f", str(py_file)],
                        cwd=self.repo_path,
                        check=True,
                        capture_output=True
                    )
                    
                    await ledger.log_action(
                        tenant_id="global",
                        actor_role="system",
                        actor_id="apoptosis_daemon",
                        action="THERMODYNAMIC_APOPTOSIS",
                        resource=str(py_file.relative_to(self.repo_path)),
                        status="Purged (0 references, >7 days decay)"
                    )
                    purged_count += 1
                except subprocess.CalledProcessError as e:
                    logger.error(f"[APOPTOSIS] Failed to purge {py_file.name}: {e}")
                    
        if purged_count > 0:
            logger.info(f"[APOPTOSIS] Purged {purged_count} decayed files. Awaiting OP_GIT_SENTINEL commit.")
        return purged_count

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    daemon = ApoptosisDaemon(Path("."))
    asyncio.run(daemon.execute_purge())
