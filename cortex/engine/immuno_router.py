import re
import hashlib
from typing import Dict, Callable, Optional

class MicroAgent:
    def __init__(self, name: str, antigen_regex: str, handler: Callable[[str], str]):
        self.name = name
        self.antigen_regex = re.compile(antigen_regex, re.IGNORECASE)
        self.handler = handler

class MHCRouter:
    """
    [C5-REAL] Major Histocompatibility Complex (MHC) Router.
    Enruta tareas (antígenos) de forma determinista usando firmas HASH y regex,
    erradicando el uso de un 'LLM Orchestrator' que consume tokens y alucina.
    """
    def __init__(self):
        self._t_cells: list[MicroAgent] = []
        
    def bind_t_cell(self, agent: MicroAgent):
        """Registra un agente (Célula T) con su firma específica."""
        self._t_cells.append(agent)
        
    def _extract_antigen_signature(self, task_intent: str) -> str:
        """
        Extrae la firma del antígeno usando stripping estructural (hash SHA-256).
        Simula la presentación de péptidos en la superficie celular.
        """
        # Normalizamos el intento para remover entropía
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', task_intent).strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def expose_and_route(self, task_intent: str) -> str:
        """
        Expone el antígeno a la malla. La expansión clonal (ejecución) ocurre
        solo si hay un 'pattern match' absoluto con el antígeno.
        Consumo de tokens LLM para enrutamiento: 0.0
        """
        # MHC Signature generada pero el binding se hace en la superficie (regex del Agente)
        for agent in self._t_cells:
            if agent.antigen_regex.search(task_intent):
                # Expansión clonal: El agente específico actúa
                return agent.handler(task_intent)
                
        # Respuesta inmune fallida o tarea no soportada (Evita alucinación del LLM)
        return "[APOPTOSIS] Tarea rechazada por el complejo MHC. Ningún agente compatible."

