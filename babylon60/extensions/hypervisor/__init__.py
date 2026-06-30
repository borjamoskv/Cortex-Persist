# [C5-REAL] Exergy-Maximized
"""CORTEX Hypervisor - Public API.

The Telescope Inversion: maximum simplicity on the outside.

Usage::

    from babylon60.extensions.hypervisor import AgencyHypervisor, Memory, HealthReport

    hypervisor = AgencyHypervisor(engine)
    handle = hypervisor.create_handle("tenant-abc", "my-project")

    receipt = await handle.remember("The launch date is Q2 2026")
    memories = await handle.recall("when is the launch?")
    health = await handle.reflect()
"""

from babylon60.extensions.hypervisor.belief_engine import BeliefEngine
from babylon60.extensions.hypervisor.belief_object import BeliefObject, BeliefVerdict
from babylon60.extensions.hypervisor.core import AgencyHypervisor
from babylon60.extensions.hypervisor.handle import AgentHandle
from babylon60.extensions.hypervisor.models import HealthReport, Memory, Receipt

__all__ = [
    "AgencyHypervisor",
    "AgentHandle",
    "BeliefEngine",
    "BeliefObject",
    "BeliefVerdict",
    "HealthReport",
    "Memory",
    "Receipt",
]
