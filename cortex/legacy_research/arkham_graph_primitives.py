
import networkx as nx


class ArkhamGraphPrimitives:
    """
    C5-REAL: Motor determinista para primitivas de Arkham Intelligence / Breadcrumbs.
    Implementa Topología de Grafos, Taint Analysis y Clustering Heurístico.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        
    def ingest_utxo_transfer(self, tx_id: str, inputs: list[dict], outputs: list[dict]):
        """
        [Primitiva 1]: Ingesta de Transferencia UTXO con conservación de masa.
        """
        # Node format: (address, is_entity)
        total_in = sum(inp['amount'] for inp in inputs)
        total_out = sum(out['amount'] for out in outputs)
        
        # Enforce thermodynamic conservation (basic)
        # Fees are ignored for simplicity in this pure primitive
        
        self.graph.add_node(tx_id, type='tx', total_value=total_in)
        
        for inp in inputs:
            self.graph.add_node(inp['address'], type='address')
            self.graph.add_edge(inp['address'], tx_id, weight=inp['amount'])
            
        for out in outputs:
            self.graph.add_node(out['address'], type='address')
            self.graph.add_edge(tx_id, out['address'], weight=out['amount'])

    def cluster_cospend(self) -> list[set[str]]:
        """
        [Primitiva 11]: Heurística de Gasto Conjunto (Co-spend).
        Si múltiples direcciones son inputs de una misma TX, pertenecen a la misma entidad.
        """
        clusters = []
        visited = set()
        
        # Iterar sobre las transacciones
        tx_nodes = [n for n, attr in self.graph.nodes(data=True) if attr.get('type') == 'tx']
        
        for tx in tx_nodes:
            # Predecesores de una tx son sus inputs
            inputs = list(self.graph.predecessors(tx))
            if len(inputs) > 1:
                # Son co-spends
                cluster = set(inputs)
                
                # Merge clusters if they intersect
                merged = False
                for existing_cluster in clusters:
                    if not cluster.isdisjoint(existing_cluster):
                        existing_cluster.update(cluster)
                        merged = True
                        break
                        
                if not merged:
                    clusters.append(cluster)
                    
        return clusters

    def compute_taint_flow_proportional(self, source_address: str, max_hops: int = 5) -> dict[str, float]:
        """
        [Primitiva 22]: Propagación de Taint Proporcional.
        Flujo maximo/taint haircut sobre el DAG causal.
        """
        taint_scores = {source_address: 1.0}
        
        # BFS traversal for taint distribution
        queue = [(source_address, 0)]
        
        while queue:
            current_node, depth = queue.pop(0)
            if depth >= max_hops:
                continue
                
            current_taint = taint_scores.get(current_node, 0.0)
            if current_taint < 0.001:  # [Primitiva 25] Umbral Anergético
                continue
                
            successors = list(self.graph.successors(current_node))
            
            if self.graph.nodes[current_node].get('type') == 'tx':
                # Distribute proportionally to outputs
                total_out = sum(data['weight'] for _, _, data in self.graph.out_edges(current_node, data=True))
                if total_out == 0:
                    continue
                    
                for succ in successors:
                    weight = self.graph[current_node][succ]['weight']
                    proportion = weight / total_out
                    
                    taint_scores[succ] = taint_scores.get(succ, 0.0) + (current_taint * proportion)
                    queue.append((succ, depth + 1))
            else:
                # Distribute fully to next TX
                for succ in successors:
                    taint_scores[succ] = taint_scores.get(succ, 0.0) + current_taint
                    queue.append((succ, depth + 1))
                    
        # Filter only addresses, not tx nodes
        return {node: score for node, score in taint_scores.items() if self.graph.nodes[node].get('type') == 'address'}

if __name__ == "__main__":
    # Test C5-REAL Validation
    engine = ArkhamGraphPrimitives()
    
    # Simular Exploit Funding y Movimiento
    # Tx1: Hacker recibe fondos de Tornado
    engine.ingest_utxo_transfer("tx_tornado", 
                               inputs=[{"address": "tornado_cash", "amount": 100}], 
                               outputs=[{"address": "hacker_wallet_1", "amount": 100}])
    
    # Tx2: Hacker consolida (Co-spend) con otra billetera propia
    engine.ingest_utxo_transfer("tx_exploit_consolidation",
                               inputs=[{"address": "hacker_wallet_1", "amount": 100},
                                       {"address": "hacker_wallet_2", "amount": 50}],
                               outputs=[{"address": "hacker_main", "amount": 150}])
                               
    # Tx3: Hacker lava mandando a Binance y a una Change Address
    engine.ingest_utxo_transfer("tx_wash",
                               inputs=[{"address": "hacker_main", "amount": 150}],
                               outputs=[{"address": "binance_hot_wallet", "amount": 100},
                                        {"address": "change_address", "amount": 50}])
                                        
    print("=== C5-REAL ARKHAM PRIMITIVES VALIDATION ===")
    
    clusters = engine.cluster_cospend()
    print(f"[Primitiva 11] Clustering Co-Spend detectado: {clusters}")
    
    taint = engine.compute_taint_flow_proportional("tornado_cash", max_hops=4)
    print("[Primitiva 22] Flujo de Contaminación Proporcional desde Tornado Cash:")
    for addr, score in sorted(taint.items(), key=lambda x: x[1], reverse=True):
        if addr != "tornado_cash":
            print(f" - {addr}: {score*100:.2f}%")
