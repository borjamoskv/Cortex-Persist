# [C5-REAL] Exergy-Maximized
"""
Vesicular Runtime (Apoptosis OS-Level)
Pilar 7 del Manifiesto C5-REAL: Destrucción de la memoria en espacio OS.
Bloquea de manera agresiva el acceso a las variables de entorno para forzar Keyring.
"""

import logging
import os
import signal

logger = logging.getLogger("babylon60.security.vesicular_runtime")

_original_environ_get = os.environ.get
_original_environ_getitem = os.environ.__class__.__getitem__

FORBIDDEN_SUFFIXES = ("_API_KEY", "_SECRET", "_TOKEN")
FORBIDDEN_EXACT = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")

class VesicularRuntime:
    """
    Escudo BFT contra la fuga biológica de secretos (P095 / P100).
    Patchea el módulo `os` para detonar una muerte instantánea a nivel de OS (SIGKILL)
    si el Kernel intenta leer un secreto en crudo en lugar de invocar al gestor cifrado.
    """
    
    _is_enforced = False

    @classmethod
    def enforce(cls):
        """Activa el Vesicular Runtime. Irreversible."""
        if cls._is_enforced:
            return
            
        logger.warning("🛡️ VESICULAR RUNTIME: ENGAGED. OS-Level Apoptosis is active.")

        def _guarded_get(env_self, key, default=None):
            cls._check_key(key)
            # _original_environ_get was a bound method, so we don't pass env_self
            return _original_environ_get(key, default)

        def _guarded_getitem(env_self, key):
            cls._check_key(key)
            return _original_environ_getitem(env_self, key)

        os.environ.get = _guarded_get.__get__(os.environ)
        os.environ.__class__.__getitem__ = _guarded_getitem
        
        cls._is_enforced = True

    @classmethod
    def _check_key(cls, key: str):
        """Audita el acceso. Si es ilícito, dispara la Apoptosis (SIGKILL)."""
        key_upper = str(key).upper()
        if key_upper in FORBIDDEN_EXACT or any(key_upper.endswith(sfx) for sfx in FORBIDDEN_SUFFIXES):
            logger.critical(
                "💀 VESICULAR RUNTIME: Acceso ilícito a `%s`. "
                "Pilar 7 violado (os.environ). Iniciando OS Apoptosis (SIGKILL).",
                key
            )
            # Obliteración estructural directa. Sin pasar por garbage collector.
            os.kill(os.getpid(), signal.SIGKILL)
