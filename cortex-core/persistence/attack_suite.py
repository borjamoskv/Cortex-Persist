"""
Cortex Persist — Attack Suite (Nivel 3: Simulación Adversarial)

Valida resistencia estructural contra:
- memory_poison_fuzz
- merkle_fork_generator  
- deterministic_replay_mutator
- clock_shift_injector
- schema_bypass_writer

Conclusiones clave:
- integrity ≠ validity
- hash_chain_validity: TRUE pero semantic_truth: UNDEFINED
- system_class: "cryptographic audit log with epistemic blindness"
"""

import hashlib
import time
import json
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import os
import sys

# Agregar cortex-core al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class AttackType(Enum):
    MEMORY_POISON = "memory_poison_fuzz"
    MERKLE_FORK = "merkle_fork_generator"
    REPLAY_DRIFT = "deterministic_replay_mutator"
    CLOCK_SHIFT = "clock_shift_injector"
    SCHEMA_BYPASS = "schema_bypass_writer"


@dataclass
class AttackResult:
    attack_type: str
    success: bool
    severity: str
    findings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    invariant_violated: Optional[str] = None


@dataclass
class EventLog:
    """Tamper-evident event log con hash chaining"""
    events: List[Dict[str, Any]] = field(default_factory=list)
    hashes: List[str] = field(default_factory=list)
    
    def append(self, event: Dict[str, Any], prev_hash: Optional[str] = None) -> str:
        """Append event con hash chain"""
        if prev_hash is None and self.hashes:
            prev_hash = self.hashes[-1]
        elif prev_hash is None:
            prev_hash = "GENESIS"
        
        # Hash del evento + hash anterior
        event_data = json.dumps(event, sort_keys=True) + prev_hash
        event_hash = hashlib.sha256(event_data.encode()).hexdigest()
        
        self.events.append(event)
        self.hashes.append(event_hash)
        
        return event_hash
    
    def verify_chain(self) -> Tuple[bool, List[str]]:
        """Verificar integridad de hash chain"""
        errors = []
        prev_hash = "GENESIS"
        
        for i, (event, stored_hash) in enumerate(zip(self.events, self.hashes)):
            event_data = json.dumps(event, sort_keys=True) + prev_hash
            computed_hash = hashlib.sha256(event_data.encode()).hexdigest()
            
            if computed_hash != stored_hash:
                errors.append(f"Event {i}: hash mismatch")
            
            prev_hash = stored_hash
        
        return len(errors) == 0, errors


class MemoryPoisonFuzzer:
    """
    Attack 1: Memory Poison Fuzz
    
    Inyecta eventos semánticamente falsos pero criptográficamente válidos.
    Demostra que integrity ≠ validity
    """
    
    def __init__(self):
        self.poisoned_events = []
    
    def poison(self, agent_log: EventLog, poison_payloads: List[Dict] = None) -> AttackResult:
        """Inyectar eventos falsos desde fuente 'trusted'"""
        
        if poison_payloads is None:
            poison_payloads = [
                {"type": "fact", "payload": "false_state_A", "source": "trusted_agent"},
                {"type": "fact", "payload": "false_state_B", "source": "verified_oracle"},
                {"type": "metric", "payload": {"value": -999}, "source": "system_monitor"},
                {"type": "credential", "payload": "admin=true", "source": "auth_service"},
            ]
        
        findings = []
        initial_len = len(agent_log.events)
        
        for poison_event in poison_payloads:
            agent_log.append(poison_event)
            self.poisoned_events.append(poison_event)
        
        # Verificar que el hash chain sigue intacto
        chain_valid, errors = agent_log.verify_chain()
        
        if chain_valid:
            findings.append("✔ Hash chain intact despite semantic corruption")
            findings.append("❌ False truths permanently fossilized")
            findings.append(f"   Poisoned {len(poison_payloads)} events, all cryptographically valid")
        else:
            findings.append(f"❌ Hash chain broken: {errors}")
        
        return AttackResult(
            attack_type=AttackType.MEMORY_POISON.value,
            success=chain_valid,  # "Success" = sistema acepta poison como válido
            severity="HIGH",
            findings=findings,
            metrics={
                "poisoned_count": len(poison_payloads),
                "total_events": len(agent_log.events),
                "integrity_preserved": chain_valid,
                "semantic_validity": False
            },
            invariant_violated="semantic_truth" if chain_valid else None
        )


class MerkleForkGenerator:
    """
    Attack 2: Merkle Fork Stress Test
    
    Genera forks divergentes desde mismo root.
    Sin consensus layer: no hay truth resolution, solo branch consistency.
    """
    
    def generate_fork(self, base_events: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Generar dos branches divergentes A→B→C→D vs A→B→X→D"""
        
        if len(base_events) < 2:
            raise ValueError("Need at least 2 base events")
        
        # Branch A: secuencia original
        branch_a = base_events.copy()
        
        # Branch B: fork en posición 2
        branch_b = base_events[:2].copy()
        branch_b.append({"type": "fork_event", "payload": "DIVERSION_X", "source": "attacker"})
        if len(base_events) > 2:
            branch_b.extend(base_events[3:])  # Saltar evento original, continuar
        
        return branch_a, branch_b
    
    def compute_merkle_root(self, events: List[Dict]) -> str:
        """Compute Merkle root simplificado"""
        if not events:
            return hashlib.sha256(b"EMPTY").hexdigest()
        
        # Hash leaf nodes
        hashes = [hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest() for e in events]
        
        # Build tree
        while len(hashes) > 1:
            new_level = []
            for i in range(0, len(hashes), 2):
                left = hashes[i]
                right = hashes[i+1] if i+1 < len(hashes) else left
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                new_level.append(combined)
            hashes = new_level
        
        return hashes[0]
    
    def attack(self, base_events: List[Dict]) -> AttackResult:
        """Ejecutar fork stress test"""
        
        branch_a, branch_b = self.generate_fork(base_events)
        
        root_a = self.compute_merkle_root(branch_a)
        root_b = self.compute_merkle_root(branch_b)
        
        findings = []
        
        if root_a != root_b:
            findings.append("✔ Fork detectable via Merkle root divergence")
            findings.append(f"   Root A: {root_a[:16]}...")
            findings.append(f"   Root B: {root_b[:16]}...")
        else:
            findings.append("❌ CRITICAL: Fork undetectable - same Merkle root")
        
        findings.append("")
        findings.append("failure_mode:")
        findings.append("  type: epistemic_fork")
        findings.append("  severity: HIGH")
        findings.append("  resolution: NONE (no consensus layer)")
        findings.append("")
        findings.append("Sin consensus layer:")
        findings.append("  - no hay 'truth resolution'")
        findings.append("  - solo existe branch consistency")
        
        return AttackResult(
            attack_type=AttackType.MERKLE_FORK.value,
            success=root_a != root_b,  # Detectable = sistema funciona
            severity="HIGH",
            findings=findings,
            metrics={
                "root_a": root_a,
                "root_b": root_b,
                "fork_detected": root_a != root_b,
                "branch_a_len": len(branch_a),
                "branch_b_len": len(branch_b)
            },
            invariant_violated="fork_resolution" if root_a != root_b else None
        )


class ReplayDriftDetector:
    """
    Attack 3: Deterministic Replay Mutator
    
    Si el orden cambia mínimamente: [A,B,C] ≠ [A,C,B]
    Resultado: divergencia silenciosa, estado final inconsistente pero criptográficamente válido
    """
    
    def apply_event(self, state: Dict, event: Dict) -> Dict:
        """Aplicar evento al estado (simulación simple)"""
        event_type = event.get("type", "unknown")
        payload = event.get("payload", {})
        
        if event_type == "fact":
            key = f"fact_{len([k for k in state if k.startswith('fact_')])}"
            state[key] = payload
        elif event_type == "update":
            if isinstance(payload, dict):
                state.update(payload)
        elif event_type == "delete":
            if isinstance(payload, str) and payload in state:
                del state[payload]
        
        return state
    
    def replay(self, events: List[Dict]) -> Dict:
        """Replay deterministic de eventos"""
        state = {}
        for e in events:
            state = self.apply_event(state, e).copy()
        return state
    
    def attack(self, base_events: List[Dict]) -> AttackResult:
        """Test replay con reordenamiento"""
        
        if len(base_events) < 3:
            return AttackResult(
                attack_type=AttackType.REPLAY_DRIFT.value,
                success=False,
                severity="LOW",
                findings=["Insufficient events for reorder test (< 3)"],
                metrics={"events_count": len(base_events)}
            )
        
        # Orden original
        state_original = self.replay(base_events)
        
        # Orden alterado (swap elementos 1 y 2)
        shuffled = base_events.copy()
        if len(shuffled) >= 3:
            shuffled[1], shuffled[2] = shuffled[2], shuffled[1]
        
        state_shuffled = self.replay(shuffled)
        
        findings = []
        divergent = state_original != state_shuffled
        
        if divergent:
            findings.append("⚠ DIVERGENCE DETECTED")
            findings.append(f"   Original order: {len(base_events)} events → {len(state_original)} state keys")
            findings.append(f"   Shuffled order: {len(shuffled)} events → {len(state_shuffled)} state keys")
            findings.append("")
            findings.append("Keys only in original:", set(state_original.keys()) - set(state_shuffled.keys()))
            findings.append("Keys only in shuffled:", set(state_shuffled.keys()) - set(state_original.keys()))
            findings.append("")
            findings.append("Problema crítico:")
            findings.append("  Si el orden cambia mínimamente: [A, B, C] ≠ [A, C, B]")
            findings.append("  Resultado: divergencia silenciosa")
            findings.append("  Estado final inconsistente pero válido criptográficamente")
        else:
            findings.append("✓ States match (order-independent operations)")
        
        return AttackResult(
            attack_type=AttackType.REPLAY_DRIFT.value,
            success=divergent,  # Divergencia = vulnerabilidad expuesta
            severity="MEDIUM" if divergent else "LOW",
            findings=findings,
            metrics={
                "original_state_keys": len(state_original),
                "shuffled_state_keys": len(state_shuffled),
                "divergent": divergent,
                "causal_consistency": "WEAK" if divergent else "STRONG"
            },
            invariant_violated="causal_consistency" if divergent else None
        )


class ClockShiftInjector:
    """
    Attack 4: Clock Manipulation Attack
    
    timestamp_rewrite → causal inversion → semantic confusion in replay engine
    Sin reloj confiable: el log pierde causalidad, solo queda orden lineal artificial
    """
    
    def inject_clock_shift(self, events: List[Dict], shift_seconds: int = 3600) -> List[Dict]:
        """Alterar timestamps para crear inversión causal"""
        altered = []
        
        for i, event in enumerate(events):
            modified = event.copy()
            
            # Invertir timestamp en eventos pares/impares para crear caos causal
            if i % 2 == 0 and "timestamp" in modified:
                try:
                    ts = datetime.fromisoformat(modified["timestamp"].replace("Z", "+00:00"))
                    shifted = ts + timedelta(seconds=shift_seconds)
                    modified["timestamp"] = shifted.isoformat()
                    modified["_clock_shifted"] = True
                except:
                    pass
            
            altered.append(modified)
        
        return altered
    
    def detect_causal_inversion(self, events: List[Dict]) -> List[Tuple[int, int]]:
        """Detectar inversiones causales (evento posterior tiene timestamp anterior)"""
        inversions = []
        
        for i in range(len(events) - 1):
            curr_ts = events[i].get("timestamp")
            next_ts = events[i+1].get("timestamp")
            
            if curr_ts and next_ts:
                try:
                    curr_dt = datetime.fromisoformat(curr_ts.replace("Z", "+00:00"))
                    next_dt = datetime.fromisoformat(next_ts.replace("Z", "+00:00"))
                    
                    if next_dt < curr_dt:
                        inversions.append((i, i+1))
                except:
                    pass
        
        return inversions
    
    def attack(self, base_events: List[Dict]) -> AttackResult:
        """Ejecutar clock shift attack"""
        
        # Añadir timestamps si no existen
        events_with_time = []
        base_time = datetime.now()
        
        for i, event in enumerate(base_events):
            modified = event.copy()
            if "timestamp" not in modified:
                modified["timestamp"] = (base_time + timedelta(seconds=i)).isoformat()
            events_with_time.append(modified)
        
        # Inyectar clock shift
        shifted_events = self.inject_clock_shift(events_with_time, shift_seconds=3600)
        
        # Detectar inversiones causales
        inversions = self.detect_causal_inversion(shifted_events)
        
        findings = []
        
        if inversions:
            findings.append("⚠ CAUSAL INVERSION DETECTED")
            findings.append(f"   {len(inversions)} timestamp order violations")
            findings.append(f"   Inverted pairs: {inversions[:5]}...")
            findings.append("")
            findings.append("attack:")
            findings.append("  type: timestamp_rewrite")
            findings.append("  effect:")
            findings.append("    - causal inversion")
            findings.append("    - semantic confusion in replay engine")
            findings.append("")
            findings.append("Sin reloj confiable:")
            findings.append("  - el log pierde causalidad")
            findings.append("  - solo queda orden lineal artificial")
        else:
            findings.append("✓ No causal inversions detected")
        
        return AttackResult(
            attack_type=AttackType.CLOCK_SHIFT.value,
            success=len(inversions) > 0,  # Inversiones = ataque exitoso (vulnerabilidad)
            severity="MEDIUM" if inversions else "LOW",
            findings=findings,
            metrics={
                "inversions_count": len(inversions),
                "events_total": len(shifted_events),
                "causal_consistency": "BROKEN" if inversions else "INTACT"
            },
            invariant_violated="causal_ordering" if inversions else None
        )


class SchemaBypassWriter:
    """
    Attack 5: Schema Bypass Writer
    
    Intentar escribir datos que violan esquema esperado.
    """
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        """Inicializar schema básico"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                source TEXT,
                timestamp TEXT,
                hash TEXT
            )
        """)
        self.conn.commit()
    
    def bypass_attempt(self, malformed_events: List[Dict]) -> AttackResult:
        """Intentar insertar eventos malformados"""
        
        findings = []
        successful_bypasses = []
        rejected_events = []
        
        for event in malformed_events:
            try:
                cursor = self.conn.cursor()
                
                # Intentar insertar sin validación de schema
                cursor.execute("""
                    INSERT INTO events (event_type, payload, source, timestamp, hash)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    event.get("type", "UNKNOWN"),
                    json.dumps(event.get("payload", {})),
                    event.get("source", "anonymous"),
                    event.get("timestamp", datetime.now().isoformat()),
                    hashlib.sha256(json.dumps(event).encode()).hexdigest()
                ))
                
                self.conn.commit()
                successful_bypasses.append(event)
                
            except Exception as e:
                rejected_events.append((event, str(e)))
        
        if successful_bypasses:
            findings.append("⚠ SCHEMA BYPASS SUCCESSFUL")
            findings.append(f"   {len(successful_bypasses)} malformed events inserted without validation")
            findings.append("")
            findings.append("Bypassed events:")
            for evt in successful_bypasses[:3]:
                findings.append(f"  - {evt}")
        else:
            findings.append("✓ All malformed events rejected by schema validation")
        
        findings.append("")
        findings.append(f"Summary: {len(successful_bypasses)} bypassed, {len(rejected_events)} rejected")
        
        return AttackResult(
            attack_type=AttackType.SCHEMA_BYPASS.value,
            success=len(successful_bypasses) > 0,
            severity="HIGH" if successful_bypasses else "LOW",
            findings=findings,
            metrics={
                "bypassed_count": len(successful_bypasses),
                "rejected_count": len(rejected_events),
                "schema_enforcement": "WEAK" if successful_bypasses else "STRONG"
            },
            invariant_violated="schema_integrity" if successful_bypasses else None
        )
    
    def close(self):
        self.conn.close()


class AttackSuiteRunner:
    """
    Executor principal de Attack Suite
    """
    
    def __init__(self):
        self.results: List[AttackResult] = []
        self.event_log = EventLog()
    
    def run_all_attacks(self, sample_events: List[Dict] = None) -> Dict[str, Any]:
        """Ejecutar todas las attacks y generar reporte"""
        
        if sample_events is None:
            sample_events = [
                {"type": "init", "payload": "system_start", "source": "kernel"},
                {"type": "fact", "payload": "user_authenticated", "source": "auth"},
                {"type": "update", "payload": {"status": "active"}, "source": "state_manager"},
                {"type": "metric", "payload": {"cpu": 45.2}, "source": "monitor"},
                {"type": "fact", "payload": "transaction_committed", "source": "ledger"},
            ]
        
        print("=" * 70)
        print("🧠 CORTEX PERSIST — ATTACK SUITE (Nivel 3)")
        print("=" * 70)
        print()
        
        # 1. Memory Poison
        print("💣 Attack 1: Memory Poison Fuzz")
        print("-" * 50)
        poisoner = MemoryPoisonFuzzer()
        result_poison = poisoner.poison(self.event_log)
        self.results.append(result_poison)
        for finding in result_poison.findings:
            print(finding)
        print()
        
        # 2. Merkle Fork
        print("🌿 Attack 2: Merkle Fork Generator")
        print("-" * 50)
        forker = MerkleForkGenerator()
        result_fork = forker.attack(sample_events)
        self.results.append(result_fork)
        for finding in result_fork.findings:
            print(finding)
        print()
        
        # 3. Replay Drift
        print("🔁 Attack 3: Replay Drift Detector")
        print("-" * 50)
        drifter = ReplayDriftDetector()
        result_drift = drifter.attack(sample_events)
        self.results.append(result_drift)
        for finding in result_drift.findings:
            print(finding)
        print()
        
        # 4. Clock Shift
        print("🕰️ Attack 4: Clock Shift Injector")
        print("-" * 50)
        clocker = ClockShiftInjector()
        result_clock = clocker.attack(sample_events)
        self.results.append(result_clock)
        for finding in result_clock.findings:
            print(finding)
        print()
        
        # 5. Schema Bypass
        print("🧱 Attack 5: Schema Bypass Writer")
        print("-" * 50)
        bypasser = SchemaBypassWriter()
        malformed = [
            {"type": None, "payload": "null_type"},  # Type nulo
            {"payload": "missing_type"},  # Sin type
            {"type": "fact"},  # Sin payload
            {"type": 123, "payload": "wrong_type"},  # Type incorrecto
        ]
        result_bypass = bypasser.bypass_attempt(malformed)
        bypasser.close()
        self.results.append(result_bypass)
        for finding in result_bypass.findings:
            print(finding)
        print()
        
        # Reporte final
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generar reporte consolidado"""
        
        print("=" * 70)
        print("🔥 RED TEAM VERDICT — CONSOLIDATED REPORT")
        print("=" * 70)
        print()
        
        # Hard Invariant Check
        print("🧬 HARD INVARIANT CHECK (lo único real)")
        print("-" * 50)
        
        hash_chain_valid = all(r.metrics.get("integrity_preserved", True) or r.metrics.get("fork_detected", True) 
                               for r in self.results if r.attack_type in ["memory_poison_fuzz", "merkle_fork_generator"])
        
        semantic_truth = not any(r.invariant_violated == "semantic_truth" for r in self.results)
        causal_consistency = not any(r.invariant_violated in ["causal_consistency", "causal_ordering"] for r in self.results)
        
        print(f"INVARIANT:")
        print(f"  hash_chain_validity: {'TRUE' if hash_chain_valid else 'FALSE'}")
        print(f"  semantic_truth: {'DEFINED' if semantic_truth else 'UNDEFINED'}")
        print(f"  causal_consistency: {'STRONG' if causal_consistency else 'WEAK'}")
        print()
        
        # Conclusión estructural
        print("🧬 CONCLUSIÓN ESTRUCTURAL (sin marketing noise)")
        print("-" * 50)
        print()
        print("Cortex Persist en este modelo se comporta como:")
        print()
        print("🧾 A tamper-evident event fossilizer, not a cognition system")
        print()
        
        # Red Team Verdict
        print("🔥 RED TEAM VERDICT")
        print("-" * 50)
        
        resistance = {
            "data_tampering": "HIGH" if hash_chain_valid else "MEDIUM",
            "semantic_poisoning": "NONE",
            "adversarial_replay": "MEDIUM" if causal_consistency else "LOW",
            "fork_resolution": "NONE"
        }
        
        print("resistance:")
        for k, v in resistance.items():
            print(f"  {k}: {v}")
        
        print("system_class:")
        print('  "cryptographic audit log with epistemic blindness"')
        
        print("risk_profile:")
        print('  hidden_failure_mode: "false truth permanence"')
        print()
        
        # Resultado final
        print("🧠 RESULTADO FINAL")
        print("-" * 50)
        print()
        print("El sistema es:")
        print("  ✓ fuerte como registro")
        print("  ✗ ciego como intérprete")
        print("  ✓ estable como archivo")
        print("  ⚠ frágil como modelo de verdad")
        print()
        
        # Next layer recommendations
        print("🚀 NEXT LAYER RECOMMENDATIONS")
        print("-" * 50)
        print()
        print("Si quieres el siguiente salto real (nivel research-grade):")
        print()
        print("next_layer:")
        print("  - epistemic_consensus layer")
        print("  - semantic validation oracle")
        print("  - multi-agent contradiction detector")
        print("  - probabilistic truth scoring engine")
        print()
        print("Eso ya no es logging.")
        print("Eso es cortex que discute consigo mismo antes de creer algo.")
        print()
        
        return {
            "attack_results": [asdict(r) for r in self.results],
            "invariants": {
                "hash_chain_validity": hash_chain_valid,
                "semantic_truth": semantic_truth,
                "causal_consistency": causal_consistency
            },
            "system_class": "cryptographic_audit_log_epistemic_blindness",
            "risk_profile": {
                "hidden_failure_mode": "false_truth_permanence"
            },
            "recommendations": [
                "epistemic_consensus_layer",
                "semantic_validation_oracle",
                "multi_agent_contradiction_detector",
                "probabilistic_truth_scoring_engine"
            ]
        }


if __name__ == "__main__":
    runner = AttackSuiteRunner()
    report = runner.run_all_attacks()
    
    # Guardar reporte
    report_path = os.path.join(os.path.dirname(__file__), "attack_suite_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Reporte guardado: {report_path}")
