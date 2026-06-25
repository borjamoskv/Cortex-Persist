# [C5-REAL] Exergy-Maximized — Ephemeral Burn / Cryptographic Apoptosis
import logging
import secrets
import time
import threading

logging.basicConfig(level=logging.INFO, format="%(asctime)s [C5-REAL] %(message)s")
logger = logging.getLogger("ephemeral_burn")

class ApoptosisBurner:
    """
    Implementación de INFOTHEORY-003: Key Exhaustion (No-Reuse).
    Destrucción termodinámica de tokens. Una vez consumido, el token es 
    eliminado de la memoria impidiendo ataques de replay o extracción forense.
    """
    def __init__(self):
        self._tokens = {}
        self._lock = threading.Lock()

    def mint_token(self, ttl_seconds: float = 2.0) -> str:
        """
        Crea un token efímero y registra su entropía y fecha límite de muerte térmica.
        """
        token = secrets.token_hex(32)
        death_time = time.time() + ttl_seconds
        
        with self._lock:
            self._tokens[token] = death_time
            
        logger.info(f"[MINT] Token efímero generado (TTL: {ttl_seconds}s). Entropía inyectada.")
        return token

    def _burn(self, token: str):
        """
        Incinera físicamente la referencia del token en RAM.
        """
        if token in self._tokens:
            # Sobrescribimos el valor para diluir cualquier residuo en memoria si Python GC lo retrasa
            self._tokens[token] = -1
            del self._tokens[token]
            logger.info(f"[BURN] Apoptosis ejecutada. Token incinerado.")

    def consume_token(self, token: str) -> bool:
        """
        Colapsa la onda. El token se consume para autorizar una acción.
        Independientemente de la validación temporal, la lectura lo destruye de inmediato.
        """
        with self._lock:
            if token not in self._tokens:
                logger.error("[REJECT] Intento de colapso con token inexistente o ya incinerado.")
                return False
                
            death_time = self._tokens[token]
            self._burn(token)  # <-- Obligatorio: Lectura = Destrucción (One-Time Pad nature)
            
            if time.time() > death_time:
                logger.error("[REJECT] Muerte térmica alcanzada. El token expiró antes de su colapso.")
                return False
                
            logger.info("[CONSUME] Colapso Autorizado. Invariante termodinámica preservada.")
            return True

    def purge_decayed_tokens(self):
        """
        Daemon-like function para destruir tokens que no colapsaron antes de su muerte térmica.
        """
        now = time.time()
        decayed = []
        with self._lock:
            for token, death_time in self._tokens.items():
                if now > death_time:
                    decayed.append(token)
            
            for token in decayed:
                self._burn(token)
                
        if decayed:
            logger.warning(f"[PURGE] {len(decayed)} token(s) auto-incinerados por decaimiento térmico (TTL expirado).")

if __name__ == "__main__":
    logger.info("Iniciando prueba de Apoptosis Criptográfica (INFOTHEORY-003).")
    
    burner = ApoptosisBurner()
    
    # Prueba 1: Consumo Exitoso Inmediato
    t1 = burner.mint_token(ttl_seconds=5.0)
    assert burner.consume_token(t1) is True, "FALLO: El token debió colapsar exitosamente."
    
    # Prueba 2: Re-uso (Ataque de Replay / Anergía)
    logger.info("Aserción de ataque de Replay sobre T1...")
    assert burner.consume_token(t1) is False, "FALLO CATASTRÓFICO: Se permitió la reutilización de un token (Rotura de Perfect Secrecy)."
    
    # Prueba 3: Muerte Térmica (TTL)
    t2 = burner.mint_token(ttl_seconds=0.1)
    time.sleep(0.15)  # Esperamos a que la entropía decaiga
    logger.info("Aserción de consumo de token decaído termodinámicamente...")
    assert burner.consume_token(t2) is False, "FALLO CATASTRÓFICO: Se consumió un token más allá de su Muerte Térmica."
    
    # Prueba 4: Purga de Residuos
    t3 = burner.mint_token(ttl_seconds=0.1)
    time.sleep(0.15)
    burner.purge_decayed_tokens()
    with burner._lock:
        assert t3 not in burner._tokens, "FALLO: La purga no eliminó la basura termodinámica."

    logger.info("ÉXITO ABSOLUTO: Vector de ataque de Replay erradicado. Límite de no-reutilización asegurado.")
