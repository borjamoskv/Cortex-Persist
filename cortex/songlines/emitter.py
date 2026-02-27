"""
ResonanceEmitter — The Ocre Painter.
Embeds hyperdimensional ghost traces into the file system.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from cortex.memory.hdc.codec import HDCEncoder
from cortex.memory.hdc.item_memory import ItemMemory

logger = logging.getLogger("cortex.songlines.emitter")


class ResonanceEmitter:
    """Marie Curie: The file becomes radioactive.

    Uses macOS xattrs (Extended Attributes) to store ghost metadata directly
    on the target file.
    """

    def __init__(self, encoder: HDCEncoder | None = None):
        self.encoder = encoder or HDCEncoder(ItemMemory())
        self.prefix = "user.cortex.ghost"

    def embed_ghost(
        self, target_file: Path, intent: str, project: str = "default", half_life_hours: int = 72
    ):
        """Paint a ghost trace on a file."""
        if not target_file.exists():
            return

        hv = self.encoder.encode_fact(intent, fact_type="ghost", project_id=project)
        ghost_id = hashlib.sha256(intent.encode()).hexdigest()[:16]
        payload = {
            "id": ghost_id,
            "intent": intent,
            "project": project,
            "created_at": datetime.now(timezone.utc).timestamp(),
            "half_life": half_life_hours,
            "resonance": hv.tolist(),
        }
        encoded_payload = json.dumps(payload).encode("utf-8")
        attr_name = f"{self.prefix}.{ghost_id}"

        # Try os.setxattr first
        if hasattr(os, "setxattr"):
            try:
                os.setxattr(str(target_file), attr_name, encoded_payload)
                logger.info(f"Embedded ghost {ghost_id} on {target_file.name} (os.setxattr)")
                return
            except OSError:
                pass

        # Primary Fallback: /usr/bin/xattr CLI (macOS)
        try:
            import subprocess

            # Use -w to write
            subprocess.run(
                ["xattr", "-w", attr_name, encoded_payload.decode("utf-8"), str(target_file)],
                check=True,
                capture_output=True,
            )
            logger.info(f"Embedded ghost {ghost_id} on {target_file.name} (xattr cli)")
            return
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Final Fallback: .songlines manifest
        self._fallback_embed(target_file, attr_name, encoded_payload)

    def _fallback_embed(self, target_file: Path, attr_name: str, payload: bytes):
        """Fallback mechanism for non-xattr systems or failures."""
        songline_file = target_file.parent / ".songlines"
        data = {}
        if songline_file.exists():
            try:
                with open(songline_file) as f:
                    data = json.load(f)
            except Exception:
                pass

        file_key = target_file.name
        if file_key not in data:
            data[file_key] = {}

        data[file_key][attr_name] = payload.decode("utf-8")

        with open(songline_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Fallback: Stored ghost for {target_file.name} in {songline_file}")
