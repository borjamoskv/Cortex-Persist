import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from cortex.engine.ultramap import UltramapSubstrate


def export_topological_map():
    print("Iniciando Mapeo Topológico C5-REAL...")
    umap = UltramapSubstrate(capacity=10000)
    
    active_nodes = []
    
    # Escanear capacidad completa para mapeo total
    for i in range(10000):
        try:
            state = umap.get_agent_state(i)
            # Un nodo está activo si tiene un target definido o coordenadas no nulas
            if state and (state['target'] or any(v != 0.0 for v in [state['x'], state['y'], state['z']])):
                active_nodes.append((i, state))
        except Exception:
            pass
            
    print("\\n--- GRAFO TOPOLÓGICO O(1) ---")
    print(f"Total Nodos Activos Detectados: {len(active_nodes)}")
    
    for idx, state in active_nodes:
        print(f"\\n[NODO {idx}] -> {state['target']}")
        print(f"  Coordenadas: ({state['x']:.2f}, {state['y']:.2f}, {state['z']:.2f})")
        print(f"  Firmas HoTT: {state['hott_signature']}")
        print(f"  Vector Control [Q: {state['queue_depth']}, Err: {state['error_rate']}, CE: {state['causal_entropy']}, CPU: {state['cpu_load']}]")
        print(f"  Entropía Estocástica: {state['entropy']:.4f}")

if __name__ == "__main__":
    export_topological_map()
