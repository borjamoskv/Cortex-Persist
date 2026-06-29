# [C5-REAL] Exergy-Maximized
#!/usr/bin/env python3
"""
cat_id: update-memory-c5
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

# Configuración C5-REAL
CORTEX_MEM_DIR = Path.home() / ".cortex" / "memory_ledger"
LEDGER_FILE = CORTEX_MEM_DIR / "ledger.json"
STATE_FILE = CORTEX_MEM_DIR / "current_state.json"


class MemoryLedger:
    def __init__(self):
        CORTEX_MEM_DIR.mkdir(parents=True, exist_ok=True)
        self.ledger = self._load_ledger()
        self.state = self._load_state()

    def _load_ledger(self):
        if LEDGER_FILE.exists():
            with open(LEDGER_FILE) as f:
                return json.load(f)
        return []

    def _load_state(self):
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(LEDGER_FILE, "w") as f:
            json.dump(self.ledger, f, indent=2)
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def compute_hash(self, payload: dict, previous_hash: str) -> str:
        """Prueba de integridad C5-REAL (Merkle-like)"""
        block = f"{json.dumps(payload, sort_keys=True)}{previous_hash}"
        return hashlib.sha256(block.encode("utf-8")).hexdigest()

    def detect_epistemic_drift(self, new_payload: dict) -> float:
        """
        Simulación de diff semántico. Calcula la divergencia
        basado en los campos modificados vs la memoria histórica.
        Retorna un valor de 'drift' (0.0 a 1.0).
        """
        if not self.state:
            return 0.0

        keys_old = set(self.state.keys())
        keys_new = set(new_payload.keys())

        keys_old.intersection(keys_new)
        difference = keys_old.symmetric_difference(keys_new)

        # Drift rudimentario: % de campos nuevos/borrados
        drift_score = len(difference) / (len(keys_old) + len(keys_new))
        return round(drift_score, 4)

    def commit(self, payload: dict, metadata: dict):
        """Aplica mutación y sella el Merkle Hash"""
        drift = self.detect_epistemic_drift(payload)

        previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        if self.ledger:
            previous_hash = self.ledger[-1]["hash"]

        new_hash = self.compute_hash(payload, previous_hash)

        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "drift_score": drift,
            "metadata": metadata,
            "payload": payload,
            "hash": new_hash,
            "previous_hash": previous_hash,
        }

        self.ledger.append(entry)

        # Conciencia de estado: Actualizar
        self.state.update(payload)
        self.state["_last_hash"] = new_hash

        self._save()

        print(f"✅ COMMIT C5-REAL. Hash: {new_hash[:8]}... Drift: {drift}")

    def verify_chain(self):
        """Auditoría de Integridad"""
        prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        for idx, block in enumerate(self.ledger):
            calculated = self.compute_hash(block["payload"], prev_hash)
            if calculated != block["hash"] or prev_hash != block["previous_hash"]:
                print(f"⚠️ CORRUPCIÓN DETECTADA en el bloque {idx}")
                return False
            prev_hash = block["hash"]
        print("🔒 LEDGER C5-REAL VERIFICADO: 100% Íntegro")
        return True

    def rollback(self, target_hash: str):
        """Rollback selectivo (tipo git)"""
        for i, block in enumerate(self.ledger):
            if block["hash"].startswith(target_hash):
                self.ledger = self.ledger[: i + 1]
                # Reconstruir estado desde 0
                self.state = {}
                for b in self.ledger:
                    self.state.update(b["payload"])
                self.state["_last_hash"] = b["hash"]
                self._save()
                print(f"⏪ ROLLBACK EJECUTADO al hash {target_hash}")
                return
        print("❌ HASH NO ENCONTRADO")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: update_memory.py [commit|verify|rollback] [payload_json|hash]")
        sys.exit(1)

    ledger = MemoryLedger()
    action = sys.argv[1]

    if action == "commit":
        if len(sys.argv) < 3:
            print("Se requiere payload en formato JSON")
            sys.exit(1)
        payload = json.loads(sys.argv[2])
        meta = {"source": "update_memory_cli", "user": os.getenv("USER", "cortex")}
        ledger.commit(payload, meta)
    elif action == "verify":
        ledger.verify_chain()
    elif action == "rollback":
        if len(sys.argv) < 3:
            print("Se requiere el hash (o inicio del hash) para rollback")
            sys.exit(1)
        ledger.rollback(sys.argv[2])
    else:
        print("Acción desconocida")
