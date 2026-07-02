# [C5-REAL] Exergy-Maximized
import logging
import math

from babylon60.crypto.hash_registry import cortex_hash
from babylon60.engine.flow.causality_models import (
    Claim,
    DecisionTrace,
    EpistemicStatus,
    TruthScore,
    UtilityScore,
)

logger = logging.getLogger("babylon60.engine.causal.epistemic_physics")


class SemanticParticle:
    def __init__(self, claim: Claim):
        self.claim = claim

        # Termodinámica LLM: Calcular Entropía de Shannon del texto original
        try:
            from babylon60.engine.core.ultrathink_physics import UltrathinkPhysicsEngine
            self.entropy_score = max(0.1, UltrathinkPhysicsEngine.estimate_shannon_entropy(claim.statement))
        except ImportError:
            self.entropy_score = 1.0

        # Determinar la masa (confianza inicial) a partir del promedio de evidencias
        if claim.evidence_list:
            self.mass = max(
                0.01, sum(e.confidence for e in claim.evidence_list) / len(claim.evidence_list)
            )
        else:
            self.mass = 0.5

        # Determinar posición semántica (embedding). Intentar leer de metadatos o crear dummy bidimensional.
        self.position: list[float] | None = None

        # Buscar en metadatos de las evidencias
        for e in claim.evidence_list:
            if e.metadata and "embedding" in e.metadata and e.metadata["embedding"] is not None:
                self.position = list(e.metadata["embedding"])
                break

        # Si no hay, usar un hash reproducible para asignar coordenadas fijas bidimensionales
        if self.position is None:
            h = hash(claim.id)
            # Normalizar entre -1.0 y 1.0
            x = (h % 1000) / 500.0 - 1.0
            y = ((h // 1000) % 1000) / 500.0 - 1.0
            self.position = [x, y]

        # Garantizar que pyright sepa que position nunca es None a partir de este punto
        assert self.position is not None

        self.velocity: list[float] = [0.0] * len(self.position)
        self.active = True

    def apply_impulse(self, impulse: list[float]):
        assert self.position is not None
        for i in range(len(self.position)):
            self.velocity[i] += impulse[i] / self.mass

    def update(self, dt: float, base_decay_rate: float):
        if not self.active:
            return
        
        # El decaimiento real es inversamente proporcional a la entropía (menor entropía = decaimiento exponencial)
        thermal_decay_rate = base_decay_rate / self.entropy_score
        
        assert self.position is not None
        for i in range(len(self.position)):
            self.position[i] += self.velocity[i] * dt
            self.velocity[i] *= 1.0 - thermal_decay_rate * dt

        # Degradación temporal
        self.mass = max(0.01, self.mass - thermal_decay_rate * 0.02 * dt)


class EpistemicPhysicsArbiter:
    """
    Resolvedor de colisiones semánticas basado en la física de impulsos de Newton.
    Trata las contradicciones entre afirmaciones como colisiones físicas.
    """

    def __init__(self, decay_rate: float = 0.05, collision_threshold: float = 0.8):
        self.decay_rate = decay_rate
        self.collision_threshold = collision_threshold

    def resolve_collisions(self, claims: list[Claim]) -> list[DecisionTrace]:
        particles = [SemanticParticle(c) for c in claims]

        # Simular 3 pasos de integración de colisiones
        dt = 0.5
        for _ in range(3):
            for i in range(len(particles)):
                for j in range(i + 1, len(particles)):
                    p1 = particles[i]
                    p2 = particles[j]

                    if not (p1.active and p2.active):
                        continue

                    # Comprobar si hay una relación de contradicción directa en los metadatos
                    is_contradictory = False

                    # Chequear en las evidencias del claim 1 si contradice al claim 2
                    for e in p1.claim.evidence_list:
                        if e.metadata and e.metadata.get("contradicts") == p2.claim.id:
                            is_contradictory = True
                            break

                    # Chequear en las evidencias del claim 2 si contradice al claim 1
                    for e in p2.claim.evidence_list:
                        if e.metadata and e.metadata.get("contradicts") == p1.claim.id:
                            is_contradictory = True
                            break

                    if is_contradictory:
                        assert p1.position is not None and p2.position is not None
                        # Distancia euclidiana en el espacio semántico
                        squared_sum = sum(
                            (x1 - x2) ** 2 for x1, x2 in zip(p1.position, p2.position, strict=True)
                        )
                        dist = math.sqrt(squared_sum)

                        if dist < self.collision_threshold:
                            # Dirección de la colisión
                            direction = [
                                x2 - x1 for x1, x2 in zip(p1.position, p2.position, strict=True)
                            ]
                            norm = math.sqrt(sum(x**2 for x in direction))
                            if norm == 0:
                                norm = 0.001
                                direction = [0.001] * len(direction)
                            direction = [x / norm for x in direction]

                            # Conservación de momento con masa proporcional a la confianza
                            total_mass = p1.mass + p2.mass
                            mass_ratio = p1.mass / total_mass

                            force = (self.collision_threshold - dist) * 3.0
                            impulse_p1 = [-x * force * (1.0 - mass_ratio) for x in direction]
                            impulse_p2 = [x * force * mass_ratio for x in direction]

                            p1.apply_impulse(impulse_p1)
                            p2.apply_impulse(impulse_p2)

                            # Reducción de masa (daño por colisión semántica)
                            p1.mass = max(0.01, p1.mass - force * 0.15 * (1.0 - mass_ratio))
                            p2.mass = max(0.01, p2.mass - force * 0.15 * mass_ratio)

                            if p1.mass <= 0.1:
                                p1.active = False
                            if p2.mass <= 0.1:
                                p2.active = False

            # Paso de actualización física
            for p in particles:
                p.update(dt, self.decay_rate)

        # Generar DecisionTrace final
        traces = []
        for p in particles:
            trace_steps = [
                f"INIT: Evaluating claim {p.claim.id} via EpistemicPhysicsArbiter",
                f"PHYS: Final semantic mass (confidence) = {p.mass:.4f}",
                f"PHYS: Particle active status = {p.active}",
            ]

            if not p.active:
                verdict = EpistemicStatus.CONTRADICTED
                truth = 0.0
                trace_steps.append("DECISION: Claim collapsed due to semantic collision.")
            else:
                truth = p.mass
                if truth >= 0.8:
                    verdict = EpistemicStatus.VERIFIED
                elif truth >= 0.5:
                    verdict = EpistemicStatus.SUPPORTED
                else:
                    verdict = EpistemicStatus.SPECULATIVE
                trace_steps.append(f"DECISION: Verdict set to {verdict.value}")

            raw_trace = "\n".join(trace_steps)
            trace_hash = cortex_hash(raw_trace.encode("utf-8"))

            traces.append(
                DecisionTrace(
                    verdict=verdict,
                    trace_steps=trace_steps,
                    trace_hash=trace_hash,
                    truth_score=TruthScore(value=truth),
                    utility_score=UtilityScore(value=0.8),
                )
            )
        return traces
