import csv
from pathlib import Path

# ==========================================
# CORTEX PERSIST: ALPHA SIGNAL EXTRACTOR 
# Reality Level: C5-REAL
# ==========================================
# Objetivo: Encontrar asimetría de mercado (Alpha).
# Identificar nodos con alto output termodinámico (código/realidad)
# pero bajo reconocimiento en la red social (narrativa).

SMOKE_INDEX_FILE = Path("data/reputation_graph/smoke_index_report.csv")

class AlphaExtractor:
    def __init__(self):
        self.alpha_nodes = []
        
    def extract_alpha(self):
        if not SMOKE_INDEX_FILE.exists():
            print("[!] Sin datos base. Ejecuta la calculadora de Humo primero.")
            return

        with open(SMOKE_INDEX_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                node = row["Node"]
                smoke = float(row["Smoke_Index"])
                real_output = int(row["Real_Output_Repos"])
                social_legit = float(row["Social_Legitimacy"])
                
                # Definición de Alpha:
                # 1. Tienen output real demostrado (> 0)
                # 2. Su humo térmico es excepcionalmente bajo (< 1.0)
                # (Es decir, la relación entre lo que construyen y la atención que reciben es asimétrica a favor de la construcción).
                if real_output > 0 and smoke < 1.0:
                    self.alpha_nodes.append({
                        "Node": node,
                        "Real_Output": real_output,
                        "Social_Legitimacy": social_legit,
                        "Smoke_Index": smoke
                    })

        # Ordenar por Output Real descendente y Smoke Index ascendente
        self.alpha_nodes.sort(key=lambda x: (-x["Real_Output"], x["Smoke_Index"]))
        
        print("\n--- CORTEX ALPHA TARGETS (ASYMMETRIC BUILDERS) ---")
        print("Métrica: Alto Output Empírico + Baja Integración en la 'Mafia AI'")
        print(f"{'Nodo (Builder)':<30} | {'Output Real':<15} | {'Smoke Index (Ruido)':<20}")
        print("-" * 75)
        for target in self.alpha_nodes:
            print(f"{target['Node']:<30} | {target['Real_Output']:<15} | {target['Smoke_Index']:<20}")
            
        print("\n[*] Acción Recomendada: Priorizar ingesta de estos nodos en el flujo SOTA.")

if __name__ == "__main__":
    extractor = AlphaExtractor()
    extractor.extract_alpha()
