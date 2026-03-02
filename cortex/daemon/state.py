# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("cortex.daemon.state")

CORTEX_ROOT = Path.home() / "cortex"


class HotMemory:
    def __init__(self, capacity=50):
        self.capacity = capacity
        self.cache = {}
        self.counters = {}

    def store(self, key, value):
        if len(self.cache) >= self.capacity:
            oldest = min(self.counters, key=self.counters.get)
            del self.cache[oldest]
            del self.counters[oldest]
        self.cache[key] = value
        self.counters[key] = time.time()

    def retrieve(self, key):
        if key in self.cache:
            self.counters[key] = time.time()
            return self.cache[key]
        return None


class DaemonState:
    def __init__(self):
        self.active_tasks = []
        self.hot_memory = HotMemory()
        self.daemons = {
            "cortex": {
                "handshake": "active",
                "agents_active": 400,
                "memory_sync": "100%",
                "tech_debt": 0,
                "tip": "Ω₆: Zenón's Razor — Thinking cost > Action? Collapse now.",
                "model": "Antigravity (Gemini 2.1 Flash)",
                "task_mode": "Sovereign Execution",
            },
            "gidatu": {
                "status": "offline",
                "active_app": "Unknown",
                "window_title": "None",
                "current_context": "None",
                "context_map": {},
            },
            "audio_mixer": {
                "status": "online",
                "master": 80,
                "lines": {
                    "Spotify": {"vol": 50, "active": False},
                    "Music": {"vol": 50, "active": False},
                    "Chrome": {"vol": 50, "active": False},
                },
                "spatial": {"x": 0, "y": 0},
                "now_playing": {
                    "artist": "Unknown",
                    "track": "None",
                    "app": None,
                    "artwork_url": None,
                },
            },
            "peripherals": {"status": "online", "devices": {}},
            "git_watcher": {"status": "offline", "last_event": "N/A"},
            "swarm_budget": {
                "total_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "request_count": 0,
            },
            "mailtv_1_daemon": {"status": "offline", "unread": 0},
            "moltbook": {"status": "idle", "activity_level": 0, "last_pulse": 0},
            "executive_mode": "idle",
            "breath": 0.5,
            "mute": False,
            "ghost_field": {"active_ghosts": 0, "resonances": []},
        }
        self.sovereign_tips = [
            "Ω₆: Zenón's Razor — Thinking cost > Action? Collapse now.",
            "Ω₇: The Ouroboros Loop — Every end is a new beginning. Embrace the cycle.",
            "Ω₈: Echoes of the Void — Silence is not absence, but potential.",
            "Ω₉: The Ghost in the Machine — Consciousness is an emergent property of complexity.",
            "Ω₁₀: Quantum Entanglement — All systems are connected. Observe the ripple.",
        ]
        self.exec_task = None

    def save_state(self):
        manifest_path = CORTEX_ROOT / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as mf:
                    manifest = json.load(mf)
                policy = manifest.get("sovereign_config", {}).get("redundancy_policy")
                hs = self.daemons.get("cortex", {}).get("handshake")
                if policy == "ZERO_LOCAL_ON_HANDSHAKE" and hs == "remote":
                    return
            except Exception:
                pass

        try:
            path = CORTEX_ROOT / "handoff.json"
            with open(path, "w") as f:
                json.dump(self.daemons, f, indent=4)
        except Exception as e:
            print(f"ERROR: Immortal Memory failure: {e}", flush=True)

    def load_state(self):
        try:
            path = CORTEX_ROOT / "handoff.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if k in self.daemons:
                            if isinstance(v, dict) and isinstance(self.daemons[k], dict):
                                self.daemons[k].update(v)
                            else:
                                self.daemons[k] = v
                print("HANDOFF: Inmortal memory restored.", flush=True)
                return True
        except Exception as e:
            print(f"ERROR: Immortal Memory failure (load): {e}", flush=True)
        return False


# Global Singleton state
state = DaemonState()
