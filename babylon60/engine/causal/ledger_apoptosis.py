import fcntl
import json
import os
import shutil
import tempfile

from babylon60.telemetry.metrics import metrics


class ThermodynamicLedgerApoptosis:
    """Motor de Poda Semántica de Entropía (C5-REAL).

    Comprime un AOF lineal en su snapshot termodinámicamente óptimo, erradicando
    subgrafos huérfanos, nodos explícitamente podados y anergía (baja entropía)
    mediante cierre transitivo causal.
    """

    def __init__(self, ledger_path: str, entropy_threshold: float = 2.0):
        self.ledger_path = ledger_path
        self.entropy_threshold = entropy_threshold
        self.stats = {
            "scanned": 0,
            "purged_explicit": 0,
            "purged_anergy": 0,
            "purged_cascade": 0,
            "crystallized": 0,
        }

    @staticmethod
    def calculate_shannon_entropy(text: str) -> float:
        """Compute the Shannon entropy of a text to measure information density."""
        if not text:
            return 0.0
        import math

        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1

        entropy = 0.0
        length = len(text)
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    def _compress_state(self) -> dict[str, dict]:
        """Calcula el estado topológico activo en memoria O(N_Active)."""
        active_state = {}
        self.stats = {
            "scanned": 0,
            "purged_explicit": 0,
            "purged_anergy": 0,
            "purged_cascade": 0,
            "crystallized": 0,
        }

        if not os.path.exists(self.ledger_path):
            return active_state

        with open(self.ledger_path, "rb") as f:
            for line in f:
                try:
                    node = json.loads(line.decode("utf-8"))
                    if "hash_id" in node:
                        active_state[node["hash_id"]] = node
                except json.JSONDecodeError:
                    continue  # Purga de bytes corruptos

        self.stats["scanned"] = len(active_state)
        pruned_hashes = set()
        explicit_pruned = set()
        anergy_pruned = set()

        # 1. Singularidad de Origen: Detectar explícitos y anergía (bajo exergy/entropía)
        for h, node in active_state.items():
            # Check explicit deletion
            if node.get("status") in ("pruned", "deleted") or node.get("action") == "delete":
                pruned_hashes.add(h)
                explicit_pruned.add(h)
                continue

            # Check for anergy / low Shannon entropy in node payload
            payload_str = ""
            payload = node.get("payload")
            if isinstance(payload, dict):
                payload_str = json.dumps(payload)
            elif payload is not None:
                payload_str = str(payload)

            if not payload_str:
                payload_str = node.get("content", "")

            # If payload exists and text is too simple (low info density), trigger apoptosis
            if payload_str:
                entropy = self.calculate_shannon_entropy(payload_str)
                if entropy < self.entropy_threshold:
                    pruned_hashes.add(h)
                    anergy_pruned.add(h)

        self.stats["purged_explicit"] = len(explicit_pruned)
        self.stats["purged_anergy"] = len(anergy_pruned)

        # 2. Cierre Transitivo Causal: Destrucción de subgrafos huérfanos
        # Iterar la topología hasta colapsar toda la onda de choque
        cascade_pruned = set()
        wave_active = True
        while wave_active:
            wave_active = False
            for h, node in active_state.items():
                if h not in pruned_hashes:
                    parent_hash = node.get("parent_hash")
                    if parent_hash and parent_hash in pruned_hashes:
                        pruned_hashes.add(h)
                        cascade_pruned.add(h)
                        wave_active = True

        self.stats["purged_cascade"] = len(cascade_pruned)

        # 3. Cristalización Final
        for h in pruned_hashes:
            active_state.pop(h, None)

        self.stats["crystallized"] = len(active_state)
        return active_state

    def trigger_snapshot(self) -> int:
        """Ejecuta la purga semántica con bloqueo atómico POSIX (fcntl)."""
        if not os.path.exists(self.ledger_path):
            return 0

        with open(self.ledger_path, "ab") as origin_fd:
            fcntl.flock(origin_fd.fileno(), fcntl.LOCK_EX)
            try:
                state = self._compress_state()

                fd, temp_path = tempfile.mkstemp(suffix=".aof")
                with os.fdopen(fd, "w") as temp_f:
                    for node in state.values():
                        temp_f.write(json.dumps(node) + "\n")

                # Reemplazo atómico a nivel de sistema operativo
                shutil.move(temp_path, self.ledger_path)

                # Emitir telemetría de decaimiento
                total_pruned = (
                    self.stats["purged_explicit"]
                    + self.stats["purged_anergy"]
                    + self.stats["purged_cascade"]
                )
                if total_pruned > 0:
                    metrics.inc("cortex_stale_memory_cleaned_total", value=total_pruned)

                return len(state)
            finally:
                fcntl.flock(origin_fd.fileno(), fcntl.LOCK_UN)
