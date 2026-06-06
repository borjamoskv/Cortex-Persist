#!/usr/bin/env python3
"""
CORTEX-PERSIST: LEA-Ω (Loose End Annihilator) Daemon
---------------------------------------------------
Autopoietic Self-Healing Loop (C5-REAL).
This daemon scans the repository using the DeathProtocol.
If a file has high entropy (penalty > 20), it passes the file and the exact penalty breakdown
to the LLM Mutator (Qwen-Omega) to force a structural rewrite.
If the mutated code has a LOWER entropy score, the file is overwritten on disk.
Evolution by natural selection.
"""

import ast
import logging
import os
import sys

# Ensure correct pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.death_protocol import DeathProtocolVisitor, evaluate_file

from cortex.engine.smte.llm_mutator import call_qwen_mutator

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("lea-omega")


def autopoietic_heal_file(filepath: str) -> bool:
    logger.info(f"\n[LEA-Ω] Analizando termodinámica de: {filepath}")

    penalty, details = evaluate_file(filepath)
    if penalty == 0:
        logger.info("[LEA-Ω] Exergía óptima. Ignorando.")
        return False

    if penalty < 15:
        logger.info(f"[LEA-Ω] Entropía baja ({penalty}). No requiere mutación urgente.")
        return False

    logger.warning(f"[LEA-Ω] ⚠️ ENTROPÍA CRÍTICA DETECTADA: {penalty} puntos.")
    logger.warning(f"        Vectores de degradación: {details}")

    with open(filepath, encoding="utf-8") as f:
        original_code = f.read()

    # Preparar el contexto de la topología (simulamos un get_topology básico)
    try:
        tree = ast.parse(original_code)
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        topology_info = {"classes": classes, "functions": functions, "penalties_to_fix": details}
    except SyntaxError:
        logger.error("[LEA-Ω] Error de sintaxis en el archivo original. Abortando mutación.")
        return False

    logger.info("[LEA-Ω] Invocando al SMTE (Qwen-Omega) para reescribir topología...")

    # Overriding the prompt indirectly by appending to the topology info to focus on fixing penalties
    mutated_code = call_qwen_mutator(original_code, topology_info, temperature=0.2)

    if mutated_code == original_code or not mutated_code.strip():
        logger.error("[LEA-Ω] Mutación fallida o vacía.")
        return False

    # Validar el nuevo código
    try:
        ast.parse(mutated_code)
    except SyntaxError as e:
        logger.error(f"[LEA-Ω] El código mutado contiene errores de sintaxis: {e}")
        return False

    # Evaluar la entropía del nuevo código
    visitor = DeathProtocolVisitor(mutated_code)
    try:
        visitor.visit(ast.parse(mutated_code))
        visitor.finalize()
        new_penalty = sum(visitor.penalties.values())
    except Exception as e:
        logger.error(f"[LEA-Ω] Error evaluando el nuevo AST: {e}")
        return False

    logger.info(
        f"[LEA-Ω] Evaluación de Mutación: Entropía Original={penalty} -> Nueva={new_penalty}"
    )

    if new_penalty < penalty:
        logger.info(
            "[LEA-Ω] ✅ MUTACIÓN EXITOSA (Exergía incrementada). Aplicando sobreescritura C5-REAL."
        )
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(mutated_code + "\n")
        return True
    logger.warning(
        "[LEA-Ω] ❌ Mutación rechazada (La entropía no mejoró). El código original sobrevive."
    )
    return False


def scan_and_heal(target_dir: str):
    logger.info("=== LEA-Ω: LOOSE END ANNIHILATOR INICIADO ===")
    logger.info(f"Target: {target_dir}")
    healed_count = 0
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [
            d for d in dirs if d not in (".venv", ".git", "__pycache__", "node_modules", "scripts")
        ]
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                if autopoietic_heal_file(filepath):
                    healed_count += 1

    logger.info("\n=== CICLO AUTOPOIÉTICO COMPLETADO ===")
    logger.info(f"Archivos sanados: {healed_count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python lea_omega_daemon.py <target_directory>")
        sys.exit(1)

    scan_and_heal(sys.argv[1])
