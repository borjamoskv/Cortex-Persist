import z3
import logging
from cortex.verification.verifier import SovereignVerifier

# Configuración de logging para visibilidad industrial
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("cortex.poc.z3")


def prove_arithmetic_safety(a_val, b_val):
    """
    Simula la Fase 3.5 de KETER: Verificación Formal de Correctitud Aritmética (I8).
    Probamos si la suma de dos enteros de 64 bits puede desbordar.
    """
    logger.info("--- Iniciando Prueba Z3 para I8 (Arithmetic Correctness) ---")
    logger.info(f"Inputs: a={a_val}, b={b_val}")

    # Definimos el modelo en Z3 (BitVectors de 64 bits)
    a = z3.BitVec("a", 64)
    b = z3.BitVec("b", 64)
    z3.BitVec("res", 64)

    s = z3.Solver()

    # Invariante I8: El resultado debe ser igual a la suma sin truncamiento inesperado
    # En SMT, buscamos un contraejemplo (SAT) que viole la propiedad.
    # Si s.check() es UNSAT, la propiedad es válida para todos los inputs posibles.

    # Restricción: Queremos ver si existe algun a, b tal que a + b desborde
    # Para BitVectors, el desbordamiento ocurre si la suma es menor que los sumandos (sin signo)
    overflow_condition = z3.And(z3.ULT(a + b, a), z3.ULT(a + b, b))

    s.add(a == a_val)
    s.add(b == b_val)
    s.add(overflow_condition)

    if s.check() == z3.sat:
        m = s.model()
        logger.error("❌ INVARIANTE I8 VIOLADO: Desbordamiento detectado!")
        logger.error(f"Contraejemplo: {m}")
        return False
    else:
        logger.info(
            "✅ INVARIANTE I8 VERIFICADO: No hay desbordamiento para estos inputs en BitVec(64)."
        )
        return True


def demo_formal_gate():
    # 1. Código propuesto por un agente (Inferencia Estocástica)
    proposed_mutation = """
def update_balance(balance, increment):
    # Esta operación es peligrosa si no se valida el overflow
    return balance + increment
    """

    # 2. El Verifier detecta la operación BinOp (+) y activa el modelo SMT
    verifier = SovereignVerifier()
    result = verifier.check(proposed_mutation, {"file_path": "wallet.py"})

    print("\n" + "=" * 60)
    print("CORTEX FORMAL VERIFICATION GATE — RESULT")
    print("=" * 60)
    print(f"Status: {'✅ VALID' if result.is_valid else '❌ INVALID'}")
    if not result.is_valid:
        for v in result.violations:
            print(f"Violation [{v['id']}]: {v['name']} -> {v['message']}")

    # 3. Prueba de estrés de desbordamiento real
    print("\n--- Ejecutando Prueba de Estrés Z3 ---")
    max_64 = (2**64) - 1
    prove_arithmetic_safety(max_64, 1)  # Esto debería fallar


if __name__ == "__main__":
    demo_formal_gate()
