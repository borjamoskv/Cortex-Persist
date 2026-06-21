import asyncio
import time

class RingAllReduceSimulation:
    """
    [C5-REAL] Exergy-Maximized Ring AllReduce Benchmark.
    Simula la topología de red en anillo para reducción y sincronización de gradientes.
    Demuestra la complejidad asintótica O(1) de ancho de banda.
    """
    def __init__(self, num_nodes=4, tensor_size=1024):
        self.num_nodes = num_nodes
        self.tensor_size = tensor_size
        self.chunk_size = tensor_size // num_nodes
        
        assert self.tensor_size % self.num_nodes == 0, "Tensor size must be divisible by num_nodes"
        
        # Cada nodo inicia con un array de tamaño `tensor_size`.
        # El nodo i está lleno de valores (i+1) para probar la suma cruzada.
        self.nodes = [
            [(i + 1.0) for _ in range(tensor_size)]
            for i in range(num_nodes)
        ]
        
    async def step_scatter_reduce(self):
        """
        Fase 1: Scatter-Reduce (N-1 pasos)
        Cada nodo envía su sub-bloque al siguiente en el anillo.
        El receptor suma los datos a su sub-bloque.
        """
        for s in range(self.num_nodes - 1):
            sends = []
            for i in range(self.num_nodes):
                chunk_idx = (i - s) % self.num_nodes
                start = chunk_idx * self.chunk_size
                end = start + self.chunk_size
                data_to_send = self.nodes[i][start:end]
                sends.append((i, chunk_idx, data_to_send))
                
            await asyncio.sleep(0.01) # Simulación exergética de latencia de red
            
            for i, chunk_idx, data in sends:
                next_node = (i + 1) % self.num_nodes
                start = chunk_idx * self.chunk_size
                # Reducción matemática (Suma de gradientes)
                for j in range(self.chunk_size):
                    self.nodes[next_node][start + j] += data[j]

    async def step_all_gather(self):
        """
        Fase 2: All-Gather (N-1 pasos)
        Los sub-bloques completamente reducidos se difunden en el anillo.
        El receptor sobrescribe sus bloques incompletos con la verdad total.
        """
        for s in range(self.num_nodes - 1):
            sends = []
            for i in range(self.num_nodes):
                chunk_idx = (i + 1 - s) % self.num_nodes
                start = chunk_idx * self.chunk_size
                end = start + self.chunk_size
                data_to_send = self.nodes[i][start:end].copy()
                sends.append((i, chunk_idx, data_to_send))
                
            await asyncio.sleep(0.01) # Simulación exergética de latencia de red
            
            for i, chunk_idx, data in sends:
                next_node = (i + 1) % self.num_nodes
                start = chunk_idx * self.chunk_size
                # Propagación de verdad estructural (Sobrescribir)
                for j in range(self.chunk_size):
                    self.nodes[next_node][start + j] = data[j]

    async def run(self):
        print(f"🚀 Iniciando Ring AllReduce Benchmark ({self.num_nodes} nodos, Tensor: {self.tensor_size} variables)")
        t0 = time.perf_counter()
        
        await self.step_scatter_reduce()
        t1 = time.perf_counter()
        print(f"✓ Scatter-Reduce completado en {t1-t0:.4f}s")
        
        await self.step_all_gather()
        t2 = time.perf_counter()
        print(f"✓ All-Gather completado en {t2-t1:.4f}s")
        
        print(f"Total Time: {t2-t0:.4f}s")
        
        self.verify_invariants()

    def verify_invariants(self):
        """Comprueba que todos los nodos convergen a la misma suma determinista."""
        expected_val = sum(i + 1.0 for i in range(self.num_nodes))
        
        for i, node_data in enumerate(self.nodes):
            for j, val in enumerate(node_data):
                if val != expected_val:
                    raise AssertionError(f"VIOLACIÓN ESTRUCTURAL: Nodo {i} en pos {j} tiene {val}, esperado {expected_val}")
                
        print(f"✅ Invariante Matemático Validado: Todos los nodos convergieron a SUM={expected_val}")
        print(f"✅ Pasos Asintóticos: 2 * (N - 1) = {2 * (self.num_nodes - 1)}")


if __name__ == "__main__":
    asyncio.run(RingAllReduceSimulation(num_nodes=8, tensor_size=8192).run())
