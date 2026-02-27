import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from cortex.songlines.decay import DecayEngine

logger = logging.getLogger("cortex.songlines.sensor")


class TopographicSensor:
    """Telemetry from the physical landscape.

    Recursively scans the directory for files and extracts their
    cortex ghost metadata from xattrs or fallback manifests.
    """

    def __init__(self):
        self.prefix = "user.cortex.ghost"

    def scan_field(self, root_dir: Path) -> list[dict[str, Any]]:
        """Scan the project topography for active ghosts."""
        resonances = []

        # 1. Recursive scan of files
        for path in root_dir.rglob("*"):
            if path.is_file() and not self._is_ignored(path):
                file_ghosts = self._read_ghosts_from_file(path)
                resonances.extend(file_ghosts)

        # 2. Scan fallback manifests (.songlines)
        resonances.extend(self._scan_fallback_manifests(root_dir))

        # 3. Deduplicate and clean (by ghost ID)
        unique_ghosts = {}
        for ghost in resonances:
            gid = ghost["id"]
            if gid not in unique_ghosts or ghost["strength"] > unique_ghosts[gid]["strength"]:
                unique_ghosts[gid] = ghost

        return list(unique_ghosts.values())

    def _read_ghosts_from_file(self, file_path: Path) -> list[dict[str, Any]]:
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
        # 1. Try native os.listxattr
        if hasattr(os, "listxattr"):
            try:
                return [a for a in os.listxattr(str(file_path)) if a.startswith(self.prefix)]
            except OSError:
                pass

        # 2. Try xattr CLI
        try:
            out = subprocess.check_output(["xattr", str(file_path)], stderr=subprocess.DEVNULL)
            return [a for a in out.decode("utf-8").splitlines() if a.startswith(self.prefix)]
        except (subprocess.SubprocessError, FileNotFoundError):
            return []

    def _get_attr_payload(self, file_path: Path, attr: str) -> bytes | None:
        """Fetch attribute content via os or CLI."""
        # 1. Try native os.getxattr
        if hasattr(os, "getxattr"):
            try:
                return os.getxattr(str(file_path), attr)
            except OSError:
                pass

        # 2. Try xattr CLI -p
        try:
            return subprocess.check_output(
                ["xattr", "-p", attr, str(file_path)], stderr=subprocess.DEVNULL
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            return None

    def _parse_ghost_payload(
        self, file_path: Path, attr: str, payload_bytes: bytes
    ) -> dict[str, Any] | None:
        """Decode payload and handle decay/evaporation."""
        try:
            ghost = json.loads(payload_bytes.decode("utf-8"))
            strength = DecayEngine.calculate_resonance(ghost["created_at"], ghost["half_life"])

            if strength < 0.05:
                logger.info(f"Ghost {ghost['id']} evaporated from {file_path.name}")
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
                os.removexattr(str(file_path), attr_name)
                return
            except OSError:
                pass

        try:
            subprocess.run(["xattr", "-d", attr_name, str(file_path)], capture_output=True)
        except Exception:
            pass

    def _scan_fallback_manifests(self, root_dir: Path) -> list[dict[str, Any]]:
        """Read ghosts from .songlines fallback files."""
        results = []
        for manifest in root_dir.rglob(".songlines"):
            try:
                with open(manifest) as f:
                    data = json.load(f)
                    # data is { filename: { attr_name: payload_str } }
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
            except Exception:
                pass
        return results

    def _is_ignored(self, path: Path) -> bool:
        """Basic ignore logic for hidden dirs and common noise."""
        parts = path.parts
        ignored = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", ".cortex"}
        return any(part in ignored for part in parts)
