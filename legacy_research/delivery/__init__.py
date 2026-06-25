# [C5-REAL] Exergy-Maximized
"""CORTEX Delivery - Typed Egress Layer.

Routes pipeline results to their delivery targets:
MCP responses, files, webhooks, or CLI stdout.
"""

from legacy_research.delivery.manager import DeliveryManager

__all__ = ["DeliveryManager"]
