# [C5-REAL] Exergy-Maximized
import logging
from dataclasses import dataclass

from .divergence import DivergenceEngine, ExecutionDiff, Trace

logger = logging.getLogger("cortex.runtime.homeostasis")


@dataclass
class HomeostasisMetrics:
    """Métricas estructuradas emitidas por el loop de control en Shadow Mode."""

    tick: int
    semantic_shift: float
    entropy_gradient: float
    drift_category: str
    requires_action: bool


class DriftThresholds:
    """Umbrales fijos [0.0, 1.0] para la categorización del drift en el espacio causal."""

    EXPECTED_DRIFT_MAX = 0.3  # Exploración válida, ruido térmico natural del agente
    PATHOLOGICAL_DRIFT_MIN = 0.7  # Ruptura de invariantes, divergencia acumulativa/alucinación


class HomeostaticController:
    """
    Control Loop (Self-healing).
    Fase inicial: Shadow Mode (Observe-only). No aplica mutaciones, rollbacks ni resets.
    Mide la calidad del detector (DivergenceEngine) antes de permitir auto-curación activa.
    """

    def __init__(self, divergence_engine: DivergenceEngine):
        self.divergence_engine = divergence_engine
        self.mode = "SHADOW"  # Observe-only by design

    def monitor_and_detect(self, baseline: Trace, current: Trace) -> HomeostasisMetrics:
        """
        Paso 1 y 2: Monitor & Detect Drift.
        Consume el Phase Space causal y calcula la divergencia actual.
        """
        diff: ExecutionDiff = self.divergence_engine.diff(baseline, current)
        return self._analyze(diff)

    def _analyze(self, diff: ExecutionDiff) -> HomeostasisMetrics:
        """
        Paso 3: Analizar.
        Clasifica el shift geométrico [0, 1] y el gradiente de entropía.
        """
        shift = diff.semantic_shift
        entropy = diff.entropy_gradient

        # Categorización del vector de drift
        if shift <= DriftThresholds.EXPECTED_DRIFT_MAX:
            category = "EXPECTED_DRIFT"
            action_needed = False
        elif shift >= DriftThresholds.PATHOLOGICAL_DRIFT_MIN:
            category = "PATHOLOGICAL_DRIFT"
            action_needed = True
        else:
            category = "WARNING_DRIFT"  # Zona de transición de divergencia
            # Acción preventiva si la entropía crece muy rápido en la zona media
            action_needed = True if entropy > 0.8 else False

        metrics = HomeostasisMetrics(
            tick=diff.tick,
            semantic_shift=shift,
            entropy_gradient=entropy,
            drift_category=category,
            requires_action=action_needed,
        )

        self._emit_shadow_telemetry(metrics, diff)
        return metrics

    def _emit_shadow_telemetry(self, metrics: HomeostasisMetrics, diff: ExecutionDiff) -> None:
        """
        Paso 4 (Shadow): Logs estructurados sin ejecución de actuadores.
        Emite la topología del error para calibración.
        """
        log_data = {
            "mode": self.mode,
            "tick": metrics.tick,
            "semantic_shift": f"{metrics.semantic_shift:.3f}",
            "entropy_gradient": f"{metrics.entropy_gradient:.3f}",
            "category": metrics.drift_category,
            "action_flagged": metrics.requires_action,
        }

        if metrics.drift_category == "PATHOLOGICAL_DRIFT":
            logger.error(f"[SHADOW-MODE] PATHOLOGICAL DRIFT DETECTED: {log_data}")
        elif metrics.requires_action:
            logger.warning(f"[SHADOW-MODE] WARNING DRIFT DETECTED: {log_data}")
        else:
            logger.info(f"[SHADOW-MODE] EXPECTED DRIFT: {log_data}")

    def remediate(self, metrics: HomeostasisMetrics) -> None:
        """
        Paso 5: Remediar -> Validar. (Desactivado).
        Futuros actuadores ultra-conservadores irán aquí:
        - Degradar a modo seguro
        - Reset controlado del agente local
        - Rollback criptográfico al último hash-chain verificado
        """
        if self.mode == "SHADOW":
            logger.debug("[SHADOW-MODE] Remediation bypassed. System remains untouched.")
            return

        raise NotImplementedError("Actuators are locked. Shadow Mode only.")
