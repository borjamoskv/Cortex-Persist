"""
VisAnomReasoner Topology - VLM Time-Series Rationales for Anomaly Detection
Implements algorithms inspired by arXiv:2605.30344v1 for visual time-series reasoning.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger("cortex.exergy.vision")


@dataclass
class AnomalyRationale:
    timestamp_range: tuple[float, float]
    anomaly_score: float
    rationale: str
    is_anomalous: bool


class VisAnomReasoner:
    """
    Simulates VLM reasoning over a sliding window of time-series visual embeddings
    to detect anomalies and generate grounded rationales.
    """

    def __init__(self, window_size: int = 5, anomaly_threshold: float = 0.75):
        self.window_size = window_size
        self.anomaly_threshold = anomaly_threshold
        self.embedding_buffer: deque[tuple[float, str]] = deque(maxlen=window_size)
        logger.info(
            "VisAnomReasoner initialized (window_size=%d, threshold=%.2f)",
            self.window_size,
            self.anomaly_threshold,
        )

    def process_frame(self, timestamp: float, frame_embedding_hex: str) -> AnomalyRationale | None:
        """
        Ingests a frame's embedding hash. If the buffer is full, calculates the time-series
        variance and emits a rationale.
        """
        self.embedding_buffer.append((timestamp, frame_embedding_hex))

        if len(self.embedding_buffer) < self.window_size:
            return None

        return self._generate_rationale()

    def _generate_rationale(self) -> AnomalyRationale:
        """
        Evaluates the current time-series window to detect structural drift or visual anomalies.
        """
        # C5-REAL deterministic pseudo-variance calculation
        variances: list[float] = []
        frames = list(self.embedding_buffer)

        for i in range(1, len(frames)):
            # Convert first 8 hex chars to int for lightweight delta simulation
            try:
                prev_hash = int(frames[i - 1][1][:8], 16)
                curr_hash = int(frames[i][1][:8], 16)
                # Normalize delta to [0, 1]
                delta = abs(curr_hash - prev_hash) / float(0xFFFFFFFF)
                variances.append(delta)
            except ValueError:
                variances.append(1.0)  # Maximum variance if invalid hex

        avg_variance = sum(variances) / len(variances) if variances else 0.0

        # Non-linear scaling to simulate VLM confidence
        anomaly_score = min(1.0, avg_variance * 1.5)
        is_anomalous = anomaly_score >= self.anomaly_threshold

        if is_anomalous:
            rationale = (
                f"Detected severe spatio-temporal divergence in window. "
                f"Variance shift reached {avg_variance:.3f}, indicating potential visual corruption."
            )
            logger.warning("VisAnomReasoner: Anomaly Detected! Score: %.2f", anomaly_score)
        else:
            rationale = "Temporal window visually coherent. No structural drift detected."

        return AnomalyRationale(
            timestamp_range=(frames[0][0], frames[-1][0]),
            anomaly_score=anomaly_score,
            rationale=rationale,
            is_anomalous=is_anomalous,
        )
