# [C5-REAL] Exergy-Maximized
import logging

from babylon60.engine.smte.llm_mutator import llm_driven_mutator
from babylon60.engine.smte.parser import AgentASTParser
from babylon60.engine.smte.weismann_barrier import enforce_weismann_barrier
from babylon60.guards.exergy_guard import calculate_exergy

logger = logging.getLogger("cortex.engine.smte.trigger")
logging.basicConfig(level=logging.INFO)


def run_mutation_cycle(target_path: str):
    logger.info(f"[*] Starting mutation cycle for {target_path}")

    def apply_mutation_to_file(file_path: str) -> bool:
        parser = AgentASTParser(file_path)
        initial_exergy = calculate_exergy(parser.source_code)

        logger.info("[*] Applying LLM-Driven AST Mutation...")
        if llm_driven_mutator(parser):
            new_source = parser.crystallize()
            new_exergy = calculate_exergy(new_source)
            if new_exergy >= initial_exergy:
                logger.info(
                    f"[+] Mutation improved/maintained exergy ({initial_exergy:.4f} -> {new_exergy:.4f})"
                )
                return True
            logger.warning("[-] Exergy degraded. Rejecting mutation.")
            return False
        logger.error("[-] Mutation structural check failed.")
        return False

    if "cortex/engine/" in target_path:
        logger.warning("[!] KERNEL COMPONENT DETECTED. Activating Weismann Barrier.")
        success = enforce_weismann_barrier(target_path, apply_mutation_to_file)
        if success:
            logger.info("[WEISMANN] Kernel Self-Modification Successful.")
        else:
            logger.error("[WEISMANN] Kernel Self-Modification Aborted to prevent thermal death.")
    else:
        apply_mutation_to_file(target_path)


if __name__ == "__main__":
    target = "cortex/engine/smte/parser.py"
    run_mutation_cycle(target)
