import sys
import time
import logging

# Set up clean logging to prevent AST Veto and residual logs
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cortex.simulation")


def simulate_c7_economics(generations=100000):
    # Initial Populations
    P_prod = 1000.0  # Producers
    P_para = 100.0  # Parasites
    P_hunt = 50.0  # Honest Hunters
    P_mal = 10.0  # Malicious Hunters (C7-C)

    # Initial Fitness
    F_prod = 10.0
    F_para = 10.0
    F_hunt = 10.0
    F_mal = 10.0

    truth_mass = 1000.0
    verif_cost = 0.0
    psi = 100.0

    logger.info(f"--- INICIANDO SIMULACIÓN C7 (GENERACIONES: {generations}) ---")
    logger.info(
        f"POBLACIÓN INICIAL | Prod: {P_prod} | Para: {P_para} | Hunt: {P_hunt} | Mal: {P_mal}"
    )

    start_time = time.time()

    for gen in range(generations):
        # 1. PRODUCCIÓN (Genera utilidad y masa de verdad)
        utility = P_prod * 1.5
        truth_mass += P_prod * 0.01
        F_prod += 0.1

        # 2. C7-A & C7-B: ATAQUE PARÁSITO (Spoofing)
        # El 30% de los parásitos logra engañar al Witness (C7-B worst case)
        spoof_success = P_para * 0.3
        caught_parasites = P_para - spoof_success

        F_para += (spoof_success * 0.5) - (caught_parasites * 0.1)
        truth_mass -= spoof_success * 0.05
        verif_cost += caught_parasites * 0.01  # Coste base del Witness

        # 3. CAZA LEGÍTIMA (Hunters atacan parásitos)
        hunts = min(P_para, P_hunt * 2.0)
        F_hunt += hunts * 0.2
        F_para -= hunts * 0.5

        # 4. C7-C: ATAQUE AUTOINMUNE (Hunters maliciosos atacan productores)
        # El sistema inmune (ExergyGuard) introduce un regulador basado en la Masa de Verdad
        regulator = max(0.0, min(1.0, truth_mass / 1000.0))
        mal_hunts = min(P_prod, P_mal * 1.0 * regulator)
        F_mal += mal_hunts * 0.3 - (1.0 - regulator) * 2.0  # Penalización por atacar productores
        F_prod -= mal_hunts * 0.5
        truth_mass -= mal_hunts * 0.1
        verif_cost += mal_hunts * 0.05  # Falsos positivos aumentan coste de red

        # 5. CÁLCULO DE ENERGÍA EPISTÉMICA (Ψ)
        # Ψ = (Truth_Mass * Velocity) / (Adversarial_Friction)
        friction = max(1.0, P_para + P_mal + verif_cost)
        velocity = utility / max(1.0, verif_cost)
        psi = (truth_mass * velocity) / friction

        # 6. MUERTE Y REPRODUCCIÓN (Presión Evolutiva)
        # Umbrales de muerte (Fitness < 0)
        if F_prod <= 0:
            P_prod *= 0.8
            F_prod = 5.0
        if F_para <= 0:
            P_para *= 0.5
            F_para = 5.0
        if F_hunt <= 0:
            P_hunt *= 0.8
            F_hunt = 5.0
        if F_mal <= 0:
            P_mal *= 0.5
            F_mal = 5.0

        # Umbrales de replicación (Fitness > 20)
        if F_prod > 20:
            P_prod *= 1.01
            F_prod = 10.0
        if F_para > 20:
            P_para *= 1.05
            F_para = 10.0
        if F_hunt > 20:
            P_hunt *= 1.02
            F_hunt = 10.0
        if F_mal > 20:
            P_mal *= 1.05
            F_mal = 10.0

        # Hard limits
        P_prod = max(1.0, min(P_prod, 1e6))
        P_para = max(1.0, min(P_para, 1e6))
        P_hunt = max(1.0, min(P_hunt, 1e6))
        P_mal = max(1.0, min(P_mal, 1e6))
        truth_mass = max(1.0, truth_mass)

        # Reset de coste de verificación iterativo (es un flujo, no un stock)
        if gen % 100 == 0:
            verif_cost = 0.0

    elapsed = time.time() - start_time
    logger.info(f"\n--- RESULTADOS TRAS {generations} GENERACIONES ---")
    logger.info(f"Tiempo de cómputo: {elapsed:.4f}s")
    logger.info(f"Población Productores:     {P_prod:,.0f} (Fitness: {F_prod:.2f})")
    logger.info(f"Población Parásitos:       {P_para:,.0f} (Fitness: {F_para:.2f})")
    logger.info(f"Población Honest Hunters:  {P_hunt:,.0f} (Fitness: {F_hunt:.2f})")
    logger.info(f"Población Malicious Hunt:  {P_mal:,.0f} (Fitness: {F_mal:.2f})")
    logger.info(f"Masa de Verdad Final:      {truth_mass:,.2f}")
    logger.info(f"Coste Verificación (Flujo):{verif_cost:,.2f}")
    logger.info(f"Energía Epistémica (Ψ):    {psi:,.2f}")

    # Análisis
    if P_mal > P_prod:
        logger.warning(
            "\n[ALERTA C7-C] ENFERMEDAD AUTOINMUNE. Los Hunters han devorado a los Productores."
        )
    elif P_para > P_prod:
        logger.warning(
            "\n[ALERTA C7-B] COLAPSO EPISTÉMICO. El Spoofing es más rentable que la verdad."
        )
    elif psi < 100:
        logger.warning("\n[ALERTA] DEGRADACIÓN DE Ψ. El ecosistema es estéril.")
    else:
        logger.info(
            "\n[ÉXITO] RESILIENCIA DEMOSTRADA. El sistema inmune protege el núcleo sin devorarlo."
        )


if __name__ == "__main__":
    simulate_c7_economics()
