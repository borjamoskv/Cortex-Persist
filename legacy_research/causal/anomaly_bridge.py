# [C5-REAL] Exergy-Maximized
import logging
from typing import Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

logger = logging.getLogger("cortex.engine.causal.anomaly_bridge")

try:
    import sys
    from pathlib import Path

    # Add cortex-core to path since it has a dash in the directory name
    sys.path.append(str(Path(__file__).parent.parent.parent.parent / "cortex-core"))
    from cortex_topology_anomaly_detector import WindowedManifoldDetector
except ImportError:
    logger.warning("Could not import WindowedManifoldDetector. Anomaly detection will be mocked.")
    WindowedManifoldDetector = None


class AnomalyBridge:
    """
    Connects the scheduled observability matrix to the Takens Delay Embedding
    Anomaly Detector. Identifies breaks in structural periodicity.
    """

    def __init__(self, window_size=50, anomaly_threshold=3.0, takens_dim=3, takens_tau=2):
        self.detector = None
        if HAS_NUMPY and WindowedManifoldDetector:
            self.detector = WindowedManifoldDetector(
                window_size=window_size,
                anomaly_threshold=anomaly_threshold,
                takens_dim=takens_dim,
                takens_tau=takens_tau,
            )

        # Keys that we expect in the state payload to form our observation vector
        self.metric_keys = ["cpu_usage", "memory_usage", "api_latency", "error_rate"]

    async def detect_anomaly(self, state: dict[str, Any]) -> bool:
        """
        Receives a state dictionary, maps it to an n-dimensional vector,
        and evaluates its Mahalanobis distance in the Takens manifold.
        """
        if not HAS_NUMPY or not self.detector:
            return False

        vector = []
        for key in self.metric_keys:
            val = state.get(key, 0.0)
            try:
                vector.append(float(val))
            except (ValueError, TypeError):
                vector.append(0.0)

        np_vec = np.array(vector)

        try:
            res = self.detector.step(np_vec)
            if res.get("is_anomaly", False):
                logger.warning(
                    "[AnomalyBridge] Takens Periodicity Break Detected! Distance: %.4f",
                    res.get("mahalanobis_distance", 0.0),
                )
                return True
            return False
        except Exception as e:
            logger.error("[AnomalyBridge] Error detecting anomaly: %s", e)
            return False
