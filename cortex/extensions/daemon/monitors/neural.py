"""Neural intent monitor for MOSKV daemon."""

from __future__ import annotations

import logging

from cortex.extensions.daemon.models import NeuralIntentAlert

logger = logging.getLogger("moskv-daemon")


class NeuralIntentMonitor:
    """Reads system context and infers user intent via NeuralIntentEngine."""

    def __init__(self) -> None:
        self._engine = None

    def check(self) -> list[NeuralIntentAlert]:
        alerts: list[NeuralIntentAlert] = []
        try:
            from cortex.extensions.agents.neural import NeuralIntentEngine
            from cortex.extensions.platform.sys import is_macos

            if not is_macos():
                return []

            if not self._engine:
                self._engine = NeuralIntentEngine()

            context = self._engine.read_context()
            raw_clip = context  # simplified — original may have deeper extraction
            hyp = self._engine.infer_intent(raw_clip)  # type: ignore[reportArgumentType]

            if hyp and hyp.confidence > 0:  # type: ignore[reportOperatorIssue]
                alerts.append(
                    NeuralIntentAlert(
                        intent=hyp.intent,
                        confidence=hyp.confidence,
                        trigger=hyp.trigger,
                        summary=hyp.summary,
                    )
                )
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("NeuralIntentMonitor failed: %s", e)

        return alerts
