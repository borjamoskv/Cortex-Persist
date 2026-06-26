"""
[C5-REAL] sat_genetic_swarm.py
Sovereign Component: SAT Genetic Swarm Generator
CORTEX-TAINT: taint:moskv1:adversarial_sat:gen2:0x9f32
"""

import random
from typing import List, Tuple

class SatGeneticSwarm:
    def __init__(self, pop_size: int = 10, graph_size: int = 10, mutation_rate: float = 0.2):
        self.pop_size = pop_size
        self.graph_size = graph_size
        self.mutation_rate = mutation_rate
        # Población: lista de listas de tuplas (aristas)
        self.population: List[List[Tuple[int, int]]] = [self._random_graph() for _ in range(pop_size)]

    def _random_graph(self) -> List[Tuple[int, int]]:
        edges = []
        for i in range(self.graph_size):
            for j in range(i + 1, self.graph_size):
                if random.random() < 0.4:  # Densidad inicial
                    edges.append((i, j))
        return edges

    def fitness(self, graph: List[Tuple[int, int]]) -> float:
        """
        Calcula la Entropía del grafo: queremos maximizar la cantidad de aristas (densidad)
        para forzar la explosión combinatoria en el solver SAT.
        """
        # La entropía en este escenario adversarial se simplifica al conteo de aristas
        # penalizando grafos vacíos o grafos completos triviales.
        edge_count = len(graph)
        max_edges = (self.graph_size * (self.graph_size - 1)) // 2
        
        # Penalizamos si está demasiado cerca del grafo completo (trivialmente Unsat rápido para cliques grandes)
        if edge_count > max_edges * 0.8:
            return float(edge_count) * 0.5
            
        return float(edge_count) + random.uniform(0, 5) # Ruido estocástico para diversificación

    def evolve(self, generations: int = 5) -> List[Tuple[int, int]]:
        for gen in range(generations):
            # Sort by fitness
            scored = [(self.fitness(g), g) for g in self.population]
            scored.sort(key=lambda x: x[0], reverse=True)
            
            # Select top 50%
            survivors = [g for _, g in scored[:self.pop_size // 2]]
            
            # Crossover and mutate
            new_population = list(survivors)
            while len(new_population) < self.pop_size:
                parent1 = random.choice(survivors)
                parent2 = random.choice(survivors)
                
                # Crossover
                split = len(parent1) // 2
                child = parent1[:split] + [e for e in parent2 if e not in parent1[:split]]
                
                # Mutation
                if random.random() < self.mutation_rate:
                    u, v = random.randint(0, self.graph_size - 1), random.randint(0, self.graph_size - 1)
                    if u != v:
                        edge = (min(u, v), max(u, v))
                        if edge in child:
                            child.remove(edge)
                        else:
                            child.append(edge)
                            
                new_population.append(child)
                
            self.population = new_population

        # Return best graph of the final generation
        best_graph = max(self.population, key=self.fitness)
        return best_graph
