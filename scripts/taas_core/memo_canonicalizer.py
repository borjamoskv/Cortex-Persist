"""
Sovereign Memo Canonicalizer (Nivel 150/100)
Garantiza hashes criptográficamente deterministas ordenando keys alfabéticamente
y neutralizando variables ambientales, evitando forjas por espacios en blanco.
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List

class MemoCanonicalizer:
    @staticmethod
    def _to_canonical_dict(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Asegura que solo las llaves válidas pasen al hash."""
        allowed_keys = [
            "type", "core_content", "derivation_reason", "resolution", 
            "entropy_score", "is_resolved", "parents"
        ]
        return {k: raw_data.get(k) for k in allowed_keys if raw_data.get(k) is not None}

    @staticmethod
    def _calculate_sha256(canonical_dict: Dict[str, Any]) -> str:
        """Serialización perfecta sin espacios. Inmune a formateos."""
        canonical_str = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

    @classmethod
    def forge_memo(cls, type_name: str, content: str, derivation: str, entropy: float, parents: List[str] = None, resolution: str = None) -> Dict[str, Any]:
        """El horno de un Memo atómico."""
        if type_name not in ["DECISION", "SCAR", "BRIDGE", "GHOST"]:
            raise ValueError(f"Ontology Violation: '{type_name}' is not a valid Trail primitive.")
        
        raw_base = {
            "type": type_name,
            "core_content": content,
            "derivation_reason": derivation,
            "entropy_score": round(entropy, 4),
            "parents": parents or []
        }
        
        if resolution:
            raw_base["resolution"] = resolution
            
        if type_name == "GHOST":
            raw_base["is_resolved"] = False
            
        canonical_payload = cls._to_canonical_dict(raw_base)
        memo_id = cls._calculate_sha256(canonical_payload)
        
        # El Memo Final inyectable
        return {
            "id": memo_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **canonical_payload,
            "derivation_hash": cls._calculate_sha256({"reason": derivation}) # Traza la lógica
        }

if __name__ == "__main__":
    memo = MemoCanonicalizer.forge_memo(
        type_name="SCAR",
        content="Race condition in TaaS SDK async lock.",
        derivation="Zero Trust (Ω3) failed due to I/O block.",
        entropy=0.85,
        resolution="Implemented @sovereign_lock decorator."
    )
    print(f" forged: {json.dumps(memo, indent=2)}")
