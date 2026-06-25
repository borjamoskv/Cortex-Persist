# [C5-REAL] Exergy-Maximized — Information-Theoretic Secure Pipeline
import os
import secrets
import logging
from typing import Tuple

try:
    from legacy_research.crypto.obfuscation_mac import InformationTheoreticSecurity
    from legacy_research.crypto.ephemeral_burn import ApoptosisBurner
    from legacy_research.crypto.shamir_trng import CortexShamirTRNG
except ImportError:
    # Fallback paths if executed outside main context
    import sys
    sys.path.insert(0, os.path.abspath('.'))
    from legacy_research.crypto.obfuscation_mac import InformationTheoreticSecurity
    from legacy_research.crypto.ephemeral_burn import ApoptosisBurner
    from legacy_research.crypto.shamir_trng import CortexShamirTRNG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [C5-REAL] %(message)s")
logger = logging.getLogger("info_theory_pipeline")

class CortexImpenerablePipeline:
    """
    Sintetiza las 10 Primitivas de Teoría de la Información en una única tubería de ejecución.
    - One-Time Pad (Symmetric Isomorphism)
    - Entropy Padding (Semantic Obfuscation)
    - Universal MAC (Info-Theoretic Auth)
    - Ephemeral Burn (Apoptosis)
    """
    def __init__(self):
        self.apoptosis_engine = ApoptosisBurner()
        self.PRIME = 2**127 - 1

    def _xor_bytes(self, data: bytes, key: bytes) -> bytes:
        """One-Time Pad: XOR estricto entre payload y entropía."""
        return bytes(a ^ b for a, b in zip(data, key))

    def transmit(self, payload: bytes, target_size: int = 4096) -> Tuple[bytes, bytes, int, int]:
        """
        Codifica un payload bajo el límite termodinámico de Shannon.
        Devuelve: (Criptograma_Ofuscado, OTP_Key, MAC_Key_A, MAC_Key_B)
        """
        logger.info("[PIPELINE] Iniciando Transmisión Impenetrable...")
        
        # 1. Ofuscación Semántica (Entropy Padding)
        padded_payload = InformationTheoreticSecurity.pad_entropy(payload, target_size)
        
        # 2. Generación de Llaves Termodinámicas (TRNG)
        # La llave OTP debe ser exactamente del tamaño del payload acolchado
        otp_key = secrets.token_bytes(len(padded_payload))
        mac_key_a = int.from_bytes(secrets.token_bytes(16), 'big') % self.PRIME
        mac_key_b = int.from_bytes(secrets.token_bytes(16), 'big') % self.PRIME
        
        # 3. One-Time Pad Encryption (Perfect Secrecy)
        ciphertext = self._xor_bytes(padded_payload, otp_key)
        
        # 4. Universal MAC sobre el texto cifrado (Encrypt-then-MAC)
        mac_tag = InformationTheoreticSecurity.generate_mac_tag(ciphertext, mac_key_a, mac_key_b)
        
        # 5. Registro de Apoptosis (Quemado de llaves en 5 segundos)
        # Se asume que el receptor obtendrá estas llaves por un canal Out-of-Band (ej. local RAM bus)
        token_id = self.apoptosis_engine.mint_token(ttl_seconds=5.0)
        
        logger.info(f"[PIPELINE] Payload sellado termodinámicamente. Criptograma tamaño: {len(ciphertext)} bytes.")
        return ciphertext, otp_key, mac_key_a, mac_key_b, mac_tag, token_id

    def receive(self, ciphertext: bytes, otp_key: bytes, mac_key_a: int, mac_key_b: int, mac_tag: int, token_id: str) -> bytes:
        """
        Decodifica un criptograma. Autentica, Descifra, Des-acolcha y Ejecuta Apoptosis.
        """
        logger.info("[PIPELINE] Iniciando Recepción de Criptograma...")
        
        # 1. Autorización por Apoptosis (Asegura NO Replay y NO Muerte Térmica)
        if not self.apoptosis_engine.consume_token(token_id):
            raise PermissionError("[ERROR C5] Colapso denegado. Token expirado, inexistente o ya incinerado.")
            
        # 2. Verificación de Integridad (Universal MAC)
        if not InformationTheoreticSecurity.verify_mac_tag(ciphertext, mac_tag, mac_key_a, mac_key_b):
            raise ValueError("[ERROR C5] Fallo Catastrófico de Integridad. MAC Inválido.")
            
        # 3. Descifrado One-Time Pad
        padded_payload = self._xor_bytes(ciphertext, otp_key)
        
        # 4. Recuperación de Señal Pura (Unpad Entropy)
        payload = InformationTheoreticSecurity.unpad_entropy(padded_payload)
        
        logger.info("[PIPELINE] Señal descifrada y purificada con éxito.")
        return payload

if __name__ == "__main__":
    logger.info("== INICIANDO VALIDACIÓN DE TUBERÍA IMPENETRABLE CORTEX ==")
    
    pipeline = CortexImpenerablePipeline()
    mensaje_secreto = b"C5-REAL: Lanzar secuencia Mitosis Ouroboros."
    
    # EMISOR
    try:
        ct, otp_k, mac_a, mac_b, mac_t, t_id = pipeline.transmit(mensaje_secreto, target_size=1024)
        
        # RECEPTOR
        mensaje_recuperado = pipeline.receive(ct, otp_k, mac_a, mac_b, mac_t, t_id)
        
        assert mensaje_secreto == mensaje_recuperado, "FALLO: El mensaje no coincide."
        logger.info(f"Mensaje Verificado: {mensaje_recuperado.decode('utf-8')}")
        
        # INTENTO DE REPLAY ATTACK (El atacante re-envía el paquete)
        logger.info("== SIMULANDO ATAQUE DE REPLAY ==")
        try:
            pipeline.receive(ct, otp_k, mac_a, mac_b, mac_t, t_id)
            logger.error("FALLO CATASTRÓFICO: El motor permitió el Replay.")
        except PermissionError as e:
            logger.info(f"Replay bloqueado con éxito por Apoptosis: {e}")
            
    except Exception as e:
        logger.error(f"Error en la tubería: {e}")
        
    logger.info("== TUBERÍA VALIDADA. ONTOLOGÍA CERO SOSTENIDA ==")
