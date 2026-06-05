import hashlib
import numpy as np
from dataclasses import dataclass
from typing import List, Callable, Any
from sklearn.cluster import KMeans

@dataclass
class SystemState:
    git_diff: str
    ast_hash: str
    active_tasks: List[str]
    error_log: List[str]

def fast_pseudo_embed(text: str, dim: int = 64) -> np.ndarray:
    """A deterministic pseudo-embedding to simulate an LLM embedder for bootstrapping."""
    h = hashlib.sha256(text.encode('utf-8')).digest()
    vec = np.array([float(x) for x in h[:dim]])
    # Normalize
    norm = np.linalg.norm(vec)
    return vec / (norm + 1e-8) if norm > 0 else vec

def encode_state(state: SystemState, embed_fn: Callable = fast_pseudo_embed) -> np.ndarray:
    payload = " | ".join([
        state.git_diff,
        state.ast_hash,
        " ".join(state.active_tasks),
        " ".join(state.error_log)
    ])
    return embed_fn(payload)

def encode_task(task_stats: Any, embed_fn: Callable = fast_pseudo_embed) -> np.ndarray:
    payload = f"""
    task:{task_stats.name}
    exergy_mean:{task_stats.exergy_mean}
    exergy_var:{task_stats.exergy_var}
    runtime:{task_stats.runtime_mean}
    """
    return embed_fn(payload)

def build_failure_centroids(ledger_embeddings: List[np.ndarray], k: int = 8) -> List[np.ndarray]:
    """Clusterización offline de estados de fallo para crear zonas de peligro."""
    if not ledger_embeddings:
        return []
    X = np.array(ledger_embeddings)
    n_clusters = min(k, len(X))
    if n_clusters == 0:
        return []
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    kmeans.fit(X)
    return kmeans.cluster_centers_

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)

def embedding_risk(state_vec: np.ndarray, task_vec: np.ndarray, failure_centroids: List[np.ndarray]) -> float:
    if not len(failure_centroids):
        return 0.0  # No known failures
        
    task_state = task_vec + state_vec * 0.5
    
    min_dist = min(
        1 - cosine(task_state, c)
        for c in failure_centroids
    )
    # The smaller the distance, the higher the risk (risk = 1 - min_dist basically, but let's map min_dist as distance.
    # Wait, the prompt says return min_dist. If min_dist is small, it means we are CLOSE to a failure centroid. 
    # The risk should probably be inversely proportional, but let's use the provided logic:
    # "Risk as distance to failure manifold -> min_dist = min(1 - cosine(...))". 
    # If 1-cosine is small (cosine ~ 1), min_dist is small. 
    # Risk should be higher if distance is small. We will return (1.0 - min_dist) as the actual risk penalty in priority().
    # Actually, the user's formula is: `semantic_risk = embedding_risk(...)`. And score uses `- (1.0 - semantic_risk)`. 
    # So if min_dist is 0 (very risky), semantic_risk = 0. `- (1.0 - 0) = -1.0` penalty. That works perfectly.
    return float(min_dist)

def efel_priority(task_stats: Any, state: SystemState, meta: Any, centroids: List[np.ndarray], embed_fn: Callable = fast_pseudo_embed) -> float:
    s = encode_state(state, embed_fn)
    t = encode_task(task_stats, embed_fn)
    
    semantic_risk = embedding_risk(s, t, centroids)
    variance_penalty = meta.alpha_risk * task_stats.exergy_var
    
    # meta.semantic_risk_weight
    semantic_weight = getattr(meta, 'semantic_risk_weight', 0.2)
    
    score = (
        task_stats.exergy_mean 
        - variance_penalty 
        - (1.0 - semantic_risk) * semantic_weight
    ) / (task_stats.runtime_mean + 1e-6)
    
    return float(score * task_stats.confidence)
