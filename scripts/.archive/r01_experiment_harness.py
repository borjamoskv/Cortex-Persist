import json
import logging
import random
import sys
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
    from scipy import stats
except ImportError:
    logging.warning(
        "scipy/numpy no localizados. El modo de evaluación estadística fallará si se invoca."
    )

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [R-01 C5-REAL] - %(message)s")

# --- CONTRATO DE FALSACIÓN PREDEFINIDO (ANTI p-hacking) ---
# Aprobado por operador BorjaMoskv - C5-REAL
R01_SUCCESS_CRITERIA = {
    "min_sample_size": 500,  # Aumentado para evidencia fuerte
    "target_p_value": 0.05,
    "target_cohens_d": 0.5,
    "min_improvement_pct": 10.0,
    "required_cohorts": 2,  # Exigencia de replicación independiente
    "presence_formula": "VERSION_1",
    "formula_frozen": True,  # CRÍTICO: El cálculo de Presence Score no puede mutar durante la campaña
}

DB_PATH = Path("r01_telemetry.jsonl")


class R01ExperimentHarness:
    GROUPS = ["CONTROL", "TDA", "SALIENCY"]

    def __init__(self):
        self.telemetry_path = DB_PATH

    def assign_group(self, user_id: str) -> str:
        random.seed(user_id)
        assigned = random.choice(self.GROUPS)
        logging.info(f"Usuario {user_id} asignado a brazo: {assigned}")
        return assigned

    def log_observation(
        self,
        user_id: str,
        group: str,
        presence_score: float,
        attention_time: float,
        interaction_rate: float,
        session_duration: float,
    ):
        if group not in self.GROUPS:
            raise ValueError(f"Grupo inválido: {group}")

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "group": group,
            "metrics": {
                "presence_score": presence_score,
                "attention_time": attention_time,
                "interaction_rate": interaction_rate,
                "session_duration": session_duration,
            },
            "formula_version": R01_SUCCESS_CRITERIA["presence_formula"],
        }

        with open(self.telemetry_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        logging.debug(f"Observación inyectada para {user_id} ({group}).")

    def _load_data(self) -> dict[str, list[float]]:
        if not self.telemetry_path.exists():
            return {"CONTROL": [], "TDA": [], "SALIENCY": []}

        data = {"CONTROL": [], "TDA": [], "SALIENCY": []}
        with open(self.telemetry_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    data[rec["group"]].append(rec["metrics"]["presence_score"])
        return data

    @staticmethod
    def _calculate_cohens_d(group1: list[float], group2: list[float]) -> float:
        n1, n2 = len(group1), len(group2)
        if n1 == 0 or n2 == 0:
            return 0.0

        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        if pooled_std == 0:
            return 0.0

        return (np.mean(group2) - np.mean(group1)) / pooled_std

    def _evaluate_pair(
        self, name: str, g1: list[float], g2: list[float]
    ) -> tuple[float, float, float]:
        if not g1 or not g2:
            return 1.0, 0.0, 0.0
        _, p_value = stats.ttest_ind(g1, g2, equal_var=False)
        cohens_d = self._calculate_cohens_d(g1, g2)
        mean_1, mean_2 = np.mean(g1), np.mean(g2)
        pct_improvement = ((mean_2 - mean_1) / mean_1) * 100 if mean_1 > 0 else 0

        sys.stdout.write(f"[{name}]\n")
        sys.stdout.write(f"  P-Value (Welch): {p_value:.4f}\n")
        sys.stdout.write(f"  Cohen's d:       {cohens_d:.4f}\n")
        sys.stdout.write(f"  Mejora Relativa: {pct_improvement:.2f}%\n")

        return p_value, cohens_d, pct_improvement

    def evaluate_h0(self):
        logging.info("Iniciando Falsación Estadística R-01 (Presence Score)")
        data = self._load_data()

        n_total = sum(len(v) for v in data.values())
        sys.stdout.write("\n" + "=" * 50 + "\n")
        sys.stdout.write("RESULTADOS DE FALSACIÓN R-01\n")
        sys.stdout.write("=" * 50 + "\n")
        sys.stdout.write(f"Muestra Total:     {n_total}\n")
        sys.stdout.write(
            f"Preservation Rule: PresenceScore Formula {R01_SUCCESS_CRITERIA['presence_formula']} [FROZEN]\n"
        )

        if n_total < R01_SUCCESS_CRITERIA["min_sample_size"]:
            sys.stdout.write(
                f"[WARNING] Muestra insuficiente ({n_total}/{R01_SUCCESS_CRITERIA['min_sample_size']}). Falsación abortada.\n"
            )
            sys.stdout.write("=" * 50 + "\n\n")
            return

        control = data["CONTROL"]
        tda = data["TDA"]
        saliency = data["SALIENCY"]

        sys.stdout.write("\n--- DESGLOSE DE COMPONENTES ---\n")
        p1, d1, i1 = self._evaluate_pair("A vs B (CONTROL vs TDA)", control, tda)
        p2, d2, i2 = self._evaluate_pair("A vs C (CONTROL vs SALIENCY)", control, saliency)
        p3, d3, i3 = self._evaluate_pair("B vs C (TDA vs SALIENCY)", tda, saliency)

        sys.stdout.write("\n" + "-" * 50 + "\n")
        # El criterio principal es A vs C para decidir si la arquitectura completa aporta valor
        if (
            p2 < R01_SUCCESS_CRITERIA["target_p_value"]
            and d2 > R01_SUCCESS_CRITERIA["target_cohens_d"]
            and i2 >= R01_SUCCESS_CRITERIA["min_improvement_pct"]
        ):
            sys.stdout.write(
                "VEREDICTO: [H0 RECHAZADA] Efecto estructural detectado en brazo Saliency.\n"
            )
            sys.stdout.write(
                "NOTA: Se requiere replicación independiente (Cohortes = 2) para asentar evidencia.\n"
            )
        else:
            sys.stdout.write(
                "VEREDICTO: [H0 MANTENIDA] Efecto insuficiente o estadísticamente insignificante.\n"
            )
            sys.stdout.write("ACCIÓN: Refactorizar o abandonar. NO escalar infraestructura.\n")
        sys.stdout.write("=" * 50 + "\n\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="R-01 Experiment Falsification Harness")
    parser.add_argument("--simulate", action="store_true", help="Simula una cohorte y evalúa")
    args = parser.parse_args()

    harness = R01ExperimentHarness()

    if args.simulate:
        if harness.telemetry_path.exists():
            harness.telemetry_path.unlink()

        logging.info("Simulando inyección de cohorte (N=600)...")
        for i in range(600):
            user_id = f"user_{i}"
            group = harness.assign_group(user_id)

            base_score = random.gauss(5.0, 1.0)
            if group == "SALIENCY":
                score = base_score + random.gauss(1.2, 0.5)
            elif group == "TDA":
                score = base_score + random.gauss(0.4, 0.5)
            else:
                score = base_score

            harness.log_observation(
                user_id,
                group,
                score,
                random.uniform(10, 300),
                random.uniform(0, 1),
                random.uniform(60, 1200),
            )

        harness.evaluate_h0()
