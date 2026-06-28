# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Singularity Nexus Symlink Engine.

Enforces INV_NEXUS_LINK: Absolute eradication of physical redundancy across
the operator's multi-repository filesystem. Canonical knowledge nodes
(e.g., AGENTS.md, GEMINI.md) exist in one definitive location, propagated
via OS-level symlinks to satellite repositories.
"""

import logging
import os

logger = logging.getLogger("cortex.nexus.symlink_engine")

class SymlinkEngine:
    """Propagates absolute structural identity across workspaces."""
    
    def __init__(self, canonical_root: str):
        """
        Args:
            canonical_root: Absolute path to the authoritative repository (e.g., 30_CORTEX).
        """
        self.canonical_root = os.path.abspath(canonical_root)
        
    def _enforce_link(self, source_path: str, target_path: str) -> bool:
        """
        Creates or repairs a symlink from target_path -> source_path.
        Returns True if successful, False if the target is an untracked real file.
        """
        if not os.path.exists(source_path):
            logger.error(f"[Nexus] Canonical source missing: {source_path}")
            return False
            
        if os.path.islink(target_path):
            current_target = os.readlink(target_path)
            if current_target == source_path:
                return True
            else:
                os.remove(target_path)
                
        elif os.path.exists(target_path):
            # Physical redundancy detected! Context Rot.
            logger.critical(f"[Nexus] Physical redundancy detected at {target_path}. Overwriting with symlink.")
            os.remove(target_path)
            
        os.symlink(source_path, target_path)
        logger.info(f"[Nexus] OP_BIND_NEXUS: {target_path} -> {source_path}")
        return True
        
    def propagate(self, target_workspaces: list[str], artifacts: list[str]) -> dict[str, bool]:
        """
        Force physical symlinks for core artifacts across given workspaces.
        
        Args:
            target_workspaces: List of absolute paths to satellite repositories.
            artifacts: List of filenames relative to the canonical root.
            
        Returns:
            Dict mapping workspace to success bool.
        """
        results = {}
        for workspace in target_workspaces:
            workspace_ok = True
            for artifact in artifacts:
                source = os.path.join(self.canonical_root, artifact)
                target = os.path.join(os.path.abspath(workspace), artifact)
                
                # Check if target workspace exists
                if not os.path.isdir(os.path.abspath(workspace)):
                    logger.warning(f"[Nexus] Target workspace unreachable: {workspace}")
                    workspace_ok = False
                    continue
                    
                if not self._enforce_link(source, target):
                    workspace_ok = False
            results[workspace] = workspace_ok
            
        return results

    def validate_invariants(self, target_workspaces: list[str], artifacts: list[str]) -> bool:
        """
        Validates INV_NEXUS_LINK strictly. Fails if any satellite artifact is a physical file.
        """
        for workspace in target_workspaces:
            for artifact in artifacts:
                target = os.path.join(os.path.abspath(workspace), artifact)
                if os.path.exists(target) and not os.path.islink(target):
                    logger.critical(f"[Nexus] INV_NEXUS_LINK VIOLATED: {target} is a physical file, not a symlink.")
                    return False
        return True
