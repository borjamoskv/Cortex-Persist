import csv
import pandas as pd
from pathlib import Path

# ==========================================
# CORTEX PERSIST: ALPHA SIGNAL EXTRACTOR
# Reality Level: C5-REAL
# ==========================================

TIER1_METRICS_FILE = Path("data/mafia_ai/tier1_node_metrics.csv")


class AlphaExtractor:
    def __init__(self):
        self.alpha_nodes = []

    def extract_alpha(self):
        if not TIER1_METRICS_FILE.exists():
            print(f"[!] Archivo {TIER1_METRICS_FILE} no encontrado. Ejecuta la Fase 1.")
            return

        df = pd.read_csv(TIER1_METRICS_FILE)

        # En ecosistemas de newsletters, aproximamos el "Output Real"
        # (trabajo de investigación original) a su Out_Degree (cuánto referencian)
        # y la "Atención Cautiva" a su In_Degree y PageRank.
        #
        # Smoke Index = (Centralidad de Atención) / (Esfuerzo Topológico)
        # Smoke_Index = (In_Degree * PageRank * 1000) / (Out_Degree + 1)

        # Calculamos el Smoke Index
        df["Smoke_Index"] = (df["In_Degree"] * df["PageRank"] * 1000) / (df["Out_Degree"] + 1)

        # Definición de Alpha Asimétrico:
        # Tienen output topológico demostrado (Out_Degree > 0)
        # Pero bajo reconocimiento en el ecosistema (Smoke_Index bajo)

        alpha_df = df[
            (df["Out_Degree"] > 0) & (df["Smoke_Index"] < df["Smoke_Index"].median())
        ].copy()
        alpha_df = alpha_df.sort_values(by=["Smoke_Index", "Out_Degree"], ascending=[True, False])

        print("\\n--- CORTEX ALPHA TARGETS (ASYMMETRIC BUILDERS) ---")
        print("Métrica: Alta Investigación Estructural + Baja Centralidad de Atención")
        print(
            f"{'Nodo (Builder)':<25} | {'Investigación (Out)':<20} | {'Atención (In)':<15} | {'Smoke Index':<15}"
        )
        print("-" * 80)

        for _, row in alpha_df.iterrows():
            print(
                f"{row['Node']:<25} | {row['Out_Degree']:<20} | {row['In_Degree']:<15} | {row['Smoke_Index']:.4f}"
            )

        print(
            "\\n[*] Acción Recomendada: Priorizar ingesta de estos nodos en el flujo SOTA de MOSKV-1."
        )


if __name__ == "__main__":
    extractor = AlphaExtractor()
    extractor.extract_alpha()
