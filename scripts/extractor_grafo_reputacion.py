import json
import time
import networkx as nx
import requests
import feedparser
from pathlib import Path
from typing import List, Dict, Tuple
from urllib.parse import urlparse

# ==========================================
# CORTEX PERSIST: REPUTATION GRAPH EXTRACTOR
# Reality Level: C5-REAL
# ==========================================

# Seed Nodes (Substack / Newsletters / Podcasts)
# Mapped by their Substack subdomain or identifier
SEED_NODES = [
    "borjamoskv",           # Nodo Cero (Borja Moskv)
    "latentspace",          # Latent Space (Swyx)
    "thesequence",          # The Sequence
    "bensbites",            # Ben's Bites
    "thealgorithmicbridge", # The Algorithmic Bridge
    "importai",             # Import AI (Jack Clark)
    "garymarcus",           # Marcus on AI
    "dwarkesh",             # Dwarkesh Podcast
    "zvi",                  # Don't Worry About the Vase
    "stratechery",          # Stratechery (Ben Thompson)
    "pragmaticengineer",    # The Pragmatic Engineer
    "lennysnewsletter",     # Lenny's Newsletter
    "cleothink",            # Cleo Abram (simulated mapping)
    "simonw",               # Simon Willison's Weblog (uses atom/rss)
    "aiweekly",             # AI Weekly
    "rundownai",            # The Rundown AI
]

OUTPUT_DIR = Path("data/reputation_graph")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class ReputationGraphBuilder:
    def __init__(self):
        self.G = nx.DiGraph()
        self.headers = {"User-Agent": "CortexPersist-Graph-Extractor/1.0 (C5-REAL)"}

    def fetch_substack_feed(self, subdomain: str) -> feedparser.FeedParserDict:
        url = f"https://{subdomain}.substack.com/feed"
        print(f"[*] Fetching feed for {subdomain}: {url}")
        return feedparser.parse(url)

    def extract_links(self, html_content: str) -> List[str]:
        # Simple extraction using regex or simple parsing
        # For C5-REAL we'll use a basic string split approach for speed and zero-dependency if bs4 is missing
        import re
        links = re.findall(r'href=[\'"]?([^\'" >]+)', html_content)
        return links

    def process_node(self, source_node: str):
        self.G.add_node(source_node, type="seed")
        feed = self.fetch_substack_feed(source_node)
        
        if feed.bozo:
            print(f"[!] Warning: Malformed feed for {source_node}")
            
        for entry in feed.entries:
            content = entry.get('content', [{'value': entry.get('summary', '')}])[0]['value']
            links = self.extract_links(content)
            
            for link in links:
                try:
                    parsed = urlparse(link)
                    domain = parsed.netloc.lower()
                    
                    # Detect if the link points to another substack
                    if "substack.com" in domain:
                        target_subdomain = domain.split(".substack.com")[0]
                        if target_subdomain != source_node and target_subdomain != "www":
                            # Add an edge representing a 'mention' (credibility transfer)
                            if self.G.has_edge(source_node, target_subdomain):
                                self.G[source_node][target_subdomain]['weight'] += 1
                            else:
                                self.G.add_edge(source_node, target_subdomain, weight=1)
                except Exception as e:
                    pass

    def build_graph(self):
        print("[*] Initiating Reputation Graph Extraction...")
        for node in SEED_NODES:
            self.process_node(node)
            time.sleep(0.5) # Rate limiting
            
        print(f"[*] Extraction Complete. Nodes: {self.G.number_of_nodes()} | Edges: {self.G.number_of_edges()}")
        
    def analyze_graph(self):
        # Calculate Eigenvector Centrality
        try:
            centrality = nx.eigenvector_centrality(self.G, max_iter=1000, weight='weight')
        except:
            centrality = nx.degree_centrality(self.G)
            
        sorted_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        print("\n--- TOP 10 NODOS POR CENTRALIDAD (ÍNDICE DE LEGITIMACIÓN) ---")
        for i, (node, score) in enumerate(sorted_centrality[:10]):
            print(f"{i+1}. {node} -> {score:.4f}")
            
        return sorted_centrality

    def export(self):
        # Export as GraphML for Gephi / Neo4j ingestion
        nx.write_graphml(self.G, OUTPUT_DIR / "mafia_ai_graph.graphml")
        print(f"[*] Graph exported to {OUTPUT_DIR / 'mafia_ai_graph.graphml'}")

if __name__ == "__main__":
    builder = ReputationGraphBuilder()
    builder.build_graph()
    builder.analyze_graph()
    builder.export()
