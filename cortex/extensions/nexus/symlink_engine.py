# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Singularity Nexus Symlink Engine.

Enforces INV_NEXUS_LINK: Absolute eradication of physical redundancy across
the operator's multi-repository filesystem. Canonical knowledge nodes
(e.g., AGENTS.md, GEMINI.md) exist in one definitive location, propagated
via OS-level symlinks to satellite repositories.
"""

import logging
import os
import shutil

logger = logging.getLogger("cortex.nexus.symlink_engine")


class SymlinkEngine:
    """Propagates absolute structural identity across workspaces."""

    def __init__(self, canonical_root: str):
        """
        Args:
            canonical_root: Absolute path to the authoritative repository (e.g., 30_CORTEX).
        """
        self.canonical_root = os.path.abspath(canonical_root)

    def _safe_backup(self, target_path: str) -> None:
        """Safely backup a physical file or directory before replacing it."""
        backup_path = f"{target_path}.nexus_bak"
        idx = 1
        while os.path.exists(backup_path):
            backup_path = f"{target_path}.nexus_bak_{idx}"
            idx += 1

        logger.warning(f"[Nexus] Backing up physical entity: {target_path} -> {backup_path}")
        if os.path.isdir(target_path) and not os.path.islink(target_path):
            shutil.copytree(target_path, backup_path)
            shutil.rmtree(target_path)
        else:
            shutil.copy2(target_path, backup_path)
            os.remove(target_path)

    def _enforce_link(self, source_path: str, target_path: str) -> bool:
        """
        Creates or repairs a symlink from target_path -> source_path.
        Returns True if successful, False if the canonical source is missing.
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
            logger.critical(
                f"[Nexus] Physical redundancy detected at {target_path}. Overwriting with symlink."
            )
            self._safe_backup(target_path)

        # Ensure parent directory of target exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        os.symlink(source_path, target_path)
        logger.info(f"[Nexus] OP_BIND_NEXUS: {target_path} -> {source_path}")
        return True

    def propagate(self, target_workspaces: list[str], artifacts: list[str]) -> dict[str, bool]:
        """
        Force physical symlinks for core artifacts across given workspaces.

        Args:
            target_workspaces: List of absolute paths to satellite repositories.
            artifacts: List of filenames/directories relative to the canonical root.

        Returns:
            Dict mapping workspace to success bool.
        """
        results = {}
        for workspace in target_workspaces:
            workspace_ok = True

            if not os.path.isdir(os.path.abspath(workspace)):
                logger.warning(f"[Nexus] Target workspace unreachable: {workspace}")
                results[workspace] = False
                continue

            for artifact in artifacts:
                source = os.path.join(self.canonical_root, artifact)
                target = os.path.join(os.path.abspath(workspace), artifact)

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
                    logger.critical(
                        f"[Nexus] INV_NEXUS_LINK VIOLATED: {target} is a physical entity, not a symlink."
                    )
                    return False
        return True
