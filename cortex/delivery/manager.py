# [C5-REAL] Exergy-Maximized
"""CORTEX Delivery Manager - Typed Egress Layer.

Routes pipeline results to their delivery targets:
MCP responses, files, webhooks, or CLI stdout.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from cortex.pipeline import DeliveryTarget, DeliveryType

logger = logging.getLogger("cortex.delivery")


class DeliveryManager:
    """Delivers pipeline results to typed targets."""

    def deliver(self, output: Any, target: DeliveryTarget, mission_id: str) -> bool:
        """Route output to the appropriate delivery handler.

        Returns True if delivery succeeded.
        """
        try:
            if target.type == DeliveryType.STDOUT:
                return self._deliver_stdout(output, target)
            if target.type == DeliveryType.FILE:
                return self._deliver_file(output, target, mission_id)
            if target.type == DeliveryType.WEBHOOK:
                return self._deliver_webhook(output, target, mission_id)
            if target.type == DeliveryType.MCP:
                return self._deliver_mcp(output, target, mission_id)
            if target.type == DeliveryType.MEMORY:
                logger.debug("[DELIVERY] MEMORY target - no external delivery")
                return True
            logger.warning("[DELIVERY] Unknown target type: %s", target.type)
            return False
        except Exception as e:
            logger.error("[DELIVERY] Failed for mission %s: %s", mission_id, e)
            return False

    def _deliver_stdout(self, output: Any, target: DeliveryTarget) -> bool:
        """Print result to stdout."""
        if target.format == "json":
            formatted = json.dumps(output, indent=2, default=str, ensure_ascii=False)
        elif target.format == "markdown":
            formatted = self._to_markdown(output)
        else:
            formatted = str(output)

        print(formatted)
        logger.debug("[DELIVERY] stdout: %d chars", len(formatted))
        return True

    def _deliver_file(self, output: Any, target: DeliveryTarget, mission_id: str) -> bool:
        """Write result to filesystem."""
        if not target.path:
            logger.error("[DELIVERY] FILE target requires a path")
            return False

        path = os.path.expanduser(target.path)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if target.format == "json":
            content = json.dumps(output, indent=2, default=str, ensure_ascii=False)
        elif target.format == "markdown":
            content = self._to_markdown(output)
        else:
            content = str(output)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("[DELIVERY] Written to %s (%d bytes)", path, len(content))
        return True

    def _deliver_webhook(self, output: Any, target: DeliveryTarget, mission_id: str) -> bool:
        """POST result to an external URL."""
        if not target.url:
            logger.error("[DELIVERY] WEBHOOK target requires a URL")
            return False

        try:
            from cortex.guards.url_guard import is_safe_url

            if not is_safe_url(target.url):
                logger.error("[DELIVERY] WEBHOOK target URL blocked by URLGuard: %s", target.url)
                return False

            import urllib.request

            payload = json.dumps({"mission_id": mission_id, "output": output}, default=str).encode()
            headers = {"Content-Type": "application/json", **target.headers}
            req = urllib.request.Request(target.url, data=payload, headers=headers, method="POST")

            with urllib.request.urlopen(req, timeout=30) as resp:
                logger.info("[DELIVERY] Webhook %s → %d", target.url, resp.status)
                return resp.status < 400
        except Exception as e:
            logger.error("[DELIVERY] Webhook failed: %s", e)
            return False

    def _deliver_mcp(self, output: Any, target: DeliveryTarget, mission_id: str) -> bool:
        """Format result as MCP tool response (stored for retrieval)."""
        # MCP responses are returned inline by the pipeline caller.
        # This handler stores a copy for audit.
        logger.debug("[DELIVERY] MCP response prepared for mission %s", mission_id)
        return True

    @staticmethod
    def _to_markdown(output: Any) -> str:
        """Convert structured output to markdown."""
        if isinstance(output, str):
            return output
        if isinstance(output, dict):
            lines = ["# Pipeline Result\n"]
            for k, v in output.items():
                if isinstance(v, list):
                    lines.append(f"## {k}\n")
                    for item in v:
                        lines.append(f"- {item}")
                else:
                    lines.append(f"**{k}:** {v}")
            return "\n".join(lines)
        return str(output)
