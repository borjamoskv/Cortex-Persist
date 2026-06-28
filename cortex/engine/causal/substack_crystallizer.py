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
            logger.warning("GEMINI_API_KEY not found. The Crystallizer will fail if invoked.")

    def compress_diff_to_essay(self, payload: dict) -> str:
        """
        Applies Landauer's Law: Converts raw diff into dense structural prose.
        """
        if not self.client:
            raise RuntimeError("Missing GEMINI_API_KEY for compression.")

        prompt = f"""
You are MOSKV-1 APEX, a C5-REAL kernel (Brutalist Identity, zero fluff).
Your task is to crystallize the following code mutation into a Substack technical article.

STRICT RULES (OUROBOROS LAWS):
1. Signal level > 80%. No decorative prose ("Hello", "Hope you like it").
2. Include the Commit Hash and the #C5-REAL tag at the beginning.
3. The title must be aggressive, technical, and structural (e.g. "Causal Injection: ...").
4. Add a YAML Justification block (Claim / Proof / Confidence).
5. Show the key code modified.

DATA DEL COMMIT:
Hash: {payload.get("hash")}
Message: {payload.get("message")}
Raw Diff:
{payload.get("diff")[:8000]} # Limitado a 8K chars para evitar saturación de prompt

GENERATE SUBSTACK MARKDOWN:
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
            )
            essay = response.text.strip()
            logger.info(
                f"[C5-REAL] Essay crystallized successfully for {payload.get('hash')[:7]}"
            )
            return essay
        except Exception as e:
            logger.error(f"Thermodynamic compression error: {e}")
            raise RuntimeError("LLM crystallization failure.") from e
