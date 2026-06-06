from typing import NamedTuple


class RawFeatures(NamedTuple):
    creator_autonomy: float
    algorithmic_pressure: float
    audience_capture: float
    creative_entropy: float
    monetization_coupling: float

class AuthenticityDynamicsEngine:
    def system_dynamics(self, vectors: RawFeatures) -> float:
        # Simple dynamics equation simulating authenticity erosion vs organic growth
        organic_pull = (vectors.creator_autonomy * 1.5) + vectors.creative_entropy
        industrial_pull = (vectors.algorithmic_pressure * 2.0) + vectors.audience_capture + (vectors.monetization_coupling * 1.5)
        
        # Output a continuous score where >0 is organic, <0 is industrial subjugation
        score = organic_pull - industrial_pull
        return score

class InterpretationLayer:
    def assign_label(self, score: float, vectors: RawFeatures) -> dict:
        anomalies = False
        
        # Edge case anomalies detection (e.g. extremely high autonomy but highly subjugated)
        if vectors.creator_autonomy > 0.9 and vectors.algorithmic_pressure > 0.9:
            anomalies = True
            
        if score > 0.5:
            label = "Low-Optimization System (Emergent Organic Signal)"
        elif score < -0.5:
            label = "Engagement-Industrial System (Algorithmic Subjugation)"
        else:
            label = "Hybrid Drift System (Critical Convergence Zone)"
            
        return {
            "assigned_label": label,
            "detected_anomalies": anomalies
        }
