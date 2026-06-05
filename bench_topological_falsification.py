import logging
logger = logging.getLogger("bench")
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'cortex-core'))
from cortex_topology_anomaly_detector import WindowedManifoldDetector

def run_advanced_suite():
    logger.info("==================================================")
    logger.info("  STATISTICAL MANIFOLD DETECTOR: ADVANCED SUITE   ")
    logger.info("==================================================")
    
    # ----------------------------------------------------
    # TEST 1: SLOW DRIFT WITH VELOCITY EMBEDDING
    # ----------------------------------------------------
    logger.info("\n[TEST 1] SLOW DRIFT RESOLUTION ([X_t, V_t] Embedding)")
    
    detector_drift = WindowedManifoldDetector(window_size=100, anomaly_threshold=3.0, use_velocity=True)
    drift_anomalies = 0
    
    # Warmup
    for _ in range(100):
        v = np.array([5.0, 0.01, 0.2, 0.1]) + np.random.normal(scale=[0.5, 0.001, 0.02, 0.02])
        detector_drift.step(v)
        
    # Gradual drift over 500 steps
    for i in range(500):
        cpu = 0.1 + (0.8 * (i / 500.0))
        entropy = 0.2 + (0.6 * (i / 500.0))
        v = np.array([5.0, 0.01, entropy, cpu]) + np.random.normal(scale=[0.5, 0.001, 0.02, 0.02])
        res = detector_drift.step(v)
        if res["is_anomaly"]:
            drift_anomalies += 1
            
    logger.info(f"False Positives during slow drift: {drift_anomalies} / 500")
    logger.info(f"Velocity Embedding assimilation: {'SUCCESS' if drift_anomalies < 10 else 'FAILED'}")

    # ----------------------------------------------------
    # TEST 2: ROC-AUC / PR-AUC SWEEP
    # ----------------------------------------------------
    logger.info("\n[TEST 2] ROC/PR CURVE GENERATION (Threshold Sweep)")
    
    # Generate static dataset for offline sweep
    samples = []
    labels = []
    for _ in range(2000):
        if np.random.rand() < 0.02: # 2% Anomaly
            v = np.array([10.0, 0.05, 1.0, 0.9]) + np.random.normal(scale=[1.0, 0.01, 0.1, 0.1])
            labels.append(1)
        else: # Normal
            v = np.array([5.0, 0.01, 0.2, 0.1]) + np.random.normal(scale=[0.5, 0.001, 0.02, 0.02])
            labels.append(0)
            
    # Calculate distances online
    detector_sweep = WindowedManifoldDetector(window_size=100, use_velocity=True)
    distances = []
    for v in samples:
        res = detector_sweep.step(v)
        distances.append(res["mahalanobis_distance"])
        
    distances = np.array(distances[100:]) # Drop warmup
    y_true = np.array(labels[100:])

    # Manual Threshold Sweep Output
    logger.info("\n[THRESHOLD SWEEP (Recall vs FPR)]")
    for t in [2.0, 3.0, 4.0, 5.0, 6.0, 8.0]:
        preds = distances > t
        tp = np.sum((preds == 1) & (y_true == 1))
        fp = np.sum((preds == 1) & (y_true == 0))
        fn = np.sum((preds == 0) & (y_true == 1))
        tn = np.sum((preds == 0) & (y_true == 0))
        
        recall = tp / max(1, tp + fn)
        fpr = fp / max(1, fp + tn)
        logger.info(f"T={t:.1f} | Recall: {recall:.4f} | FPR: {fpr:.4f}")

    # ----------------------------------------------------
    # TEST 3: DIMENSIONALITY STRESS
    # ----------------------------------------------------
    logger.info("\n[TEST 3] DIMENSIONALITY STRESS (d=64)")
    d = 64
    detector_dim = WindowedManifoldDetector(window_size=200, anomaly_threshold=5.0, use_velocity=False)
    # Warmup
    for _ in range(200):
        v = np.random.normal(size=d)
        detector_dim.step(v)
        
    # Shock
    v_shock = np.random.normal(size=d)
    v_shock[0] = 5.0 # Spike in one dimension
    res_shock = detector_dim.step(v_shock)
    
    logger.info(f"Matrix inversion stable at d={d}: {not np.isnan(res_shock['mahalanobis_distance'])}")
    logger.info(f"Shock detected in R^{d}: {res_shock['is_anomaly']} (Dist: {res_shock['mahalanobis_distance']:.2f})")

if __name__ == "__main__":
    run_advanced_suite()
