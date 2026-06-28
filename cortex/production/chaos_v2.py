# [C5-REAL] Exergy-Maximized
import pathlib
import random
import threading


class ChaosLayerV2:
    def __init__(self, kernel, snapshots_dir):
        self.kernel = kernel
        self.snapshots_dir = pathlib.Path(snapshots_dir)

    def entropy_storm(self, generate_event):
        """1. Inyecta ráfagas exponenciales y silencios prolongados."""
        burst_size = int(random.expovariate(0.01))
        for _ in range(burst_size):
            self.kernel.process(generate_event())
        threading.Event().wait(random.expovariate(0.001))  # noqa: TID251 # Synchronous chaos delay

    def byzantine_memory_corruption(self, state):
        """2. Mutación controlada de estado persistente."""
        if random.random() < 0.001:
            state["entropy"] = float("nan")
        return state

    def snapshot_assassination(self):
        """3. Eliminar snapshots aleatoriamente."""
        snapshots = list(self.snapshots_dir.glob("*.snap"))
        if snapshots:
            victim = random.choice(snapshots)
            try:
                victim.unlink()
            except Exception as exc:
                import logging

                logging.warning("Suppressed exception: %s", exc)

    def temporal_distortion_attack(self, event):
        """4. Desordenar timestamps."""
        event.timestamp += random.randint(-3600, 3600)
        return event

    def freeze_saturation_test(self):
        """6. Forzar activación masiva del Freeze Protocol."""
        for _ in range(1000):
            self.kernel.freeze()

    def collect_telemetry(self):
        """Telemetría mínima obligatoria durante asedio."""
        return {
            "tick_latency_ms": getattr(self.kernel, "last_tick_latency", 0),
            "wal_depth": getattr(self.kernel, "wal_depth", 0),
            "snapshot_count": len(list(self.snapshots_dir.glob("*.snap"))),
            "entropy_score": getattr(self.kernel, "current_entropy", 0),
            "freeze_events": getattr(self.kernel, "freeze_count", 0),
            "recovery_time_ms": getattr(self.kernel, "last_recovery_time", 0),
            "split_brain_events": getattr(self.kernel, "lock_contentions", 0),
            "state_divergence": getattr(self.kernel, "divergence_score", 0),
        }
