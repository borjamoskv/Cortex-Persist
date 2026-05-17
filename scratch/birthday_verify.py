import random


def calculate_exact_probability(n, days=365):
    """Calcula la probabilidad exacta usando la fórmula 1 - (365! / (365-n)! * 365^n)."""
    prob_no_match = 1.0
    for i in range(n):
        prob_no_match *= (days - i) / days
    return 1 - prob_no_match


def run_monte_carlo_simulation(n, trials=100000, days=365):
    """Simula n personas en una habitación miles de veces para verificar el resultado."""
    matches = 0
    for _ in range(trials):
        birthdays = [random.randint(1, days) for _ in range(n)]
        if len(birthdays) != len(set(birthdays)):
            matches += 1
    return matches / trials


if __name__ == "__main__":
    n = 23
    exact = calculate_exact_probability(n)
    simulated = run_monte_carlo_simulation(n)

    print("--- VERIFICACIÓN C5-REAL ---")
    print(f"Personas: {n}")
    print(f"Probabilidad Matemática Exacta: {exact:.6%}")
    print(f"Probabilidad Simulada (100k intentos): {simulated:.6%}")
    print(f"Invariante: Exact > 50% -> {'VERIFICADO' if exact > 0.5 else 'FALLO'}")
