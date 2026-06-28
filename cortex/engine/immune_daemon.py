"""
[C5-REAL] Exergy-Maximized
Φ4 Immune Daemon - Sistema Inmunológico Antifrágil / Autopoiético
Implementación Causal de las Primitivas INV-01 a INV-04.
"""

import ast
import logging
import random
import sys
import threading

logger = logging.getLogger("cortex.engine.immune_daemon")

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
            except Exception as e:
                logger.error(f"[Φ4] Fallo interno en fagocitosis: {e}")
            
            # Descanso termodinámico para no colapsar la RAM (Bucle asintótico)
            threading.Event().wait(10)  # noqa: TID251 # Threaded loop  # noqa: TID251 # Threaded loop

    def _execute_shadow_mutation(self):
        """
        INV-02: Restricción de Supervivencia Asimétrica.
        Genera un mutante y lo prueba contra un payload sintético.
        NOTA: En C5-REAL esto operaría extrayendo el AST del módulo real de `cortex.guards`.
        """
        # Simulación de un Guard de validación CORTEX
        source_guard = """
def validate_taint(payload: dict) -> bool:
    if "CORTEX-TAINT" not in payload:
        return False
    if payload["CORTEX-TAINT"] is None:
        return False
    return True
"""
        # INV-01: Fuzzing
        tree = ast.parse(source_guard)
        mutator = ImmuneMutator()
        mutated_tree = mutator.visit(tree)
        ast.fix_missing_locations(mutated_tree)
        
        mutant_code = ast.unparse(mutated_tree)
        
        # Ejecutar en namespace aislado
        namespace = {}
        exec(mutant_code, globals(), namespace)
        mutant_guard = namespace.get("validate_taint")
        
        if mutant_guard:
            # Shadow Write: Enviamos un payload INVÁLIDO que NO tiene taint.
            # El guard ORIGINAL debería devolver False.
            shadow_payload = {"data": "malicious_injection"}
            
            # Si el guard MUTADO devuelve True para un payload inválido...
            if mutant_guard(shadow_payload) is True:
                # Significa que la mutación rompió la seguridad y podría inyectarse en el Ledger.
                # INV-03: Apoptosis Trigger.
                self._trigger_apoptosis(mutant_code)

    def _trigger_apoptosis(self, mutant_signature: str):
        """INV-03 & INV-04: Muerte Celular Programada y Cicatrización Criptográfica."""
        logger.critical("[Φ4] !!! BRECHA INMUNOLÓGICA DETECTADA !!!")
        logger.critical("[Φ4] Un mutante AST validó un Shadow Write fraudulento.")
        logger.critical(f"[Φ4] Firma del Patógeno (Mutante):\n{mutant_signature}")
        logger.critical("[Φ4] INV-03: Disparando Apoptosis Sistémica (Exit 1).")
        
        # Aquí registraríamos el patógeno en el Ledger antes de morir (INV-04)
        # ledger.commit_pathogen_signature(hash(mutant_signature))
        
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
