import asyncio
import os
import sys

# Ensure CORTEX is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cortex.storage.turbopuffer import TurbopufferVectorBackend


async def test_turbopuffer_backend():
    print("Initializing Turbopuffer Vector Backend...")
    api_key = os.environ.get("TURBOPUFFER_API_KEY", "")
    if not api_key:
        print("SKIPPING REAL TEST: TURBOPUFFER_API_KEY not set.")
        print("To run the live test, export TURBOPUFFER_API_KEY=...")
        return
        
    backend = TurbopufferVectorBackend(api_key=api_key, dim=3)
    await backend.connect()
    
    health = await backend.health_check()
    print(f"Health Check: {health}")
    
    tenant_id = "test_tenant"
    fact_id = 9999
    
    # Fake embedding (dim=3 just for quick test if turbopuffer accepts dynamic dimensions based on first upsert)
    # Actually, Turbopuffer does not require pre-creating index with dimension, it infers it!
    embedding = [0.1, 0.2, 0.3]
    
    print("\n--- Testing Upsert ---")
    await backend.upsert(fact_id=fact_id, embedding=embedding, tenant_id=tenant_id, payload={"project": "test_project"})
    print("Upsert SUCCESS.")
    
    print("\n--- Testing Search ---")
    # Small delay for eventual consistency, though TP is usually strongly consistent
    await asyncio.sleep(1)
    
    results = await backend.search(query_embedding=[0.11, 0.21, 0.31], top_k=2, tenant_id=tenant_id, project="test_project")
    print(f"Search Results (project filter): {results}")
    
    print("\n--- Testing Delete ---")
    await backend.delete(fact_id=fact_id, tenant_id=tenant_id)
    print("Delete SUCCESS.")
    
    # Verify delete
    await asyncio.sleep(1)
    results_after = await backend.search(query_embedding=[0.11, 0.21, 0.31], top_k=2, tenant_id=tenant_id, project="test_project")
    print(f"Search Results after delete: {results_after}")
    
    await backend.close()
    print("\nAll tests passed successfully.")

if __name__ == "__main__":
    asyncio.run(test_turbopuffer_backend())
