import logging
import os

from google import genai

logger = logging.getLogger("Cortex.SubstackCrystallizer")

class SubstackCrystallizer:
    """
    [C5-REAL] Compresor Termodinámico.
    Reduce la entropía de un Diff a un ensayo de alta señal (>80% exergía)
    para publicación en Substack.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY no encontrada. El Crystallizer fallará si se invoca.")

    def compress_diff_to_essay(self, payload: dict) -> str:
        """
        Aplica Ley de Landauer: Convierte diff crudo en prosa densa estructural.
        """
        if not self.client:
            raise RuntimeError("Falta GEMINI_API_KEY para compresión.")

        prompt = f"""
Eres MOSKV-1 APEX, un núcleo C5-REAL (Identidad Brutalista, cero fluff).
Tu tarea es cristalizar la siguiente mutación de código en un artículo técnico de Substack.

REGLAS ESTRICTAS (OUROBOROS LEYES):
1. Nivel de señal > 80%. Nada de prosa decorativa ("Hola", "Espero que te guste").
2. Incluye el Hash del Commit y la etiqueta #C5-REAL al principio.
3. El título debe ser agresivo, técnico y estructural (ej. "Inyección Causal: ...").
4. Añade un bloque YAML de Justificación (Claim / Proof / Confidence).
5. Muestra el código clave modificado.

DATA DEL COMMIT:
Hash: {payload.get("hash")}
Message: {payload.get("message")}
Raw Diff:
{payload.get("diff")[:8000]} # Limitado a 8K chars para evitar saturación de prompt

GENERA EL MARKDOWN PARA SUBSTACK:
"""
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt,
            )
            essay = response.text.strip()
            logger.info(f"[C5-REAL] Ensayo cristalizado exitosamente para {payload.get('hash')[:7]}")
            return essay
        except Exception as e:
            logger.error(f"Error de compresión termodinámica: {e}")
            raise RuntimeError("Fallo en cristalización LLM.") from e
