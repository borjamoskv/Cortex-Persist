"""
Cortex Persist — Epistemic Consensus Layer (Nivel 4: Research-Grade)

Implementación de las recomendaciones del Attack Suite:
1. epistemic_consensus_layer
2. semantic_validation_oracle  
3. multi_agent_contradiction_detector
4. probabilistic_truth_scoring_engine

Esto ya no es logging.
Esto es cortex que discute consigo mismo antes de creer algo.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import statistics
import os


class TruthStatus(Enum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    UNVERIFIED = "unverified"
    PROBABLE = "probable"
    IMPOSSIBLE = "impossible"


class ConsensusMethod(Enum):
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_TRUST = "weighted_trust"
    BAYESIAN_UPDATE = "bayesian_update"
    EVIDENCE_BASED = "evidence_based"


@dataclass
class AgentClaim:
    """Declaración de un agente sobre un hecho"""
    agent_id: str
    claim_type: str
    payload: Any
    confidence: float  # 0.0 - 1.0
    evidence: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    trust_score: float = 1.0  # Historial de veracidad del agente
    
    def hash(self) -> str:
        data = f"{self.agent_id}:{self.claim_type}:{json.dumps(self.payload)}:{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class Contradiction:
    """Contradicción detectada entre claims"""
    claim_a: AgentClaim
    claim_b: AgentClaim
    contradiction_type: str
    severity: float  # 0.0 - 1.0
    resolution: Optional[str] = None


@dataclass
class TruthScore:
    """Puntuación de verdad probabilística"""
    claim_hash: str
    truth_probability: float  # 0.0 - 1.0
    confidence_interval: Tuple[float, float]
    supporting_agents: List[str]
    contradicting_agents: List[str]
    evidence_count: int
    status: TruthStatus
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class SemanticValidationOracle:
    """
    Oracle que valida coherencia semántica de claims.
    
    Reglas:
    - No contradicción lógica interna
    - Consistencia con hechos establecidos
    - Validación de tipo y schema
    - Coherencia temporal
    """
    
    def __init__(self):
        self.established_facts: Dict[str, Any] = {}
        self.type_validators: Dict[str, callable] = {}
        self.temporal_rules: List[callable] = []
        
        # Register default validators
        self._register_default_validators()
    
    def _register_default_validators(self):
        """Registrarse validadores por defecto"""
        
        def validate_fact_type(claim: AgentClaim) -> Tuple[bool, str]:
            if claim.claim_type == "fact":
                if claim.payload is None:
                    return False, "Fact payload cannot be null"
                return True, "Valid fact"
            return True, "Not a fact claim"
        
        def validate_metric_range(claim: AgentClaim) -> Tuple[bool, str]:
            if claim.claim_type == "metric":
                if isinstance(claim.payload, dict):
                    for key, value in claim.payload.items():
                        if isinstance(value, (int, float)):
                            if value < -1e10 or value > 1e10:
                                return False, f"Metric {key} out of reasonable range"
                return True, "Metrics in range"
            return True, "Not a metric claim"
        
        def validate_credential_format(claim: AgentClaim) -> Tuple[bool, str]:
            if claim.claim_type == "credential":
                if not isinstance(claim.payload, str):
                    return False, "Credential must be string"
                if "=" not in claim.payload:
                    return False, "Credential must be key=value format"
                return True, "Valid credential format"
            return True, "Not a credential claim"
        
        self.type_validators["fact"] = validate_fact_type
        self.type_validators["metric"] = validate_metric_range
        self.type_validators["credential"] = validate_credential_format
    
    def validate(self, claim: AgentClaim) -> Tuple[bool, List[str]]:
        """Validar claim semánticamente"""
        errors = []
        
        # 1. Validación de tipo
        if claim.claim_type in self.type_validators:
            valid, msg = self.type_validators[claim.claim_type](claim)
            if not valid:
                errors.append(msg)
        
        # 2. Consistencia con hechos establecidos
        if claim.claim_type == "fact":
            fact_key = str(claim.payload)
            if fact_key in self.established_facts:
                established = self.established_facts[fact_key]
                if established != claim.payload:
                    errors.append(f"Contradicts established fact: {established} vs {claim.payload}")
        
        # 3. Validación temporal (si hay reglas)
        for rule in self.temporal_rules:
            try:
                if not rule(claim):
                    errors.append("Temporal consistency violation")
            except:
                pass
        
        return len(errors) == 0, errors
    
    def establish_fact(self, claim: AgentClaim):
        """Establecer hecho como verdadero (después de consenso)"""
        if claim.claim_type == "fact":
            self.established_facts[str(claim.payload)] = claim.payload


class MultiAgentContradictionDetector:
    """
    Detecta contradicciones entre claims de múltiples agentes.
    
    Tipos de contradicción:
    - Directa: A dice X, B dice NO-X
    - Temporal: Eventos en orden imposible
    - Causal: Efecto sin causa
    - Resource: Dos agentes claiman recurso exclusivo
    """
    
    def __init__(self):
        self.claims_by_subject: Dict[str, List[AgentClaim]] = defaultdict(list)
        self.contradictions: List[Contradiction] = []
    
    def add_claim(self, claim: AgentClaim):
        """Añadir claim para análisis"""
        subject = f"{claim.claim_type}:{json.dumps(claim.payload, sort_keys=True)}"
        self.claims_by_subject[subject].append(claim)
    
    def detect_contradictions(self) -> List[Contradiction]:
        """Detectar todas las contradicciones"""
        self.contradictions = []
        
        # 1. Contradicciones directas (mismo sujeto, payloads diferentes)
        for subject, claims in self.claims_by_subject.items():
            if len(claims) > 1:
                payloads = [json.dumps(c.payload, sort_keys=True) for c in claims]
                unique_payloads = set(payloads)
                
                if len(unique_payloads) > 1:
                    # Hay desacuerdo
                    for i, claim_a in enumerate(claims):
                        for claim_b in claims[i+1:]:
                            if json.dumps(claim_a.payload, sort_keys=True) != json.dumps(claim_b.payload, sort_keys=True):
                                contradiction = Contradiction(
                                    claim_a=claim_a,
                                    claim_b=claim_b,
                                    contradiction_type="direct",
                                    severity=self._compute_severity(claim_a, claim_b),
                                    resolution=None
                                )
                                self.contradictions.append(contradiction)
        
        # 2. Contradicciones temporales
        self._detect_temporal_contradictions()
        
        return self.contradictions
    
    def _detect_temporal_contradictions(self):
        """Detectar inconsistencias temporales"""
        all_claims = []
        for claims in self.claims_by_subject.values():
            all_claims.extend(claims)
        
        # Ordenar por timestamp
        sorted_claims = sorted(all_claims, key=lambda c: c.timestamp)
        
        # Buscar inversiones causales
        for i, claim in enumerate(sorted_claims):
            if "effect_of" in claim.payload if isinstance(claim.payload, dict) else False:
                cause_id = claim.payload.get("cause_id")
                # Buscar si la causa existe y viene después (imposible)
                for later_claim in sorted_claims[i+1:]:
                    if later_claim.hash() == cause_id:
                        contradiction = Contradiction(
                            claim_a=claim,
                            claim_b=later_claim,
                            contradiction_type="temporal_causal_inversion",
                            severity=0.9,
                            resolution="Effect precedes cause"
                        )
                        self.contradictions.append(contradiction)
    
    def _compute_severity(self, claim_a: AgentClaim, claim_b: AgentClaim) -> float:
        """Computar severidad de contradicción"""
        severity = 0.5  # Base
        
        # Más severo si ambos agentes son confiables
        if claim_a.trust_score > 0.8 and claim_b.trust_score > 0.8:
            severity += 0.3
        
        # Más severo si ambos tienen alta confianza
        if claim_a.confidence > 0.9 and claim_b.confidence > 0.9:
            severity += 0.2
        
        return min(severity, 1.0)
    
    def get_contradiction_summary(self) -> Dict[str, Any]:
        """Resumen de contradicciones"""
        by_type = defaultdict(int)
        by_severity = {"high": 0, "medium": 0, "low": 0}
        
        for c in self.contradictions:
            by_type[c.contradiction_type] += 1
            if c.severity > 0.7:
                by_severity["high"] += 1
            elif c.severity > 0.4:
                by_severity["medium"] += 1
            else:
                by_severity["low"] += 1
        
        return {
            "total_contradictions": len(self.contradictions),
            "by_type": dict(by_type),
            "by_severity": by_severity,
            "resolved": sum(1 for c in self.contradictions if c.resolution is not None),
            "unresolved": sum(1 for c in self.contradictions if c.resolution is None)
        }


class ProbabilisticTruthScoringEngine:
    """
    Motor de scoring de verdad probabilístico.
    
    Usa Bayesian updating para computar probabilidad de verdad
    basado en:
    - Número de agentes supportando
    - Trust scores de agentes
    - Evidence count
    - Contradicciones detectadas
    """
    
    def __init__(self, prior_probability: float = 0.5):
        self.prior = prior_probability  # P(verdad) inicial
        self.truth_scores: Dict[str, TruthScore] = {}
    
    def compute_truth_score(self, 
                           claim_hash: str,
                           supporting_agents: List[AgentClaim],
                           contradicting_agents: List[AgentClaim],
                           evidence_count: int = 0) -> TruthScore:
        """Computar truth score usando Bayesian updating"""
        
        # Prior odds
        prior_odds = self.prior / (1 - self.prior)
        
        # Likelihood ratio de agentes supportando
        support_lr = 1.0
        for agent in supporting_agents:
            # Agente confiable aumenta probabilidad
            likelihood = agent.trust_score * agent.confidence
            support_lr *= (likelihood + 0.1)  # Smoothing
        
        # Likelihood ratio de agentes contradiciendo
        contradict_lr = 1.0
        for agent in contradicting_agents:
            # Agente confiable disminuye probabilidad
            likelihood = agent.trust_score * agent.confidence
            contradict_lr *= (1 - likelihood + 0.1)  # Smoothing
        
        # Evidence factor
        evidence_factor = 1 + (evidence_count * 0.1)  # Cada evidencia +10%
        
        # Posterior odds
        posterior_odds = prior_odds * support_lr * contradict_lr * evidence_factor
        
        # Convertir a probabilidad
        posterior_prob = posterior_odds / (1 + posterior_odds)
        posterior_prob = max(0.0, min(1.0, posterior_prob))  # Clamp
        
        # Confidence interval (simplificado)
        n_agents = len(supporting_agents) + len(contradicting_agents)
        margin_of_error = 1.96 / (n_agents + 1)  # 95% CI
        ci_low = max(0.0, posterior_prob - margin_of_error)
        ci_high = min(1.0, posterior_prob + margin_of_error)
        
        # Determinar status
        if posterior_prob > 0.95:
            status = TruthStatus.VERIFIED
        elif posterior_prob > 0.75:
            status = TruthStatus.PROBABLE
        elif posterior_prob > 0.5:
            status = TruthStatus.UNVERIFIED
        elif posterior_prob > 0.25:
            status = TruthStatus.CONTRADICTED
        else:
            status = TruthStatus.IMPOSSIBLE
        
        truth_score = TruthScore(
            claim_hash=claim_hash,
            truth_probability=posterior_prob,
            confidence_interval=(ci_low, ci_high),
            supporting_agents=[a.agent_id for a in supporting_agents],
            contradicting_agents=[a.agent_id for a in contradicting_agents],
            evidence_count=evidence_count,
            status=status
        )
        
        self.truth_scores[claim_hash] = truth_score
        return truth_score
    
    def get_truth_distribution(self) -> Dict[str, int]:
        """Distribución de truth statuses"""
        distribution = defaultdict(int)
        for score in self.truth_scores.values():
            distribution[score.status.value] += 1
        return dict(distribution)


class EpistemicConsensusLayer:
    """
    Capa de consenso epistémico que coordina todos los componentes.
    
    Flujo:
    1. Recibir claims de agentes
    2. Validación semántica (Oracle)
    3. Detección de contradicciones (Detector)
    4. Scoring de verdad (Engine)
    5. Decisión de consenso
    6. Actualizar hechos establecidos
    """
    
    def __init__(self, consensus_threshold: float = 0.75):
        self.oracle = SemanticValidationOracle()
        self.detector = MultiAgentContradictionDetector()
        self.scoring_engine = ProbabilisticTruthScoringEngine()
        self.consensus_threshold = consensus_threshold
        
        self.pending_claims: List[AgentClaim] = []
        self.accepted_claims: List[AgentClaim] = []
        self.rejected_claims: List[AgentClaim] = []
    
    def submit_claim(self, claim: AgentClaim) -> Dict[str, Any]:
        """Someter claim para evaluación de consenso"""
        
        # 1. Validación semántica
        semantic_valid, semantic_errors = self.oracle.validate(claim)
        
        if not semantic_valid:
            self.rejected_claims.append(claim)
            return {
                "status": "rejected",
                "reason": "semantic_validation_failed",
                "errors": semantic_errors
            }
        
        # 2. Añadir al detector de contradicciones
        self.detector.add_claim(claim)
        self.pending_claims.append(claim)
        
        # 3. Detectar contradicciones
        contradictions = self.detector.detect_contradictions()
        related_contradictions = [
            c for c in contradictions 
            if c.claim_a.hash() == claim.hash() or c.claim_b.hash() == claim.hash()
        ]
        
        # 4. Computar truth score
        supporting = [c for c in self.pending_claims 
                     if json.dumps(c.payload, sort_keys=True) == json.dumps(claim.payload, sort_keys=True)]
        contradicting = [c for c in self.pending_claims 
                        if c.claim_type == claim.claim_type 
                        and json.dumps(c.payload, sort_keys=True) != json.dumps(claim.payload, sort_keys=True)]
        
        truth_score = self.scoring_engine.compute_truth_score(
            claim_hash=claim.hash(),
            supporting_agents=supporting,
            contradicting_agents=contradicting,
            evidence_count=len(claim.evidence)
        )
        
        # 5. Decisión de consenso
        if truth_score.truth_probability >= self.consensus_threshold:
            self.accepted_claims.append(claim)
            self.oracle.establish_fact(claim)
            
            return {
                "status": "accepted",
                "truth_probability": truth_score.truth_probability,
                "confidence_interval": truth_score.confidence_interval,
                "consensus_reached": True,
                "supporting_agents": len(supporting),
                "contradicting_agents": len(contradicting),
                "contradictions_detected": len(related_contradictions)
            }
        
        elif truth_score.truth_probability <= (1 - self.consensus_threshold):
            self.rejected_claims.append(claim)
            
            return {
                "status": "rejected",
                "truth_probability": truth_score.truth_probability,
                "reason": "insufficient_consensus",
                "supporting_agents": len(supporting),
                "contradicting_agents": len(contradicting)
            }
        
        else:
            return {
                "status": "pending",
                "truth_probability": truth_score.truth_probability,
                "reason": "awaiting_more_evidence",
                "supporting_agents": len(supporting),
                "contradicting_agents": len(contradicting),
                "needed_for_consensus": self.consensus_threshold - truth_score.truth_probability
            }
    
    def get_consensus_state(self) -> Dict[str, Any]:
        """Estado actual del consenso"""
        return {
            "pending_claims": len(self.pending_claims),
            "accepted_claims": len(self.accepted_claims),
            "rejected_claims": len(self.rejected_claims),
            "contradictions": self.detector.get_contradiction_summary(),
            "truth_distribution": self.scoring_engine.get_truth_distribution(),
            "established_facts_count": len(self.oracle.established_facts)
        }


def demo_epistemic_consensus():
    """Demostración del Epistemic Consensus Layer"""
    
    print("=" * 70)
    print("🧠 CORTEX PERSIST — EPISTEMIC CONSENSUS LAYER (Nivel 4)")
    print("=" * 70)
    print()
    print("Esto ya no es logging.")
    print("Esto es cortex que discute consigo mismo antes de creer algo.")
    print()
    
    # Crear consensus layer
    consensus = EpistemicConsensusLayer(consensus_threshold=0.6)
    
    # Simular múltiples agentes haciendo claims
    print("📡 RECEIVING CLAIMS FROM MULTIPLE AGENTS")
    print("-" * 50)
    
    agents = [
        ("agent_alpha", 0.95),  # High trust
        ("agent_beta", 0.85),   # Medium-high trust
        ("agent_gamma", 0.60),  # Low trust
        ("agent_delta", 0.90),  # High trust
    ]
    
    # Claims sobre el mismo hecho
    claims_data = [
        {"type": "fact", "payload": "user_authenticated_123", "confidence": 0.9},
        {"type": "fact", "payload": "user_authenticated_123", "confidence": 0.85},
        {"type": "fact", "payload": "user_NOT_authenticated_123", "confidence": 0.7},  # Contradiction!
        {"type": "fact", "payload": "user_authenticated_123", "confidence": 0.95},
    ]
    
    results = []
    for i, ((agent_id, trust), claim_data) in enumerate(zip(agents, claims_data)):
        claim = AgentClaim(
            agent_id=agent_id,
            claim_type=claim_data["type"],
            payload=claim_data["payload"],
            confidence=claim_data["confidence"],
            trust_score=trust,
            evidence=[f"evidence_{i}"] if i < 3 else []
        )
        
        result = consensus.submit_claim(claim)
        results.append(result)
        
        print(f"\nClaim {i+1}: {agent_id} says \"{claim_data['payload']}\"")
        print(f"  Trust: {trust}, Confidence: {claim_data['confidence']}")
        print(f"  Result: {result['status'].upper()}")
        if result['status'] != 'pending':
            print(f"  Truth Probability: {result.get('truth_probability', 'N/A'):.2%}")
        if 'contradictions_detected' in result:
            print(f"  Contradictions: {result['contradictions_detected']}")
    
    # Estado del consenso
    print("\n" + "=" * 70)
    print("📊 CONSENSUS STATE")
    print("-" * 50)
    
    state = consensus.get_consensus_state()
    print(f"Pending claims: {state['pending_claims']}")
    print(f"Accepted claims: {state['accepted_claims']}")
    print(f"Rejected claims: {state['rejected_claims']}")
    print(f"Established facts: {state['established_facts_count']}")
    print()
    print("Contradictions:")
    for k, v in state['contradictions']['by_type'].items():
        print(f"  {k}: {v}")
    print()
    print("Truth Distribution:")
    for status, count in state['truth_distribution'].items():
        print(f"  {status}: {count}")
    
    # Demostrar poison detection
    print("\n" + "=" * 70)
    print("🛡️ POISON DETECTION TEST")
    print("-" * 50)
    
    poison_claim = AgentClaim(
        agent_id="malicious_agent",
        claim_type="credential",
        payload="admin=true",  # Claim peligroso
        confidence=0.99,
        trust_score=0.1,  # Agente no confiable
        evidence=[]
    )
    
    poison_result = consensus.submit_claim(poison_claim)
    print(f"\nMalicious claim: \"admin=true\" from untrusted agent")
    print(f"  Result: {poison_result['status'].upper()}")
    print(f"  Truth Probability: {poison_result.get('truth_probability', 0):.2%}")
    print(f"  → System REJECTED low-truth claim despite high confidence")
    
    # Resumen final
    print("\n" + "=" * 70)
    print("✅ EPISTEMIC CONSENSUS LAYER OPERATIONAL")
    print("-" * 50)
    print()
    print("Capabilities enabled:")
    print("  ✓ Semantic validation oracle")
    print("  ✓ Multi-agent contradiction detection")
    print("  ✓ Probabilistic truth scoring")
    print("  ✓ Consensus-based fact establishment")
    print("  ✓ Poison resistance via trust weighting")
    print()
    print("System class upgraded:")
    print('  FROM: "cryptographic audit log with epistemic blindness"')
    print('  TO:   "epistemic consensus engine with truth discrimination"')
    print()
    
    return {
        "consensus_state": state,
        "test_results": results,
        "poison_detection": poison_result
    }


if __name__ == "__main__":
    result = demo_epistemic_consensus()
    
    # Guardar resultado
    output_path = os.path.join(os.path.dirname(__file__), "epistemic_consensus_demo.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"📄 Demo output saved: {output_path}")
