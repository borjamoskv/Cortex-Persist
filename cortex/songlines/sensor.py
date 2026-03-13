import json
import logging
import os
import subprocess
from pathlib import Path
from typing import TypedDict

from cortex.songlines.decay import DecayEngine

logger = logging.getLogger("cortex.songlines.sensor")


class GhostTrace(TypedDict):
    """Structured telemetry payload for embedded ghosts."""

    id: str
    strength: float
    source_file: str
    created_at: float
    half_life: float
    intent: str
    project: str


class TopographicSensor:
    """Telemetry from the physical landscape.

    Recursively scans the directory for files and extracts their
    cortex ghost metadata from xattrs or fallback manifests.
    """

    def __init__(self):
        self.prefix = "user.cortex.ghost"

    def scan_field(self, root_dir: Path) -> list[GhostTrace]:
        """Scan the project topography for active ghosts."""
        resonances = []
        ignored = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", ".cortex"}

        # 1. Faster recursive scan avoiding ignored directories
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in ignored]

            # Check for fallback manifests in this directory
            if ".songlines" in files:
                manifest_path = Path(root) / ".songlines"
                resonances.extend(self._scan_single_manifest(manifest_path))

            for file in files:
                if file in ignored:
                    continue
                path = Path(root) / file
                try:
                    if path.stat().st_size > 1024 * 1024:
                        continue
                except OSError:
                    continue

                file_ghosts = self._read_ghosts_from_file(path)
                resonances.extend(file_ghosts)

        # 2. Deduplicate and clean (by ghost ID)
        unique_ghosts = {}
        for ghost in resonances:
            gid = ghost["id"]
            if gid not in unique_ghosts or ghost["strength"] > unique_ghosts[gid]["strength"]:
                unique_ghosts[gid] = ghost

        return list(unique_ghosts.values())

    def _read_ghosts_from_file(self, file_path: Path) -> list[GhostTrace]:
        """Read ghosts from macOS xattrs or xattr CLI."""
        results = []
        attr_names = self._get_attr_names(file_path)

        for attr in attr_names:
            payload = self._get_attr_payload(file_path, attr)
            if payload:
                ghost = self._parse_ghost_payload(file_path, attr, payload)
                if ghost:
                    results.append(ghost)

        return results

    def _get_attr_names(self, file_path: Path) -> list[str]:
        """Fetch matching attribute names via os or CLI."""
        # 1. Try native os.listxattr (Linux mostly)
        if hasattr(os, "listxattr"):
            try:
                # type: ignore[reportAttributeAccessIssue]
                return [a for a in os.listxattr(str(file_path)) if a.startswith(self.prefix)]
            except OSError:
                pass

        # 1.5 Try native python xattr package (macOS mostly) if installed
        try:
            import xattr

            try:
                attrs = xattr.listxattr(str(file_path))
                return [a for a in attrs if a.startswith(self.prefix)]
            except OSError:
                pass
        except ImportError:
            pass

        # 2. Try xattr CLI (Chronos Sniper: added timeout)
        try:
            out = subprocess.check_output(
                ["xattr", str(file_path)], stderr=subprocess.DEVNULL, timeout=2.0
            )
            return [
                a
                for a in out.decode("utf-8", errors="ignore").splitlines()
                if a.startswith(self.prefix)
            ]
        except (subprocess.SubprocessError, FileNotFoundError, TimeoutError):
            return []

    def _get_attr_payload(self, file_path: Path, attr: str) -> bytes | None:
        """Fetch attribute content via os or CLI."""
        # 1. Try native os.getxattr
        if hasattr(os, "getxattr"):
            try:
                return os.getxattr(str(file_path), attr)  # type: ignore[reportAttributeAccessIssue]
            except OSError:
                pass

        # 1.5 Try native python xattr package (macOS mostly) if installed
        try:
            import xattr

            try:
                return xattr.getxattr(str(file_path), attr)
            except OSError:
                pass
        except ImportError:
            pass

        # 2. Try xattr CLI -p (Chronos Sniper: added timeout)
        try:
            return subprocess.check_output(
                ["xattr", "-p", attr, str(file_path)], stderr=subprocess.DEVNULL, timeout=2.0
            )
        except (subprocess.SubprocessError, FileNotFoundError, TimeoutError):
            return None

    def _parse_ghost_payload(
        self, file_path: Path, attr: str, payload_bytes: bytes
    ) -> GhostTrace | None:
        """Decode payload and handle decay/evaporation."""
        try:
            # Entropy Demon Guard: Handle malformed UTF-8 or unexpected JSON
            payload_str = payload_bytes.decode("utf-8", errors="replace")
            ghost = json.loads(payload_str)

            if not isinstance(ghost, dict) or "created_at" not in ghost or "half_life" not in ghost:
                return None

            strength = DecayEngine.calculate_resonance(ghost["created_at"], ghost["half_life"])

            if strength < 0.05:
                logger.info("Ghost %s evaporated from %s", ghost["id"], file_path.name)
                self._delete_xattr(file_path, attr)
                return None

            ghost["strength"] = strength
            ghost["source_file"] = str(file_path)
            return ghost
        except (json.JSONDecodeError, KeyError):
            return None

    def _delete_xattr(self, file_path: Path, attr_name: str):
        """Helper to delete an xattr."""
        if hasattr(os, "removexattr"):
            try:
                # type: ignore[reportAttributeAccessIssue]
                os.removexattr(str(file_path), attr_name)
                return
            except OSError:
                pass

        try:
            subprocess.run(["xattr", "-d", attr_name, str(file_path)], capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            pass

    def _scan_single_manifest(self, manifest: Path) -> list[GhostTrace]:
        """Read ghosts from a single .songlines fallback file."""
        results = []
        try:
            with open(manifest) as f:
                data = json.load(f)
                for filename, attrs in data.items():
                    for _, payload_str in attrs.items():
                        ghost = json.loads(payload_str)
                        strength = DecayEngine.calculate_resonance(
                            ghost["created_at"], ghost["half_life"]
                        )
                        if strength < 0.05:
                            continue
                        ghost["strength"] = strength
                        ghost["source_file"] = str(manifest.parent / filename)
                        results.append(ghost)
        except (json.JSONDecodeError, KeyError, OSError):
            pass
        return results
