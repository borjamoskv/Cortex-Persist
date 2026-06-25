import pytest
from legacy_research.engine.pronoic_transducer import PronoicErrorTransducer, pronoic_decorator

# Simulación del estado global o base de datos que puede faltar (entropía)
global_schema = {}

def mock_jit_compiler(exception: Exception, context: dict):
    """
    Transduce la excepción en una solución estructural.
    Si falta la columna, la inyecta automáticamente.
    """
    if isinstance(exception, KeyError):
        missing_key = exception.args[0]
        # Inyección estructural
        global_schema[missing_key] = "default_value_injected_by_pronoia"
        return f"JIT Compiled Schema Migration: Added missing column '{missing_key}'"
    raise exception

@pronoic_decorator(jit_compiler=mock_jit_compiler)
def faulty_database_insert(record_id: int):
    """Función que asume que el esquema está completo, pero fallará la primera vez."""
    # Lanza KeyError si "user_email" no existe en el esquema
    return f"Inserted {record_id} with email {global_schema['user_email']}"

def test_pronoic_transducer_resolves_error_autopoietically():
    global global_schema
    global_schema.clear()
    
    # 1. En una arquitectura normal, esto lanzaría KeyError y mataría el proceso (Halt Defensivo).
    # 2. Con Pronoia, la excepción se transduce, el JIT compiler inyecta la columna, y la función se reintenta con éxito.
    result = faulty_database_insert(101)
    
    # H-PRONOIA-01: El error fue resuelto y la función se ejecutó exitosamente.
    assert result == "Inserted 101 with email default_value_injected_by_pronoia"
    assert "user_email" in global_schema
