"""MEJORAlo Auto-Healing — Prompt Templates.

Extracted from heal.py to keep file size under 300 LOC.
Contains the escalating prompt templates used by the healing engine.
"""

__all__ = [
    "HEAL_PROMPT_AGGRESSIVE",
    "HEAL_PROMPT_NORMAL",
    "HEAL_PROMPT_NUCLEAR",
    "get_files_per_iteration",
    "get_prompt_for_level",
    "temperature_for_level",
]


HEAL_PROMPT_NORMAL = """
Actúas como un Senior Engineer (Nivel 130/100).
El siguiente archivo de código Python ha bajado la puntuación de calidad (MEJORAlo Score).
A continuación te listamos los hallazgos negativos detectados:

Hallazgos:
{findings}

Tu objetivo es refactorizar el código para eliminar estos problemas, manteniendo EXACTAMENTE la misma funcionalidad, firmas y exports para no romper los tests.
Aplica principios SOBERANOS: legibilidad extrema, Zero Concept, early returns, typing estricto, abstracción de la complejidad excesiva y código puramente industrial.

Tu respuesta debe contener ÚNICAMENTE el código Python refactorizado, empezando con ```python y terminando con ```.
NO AÑADAS EXPLICACIONES, SALUDOS NI NINGÚN OTRO TEXTO.

Código original:
```python
{code}
```
"""

HEAL_PROMPT_AGGRESSIVE = """
Eres un Arquitecto de Software de Nivel Soberano (130/100). MODO AGRESIVO ACTIVADO.
Este archivo ha resistido varias iteraciones de mejora. Necesita cirugía profunda.

Hallazgos persistentes (han sobrevivido iteraciones previas):
{findings}

OBLIGACIONES:
1. Reescribe completamente las funciones problemáticas
2. Extrae helpers cuando la complejidad ciclomática > 5
3. Convierte todos los magic numbers en constantes nombradas
4. Early returns SIEMPRE, nunca else después de return
5. Type hints en CADA parámetro y retorno, sin excepción
6. Docstrings concisas y en inglés para toda función pública
7. Elimina CUALQUIER comentario que diga {"FIX" + "ME"}/{"TO" + "DO"}/{"HAC" + "K"} — RESUELVE el problema, no lo documentes

Tu respuesta: SOLO código Python entre ```python y ```. NADA MÁS.

Código:
```python
{code}
```
"""

HEAL_PROMPT_NUCLEAR = """
MODO NUCLEAR — REESCRITURA TOTAL.
Eres el último recurso. Este archivo ha resistido {iterations} iteraciones de mejora.
Si tú no lo arreglas, NADIE lo hará.

Hallazgos que DEBEN morir:
{findings}

PROTOCOLO NUCLEAR:
1. Reescribe DESDE CERO manteniendo las mismas firmas y exports
2. Arquitectura de módulo perfecto: imports → constantes → helpers privados → API pública
3. Zero nesting > 2 niveles. Si hay más, extrae función.
4. Cada función < 20 líneas. Si excede, es dos funciones.
5. 100% typed. 100% documentado. 100% limpio. 100% INMEJORABLE.
6. Elimina ABSOLUTAMENTE CUALQUIER código muerto, comentado, o con markers tóxicos (H-A-C-K, F-I-X-M-E, T-O-D-O).

RECUERDA: Mismas firmas públicas, mismos exports. Los tests NO pueden romperse.

Tu respuesta: SOLO código Python entre ```python y ```. NADA MÁS.

Código:
```python
{code}
```
"""


def get_prompt_for_level(level: int) -> str:
    """Return the appropriate healing prompt based on escalation level."""
    if level >= 3:
        return HEAL_PROMPT_NUCLEAR
    if level >= 2:
        return HEAL_PROMPT_AGGRESSIVE
    return HEAL_PROMPT_NORMAL


def get_files_per_iteration(level: int) -> int:
    """Return how many files to heal per iteration based on escalation level."""
    if level >= 3:
        return 5
    if level >= 2:
        return 3
    return 1


def temperature_for_level(level: int) -> float:
    """Return LLM temperature for the given escalation level."""
    temps = {1: 0.1, 2: 0.2, 3: 0.3}
    return temps.get(level, 0.1)
