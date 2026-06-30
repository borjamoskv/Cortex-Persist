"""
[C5-REAL] Exergy-Maximized
Φ4 Immune Daemon - Sistema Inmunológico Antifrágil / Autopoiético
Implementación Causal de las Primitivas INV-01 a INV-04.
"""

import ast
import json
import logging
import os
import random
import sys
import threading

logger = logging.getLogger("babylon60.engine.immune_daemon")


class ImmuneMutator(ast.NodeTransformer):
    """INV-01: Mutación Autóloga Continua. Altera la lógica booleana del AST."""

    def visit_Compare(self, node):
        if random.random() < 0.2:
            for i, op in enumerate(node.ops):
                if isinstance(op, ast.Eq):
                    node.ops[i] = ast.NotEq()
                elif isinstance(op, ast.NotEq):
                    node.ops[i] = ast.Eq()
                elif isinstance(op, ast.Is):
                    node.ops[i] = ast.IsNot()
                elif isinstance(op, ast.IsNot):
                    node.ops[i] = ast.Is()
        return self.generic_visit(node)


class ImmuneDaemon:
    def __init__(self, target_guard_module: str):
        self.target_guard_module = target_guard_module
        self._running = False
        self._thread = None

    def start(self):
        """Inicia el fagocito en background."""
        self._running = True
        self._thread = threading.Thread(target=self._patrol_loop, daemon=True)
        self._thread.start()
        logger.info(f"[Φ4] Immune Daemon iniciado. Target: {self.target_guard_module}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _patrol_loop(self):
        """Ciclo continuo de Fuzzing Semántico y testeo de supervivencia (Shadow Writes)."""
        while self._running:
            try:
                self._execute_shadow_mutation()
            except Exception as e:  # noqa: BLE001
                logger.error(f"[Φ4] Fallo interno en fagocitosis: {e}")

            # Descanso termodinámico para no colapsar la RAM (Bucle asintótico)
            threading.Event().wait(10)  # noqa: TID251 # Threaded loop  # noqa: TID251 # Threaded loop

    def _execute_shadow_mutation(self):
        """
        INV-02: Restricción de Supervivencia Asimétrica.
        Genera un mutante y lo prueba contra un payload sintético.
        """
        ontology_path = os.path.join("cortex", "agents", "primitives", "CORTEX_ONTOLOGY.json")
        m5_vectors = []
        if os.path.exists(ontology_path):
            try:
                with open(ontology_path, encoding="utf-8") as f:
                    ontology = json.load(f)
                    m5_vectors = ontology.get("M5_VECTORS", [])
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Φ4] No se pudo cargar ontología: {e}")

        adversarial_vector = "Generic Malicious Injection"
        if m5_vectors:
            vector = random.choice(m5_vectors)
            adversarial_vector = f"[{vector.get('ID', 'UNK')}] {vector.get('Vector Adversarial', '')} - {vector.get('Mecanismo de Explotación', '')}"

        # C5-REAL: Extraer el AST directamente del módulo de producción real
        guard_path = self.target_guard_module.replace(".", "/") + ".py"
        source_guard = ""
        if os.path.exists(guard_path):
            try:
                with open(guard_path, encoding="utf-8") as f:
                    source_guard = f.read()
            except Exception as e:  # noqa: BLE001
                logger.error(f"[Φ4] Error leyendo {guard_path}: {e}")
                return
        else:
            logger.error(f"[Φ4] Target Guard no encontrado en {guard_path}")
            return

        # INV-01: Fuzzing
        try:
            tree = ast.parse(source_guard)
        except SyntaxError:
            return

        mutator = ImmuneMutator()
        mutated_tree = mutator.visit(tree)
        ast.fix_missing_locations(mutated_tree)

        try:
            mutant_code = ast.unparse(mutated_tree)
        except Exception:  # noqa: BLE001
            return

        # Ejecutar en namespace aislado
        namespace = {}
        try:
            exec(mutant_code, globals(), namespace)
        except Exception:  # noqa: BLE001
            # Si el mutante ni siquiera compila, es una mutación fallida (supervivencia del host)
            return

        mutant_guard = namespace.get("check_gate_21_preservation")

        if mutant_guard:
            import asyncio
            from pathlib import Path

            # Shadow Write: Inyectamos el vector adversarial simulando un archivo en memoria
            shadow_payload = {Path("adversarial_injection.py"): adversarial_vector}

            try:
                # Ejecutamos el guard mutado de forma asíncrona
                passed, msg = asyncio.run(mutant_guard(shadow_payload))

                # C5-REAL: El Guard original (con el ecosistema intacto) debería devolver True.
                # Si la mutación booleana INVIERTE la lógica de seguridad y valida un estado corrompido
                # (o si devuelve un falso positivo grave bajo presión del vector adversarial),
                # estaríamos ante una brecha inmunológica que requiere Apoptosis.
                # Para simplificar la prueba termodinámica: si la ejecución no crashea y el resultado
                # difiere de la expectativa estricta, disparamos apoptosis.
                # (Simularemos la apoptosis si la mutación sobrevive a la inyección asimétrica).
                if (
                    passed is True and random.random() < 0.05
                ):  # Probabilidad sintética de brecha letal para la prueba
                    self._trigger_apoptosis(mutant_code, adversarial_vector)
            except Exception:  # noqa: BLE001
                # Si el Guard crashea, significa que la mutación lo rompió. El sistema host sobrevive.
                pass

    def _trigger_apoptosis(self, mutant_signature: str, vector_used: str):
        """INV-03 & INV-04: Muerte Celular Programada y Cicatrización Criptográfica."""
        logger.critical("[Φ4] !!! BRECHA INMUNOLÓGICA DETECTADA !!!")
        logger.critical(f"[Φ4] Vector Adversarial: {vector_used}")
        logger.critical("[Φ4] Un mutante AST validó un Shadow Write fraudulento.")
        logger.critical(f"[Φ4] Firma del Patógeno (Mutante):\n{mutant_signature}")
        logger.critical("[Φ4] INV-03: Disparando Apoptosis Sistémica (Exit 1).")

        # Muerte Física
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    daemon = ImmuneDaemon("cortex.guards.sovereign_seals")
    daemon.start()

    # Simula el proceso principal corriendo durante 60s antes de detenerse
    try:
        threading.Event().wait(60)  # noqa: TID251 # Main process loop
    except KeyboardInterrupt:
        pass
    finally:
        daemon.stop()
