import logging
logger = logging.getLogger(__name__)
# [C5-REAL] Exergy-Maximized
import json

import numpy as np


def calculate_true_ate_numpy(dataset_path):
    with open(dataset_path) as f:
        data = json.load(f)

    if len(data) == 0:
        return {"error": "Empty dataset"}

    Y = np.array([d["failures"] for d in data], dtype=float)
    T = [d["pattern_present"] for d in data]
    loc = [d["loc"] for d in data]
    authors = [d["authors"] for d in data]

    # X = [Treatment, LOC, Authors, Intercept]
    X = np.column_stack((T, loc, authors, np.ones(len(data))))

    try:
        # beta = (X^T X)^-1 X^T Y
        beta = np.linalg.inv(X.T @ X) @ X.T @ Y

        # Calculate standard errors and t-statistics (simplified p-value approximation)
        n, k = X.shape
        dof = n - k
        residuals = Y - (X @ beta)
        rss = np.sum(residuals**2)
        variance = rss / dof

        var_beta = variance * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diagonal(var_beta))

        t_stat = beta / se

        # We approximate p-value significance (t > 1.96 for roughly p < 0.05)
        # Treatment is beta[0], t_stat[0]
        ate = beta[0]
        t_value = t_stat[0]
        is_significant = abs(t_value) > 1.96

        return {
            "ate": round(float(ate), 4),
            "t_stat": round(float(t_value), 4),
            "is_significant": bool(is_significant),
            "advisory": "REFACTOR_URGENT" if (is_significant and ate > 0) else "NO_CAUSAL_LINK",
        }
    except np.linalg.LinAlgError:
        return {"error": "Singular matrix (Perfect collinearity)"}


if __name__ == "__main__":
    import sys

    dataset = sys.argv[1] if len(sys.argv) > 1 else ".cortex_ast_dataset.json"
    result = calculate_true_ate_numpy(dataset)
    logger.info("Advisory Result:\n%s", json.dumps(result, indent=2))
