import logging
from typing import Any

from cortex.agents.sat_orchestrator import SatOrchestrator
from cortex.swarm.sat_genetic_swarm import SatGeneticSwarm

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class SatAdversarialGame:
    """
    Motor del juego adversarial (Fase 2).
    Generador (Enjambre): Intenta crear grafos que sean EXACTAMENTE k-colorables (o muy densos pero colorables).
    Destructor (Z3): Inyecta ruido/prueba rigurosamente si el grafo propuesto es k-colorable.
    """
    def __init__(self, n: int = 10, k: int = 3, timeout_ms: int = 5000):
        self.n = n
        self.k = k
        self.orchestrator = SatOrchestrator(timeout_ms=timeout_ms)
        # Usamos el enjambre de la fase 1 para generar el "Champion"
        self.swarm = SatGeneticSwarm(population_size=10, n=n, k=k, timeout_ms=timeout_ms)
        
    def play_round(self, evolutions: int = 5) -> dict[str, Any]:
        """Juega una ronda adversarial: Enjambre Genético vs Z3 K-Color."""
        logger.info(f"--- BATALLA ADVERSARIAL: Enjambre vs Z3 (K={self.k}) ---")
        
        # Turno 1: Generador
        logger.info(f"Generador: Evolucionando grafos por {evolutions} generaciones...")
        evolution_result = self.swarm.evolve(generations=evolutions)
        champion_genome = evolution_result['best_genome']
        
        # Turno 2: Destructor (Z3 Evalúa Colorabilidad)
        logger.info(f"Destructor: Z3 analizando si el grafo óptimo es {self.k}-colorable...")
        eval_result = self.orchestrator.verify_k_colorability(self.n, self.k, champion_genome)
        
        verdict = eval_result['verdict']
        elapsed = eval_result['elapsed_s']
        edges = eval_result['edges_count']
        
        logger.info(f"Veredicto Z3: {verdict} (Tiempo: {elapsed:.4f}s) | Aristas: {edges}")
        
        # Auditoría Causal
        winner = "GENERADOR (Enjambre)" if verdict == "Sat" else "DESTRUCTOR (Z3 Python Fallback)"
        if verdict == "Timeout":
            winner = "EMPATE (Límite Computacional Alcanzado)"
            
        logger.info(f"🏆 Ganador de la Ronda: {winner}")
        
        return {
            "winner": winner,
            "verdict": verdict,
            "elapsed_s": elapsed,
            "edges": edges
        }

if __name__ == "__main__":
    game = SatAdversarialGame(n=10, k=3)
    game.play_round()
