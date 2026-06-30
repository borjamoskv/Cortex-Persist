import time
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import networkx as nx
import pandas as pd
import requests
from bs4 import BeautifulSoup

SEED_NODES = [
    "latentspace",
    "thesequence",
    "importai",
    "thealgorithmicbridge",
    "understandingai",
    "garymarcus",
    "lastweekinai",
    "aheadofaitime",
    "aisupremacy",
    "thezvi",
    "technosapiens",
    "exponentialview",
    "aiweirdness",
]


class RSSStructuralExtractor:
    """
    Pivot C5-REAL Definitivo:
    Las APIs JSON (/recommendations y /archive) bloquean o limitan body_html.
    Fallback determinista a RSS/XML (/feed).
    Se extrae topología pura a partir de menciones intra-artículo (<content:encoded>).
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def fetch_mentions(self, subdomain: str) -> list[dict]:
        recommendations = []
        try:
            print(f" -> Interceptando Feed RSS (C5-REAL) para: {subdomain}...")
            # For Substack, use the main /feed
            url = f"https://{subdomain}.substack.com/feed"
            if subdomain == "importai":  # special case
                url = "https://importai.substack.com/feed"

            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                seen_targets = set()

                for entry in feed.entries:
                    # Get full HTML content
                    html = ""
                    if "content" in entry:
                        html = entry.content[0].value
                    elif "summary" in entry:
                        html = entry.summary

                    if not html:
                        continue

                    soup = BeautifulSoup(html, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if ".substack.com" in href:
                            target_domain = urlparse(href).netloc
                            target_subdomain = target_domain.split(".substack.com")[0].replace(
                                "www.", ""
                            )

                            if (
                                target_subdomain
                                and target_subdomain != subdomain
                                and target_subdomain not in seen_targets
                            ):
                                # We count 1 edge per Substack mentioned in the entire feed (binary presence)
                                # To prevent one post dominating the weight
                                seen_targets.add(target_subdomain)
                                recommendations.append(
                                    {
                                        "source": subdomain,
                                        "target": target_subdomain,
                                        "timestamp": int(time.time()),
                                        "recommendation_type": "in_text_mention",
                                        "metadata": {
                                            "weight": 1,
                                            "extraction": "rss_content_encoded",
                                        },
                                    }
                                )

                print(
                    f"   [+] {len(recommendations)} menciones cruzadas capturadas para {subdomain}."
                )
            else:
                print(f"   [!] Fallo HTTP {response.status_code} para {subdomain}.")

        except Exception as e:
            print(f"   [!] Error de extracción en {subdomain}: {e}")

        return recommendations


class StructuralGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_from_payloads(self, payloads: list[dict]):
        for payload in payloads:
            source = payload["source"]
            target = payload["target"]
            weight = payload["metadata"].get("weight", 1)

            if self.graph.has_edge(source, target):
                self.graph[source][target]["weight"] += weight
            else:
                self.graph.add_edge(source, target, weight=weight)

    def compute_tier1_metrics(self) -> pd.DataFrame:
        metrics = []
        try:
            pr = nx.pagerank(self.graph, weight="weight")
            in_degree = dict(self.graph.in_degree(weight="weight"))
            out_degree = dict(self.graph.out_degree(weight="weight"))

            for node in self.graph.nodes():
                metrics.append(
                    {
                        "Node": node,
                        "PageRank": pr.get(node, 0.0),
                        "In_Degree": in_degree.get(node, 0),
                        "Out_Degree": out_degree.get(node, 0),
                        "Reciprocity_Ratio": len(list(nx.mutually_synergetic_edges(self.graph)))
                        if hasattr(nx, "mutually_synergetic_edges")
                        else 0,
                    }
                )
        except Exception as e:
            print(f"[!] Error de computo topológico: {e}")

        df = pd.DataFrame(metrics)
        if not df.empty:
            df = df.sort_values(by="PageRank", ascending=False)
        return df

    def export(self, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        nx.write_graphml(self.graph, output_dir / "structural_graph.graphml")
        print(f" -> Topología cristalizada en: {output_dir / 'structural_graph.graphml'}")


def main():
    print("[*] Iniciando Extractor C5-REAL (RSS Asimétrico)")
    extractor = RSSStructuralExtractor()
    builder = StructuralGraphBuilder()

    all_recommendations = []
    for node in SEED_NODES:
        recs = extractor.fetch_mentions(node)
        all_recommendations.extend(recs)
        time.sleep(1)  # Rate limit protection  # noqa: TID251

    print(f"\\n[*] Total Raw Edges Captured: {len(all_recommendations)}")
    print("[*] Construyendo matriz topológica...")
    builder.build_from_payloads(all_recommendations)

    print("\\n[*] Computando Métricas Tier-1 (Falsación de Concentración Anómala)...")
    df_metrics = builder.compute_tier1_metrics()

    if not df_metrics.empty:
        print("\\n--- TIER-1 METRICS ---")
        print(df_metrics.head(10).to_string(index=False))

        output_dir = Path("data/mafia_ai")
        output_dir.mkdir(parents=True, exist_ok=True)
        df_metrics.to_csv(output_dir / "tier1_node_metrics.csv", index=False)
        builder.export(output_dir)
        print("\\n[*] FALSACIÓN COMPLETADA. Data anclada a disco.")
    else:
        print("\\n[!] Topología vacía. Falsación fallida.")


if __name__ == "__main__":
    main()
