import logging
import time
import uuid

# Configuración de logging estilo Industrial Noir
logging.basicConfig(level=logging.INFO, format='%(asctime)s - ◈ %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CORTEX-SHIELD")

class MockMem0:
    """Simulación del fallo de mem0 Issue #3245"""
    def __init__(self):
        self.vector_store = {"mem_1": "Me gusta el café solo"}
        self.graph_store = {"mem_1": ["borja", "GUSTA", "café solo"]}
        self.history = []

    def delete(self, memory_id):
        # Simula el comportamiento erróneo reportado en mem0 #3245
        logger.info(f"SIMULANDO MEM0 NATIVO: Deleting {memory_id} from Vector Store...")
        if memory_id in self.vector_store:
            del self.vector_store[memory_id]
            self.history.append({"id": memory_id, "action": "DELETE", "timestamp": time.time()})
            # ❌ FALLO: No borra del grafo (Neo4j)
            logger.warning(f"⚠️ BUG #3245 DETECTADO: {memory_id} persiste en Graph Store!")
            return True
        return False

class CortexShield:
    """Implementación del Protocolo de Integridad CORTEX v6 sobre mem0"""
    def __init__(self, mem0_instance):
        self.mem0 = mem0_instance
        self.ledger = [] # CORTEX Fact Ledger local

    def _log_fact(self, fact_type, content, metadata=None):
        fact = {
            "fact_id": str(uuid.uuid4()),
            "type": fact_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self.ledger.append(fact)
        logger.info(f"FACT STORED: [{fact_type}] - {content}")

    def delete_with_integrity(self, memory_id):
        """
        Garantiza Integridad Referencial Cognitiva (Atomic Deletion).
        Axioma: Un hecho no puede estar parcialmente muerto.
        """
        logger.info(f"CORTEX-SHIELD: Atomatizing deletion for {memory_id}")
        
        # 1. Auditoría Pre-colapso (D1: Percepción)
        if memory_id not in self.mem0.graph_store and memory_id not in self.mem0.vector_store:
            logger.error(f"Integrity Error: {memory_id} not found in any store.")
            return False

        # 2. Cleanup del Grafo PRIMERO (D4: Validación)
        # En una implementación real, aquí haríamos el MATCH (n) DETACH DELETE
        if memory_id in self.mem0.graph_store:
            logger.info(f"SHIELD PROTECT: Detaching relationships in Neo4j for {memory_id}")
            del self.mem0.graph_store[memory_id]
        
        # 3. Delegar al motor subyacente (D3: Creación)
        self.mem0.delete(memory_id)

        # 4. Registrar en el Ledger (Fact Persistence)
        self._log_fact("SUPERSESSION", f"Memory {memory_id} hard-deleted with graph integrity.")
        
        return True

# --- DEMO ---
if __name__ == "__main__":
    m0 = MockMem0()
    shield = CortexShield(m0)

    print("\n--- ESTADO INICIAL ---")
    print(f"Vector Store: {m0.vector_store}")
    print(f"Graph Store:  {m0.graph_store}")

    print("\n--- EJECUTANDO DELETE CON LÓGICA CORTEX ---")
    shield.delete_with_integrity("mem_1")

    print("\n--- ESTADO FINAL (CON INTEGRIDAD CORTEX) ---")
    print(f"Vector Store: {m0.vector_store}")
    print(f"Graph Store:  {m0.graph_store}")
    
    if not m0.graph_store:
        print("\n✅ SHIELD SUCCESS: No orphaned nodes found.")
    else:
        print("\n❌ SHIELD FAILED: Orphans still exist.")
