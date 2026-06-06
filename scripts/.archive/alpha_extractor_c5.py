from pathlib import Path

import pandas as pd

# CORTEX PERSIST: ALPHA SIGNAL EXTRACTOR
# Reality Level: C5-REAL

TIER1_METRICS_FILE = Path("data/mafia_ai/tier1_node_metrics.csv")


class AlphaExtractor:
    def __init__(self):
        self.alpha_nodes = []

    def extract_alpha(self):
        if not TIER1_METRICS_FILE.exists():
            print(f"ERROR: {TIER1_METRICS_FILE} NOT_FOUND")
            return

        df = pd.read_csv(TIER1_METRICS_FILE)

        # Smoke_Index = (In_Degree * PageRank * 1000) / (Out_Degree + 1)
        df["Smoke_Index"] = (df["In_Degree"] * df["PageRank"] * 1000) / (df["Out_Degree"] + 1)

        # Alpha: Out_Degree > 0 AND Smoke_Index < median
        alpha_df = df[
            (df["Out_Degree"] > 0) & (df["Smoke_Index"] < df["Smoke_Index"].median())
        ].copy()
        alpha_df = alpha_df.sort_values(by=["Smoke_Index", "Out_Degree"], ascending=[True, False])

        print("Claim: ALPHA_TARGETS_EXTRACTED")
        print(
            f"Proof: {{ Base: [Alpha Filter], Range: [{len(alpha_df)},{len(df)}], Confidence: [C5-REAL] }}"
        )
        print(
            alpha_df[["Node", "Out_Degree", "In_Degree", "Smoke_Index"]].to_csv(
                index=False, sep="|"
            )
        )


if __name__ == "__main__":
    AlphaExtractor().extract_alpha()
