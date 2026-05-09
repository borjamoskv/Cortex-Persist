"""Neuro-Sincro-Caching (P1): Neural-Augmented Caching Layer.

Ajusta el TTL de los objetos en cache basándose en patrones de acceso y entropía.
"""

from __future__ import annotations

import time
import math
from typing import Dict, Any, Optional

class NeuroCache:
    """Cache que aprende la 'relevancia' de los datos mediante pesos dinámicos."""

    def __init__(self, base_ttl: int = 3600, alpha: float = 0.1):
        self.store: Dict[str, Dict[str, Any]] = {}
        self.base_ttl = base_ttl
        self.alpha = alpha  # Factor de aprendizaje (exergy gain)

    def set(self, key: str, value: Any):
        """Almacena un valor con peso inicial."""
        now = time.time()
        self.store[key] = {
            "value": value,
            "weight": 1.0,
            "access_count": 1,
            "last_access": now,
            "ttl": self.base_ttl,
            "expiry": now + self.base_ttl
        }

    def get(self, key: str) -> Optional[Any]:
        """Recupera un valor y recalcula su TTL (Neural Update)."""
        if key not in self.store:
            return None
        
        entry = self.store[key]
        now = time.time()

        if now > entry["expiry"]:
            del self.store[key]
            return None

        # --- Neural-Sincro Update ---
        # 1. Calculamos el intervalo desde el último acceso
        interval = now - entry["last_access"]
        
        # 2. Incrementamos el peso si el acceso es frecuente (baja latencia entre accesos)
        # Weight increases if accessed frequently. 
        # Si el intervalo es menor que el 10% del TTL, es un 'Hot Access'.
        hot_factor = 1.0 / (interval + 1)
        entry["weight"] = (1 - self.alpha) * entry["weight"] + self.alpha * (hot_factor * 100)
        
        # 3. Ajuste Dinámico de TTL: TTL = base_ttl * log(weight + 1)
        new_ttl = self.base_ttl * (1 + math.log10(max(1, entry["weight"])))
        entry["ttl"] = min(new_ttl, self.base_ttl * 24) # Cap at 24x base
        
        entry["expiry"] = now + entry["ttl"]
        entry["access_count"] += 1
        entry["last_access"] = now
        
        return entry["value"]

    def get_stats(self, key: str) -> Dict[str, Any]:
        """Retorna la exergía de la entrada."""
        return self.store.get(key, {})

if __name__ == "__main__":
    cache = NeuroCache(base_ttl=10)
    cache.set("key1", "data")
    print(f"Initial TTL: {cache.get_stats('key1')['ttl']}")
    
    # Simular accesos rápidos
    for _ in range(5):
        time.sleep(0.1)
        cache.get("key1")
        print(f"Updated TTL: {cache.get_stats('key1')['ttl']}")
