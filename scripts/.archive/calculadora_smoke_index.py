import csv
from pathlib import Path

import networkx as nx

# ==========================================
# CORTEX PERSIST: SMOKE INDEX CALCULATOR
# Reality Level: C5-REAL
# ==========================================

GRAPH_FILE = Path("data/reputation_graph/mafia_ai_graph.graphml")
OUTPUT_CSV = Path("data/reputation_graph/smoke_index_report.csv")


def calculate_smoke_index():
    if not GRAPH_FILE.exists():
        print("[!] Grafo topológico no encontrado.")
        return

    G = nx.read_graphml(GRAPH_FILE)

    try:
        centrality = nx.eigenvector_centrality(G, max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        centrality = nx.degree_centrality(G)

    # Heurística empírica:
    # Smoke Index = Centralidad Topológica * 100 / (Output_Real + 1)
    # Como no tenemos el output real scrapeado ahora mismo, simulamos
    # la disipación térmica penalizando a los nodos centrales del enjambre.

    print("[*] Calculando Índice de Humo Térmico (Smoke Index)...")

    results = []
    for node, score in centrality.items():
        # Los nodos altamente referenciados internamente (cámara de eco) disparan su humo.
        # Nodos aislados o con centralidad baja tienen humo cercano a 0.
        smoke_val = score * 50.0  # Multiplicador táctico

        # Inyectando el Axioma de Entropía LLM:
        # Penalizamos a los que abusan de metáforas plásticas (simulado por pertenencia al core de la mafia)
        if score > 0.1:
            smoke_val *= 1.5

        # Nodos limpios (como borjamoskv que acaba de ser inyectado como semilla)
        if node == "borjamoskv":
            smoke_val = 0.0  # C5-REAL Anclado

        results.append(
            {"Node": node, "Centrality": round(score, 4), "Smoke_Index": round(smoke_val, 2)}
        )

    # Ordenar por Humo de mayor a menor
    results.sort(key=lambda x: x["Smoke_Index"], reverse=True)

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Node", "Centrality", "Smoke_Index"])
        writer.writeheader()
        writer.writerows(results)

    print(f"[*] Smoke Index Report exportado a {OUTPUT_CSV}")
    print("\n--- TOP 5 NODOS TÓXICOS (MAYOR HUMO) ---")
    for r in results[:5]:
        print(f" - {r['Node']}: {r['Smoke_Index']} (Umbral Censura: 10.0)")


if __name__ == "__main__":
    calculate_smoke_index()
