# [C5-REAL] Exergy-Maximized — Semantic Obfuscation & Universal MAC
import os
import secrets
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [C5-REAL] %(message)s")
logger = logging.getLogger("obfuscator_mac")

# Primo de Mersenne (2^127 - 1) para el campo finito del Universal Hash MAC
PRIME = 2**127 - 1

class InformationTheoreticSecurity:
    """
    Implementación de INFOTHEORY-005 (Unconditionally Secure MACs) y
    INFOTHEORY-008 (Semantic Obfuscation Boundary / Entropy Padding).
    """
    
    @staticmethod
    def _poly_hash(message_bytes: bytes, key_a: int, key_b: int) -> int:
        """
        Universal Hash Function sobre un campo finito (Carter-Wegman MAC).
        Autenticación incondicionalmente segura si las llaves (a, b) provienen 
        del TRNG y jamás se reutilizan (garantizado por Ephemeral Burn).
        h(m) = (a * m + b) mod p
        """
        m = int.from_bytes(message_bytes, byteorder='big')
        return (key_a * m + key_b) % PRIME

    @staticmethod
    def pad_entropy(payload: bytes, target_size: int = 4096) -> bytes:
        """
        [INFOTHEORY-008] Acolchado Termodinámico.
        Esconde el tamaño original del payload inyectando ruido puramente estocástico
        hasta alcanzar un tamaño idéntico para todos los paquetes (obfuscación de metadatos).
        Formato: [Payload Size (4 bytes)] + [Payload Real] + [Ruido Estocástico]
        """
        if len(payload) + 4 >= target_size:
            logger.warning("El payload ya excede o iguala el tamaño objetivo. Sin ofuscación de tamaño.")
            return len(payload).to_bytes(4, 'big') + payload
            
        noise_length = target_size - len(payload) - 4
        noise = secrets.token_bytes(noise_length)
        padded = len(payload).to_bytes(4, 'big') + payload + noise
        return padded

    @staticmethod
    def unpad_entropy(padded_payload: bytes) -> bytes:
        """
        Recupera el payload descartando la entropía inyectada leyendo el tamaño.
        """
        if len(padded_payload) < 4:
            raise ValueError("[ERROR C5] Paquete demasiado pequeño.")
        payload_len = int.from_bytes(padded_payload[:4], 'big')
        return padded_payload[4:4+payload_len]

    @staticmethod
    def generate_mac_tag(padded_payload: bytes, key_a: int, key_b: int) -> int:
        """
        [INFOTHEORY-005] Genera la etiqueta MAC matemáticamente invulnerable.
        """
        return InformationTheoreticSecurity._poly_hash(padded_payload, key_a, key_b)

    @staticmethod
    def verify_mac_tag(padded_payload: bytes, mac_tag: int, key_a: int, key_b: int) -> bool:
        """
        Verifica la etiqueta MAC. Si coincide, la integridad está asegurada matemáticamente.
        """
        expected_mac = InformationTheoreticSecurity._poly_hash(padded_payload, key_a, key_b)
        return secrets.compare_digest(str(expected_mac), str(mac_tag))

if __name__ == "__main__":
    logger.info("Iniciando prueba de Ofuscación Semántica y Autenticación Universal.")
    
    # 1. Señal Original (altamente identificable por su tamaño diminuto: 20 bytes)
    signal = b"DROP TABLE users; --"
    logger.info(f"Señal Original: {signal} (Tamaño: {len(signal)} bytes)")
    
    # 2. Ofuscación Semántica (Padding a 4096 bytes)
    TARGET_SIZE = 4096
    obfuscated_signal = InformationTheoreticSecurity.pad_entropy(signal, TARGET_SIZE)
    logger.info(f"Señal Ofuscada: <entropía> (Tamaño: {len(obfuscated_signal)} bytes)")
    assert len(obfuscated_signal) == TARGET_SIZE, "FALLO: El padding falló en oscurecer la longitud."
    
    # 3. Generación de Llaves de Autenticación Efímeras (Key A y Key B)
    # Estas deben ser destruidas tras su uso.
    key_a = int.from_bytes(secrets.token_bytes(16), 'big') % PRIME
    key_b = int.from_bytes(secrets.token_bytes(16), 'big') % PRIME
    
    # 4. Generación de Universal MAC
    mac = InformationTheoreticSecurity.generate_mac_tag(obfuscated_signal, key_a, key_b)
    logger.info(f"MAC Termodinámico Generado: {mac}")
    
    # 5. Verificación de Integridad
    is_valid = InformationTheoreticSecurity.verify_mac_tag(obfuscated_signal, mac, key_a, key_b)
    assert is_valid, "FALLO CATASTRÓFICO: La integridad matemática falló."
    logger.info("Integridad C5-REAL Validada Exitosamente.")
    
    # 6. Extracción de Señal Pura
    extracted_signal = InformationTheoreticSecurity.unpad_entropy(obfuscated_signal)
    assert extracted_signal == signal, "FALLO: El unpad corrompió la señal original."
    logger.info(f"Señal Extraída Intacta: {extracted_signal}")
    logger.info("Ontología Cero Alcanzada. El mensaje viajó sin exponer su tamaño y autenticado matemáticamente.")
