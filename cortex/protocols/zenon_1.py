"""
ZENÓN-1: Formalización Algorítmica del Detector de Rendimiento Decreciente.
Protocolo Soberano para prevenir la recursividad infinita (Parálisis de Análisis)
en enjambres multi-modelo y ciclos meta-cognitivos (OUROBOROS-∞ / SINGULARIS-0).

Axioma 15: La Inteligencia no es pensar infinitamente;
es saber matemáticamente cuándo dejar de pensar y actuar.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger("cortex.protocols.zenon_1")


class ZenonSignal(Enum):
    """Zeno Exhaustion Signals."""

    D_VALUE_CONVERGENCE = auto()  # S1: Delta Value drops below threshold ε.
    ZENO_RATIO_INVERTED = auto()  # S2: Cost consumed > Value produced.
    ENTROPIC_INVERSION = auto()  # S3: Adding thought increases confusion.


@dataclass
class CognitiveIteration:
    """Una ronda de reflexión o meta-análisis del enjambre o agente."""

    iteration_id: int
    decision_candidate: str

    # 1. Valor (V): Certeza, información nueva útil.
    value_produced: float

    # 2. Coste (C): Tokens, tiempo de CPU, complejidad termodinámica de la decisión.
    computational_cost: float

    # 3. Entropía (S): Índice de confusión o discrepancia semántica en el texto generado.
    entropy_score: float

    @property
    def zeno_ratio(self) -> float:
        """Ratio entre Coste(C) y Valor(V). Si > 1.0, pensar cuesta más que lo que rinde."""
        if self.value_produced <= 0:
            return float("inf")
        return self.computational_cost / self.value_produced


@dataclass
class ZenoExhaustionException(Exception):
    """Lanzada cuando la recursividad alcanza un estado estricto de agotamiento Zenon."""

    signal: ZenonSignal
    iteration_k: int
    delta_v_final: float
    zeno_ratio_final: float
    message: str


class ZenonDetector:
    """
    El mecanismo de freno para ciclos meta-cognitivos.
    Mide el ΔV, el Ratio de Zenón (C/V) y las inversiones de Entropía.
    """

    def __init__(
        self, epsilon: float = 0.05, convergence_n: int = 3, max_entropy_inversions: int = 2
    ):
        self.epsilon = epsilon  # Mínimo valor requerido por iteración
        self.convergence_n = convergence_n  # Iteraciones requeridas para declarar estancamiento
        self.max_entropy_inversions = max_entropy_inversions

        self.history: list[CognitiveIteration] = []

    def absorb_iteration(self, iteration: CognitiveIteration) -> ZenoExhaustionException | None:
        """
        Absorbe la iteración de cálculo algorítmico y comprueba si hemos topado
        con el Muro Asintótico de Kleene-Zenon.
        """
        self.history.append(iteration)
        logger.debug(
            f"[ZENÓN-1] Iteración {iteration.iteration_id} absorbida. V={iteration.value_produced:.4f}, C={iteration.computational_cost:.4f}, S={iteration.entropy_score:.4f}"
        )

        # Necesitamos algo de historia para derivar el ΔV
        if len(self.history) < 2:
            return None

        # ==========================================
        # SIGNAL 1: CONVERGENCIA DE DELTA VALOR (S1)
        # ==========================================
        # Verificamos las últimas 'N' iteraciones para ver si el ΔV cayó por debajo de ε
        if len(self.history) > self.convergence_n:
            recent_deltas = [
                self.history[i].value_produced - self.history[i - 1].value_produced
                for i in range(-self.convergence_n, 0)
            ]

            # Si todas las iteraciones recientes tuvieron una mejora marginal insignificante
            if all(d_v < self.epsilon for d_v in recent_deltas):
                logger.warning(
                    f"[ZENÓN-1] ALERTA S1: Convergencia de V detectada. ΔV {recent_deltas[-1]:.4f} < {self.epsilon}."
                )
                return ZenoExhaustionException(
                    signal=ZenonSignal.D_VALUE_CONVERGENCE,
                    iteration_k=iteration.iteration_id,
                    delta_v_final=recent_deltas[-1],
                    zeno_ratio_final=iteration.zeno_ratio,
                    message="El agua dejó de calentarse, pero el fuego sigue encendido (Convergencia ΔV).",
                )

        # ==========================================
        # SIGNAL 2: INVERSIÓN DEL RATIO DE ZENÓN (S2)
        # ==========================================
        # Gastar más energía evaluando que el valor resultante derivado
        if iteration.zeno_ratio > 1.0:
            logger.warning(
                f"[ZENÓN-1] ALERTA S2: Coste computacional supera el valor semántico. Ratio Z = {iteration.zeno_ratio:.2f}."
            )
            # Se permite 1 anomalía, pero si la decadencia es estricta, colapsa
            return ZenoExhaustionException(
                signal=ZenonSignal.ZENO_RATIO_INVERTED,
                iteration_k=iteration.iteration_id,
                delta_v_final=self.history[-1].value_produced - self.history[-2].value_produced,
                zeno_ratio_final=iteration.zeno_ratio,
                message="Pensar está siendo energéticamente más costoso que el valor de la decisión generada.",
            )

        # ==========================================
        # SIGNAL 3: INVERSIÓN ENTRÓPICA (S3)
        # ==========================================
        # Más reflexión = Más confusión.
        if len(self.history) > self.max_entropy_inversions:
            inversion_count = 0
            for i in range(-self.max_entropy_inversions, 0):
                # Entropía subiendo = Empeoramiento. (Debería bajar o ser constante).
                if self.history[i].entropy_score > self.history[i - 1].entropy_score:
                    inversion_count += 1

            if inversion_count >= self.max_entropy_inversions:
                logger.error(
                    "[ZENÓN-1] ALERTA S3: Fallo Categórico por Aumento Entrópico. La iteración genera caos."
                )
                return ZenoExhaustionException(
                    signal=ZenonSignal.ENTROPIC_INVERSION,
                    iteration_k=iteration.iteration_id,
                    delta_v_final=self.history[-1].value_produced - self.history[-2].value_produced,
                    zeno_ratio_final=iteration.zeno_ratio,
                    message="Ciclo Meta-Cognitivo Tóxico: cada reflexión adicional AUMENTA la incertidumbre del enjambre.",
                )

        return None


class ZenonColapseEngine:
    """Motor de Ejecución Forzada (FREEZE -> SELECT -> EXECUTE -> LEARN)"""

    @staticmethod
    def colapse(detector: ZenonDetector) -> CognitiveIteration:
        """
        Obliga a la convergencia a partir del historial capturado por el ZENÓN-1.
        Soberanía en tiempo real: Se toma la decisión óptima estática en vez de perseguir un espejismo asintótico.
        """
        k_history = detector.history
        if not k_history:
            raise RuntimeError("Imposible aplicar colapso Zenón sin historial previo.")

        logger.info(
            "[ZENÓN-1 Colapse] FASE 1: FREEZE ejecutada. Recursión congelada en iteración K."
        )

        # FASE 2: SELECT -> Buscar qué iteración maximizó el Valor Absoluto asumiendo ratios estables.
        best_candidate = max(k_history, key=lambda x: (x.value_produced, -x.entropy_score))
        logger.info(
            f"[ZENÓN-1 Colapse] FASE 2: SELECT completada. Seleccionada iteración {best_candidate.iteration_id}."
        )

        # FASE 3: EXECUTE / LEARN se devuelven al Orquestador Principal o Motor Legión
        return best_candidate


# =========================================================================
# Ejemplo de uso Termodinámico en un Loop Meta-Cognitivo
# =========================================================================
if __name__ == "__main__":
    detector = ZenonDetector()

    # Simulando reflexiones de un enjambre (V: Value, C: Cost, S: Entropy)
    simulated_loop = [
        CognitiveIteration(
            1, "Opcion A - Borrador", value_produced=10.0, computational_cost=1.5, entropy_score=0.9
        ),
        CognitiveIteration(
            2, "Opcion A - Refinado", value_produced=25.0, computational_cost=2.0, entropy_score=0.6
        ),
        CognitiveIteration(
            3,
            "Opcion A - Micro Opt",
            value_produced=26.0,
            computational_cost=2.5,
            entropy_score=0.55,
        ),
        CognitiveIteration(
            4,
            "Opcion A - Rumiación Pura",
            value_produced=26.2,
            computational_cost=3.0,
            entropy_score=0.56,
        ),
        CognitiveIteration(
            5,
            "Opcion A - Duda existencial",
            value_produced=26.25,
            computational_cost=3.5,
            entropy_score=0.6,
        ),
    ]

    for i, it in enumerate(simulated_loop):
        print(f"\\n--- Iteración {it.iteration_id} ---")
        exhaustion_error = detector.absorb_iteration(it)
        if exhaustion_error:
            print(f"\\n🚨 COLAPSO ZENÓN (Señal: {exhaustion_error.signal.name})")
            print(f"Razón: {exhaustion_error.message}")

            # Forzar colapso
            best_decision = ZenonColapseEngine.colapse(detector)
            print(
                f"🎯 EJECUCIÓN SOBERANA: Procediendo implacablemente con output de la Iteración {best_decision.iteration_id}"
            )
            break
