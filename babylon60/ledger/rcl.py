# [C5-REAL] Exergy-Maximized
"""
Runtime Causal Ledger (RCL)
El sistema auditable de causalidad para el runtime de imports de Python.
No asume determinismo total; ancla los eventos en un grafo causal y detecta divergencias 
estructurales bajo BFT.
"""

import contextvars
import hashlib
import sys
import time
from enum import Enum
from typing import Any, Literal, Optional, TypedDict

import babylon60.utils.canonical as canonical

# Context variable for async temporal coherence tracking
current_import_parent = contextvars.ContextVar("current_import_parent", default=None)

class CausalEvent(TypedDict):
    id: str                   
    ts: float                 
    kind: Literal[
        "import_request", "resolver_choice", "load_exec",
        "module_bind", "mutation", "invalidate", "reload"
    ]
    subject: str              
    inputs: dict[str, Any]    
    outputs: dict[str, Any]   
    parent_event_id: Optional[str] 
    tenant_id: str            

class RuntimeSnapshot(TypedDict):
    snapshot_id: str
    ts: float
    sys_modules_hash: str     
    sys_meta_path_hash: str   
    sys_path_hash: str        
    import_cache_hashes: dict[str, str] 
    loader_state_hashes: dict[str, str] 

class EdgeRelation(str, Enum):
    TRIGGERS = "triggers"       
    CONSUMES = "consumes"       
    OVERRIDES = "overrides"     
    ALIASES = "aliases"         
    MUTATES = "mutates"         

class DivergenceReport(TypedDict):
    severity: Literal["WARNING", "ERROR", "CRITICAL"]
    classification: Literal[
        "DIVERGENCE_IDENTITY", 
        "DIVERGENCE_ORDER", 
        "DIVERGENCE_LOADER", 
        "DIVERGENCE_SIDE_EFFECT"
    ]
    details: str

def _compute_sha3_256(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()

def _hash_dict(d: dict) -> str:
    # Deterministic hash of a dict using canonical JSON from cortex/babylon60
    return _compute_sha3_256(canonical.canonical_json(d).encode('utf-8'))

def _hash_list(lst: list) -> str:
    # Deterministic hash of a list
    return _compute_sha3_256(canonical.canonical_json(lst).encode('utf-8'))

class RuntimeCausalLedger:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.events: list[CausalEvent] = []
        self._module_identity_map: dict[str, str] = {}
        self.pre_snapshot: Optional[RuntimeSnapshot] = None
        self.post_snapshot: Optional[RuntimeSnapshot] = None

    def record_event(self, kind: str, subject: str, inputs: dict[str, Any], outputs: dict[str, Any]) -> str:
        """Forja un evento atómico y lo anexa al grafo en memoria."""
        ts = time.perf_counter()
        
        # Propagación de causalidad asíncrona (Async Temporal Coherence)
        parent_id = current_import_parent.get()
        
        # Payload canónico para SHA3-256
        payload = f"{ts}|{kind}|{subject}|{parent_id}".encode()
        event_id = _compute_sha3_256(payload)
        
        event = CausalEvent(
            id=event_id,
            ts=ts,
            kind=kind, # type: ignore
            subject=subject,
            inputs=inputs,
            outputs=outputs,
            parent_event_id=parent_id,
            tenant_id=self.tenant_id
        )
        
        self.events.append(event)
        
        # Actualizamos el contexto de procedencia si este evento desencadena otros
        current_import_parent.set(event_id)
        
        return event_id

    def capture_snapshot(self) -> RuntimeSnapshot:
        """Congela el estado actual de sys para validación posterior."""
        ts = time.perf_counter()
        
        sys_modules_keys = sorted(list(sys.modules.keys()))
        sys_modules_hash = _hash_list(sys_modules_keys)
        
        sys_meta_path_reprs = [repr(finder) for finder in sys.meta_path]
        sys_meta_path_hash = _hash_list(sys_meta_path_reprs)
        
        sys_path_hash = _hash_list(sys.path)
        
        import_cache_hashes = {
            k: repr(v) for k, v in sys.path_importer_cache.items()
        }
        
        # Loader state is tricky, just stubbing for pure loaders
        loader_state_hashes = {}
        
        payload = f"{ts}|{sys_modules_hash}|{sys_meta_path_hash}".encode()
        snapshot_id = _compute_sha3_256(payload)
        
        snapshot = RuntimeSnapshot(
            snapshot_id=snapshot_id,
            ts=ts,
            sys_modules_hash=sys_modules_hash,
            sys_meta_path_hash=sys_meta_path_hash,
            sys_path_hash=sys_path_hash,
            import_cache_hashes=import_cache_hashes,
            loader_state_hashes=loader_state_hashes
        )
        
        if not self.pre_snapshot:
            self.pre_snapshot = snapshot
        else:
            self.post_snapshot = snapshot
            
        return snapshot

    def commit_segment(self) -> Optional[DivergenceReport]:
        """
        Evalúa el catálogo de Constraints sobre el segmento actual.
        Si hay divergencia, retorna el reporte. Si no, consolida la memoria.
        """
        # Constraint 1: IdentityCoherence (Split-brain detection)
        # Buscar eventos module_bind
        binds = [e for e in self.events if e["kind"] == "module_bind"]
        identity_map = {}
        for b in binds:
            mod_name = b["subject"]
            obj_id = b["outputs"].get("object_id")
            if mod_name in identity_map and identity_map[mod_name] != obj_id:
                return DivergenceReport(
                    severity="CRITICAL",
                    classification="DIVERGENCE_IDENTITY",
                    details=f"Split-brain import detectado en {mod_name}: Multiples identidades en un segmento causal."
                )
            identity_map[mod_name] = obj_id

        # Constraint 2: ResolverMonotonicity
        if self.pre_snapshot and self.post_snapshot:
            if self.pre_snapshot["sys_meta_path_hash"] != self.post_snapshot["sys_meta_path_hash"]:
                # Check si hubo evento de mutación legitima
                mutations = [e for e in self.events if e["kind"] == "mutation" and "sys.meta_path" in e["subject"]]
                if not mutations:
                    return DivergenceReport(
                        severity="ERROR",
                        classification="DIVERGENCE_ORDER",
                        details="Resolver shadowing detectado. sys.meta_path mutado sin evento causal."
                    )
                    
        # Limpiamos segmento para la siguiente iteración
        self.events.clear()
        self.pre_snapshot = None
        self.post_snapshot = None
        return None

# Singleton / Global Hook Manager support
_active_ledgers: dict[str, RuntimeCausalLedger] = {}

def get_ledger(tenant_id: str) -> RuntimeCausalLedger:
    if tenant_id not in _active_ledgers:
        _active_ledgers[tenant_id] = RuntimeCausalLedger(tenant_id)
    return _active_ledgers[tenant_id]
