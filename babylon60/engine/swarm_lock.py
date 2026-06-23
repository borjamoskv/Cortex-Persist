import fcntl
import logging
import os
import time
from contextlib import contextmanager

logger = logging.getLogger("babylon60.engine.swarm_lock")

# Ubicación del cerrojo termodinámico
LOCK_FILE = ".cortex_swarm.lock"

@contextmanager
def swarm_git_lock(timeout: float = 60.0):
    """
    [C5-REAL] Swarm Lock para Concurrencia Confiable (Axioma R10 / Ω1).
    Usa POSIX fcntl (flock) para serializar el acceso al Git index a través
    de múltiples agentes independientes corriendo concurrentemente.
    """
    lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
    start_time = time.time()
    
    acquired = False
    while time.time() - start_time < timeout:
        try:
            # LOCK_EX: Bloqueo exclusivo, LOCK_NB: No bloqueante (falla inmediatamente si está bloqueado)
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
            break
        except BlockingIOError:
            time.sleep(0.5) # Espera termodinámica (Base-60 ratio fallback)
            
    if not acquired:
        os.close(lock_fd)
        logger.error(f"[C5-REAL FATAL] Swarm Deadlock: No se pudo adquirir {LOCK_FILE} tras {timeout}s.")
        raise TimeoutError("Swarm Git Lock Timeout: El índice está saturado de concurrencia.")
        
    try:
        logger.info("[C5-REAL] Swarm Lock adquirido. Dominio físico asegurado.")
        yield
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        logger.info("[C5-REAL] Swarm Lock liberado.")

