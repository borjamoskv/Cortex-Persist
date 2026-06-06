# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import subprocess
from typing import Any

from cortex.extensions.daemon.models import ASTAlert  # type: ignore[reportAttributeAccessIssue]
from cortex.extensions.daemon.monitors.base import IntervalProjectMonitor

logger = logging.getLogger("moskv-daemon")


class ASTOracleMonitor(IntervalProjectMonitor[ASTAlert]):
    """Monitors the project for Pyright strict typing drift."""

    def __init__(
        self,
        projects: dict[str, str] | None = None,
        interval_seconds: int = 3600,
        engine: Any = None,
    ):
        super().__init__(projects, interval_seconds, engine)

    def _check_ast_entropy(self, project: str, path_str: str) -> ASTAlert | None:
        try:
            logger.info("ASTOracle: Midiendo deuda estructural en %s", project)

            # Executing pyright directly
            result = subprocess.run(
                ["uv", "run", "pyright", "--outputjson"],
                cwd=path_str,
                capture_output=True,
                text=True,
                timeout=45,
            )

            import json

            try:
                data = json.loads(result.stdout)
                error_count = data.get("summary", {}).get("errorCount", 0)
                warning_count = data.get("summary", {}).get("warningCount", 0)

                total_entropy = error_count + warning_count

                if total_entropy > 0:
                    return ASTAlert(
                        project=project,
                        entropy_score=total_entropy,
                        message=f"AST Drift Detected: {error_count} errors, {warning_count} warnings.",
                    )
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)

        except Exception as e:
            logger.error("ASTOracle failed to scan %s: %s", project, e)

        return None

    def check(self) -> list[ASTAlert]:
        return self.generate_alerts(self._check_ast_entropy)
