import numpy as np
from collections import deque

class WindowedManifoldDetector:
    """
    CORTEX STATISTICAL MANIFOLD DETECTOR (C5-REAL)
    
    Uses Takens' Delay Embedding to map a multivariate time series into a 
    higher-dimensional geometric manifold, evaluating Mahalanobis distance 
    over the trajectory S_t = [x_t, x_{t-tau}, x_{t-2tau}] instead of just x_t.
    """
    
    def __init__(self, window_size=100, anomaly_threshold=3.0, takens_dim=3, takens_tau=1):
        self.window_size = window_size
        self.threshold = anomaly_threshold
        self.dim = takens_dim
        self.tau = takens_tau
        
        # We need a buffer to store the last (dim-1)*tau + 1 raw states
        self.raw_buffer = deque(maxlen=(self.dim - 1) * self.tau + 1)
        self.history = deque(maxlen=window_size)
        self.n = 0
        
    def step(self, x: np.ndarray) -> dict:
        self.n += 1
        self.raw_buffer.append(x)
        
        # Wait until we have enough history to form a Takens embedding vector
        if len(self.raw_buffer) < self.raw_buffer.maxlen:
            return {"mahalanobis_distance": 0.0, "is_anomaly": False, "adapting": True}
            
        # Construct Takens' Embedding Vector: [x_t, x_{t-tau}, ..., x_{t-(dim-1)tau}]
        # Deque index 0 is oldest. 
        # Current x_t is at index -1.
        # x_{t-tau} is at index -1 - tau.
        embedded_states = []
        for i in range(self.dim):
            idx = -(1 + i * self.tau)
            embedded_states.append(self.raw_buffer[idx])
            
        # S_t in R^(d * takens_dim)
        s_t = np.concatenate(embedded_states)
        
        if len(self.history) < 10:
            self.history.append(s_t)
            return {"mahalanobis_distance": 0.0, "is_anomaly": False, "adapting": True}
            
        data = np.vstack(self.history)
        mu = np.mean(data, axis=0)
        cov = np.cov(data, rowvar=False)
        
        # Regularization for stability in higher dimensions
        cov_dim = s_t.shape[0]
        inv_cov = np.linalg.pinv(cov + np.eye(cov_dim)*1e-6)
        
        diff = s_t - mu
        m_dist = np.sqrt(diff.T @ inv_cov @ diff)
        
        is_anomaly = m_dist > self.threshold
        
        # Ingest state to allow adaptation
        self.history.append(s_t)
        
        return {
            "mahalanobis_distance": round(float(m_dist), 4),
            "is_anomaly": bool(is_anomaly),
            "adapting": False
        }

if __name__ == "__main__":
    # Smoke Test: Takens Embedding Integration
    print("==================================================")
    print("  CORTEX TAKENS MANIFOLD DETECTOR (C5-REAL)       ")
    print("==================================================")
    
    # 4 variables: queue, error, causal, cpu
    detector = WindowedManifoldDetector(window_size=50, takens_dim=3, takens_tau=2)
    
    # Simulate an orbital cycle (e.g. a sinusoidal pattern)
    print("\n[PHASE 1] ORBITAL EQUILIBRIUM (Sinusoidal dynamics)")
    for i in range(100):
        # A stable periodic signal
        v = np.array([
            5.0 + np.sin(i * 0.5), 
            0.01 + 0.005 * np.cos(i * 0.5), 
            0.5, 
            0.1
        ])
        res = detector.step(v)
        
    print(f"Distance inside stable orbit: {res['mahalanobis_distance']:.4f}")
    
    print("\n[PHASE 2] ORBITAL DEFORMATION (Periodicity Break)")
    # We break the sine wave pattern, even if the absolute values are normal
    v_break = np.array([5.0 + np.sin(100 * 0.5 + 3.14), 0.01, 0.5, 0.1])
    res_break = detector.step(v_break)
    print(f"Vector: {v_break}")
    print(f"Distance (Orbital Anomaly): {res_break['mahalanobis_distance']:.4f}")
    print(f"Is Anomaly: {res_break['is_anomaly']} -> DETECTED PHASE SHIFT")
