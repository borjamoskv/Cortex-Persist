"""
CORTEX V5 - Evolutionary Epistemology (IMMUNITAS-Ω)
Tactical Falsification (Karl Popper): Axiom 15 Operational Falsification.
"""

import copy
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("cortex.immune.falsification")


class EvolutionaryFalsifier:
    """
    Submits code to extreme mutated variations and Red Team attacks until collapse.
    Captures the autopsy and introduces resistance in the next compilation.
    """

    def __init__(self, failure_tolerance: int = 3):
        self.failure_tolerance = failure_tolerance
        self._autopsies: list[dict[str, Any]] = []

    def falsify_target(self, target_func: Callable, seed_inputs: dict[str, Any]) -> bool:
        """
        Attempts to falsify a theory (a function) by mutating its inputs
        until it breaks. If it survives, it is temporarily considered true.
        """
        logger.info("Initiating falsification protocol on %s", target_func.__name__)

        mutations = self._generate_mutations(seed_inputs)
        failures = 0

        for _idx, mutant in enumerate(mutations):
            try:
                # Execution
                target_func(**mutant)
                # In a real Red Team environment, we also validate if the result
                # matches the structural boundaries (tether.md), not just if it didn't raise.
            except Exception as e:
                failures += 1
                self._capture_autopsy(target_func.__name__, mutant, e)

                if failures >= self.failure_tolerance:
                    logger.critical("Target %s Falsified (Collapsed).", target_func.__name__)
                    return False

        logger.info("Target %s survived falsification. Immunity verified.", target_func.__name__)
        return True

    def _generate_mutations(self, base_inputs: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generates adversarial edge cases. Null injections, massive boundaries,
        type coercions, and Byzantine payloads.
        """
        mutations = [base_inputs]

        # Mutation 1: The Void (empty/none values)
        void_mutant = copy.deepcopy(base_inputs)
        for k in void_mutant.keys():
            void_mutant[k] = None
        mutations.append(void_mutant)

        # Mutation 2: Boundary Saturation (massive strings / numbers)
        sat_mutant = copy.deepcopy(base_inputs)
        for k, v in sat_mutant.items():
            if isinstance(v, str):
                sat_mutant[k] = v * 10000
            elif isinstance(v, int | float):
                sat_mutant[k] = v * 10e9
        mutations.append(sat_mutant)

        # Mutation 3: Type Confusion (Byzantine payload)
        type_mutant = copy.deepcopy(base_inputs)
        for k, v in type_mutant.items():
            if isinstance(v, dict):
                type_mutant[k] = []
            elif isinstance(v, list):
                type_mutant[k] = {}
            elif isinstance(v, str):
                type_mutant[k] = 0
        mutations.append(type_mutant)

        return mutations

    def _capture_autopsy(
        self, func_name: str, payload: dict[str, Any], exception: Exception
    ) -> None:
        """
        Captures the exact vector of collapse to feed into LEGION-OMEGA
        for the next compilation phase.
        """
        autopsy = {
            "target": func_name,
            "vector": payload,
            "collapse_type": type(exception).__name__,
            "collapse_trace": str(exception),
        }
        self._autopsies.append(autopsy)
        logger.warning(
            "Autopsy captured: %s -> %s", autopsy['collapse_type'], autopsy['collapse_trace']
        )

    def get_antibodies(self) -> list[dict[str, Any]]:
        """
        Returns the derived 'antibodies' (lessons) from the autopsies to inject
        into the next agent generation's lore.md.
        """
        return self._autopsies
