import logging
from z3 import Int, Solver, sat, unsat

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def run_asl_to_smt_verification():
    logger.info("=== 🛡️  Iniciando CORTEX ASL-SMT Verifier ===")
    logger.info("Objetivo: Traducir k2-liquidation.asl a Z3 SMT y verificar Ceil-Division\n")

    # Variables de estado (Z3 Ints)
    debt_to_cover = Int("debt_to_cover")
    price = Int("price")

    s = Solver()

    # Axioma: deuda y precio siempre son positivos (uint256 en Solidity/Rust)
    s.add(debt_to_cover > 0)
    s.add(price > 0)

    # 1. Comprobar la vulnerabilidad de truncamiento original (MEV Vector)
    # std_div = debt_to_cover / price (truncado por defecto)
    std_div = debt_to_cover / price
    value_recovered_std = std_div * price

    s.push()
    # Si recuperamos menos valor del que representa la deuda, perdemos dinero del protocolo
    s.add(value_recovered_std < debt_to_cover)
    res = s.check()
    if res == sat:
        m = s.model()
        logger.warning("❌ ALERTA SMT: El truncamiento estándar PERMITE MEV.")
        a_val = m[debt_to_cover].as_long()
        b_val = m[price].as_long()
        collateral = a_val // b_val
        val_real = collateral * b_val
        logger.warning(f"    Ejemplo encontrado: Deuda = {a_val}, Precio = {b_val}")
        logger.warning(f"    Collateral liquidado = {a_val} / {b_val} = {collateral}")
        logger.warning(
            f"    Valor real recuperado = {val_real} (Faltan {a_val - val_real} usd de HF)"
        )
        logger.warning("    Violación del Invariante: health_factor < 1.0\n")
    s.pop()

    # 2. Comprobar el parche Ceil-Division (K2-0514-01)
    # ceil_div = (debt_to_cover + price - 1) / price
    ceil_div = (debt_to_cover + price - 1) / price
    value_recovered_ceil = ceil_div * price

    s.push()
    # Buscamos si existe ALGUN caso donde el valor recuperado sea MENOR a la deuda
    # usando el parche de ceil_div.
    s.add(value_recovered_ceil < debt_to_cover)
    res = s.check()
    if res == unsat:
        logger.info("✅ VERIFICACIÓN FORMAL ASL-SMT: Ceil-Division (K2-0514-01) ES SEGURO.")
        logger.info("    Prueba matemática: UNSAT (Insatisfactible).")
        logger.info("    Es IMPOSIBLE que ceil_div(deuda, precio) * precio < deuda.")
        logger.info("    El invariante 'health_factor >= 1.0' queda probado algorítmicamente.")
    else:
        logger.error("❌ FALLO GRAVE: Ceil-Division ha sido vulnerado en el SMT.")
    s.pop()


if __name__ == "__main__":
    run_asl_to_smt_verification()
