"""
Scoring TaaS (Top-N Inhalación de Boot) - 150/100
Decide qué Memos (Decisions, Ghosts, Scars) sobreviven la selección
y se inyectan en el Context Window durante el Cold Boot JIT.
Combina Fuerza Gravitacional = Time-Decay * Entropy * DAG-Centrality.
"""
from typing import List, Dict, Any
from datetime import datetime, timezone
import math

class sovereign_gravity_engine:
    @staticmethod
    def _calculate_time_decay(timestamp_str: str, half_life_days: float = 30.0) -> float:
        """
        Calcula el decaimiento exponencial del peso de un Memo.
        Un memo antiguo pesa menos, a menos que su entropía sea altísima.
        """
        try:
            # Handle ISO formats
            if "Z" in timestamp_str:
                timestamp_str = timestamp_str.replace("Z", "+00:00")
            memo_time = datetime.fromisoformat(timestamp_str)
            if memo_time.tzinfo is None:
                memo_time = memo_time.replace(tzinfo=timezone.utc)
        except ValueError:
            return 0.5 # Fallback neutro

        delta_time = datetime.now(timezone.utc) - memo_time
        days_old = max(0, delta_time.total_seconds() / (24 * 3600))
        
        # Fórmula de desintegración: N(t) = N0 * (1/2)^(t/t_half)
        return (0.5) ** (days_old / half_life_days)

    @classmethod
    def score_memos(cls, trail_memos: List[Dict[str, Any]], context_capacity: int = 15) -> List[Dict[str, Any]]:
        """
        Física Pura: Score_Final = Entropía(Masa) * TimeDecay(DistanciaTemporal).
        Los Ghosts tienen multiplicador x3 (Atractores probabilísticos).
        Las Scars (Cicatrices) no decaen casi nada (Inmunidad).
        """
        scored_memos = []

        for memo in trail_memos:
            base_entropy = memo.get("entropy_score", 0.5)
            memo_type = memo.get("type", "DECISION")
            
            # Modificadores de Gravedad Específicos
            if memo_type == "GHOST" and not memo.get("is_resolved", True):
                decay = cls._calculate_time_decay(memo.get("timestamp", ""), half_life_days=7.0) 
                gravity = base_entropy * decay * 3.0 # Atractor Masivo
            elif memo_type == "SCAR":
                decay = cls._calculate_time_decay(memo.get("timestamp", ""), half_life_days=365.0) # Cicatrice eterna
                gravity = base_entropy * decay * 1.5
            elif memo_type == "BRIDGE":
                decay = cls._calculate_time_decay(memo.get("timestamp", ""), half_life_days=90.0) 
                gravity = base_entropy * decay * 1.2
            else: # DECISION
                decay = cls._calculate_time_decay(memo.get("timestamp", ""), half_life_days=30.0)
                gravity = base_entropy * decay

            memo["_gravity"] = round(gravity, 4)
            scored_memos.append(memo)

        # Ordenar por el campo _gravity inverso (Black Hole = Index 0)
        scored_memos.sort(key=lambda x: x["_gravity"], reverse=True)
        
        # Limpiar el campo efímero antes de devolver
        top_n = scored_memos[:context_capacity]
        for m in top_n:
            print(f"[BOOT] Memo [{m['type']}] ({m['id'][:8]}...) G-Force: {m.pop('_gravity')}")
            
        return top_n
