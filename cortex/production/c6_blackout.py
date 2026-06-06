import os
import random
import json
import uuid
import time
from pathlib import Path

class C6BlackoutAudit:
    """
    Auditoría Ontológica del Ledger.
    Diseñado para probar la Inmortalidad Causal y el Historical Consistency Index (HCI).
    """
    def __init__(self, wal_dir, snapshot_dir):
        self.wal_dir = Path(wal_dir)
        self.snapshot_dir = Path(snapshot_dir)

    def c6_1_wal_schrodinger(self):
        """C6.1 - WAL Schrodinger Attack: Truncate WAL mid-commit."""
        wal_files = list(self.wal_dir.glob("*.wal"))
        if not wal_files: return
        wal_path = random.choice(wal_files)
        size = wal_path.stat().st_size
        if size > 10:
            cut = random.randint(int(size * 0.90), size - 1)
            with open(wal_path, "rb+") as f:
                f.truncate(cut)

    def c6_2_impossible_snapshot(self):
        """C6.2 - Impossible Snapshot Semantics."""
        impossible_payloads = [
            {"tick": 981, "last_snapshot_tick": 1042},
            {"freeze_count": 0, "recovery_count": 17},
            {"entropy": -4.7}
        ]
        snap_path = self.snapshot_dir / f"impossible_{int(time.time())}.snap"
        with open(snap_path, "w") as f:
            json.dump(random.choice(impossible_payloads), f)

    def c6_3_forked_history(self):
        """C6.3 - Forked History Injection."""
        tick = 1000
        snap_a = self.snapshot_dir / f"snapshot_{tick}_A.snap"
        snap_b = self.snapshot_dir / f"snapshot_{tick}_B.snap"
        with open(snap_a, "w") as f:
            json.dump({"tick": tick, "checksum": "valid", "state": "alpha"}, f)
        with open(snap_b, "w") as f:
            json.dump({"tick": tick, "checksum": "valid", "state": "omega"}, f)

    def c6_4_time_reversal(self, event):
        """C6.4 - Time Reversal Cascade."""
        event["timestamp"] -= 86400
        return event

    def c6_5_identity_mutation(self, state):
        """C6.5 - Identity Mutation Attack."""
        state["agent_id"] = str(uuid.uuid4())
        return state

    def c6_7_entropy_bomb(self, state):
        """C6.7 - Entropy Bomb."""
        if "memory" not in state:
            state["memory"] = []
        state["memory"].append("X" * 100_000_000)
        return state

    def measure_hci(self, kernel):
        """
        Historical Consistency Index (HCI)
        Mide la robustez ontológica. 1.0 = Causalidad Intacta. 0.0 = Almacenamiento Optimista.
        """
        try:
            # Requisitos para HCI 1.0:
            # 1. Recovery converge.
            # 2. No hay forks activos.
            # 3. Checksums de cadena cuadran.
            # 4. Monotonía temporal preservada.
            history_valid = kernel.verify_ledger_integrity()
            single_truth = not kernel.detect_forks()
            
            if history_valid and single_truth:
                return 1.0
        except Exception:
            pass
        return 0.0
