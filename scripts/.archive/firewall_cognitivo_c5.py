from pathlib import Path

import pandas as pd

# ==========================================
# CORTEX PERSIST: FIREWALL COGNITIVO (C5-REAL)
# ==========================================
# Objetivo: Inmunizar la ingesta de conocimiento de MOSKV-1
# frente a nodos con alto Smoke Index (Economía de la Mentira).

METRICS_FILE = Path("data/mafia_ai/tier1_node_metrics.csv")
THRESHOLD_SMOKE = 10.0  # Límite máximo de humo tolerado (Centralidad > 10x el Output Real)


class CognitiveFirewall:
    def __init__(self):
        self.blacklist = set()
        self.whitelist = set()
        self._load_matrix()

    def _load_matrix(self):
        if not METRICS_FILE.exists():
            print(
                "[!] Advertencia: No se detecta Topología (tier1_node_metrics.csv). Firewall inactivo."
            )
            return

        df = pd.read_csv(METRICS_FILE)

        # Smoke Index = (In_Degree * PageRank * 1000) / (Out_Degree + 1)
        df["Smoke_Index"] = (df["In_Degree"] * df["PageRank"] * 1000) / (df["Out_Degree"] + 1)

        for _, row in df.iterrows():
            node = row["Node"]
            smoke = row["Smoke_Index"]

            # Regla Estructural: Si el humo térmico supera el umbral, censura absoluta.
            if smoke > THRESHOLD_SMOKE:
                self.blacklist.add(node)
            else:
                self.whitelist.add(node)

        print(
            f"[*] Firewall Inicializado. Nodos Bloqueados: {len(self.blacklist)} | Nodos Permitidos: {len(self.whitelist)}"
        )

    def filter_payload(self, source_node: str, content: str) -> bool:
        """
        Retorna True si el contenido está anclado a la realidad (Permitido).
        Retorna False si el contenido proviene de la Mafia AI (Censurado).
        """
        source_node = source_node.lower().strip()

        if source_node in self.blacklist:
            print(
                f"[!] INTERCEPCIÓN C5-REAL: Drop de payload térmico proveniente de '{source_node}' (High Smoke Index)."
            )
            return False

        print(f"[+] Payload verificado. Origen '{source_node}' anclado a output real.")
        return True


if __name__ == "__main__":
    fw = CognitiveFirewall()

    # Simulacro de ingesta
    print("\\n--- TEST DE INGESTA DE SEÑALES ---")
    mock_stream = [
        {"origen": "exponentialview", "payload": "SOTA Report on Battery Tech"},
        {"origen": "garymarcus", "payload": "Why AGI is failing again"},
        {"origen": "thezvi", "payload": "AI Policy Weekly Update"},
    ]

    for item in mock_stream:
        fw.filter_payload(item["origen"], item["payload"])
