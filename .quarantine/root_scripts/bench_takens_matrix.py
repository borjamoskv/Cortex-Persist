# [C5-REAL] Exergy-Maximized
import numpy as np
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "cortex-core"))
from cortex_topology_anomaly_detector import WindowedManifoldDetector

# Ensure scikit-learn is installed for metrics
try:
    from sklearn.metrics import roc_auc_score, precision_score, recall_score, confusion_matrix
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn"])
    from sklearn.metrics import roc_auc_score, precision_score, recall_score, confusion_matrix


def generate_shock():
    # 1000 normal, 20 random shocks
    y = np.zeros(1000)
    data = []
    for i in range(1000):
        if i > 100 and np.random.rand() < 0.02:
            data.append(np.random.normal(loc=[10.0, 0.05, 1.0, 0.9], scale=[1.0, 0.01, 0.1, 0.1]))
            y[i] = 1
        else:
            data.append(np.random.normal(loc=[5.0, 0.01, 0.2, 0.1], scale=[0.5, 0.001, 0.02, 0.02]))
    return data, y


def generate_drift():
    # 1000 total, last 300 have slow drift
    y = np.zeros(1000)
    data = []
    for i in range(1000):
        if i >= 700:
            drift = (i - 700) / 300.0
            data.append(
                np.random.normal(
                    loc=[5.0, 0.01, 0.2 + 0.6 * drift, 0.1 + 0.8 * drift],
                    scale=[0.5, 0.001, 0.02, 0.02],
                )
            )
            # In anomaly detection, drift outside 3-sigma is technically an anomaly
            # Let's label the last 150 as true anomalies
            if i >= 850:
                y[i] = 1
        else:
            data.append(np.random.normal(loc=[5.0, 0.01, 0.2, 0.1], scale=[0.5, 0.001, 0.02, 0.02]))
    return data, y


def generate_regime():
    # 1000 total, at 500 switch to new regime
    y = np.zeros(1000)
    data = []
    for i in range(1000):
        if i >= 500:
            data.append(np.random.normal(loc=[8.0, 0.02, 0.8, 0.9], scale=[0.5, 0.001, 0.02, 0.02]))
            # The transition itself is an anomaly, but the stable new regime is NOT.
            # We label the first 20 steps of the new regime as anomaly, then 0.
            if i < 520:
                y[i] = 1
        else:
            data.append(np.random.normal(loc=[5.0, 0.01, 0.2, 0.1], scale=[0.5, 0.001, 0.02, 0.02]))
    return data, y


def generate_periodicity():
    # 1000 total, stable orbit, phase shift at 700
    y = np.zeros(1000)
    data = []
    for i in range(1000):
        if i >= 700 and i < 720:
            # Phase break!
            v = np.array([5.0 + np.sin(i * 0.5 + 3.14), 0.01, 0.2, 0.1])
            data.append(v)
            y[i] = 1
        else:
            v = np.array([5.0 + np.sin(i * 0.5), 0.01, 0.2, 0.1])
            data.append(v)
    return data, y


def evaluate_detector(detector_cls, kwargs, data, y_true):
    detector = detector_cls(**kwargs)

    start = time.perf_counter()
    distances = []
    preds = []

    for v in data:
        res = detector.step(v)
        distances.append(res["mahalanobis_distance"])
        preds.append(1 if res["is_anomaly"] else 0)

    end = time.perf_counter()

    # Drop first 100 (warmup)
    y_eval = y_true[100:]
    p_eval = np.array(preds[100:])
    d_eval = np.array(distances[100:])

    auc = roc_auc_score(y_eval, d_eval) if len(np.unique(y_eval)) > 1 else 0.0
    prec = precision_score(y_eval, p_eval, zero_division=0)
    rec = recall_score(y_eval, p_eval, zero_division=0)

    tn, fp, fn, tp = (
        confusion_matrix(y_eval, p_eval).ravel()
        if len(np.unique(y_eval)) > 1
        else (len(y_eval), 0, 0, 0)
    )
    fpr = fp / max(1, (fp + tn))

    throughput = len(data) / (end - start)

    return {"AUC": auc, "Precision": prec, "Recall": rec, "FPR": fpr, "Throughput": throughput}


def main():
    print("==================================================")
    print("  CORTEX BENCHMARK: TAKENS VS ORIGINAL MANIFOLD   ")
    print("==================================================")

    scenarios = {
        "Shock Instantáneo": generate_shock(),
        "Deriva Lenta": generate_drift(),
        "Cambio de Régimen": generate_regime(),
        "Ruptura de Periodicidad": generate_periodicity(),
    }

    configs = {
        "Original (d=1)": {
            "window_size": 100,
            "anomaly_threshold": 3.0,
            "takens_dim": 1,
            "takens_tau": 1,
        },
        "Takens (d=3, t=2)": {
            "window_size": 100,
            "anomaly_threshold": 3.0,
            "takens_dim": 3,
            "takens_tau": 2,
        },
    }

    results = {s: {} for s in scenarios}

    for s_name, (data, y_true) in scenarios.items():
        for c_name, kwargs in configs.items():
            metrics = evaluate_detector(WindowedManifoldDetector, kwargs, data, y_true)
            results[s_name][c_name] = metrics

    # Print Markdown Table
    print("\n| Scenario | Detector | ROC-AUC | Precision | Recall | FPR | Throughput (ops/s) |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for s_name in scenarios:
        for c_name in configs:
            m = results[s_name][c_name]
            print(
                f"| {s_name} | {c_name} | {m['AUC']:.4f} | {m['Precision']:.4f} | {m['Recall']:.4f} | {m['FPR']:.4f} | {m['Throughput']:,.0f} |"
            )


if __name__ == "__main__":
    main()
