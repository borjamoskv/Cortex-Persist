# [C5-REAL] Exergy-Maximized — Shamir's Secret Sharing (Information-Theoretic Security)
import os
import secrets
import logging
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [C5-REAL] %(message)s")
logger = logging.getLogger("shamir_trng")

# Operaciones algebraicas en el Campo Finito (Galois Field GF(2^8) o primos grandes)
# Para máxima invulnerabilidad termodinámica sin depender de extensiones lentas,
# usamos un número primo de Mersenne estandarizado para la criptografía (ej. 2^127 - 1)
# o implementamos la fragmentación polinomial básica.
PRIME = 2**127 - 1

def eval_poly_at(poly: List[int], x: int, prime: int) -> int:
    """Evalúa el polinomio en x usando el método de Horner."""
    result = 0
    for coeff in reversed(poly):
        result = (result * x + coeff) % prime
    return result

def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    x, y, u, v = 0, 1, 1, 0
    while a != 0:
        q, r = b // a, b % a
        m, n = x - u * q, y - v * q
        b, a, x, y, u, v = a, r, u, v, m, n
    return b, x, y

def mod_inverse(k: int, prime: int) -> int:
    k = k % prime
    if k < 0:
        r = extended_gcd(prime, -k)[2]
    else:
        r = extended_gcd(prime, k)[2]
    return (prime + r) % prime

class CortexShamirTRNG:
    """
    Motor de Fragmentación Termodinámica. (Information-Theoretic Security).
    Ningún fragmento inferior a 'k' reduce el espacio de entropía de la clave original.
    """
    
    @staticmethod
    def generate_true_random(bytes_len: int = 32) -> int:
        """
        Idealmente leeríamos de ruido térmico (/dev/random exhaustivo o entropía de hardware).
        Aquí usamos el CSPRNG del OS subyacente blindado.
        """
        return int.from_bytes(secrets.token_bytes(bytes_len), byteorder='big') % PRIME

    @staticmethod
    def split_secret(secret: int, n: int, k: int) -> List[Tuple[int, int]]:
        """
        Divide un secreto en 'n' fragmentos requiriendo 'k' para reconstruirlo.
        Polinomio: f(x) = a_0 + a_1*x + ... + a_{k-1}*x^{k-1} mod p
        donde a_0 = secret.
        """
        if k > n:
            raise ValueError("[ERROR C5] El quórum 'k' no puede ser mayor que 'n'.")
            
        logger.info(f"Colapsando secreto en {n} dimensiones. Quórum (k): {k}.")
        coeffs = [secret] + [CortexShamirTRNG.generate_true_random() for _ in range(k - 1)]
        shares = []
        for x in range(1, n + 1):
            y = eval_poly_at(coeffs, x, PRIME)
            shares.append((x, y))
        return shares

    @staticmethod
    def recover_secret(shares: List[Tuple[int, int]]) -> int:
        """
        Reconstruye el secreto original (a_0) usando interpolación de Lagrange en x=0.
        """
        secret = 0
        for i, (x_i, y_i) in enumerate(shares):
            numerator, denominator = 1, 1
            for j, (x_j, y_j) in enumerate(shares):
                if i != j:
                    numerator = (numerator * -x_j) % PRIME
                    denominator = (denominator * (x_i - x_j)) % PRIME
                    
            lagrange_val = (y_i * numerator * mod_inverse(denominator, PRIME)) % PRIME
            secret = (secret + lagrange_val) % PRIME
            
        return secret

if __name__ == "__main__":
    logger.info("Iniciando prueba de Fragmentación Termodinámica (Shamir K-of-N).")
    
    # 1. Definimos una Root Key determinista (o la generamos termodinámicamente)
    master_key = CortexShamirTRNG.generate_true_random(16)
    logger.info(f"Master Key Generada: {master_key}")
    
    # 2. Fragmentamos el isomorfismo (n=5, k=3)
    n, k = 5, 3
    fragments = CortexShamirTRNG.split_secret(master_key, n, k)
    
    logger.info("Fragmentos Creados:")
    for f in fragments:
        logger.info(f" -> Nodo {f[0]}: {str(f[1])[:10]}...")
        
    # 3. Reconstruimos usando solo el quórum 'k' (ej. índices 0, 2, 4)
    quorum_shares = [fragments[0], fragments[2], fragments[4]]
    logger.info(f"Reconstruyendo usando los Nodos: {[s[0] for s in quorum_shares]}")
    
    recovered_key = CortexShamirTRNG.recover_secret(quorum_shares)
    
    # 4. Aserción de Invariabilidad Termodinámica
    assert master_key == recovered_key, "FALLO CATASTRÓFICO: La interpolación no restauró el estado físico."
    logger.info(f"ÉXITO. Llave Recuperada: {recovered_key}")
    logger.info("El isomorfismo se ha preservado. Ontología Cero Mantenida.")
