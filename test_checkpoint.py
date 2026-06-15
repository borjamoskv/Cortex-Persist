import os
from cortex.engine.evolution_ledger import EvolutionLedger, ControlVector
from cortex.engine.checkpoint import CheckpointManager

def main():
    log_path = "test_evolution.jsonl"
    if os.path.exists(log_path):
        os.remove(log_path)
    if os.path.exists("test_evolution.checkpoints.jsonl"):
        os.remove("test_evolution.checkpoints.jsonl")

    ledger = EvolutionLedger(log_path)
    
    # Generate 2500 mutations
    vector = ControlVector(1.0, 0.05, 0.1, 0.5)
    for i in range(2500):
        # Mutate vector slightly
        new_vector = ControlVector(
            vector.queue_depth + 0.1,
            vector.error_rate,
            vector.causal_entropy,
            vector.cpu_load
        )
        ledger.record_mutation(agent_idx=0, vector_before=vector, vector_after=new_vector)
        vector = new_vector

    print(f"Ledger generated with {ledger.record_count} records.")
    
    # Generate checkpoints
    manager = CheckpointManager(ledger, chunk_size=1000)
    manager.generate_index()
    
    checkpoints = list(manager.iter_checkpoints())
    print(f"Generated {len(checkpoints)} checkpoints:")
    for cp in checkpoints:
        print(f"  [{cp.sequence_start}-{cp.sequence_end}] count={cp.record_count} root={cp.merkle_root[:8]}... head={cp.head_hash[:8]}...")
        
    # Verify
    report = manager.verify_ledger_with_checkpoints()
    print("Verification Report:", report)

    # Clean up
    if os.path.exists(log_path):
        os.remove(log_path)
    if os.path.exists("test_evolution.checkpoints.jsonl"):
        os.remove("test_evolution.checkpoints.jsonl")

if __name__ == "__main__":
    main()
