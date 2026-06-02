import json
from pathlib import Path
import csv

# ==========================================
# CORTEX PERSIST: FIREWALL COGNITIVO (C5-REAL)
# ==========================================
# Objetivo: Inmunizar la ingesta de conocimiento de MOSKV-1
# frente a nodos con alto Smoke Index (Economía de la Mentira).

SMOKE_INDEX_FILE = Path("data/reputation_graph/smoke_index_report.csv")
THRESHOLD_SMOKE = 10.0  # Límite máximo de humo tolerado (Centralidad > 10x el Output Real)

class CognitiveFirewall:
    def __init__(self):
        self.blacklist = set()
        self.whitelist = set()
        self._load_matrix()

    def _load_matrix(self):
        if not SMOKE_INDEX_FILE.exists():
            print("[!] Advertencia: No se detecta Smoke Index previo. Firewall inactivo.")
            return

        with open(SMOKE_INDEX_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                node = row["Node"]
                smoke = float(row["Smoke_Index"])
                
                # Regla Estructural: Si el humo térmico supera el umbral, censura absoluta.
                if smoke > THRESHOLD_SMOKE:
                    self.blacklist.add(node)
                else:
                    self.whitelist.add(node)
                    
        print(f"[*] Firewall Inicializado. Nodos Bloqueados: {len(self.blacklist)} | Nodos Permitidos: {len(self.whitelist)}")

    def filter_payload(self, source_node: str, content: str) -> bool:
        """
        Retorna True si el contenido está anclado a la realidad (Permitido).
        Retorna False si el contenido proviene de la Mafia AI (Censurado).
        """
        # Normalizar nodo
        source_node = source_node.lower().strip()
        
        if source_node in self.blacklist:
            print(f"[!] INTERCEPCIÓN C5-REAL: Drop de payload térmico proveniente de '{source_node}' (High Smoke Index).")
            return False
            
        print(f"[+] Payload verificado. Origen '{source_node}' anclado a output real.")
        return True

if __name__ == "__main__":
    fw = CognitiveFirewall()
    
    # Simulacro de ingesta
    print("\n--- TEST DE INGESTA DE SEÑALES ---")
    mock_stream = [
        {"origen": "aleximas", "payload": "10 ways AI will change B2B sales in 2027"},
        {"origen": "forecastingresearch", "payload": "New empirical benchmark on LLM logic constraints"},
        {"origen": "freesystems", "payload": "Why you need an AI strategy tomorrow"}
    ]
    
    for item in mock_stream:
        fw.filter_payload(item["origen"], item["payload"])
