"""CORTEX Delivery — Typed Egress Layer.

Routes pipeline results to their delivery targets:
MCP responses, files, webhooks, or CLI stdout.
"""

from cortex.delivery.manager import DeliveryManager

__all__ = ["DeliveryManager"]
