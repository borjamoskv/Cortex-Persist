import z3


def audit_liquidation_math():
    # Inicializar Solver de Z3 con timeout estricto (Anti-Infinite-Loop Ouroboros)
    s = z3.Solver()
    s.set("timeout", 5000)

    # Reducimos el vector a 64 bits para que el SAT solver no se ahogue con división no lineal
    WAD = z3.BitVecVal(10**6, 64)  # Usamos un WAD escalado para la demo

    # liquidation_bonus = 105% (1.05 * 10^6)
    bonus_u64 = z3.BitVecVal(int(1.05 * 10**6), 64)

    initial_debt_to_cover = z3.BitVec("initial_debt_to_cover", 64)
    total_collateral_base = z3.BitVec("total_collateral_base", 64)

    s.add(initial_debt_to_cover > 0)
    s.add(initial_debt_to_cover < 10**12)
    s.add(total_collateral_base > 0)
    s.add(total_collateral_base < 10**12)

    # Paso 1: collateral_amount_base
    collateral_amount_base_1 = z3.UDiv(initial_debt_to_cover * bonus_u64, WAD)

    # Paso 2: if collateral_amount_base > user_account_data.total_collateral_base
    s.add(collateral_amount_base_1 > total_collateral_base)
    collateral_amount_base_final = total_collateral_base

    # Recálculo de la deuda (truncamiento hacia abajo por división)
    recalculated_debt_to_cover = z3.UDiv(collateral_amount_base_final * WAD, bonus_u64)

    # Forward check
    forward_check = z3.UDiv(recalculated_debt_to_cover * bonus_u64, WAD)

    # Condición de vulnerabilidad
    s.add(forward_check < total_collateral_base)

    print("[*] Z3 Solver v2: Analizando Precision Loss (64-bit Fast Lane)...")

    res = s.check()
    if res == z3.sat:
        m = s.model()
        print("\n[!] VULNERABILIDAD ENCONTRADA (Precision Loss / Rounding Extraction)")
        print("==================================================================")
        print(f"Total Collateral Base: {m[total_collateral_base].as_long()}")
        print(f"Initial Debt: {m[initial_debt_to_cover].as_long()}")
        print(f"Recalculated Debt Paid: {m.eval(recalculated_debt_to_cover).as_long()}")
        print(f"Collateral Equivalent of Paid Debt: {m.eval(forward_check).as_long()}")
        print(
            f"Value Extracted (Free Base Tokens): {m.eval(total_collateral_base - forward_check).as_long()}"
        )
        print("\n[+] Vector de Ataque C5-REAL Generado.")
    elif res == z3.unsat:
        print(
            "\n[✓] Z3 UNSAT: El contrato es matemáticamente seguro contra extracción por truncamiento en este vector."
        )
    else:
        print("\n[?] Z3 UNKNOWN: El solver alcanzó el timeout.")


if __name__ == "__main__":
    audit_liquidation_math()
