# [C5-REAL] Exergy-Maximized
import glob
import json
import os

from .state import RuntimeState


class DiskSnapshotManager:
    """Physical State Anchoring. Survives process death."""

    def __init__(self, snap_dir: str = "snapshots", interval: int = 5):
        self.snap_dir = snap_dir
        self.interval = interval
        os.makedirs(self.snap_dir, exist_ok=True)

    def maybe_save(self, state: RuntimeState) -> str | None:
        if state.version > 0 and state.version % self.interval == 0:
            path = os.path.join(self.snap_dir, f"snap_{state.version}.json")
            # Write temp then rename to prevent partial writes
            temp_path = path + ".tmp"
            with open(temp_path, "w") as f:
                json.dump({"version": state.version, "hash": state.hash, "data": state.data}, f)
            os.rename(temp_path, path)
            return state.hash
        return None

    def load_latest(self) -> RuntimeState | None:
        snaps = glob.glob(os.path.join(self.snap_dir, "snap_*.json"))
        if not snaps:
            return None

        def extract_version(p):
            try:
                return int(os.path.basename(p).split("_")[1].split(".")[0])
            except ValueError:
                return -1

        valid_snaps = sorted(snaps, key=extract_version, reverse=True)

        for snap_path in valid_snaps:
            try:
                with open(snap_path) as f:
                    data = json.load(f)
                return RuntimeState(initial_state=data["data"], version=data["version"])
            except Exception:
                # Silent fallback on corrupted snapshot (handled by Chaos Harness)
                continue
        return None
