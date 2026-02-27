import asyncio
import logging
from uuid import uuid4

# Import internal mechanics to simulate environment
import cortex.memory.sqlite_vec_store as store_mod
from cortex.memory.semantic_ram import DynamicSemanticSpace
from cortex.swarm.infinite_minds import InfiniteMindsManager
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.models import CortexFactModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dummy Encoder that wraps vector into Float32 Numpy
class MockEncoder(AsyncEncoder):
    @property
    def dimension(self):
        return 2

    async def encode(self, text: str):
        return [0.5, 0.5]

async def stress_test():
    logger.info("======== BOOTING SOVEREIGN UNIVERSE ========")
    
    encoder = MockEncoder()
    # Mocking memory in temporary space to not trash production
    l2_store = store_mod.SovereignVectorStoreL2(
        encoder=encoder, db_path="/tmp/cortex_omega_test.db"
    )
    
    logger.info("✓ Initialized SovereignVectorStoreL2")
    
    # Insert some dummy facts
    for i in range(3):
        fact = CortexFactModel(
            id=str(uuid4()),
            tenant_id="test_tenant",
            project_id="test_project",
            content=f"Fact number {i} regarding quantum topological decay.",
            embedding=[0.5, 0.5],
            timestamp=1700000000.0,  # Old timestamp
            success_rate=1.0
        )
        await l2_store.memorize(fact)
    
    logger.info("✓ Stored 3 baseline facts")
    
    # Boot the Dynamic Semantic Space
    space = DynamicSemanticSpace(l2_store)
    space.hebbian_daemon.start()
    
    logger.info("✓ Hebbian Daemon Running in Background")
    
    infinite_minds = InfiniteMindsManager(space)
    
    # Spawn minds
    mind_a = infinite_minds.spawn_mind("AGENT_NOVA", "test_tenant", "test_project")
    mind_b = infinite_minds.spawn_mind("AGENT_VEGA", "test_tenant", "test_project")
    
    # Evolve Deltas
    mind_a.evolve_bias("Focused on topological constraints.")
    mind_b.evolve_bias("Focused on emotional narrative dynamics.")
    
    logger.info("✓ Agent NOVA Bias: %s", mind_a.semantic_bias)
    logger.info("✓ Agent VEGA Bias: %s", mind_b.semantic_bias)
    
    # Query Time! (Read as Rewrite)
    results_a = await mind_a.think("Explain quantum")
    logger.info("✓ NOVA retrieved %d facts. Pulse Emitted.", len(results_a))
    
    # Allow daemon to process pulse
    await asyncio.sleep(0.5)
    
    # Fetch directly to verify success_rate mutation
    conn = l2_store._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT success_rate FROM facts_meta")
    rates = cursor.fetchall()
    logger.info("=> Current Topologies (Success Rates): %s", [r[0] for r in rates])
    
    # Verify decay calculation works
    cursor.execute("SELECT cortex_decay(0, 1000, 2000, 500)")
    decay_val = cursor.fetchone()[0]
    logger.info("=> Topological Decay verification (1000s age, 500s halflife): %.4f", decay_val)
    
    await space.hebbian_daemon.stop()
    await l2_store.close()
    
    logger.info("======== STRESS TEST COMPLETE ========")

if __name__ == "__main__":
    asyncio.run(stress_test())
