import os
os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
import tempfile
import json
import pytest
from concurrent.futures import ProcessPoolExecutor
from babylon60.consensus.sync_protocol import BFTMerger

def simulate_agent_merge(args):
    agent_id, shared_ledger, remote_ledger = args
    merger = BFTMerger(shared_ledger)
    return merger.merge_subgraphs(remote_ledger)

def test_bft_merger_concurrent_writes():
    """
    Termodinámica P0: Aserción formal de concurrencia BFT.
    Simula un Swarm de N agentes intentando inyectar deltas sobre el mismo Ledger AOF.
    Garantiza que fcntl previene Torn Writes y data races a nivel de Kernel OS.
    """
    N_AGENTS = 10
    M_NODES_PER_AGENT = 100
    
    with tempfile.TemporaryDirectory() as tmpdir:
        shared_ledger = os.path.join(tmpdir, "master_cortex_state.aof")
        
        # Generar remote ledgers inmutables para cada agente del enjambre
        args_list = []
        for i in range(N_AGENTS):
            remote_ledger = os.path.join(tmpdir, f"remote_{i}.aof")
            with open(remote_ledger, "wb") as f:
                for j in range(M_NODES_PER_AGENT):
                    # Simulación de Invarianza: Nodos únicos criptográficamente anclados
                    node = {"hash_id": f"hash_{i}_{j}", "agent": i, "exergy_value": 1000}
                    f.write((json.dumps(node) + "\n").encode('utf-8'))
            args_list.append((i, shared_ledger, remote_ledger))
            
        # Inyectar colisión entrópica masiva (Swarm Assault) vía multiprocessing
        # para aislar el fcntl a nivel OS, garantizando concurrencia dura.
        with ProcessPoolExecutor(max_workers=N_AGENTS) as executor:
            results = list(executor.map(simulate_agent_merge, args_list))
            
        # Aserción Causal: Ningún nodo se perdió por colisión
        assert sum(results) == N_AGENTS * M_NODES_PER_AGENT
        
        # Aserción Estructural: Integridad absoluta de bytes en el AOF
        total_read = 0
        seen_hashes = set()
        
        with open(shared_ledger, "rb") as f:
            for line in f:
                # Si fcntl falla, se producirá json.JSONDecodeError por 'torn writes'
                node = json.loads(line.decode('utf-8'))
                assert "hash_id" in node
                seen_hashes.add(node["hash_id"])
                total_read += 1
                
        # Zero Entropy Loss Verification
        assert total_read == N_AGENTS * M_NODES_PER_AGENT
        assert len(seen_hashes) == N_AGENTS * M_NODES_PER_AGENT
