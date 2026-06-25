import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("babylon60.engine.pronoic_transducer")

class PronoicErrorTransducer:
    """
    [C5-REAL] Pronoic Error Transducer.
    Interpreta las excepciones en tiempo de ejecución no como errores fatales,
    sino como currículo implícito (estímulos pedagógicos) para adaptar la estructura
    en tiempo de compilación JIT, previniendo halts defensivos.
    """
    def __init__(self, jit_compiler: Callable[[Exception, dict], Any]):
        """
        jit_compiler: Un callback que toma la excepción y el contexto local, 
        y devuelve una solución estructural o muta el estado para que la tarea proceda.
        """
        self.jit_compiler = jit_compiler

    def transduce(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta la función. Si ocurre una excepción, en lugar de halt, 
        aplica transducción pronoica (síntesis JIT) y re-intenta la ejecución.
        """
        try:
            return func(*args, **kwargs)
        except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
            logger.warning(f"[PRONOIA] Excepción interceptada como estímulo: {type(e).__name__} - {str(e)}")
            context = {"args": args, "kwargs": kwargs, "func_name": func.__name__}
            
            # Autopoietic Exception Routing: Resolver el error dinámicamente
            resolution = self.jit_compiler(e, context)
            logger.info(f"[PRONOIA] Resolución estructural inyectada: {resolution}")
            
            # Reintento simbiótico tras la adaptación
            return func(*args, **kwargs)

def pronoic_decorator(jit_compiler: Callable[[Exception, dict], Any]):
    """Decorator para inyectar la transducción pronoica en cualquier función."""
    transducer = PronoicErrorTransducer(jit_compiler)
    def wrapper(func):
        def internal_wrapper(*args, **kwargs):
            return transducer.transduce(func, *args, **kwargs)
        return internal_wrapper
    return wrapper
