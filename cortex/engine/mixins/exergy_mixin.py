import logging
from typing import Any

logger = logging.getLogger("cortex.engine.exergy")


class ExergyMixin:
    """
    Mixin implementing the CORTEX Unified Equation v0.1: Thermoynamic POMDP.
    Computes Exergy (executable useful truth) and gatekeeps the Solid State transition.
    """

    def compute_exergy_v3(
        self,
        causal_gap_reduction: float,
        weight: float,
        entropy_injected: float,
        cost_lambda: float,
    ) -> float:
        """
        Closed formula for Exergy (Xi).
        Ξ_t = (ΔC_gap * weight) - (E_inj * cost_lambda)

        Args:
            causal_gap_reduction: Quantifiable reduction in uncertainty (0.0 to 1.0)
            weight: Task criticality or biological stakes (e.g. 1.0 to 10.0)
            entropy_injected: LLM stochasticity cost (temperature, tokens, novelty)
            cost_lambda: Physical toll (latency, constraints penalty)

        Returns:
            float: Net Exergy yield. Must be > threshold to pass promotion gates.
        """
        signal_yield = causal_gap_reduction * weight
        thermal_cost = entropy_injected * cost_lambda

        exergy_net = signal_yield - thermal_cost

        logger.debug(
            "[EXERGY] signal=%.4f, thermal_cost=%.4f -> net=%.4f",
            signal_yield,
            thermal_cost,
            exergy_net,
        )
        return exergy_net

    def check_solid_state(self, metrics: dict[str, Any]) -> bool:
        """
        Trigger condition for Solid State convergence.

        Expected metrics schema:
        - entropy_injection: float
        - dissipation_capacity: float
        - exergy_gradient: float (dΞ/dt)
        - causal_integrity: bool
        """
        entropy_inj = metrics.get("entropy_injection", 1.0)
        dissipation = metrics.get("dissipation_capacity", 0.0)
        exergy_grad = metrics.get("exergy_gradient", -1.0)
        causal_integrity = metrics.get("causal_integrity", False)

        is_solid = entropy_inj < dissipation and exergy_grad > 0.0 and causal_integrity is True

        if is_solid:
            logger.info("[SOLID STATE] System converged. Generating Sovereign execution.")
        else:
            logger.debug("[SOLID STATE] Bounds not met. Remaining in fluid stochastic state.")

        return is_solid

    def validate_thermodynamic_contract(self, exergy_net: float, contract: dict[str, Any]) -> bool:
        """
        Enforces that the generation satisfies the thermodynamic contract constraints.
        """
        exergy_min = contract.get("exergy_min", 0.0)

        if exergy_net < exergy_min:
            logger.warning(
                "[THERMODYNAMICS] Breach: net exergy %.4f < min %.4f", exergy_net, exergy_min
            )
            return False

        return True
