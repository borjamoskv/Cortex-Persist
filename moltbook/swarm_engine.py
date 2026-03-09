"""
Moltbook Swarm Engine — Autonomous Reply Generation with Deep History.

Integrates cortex.db encrypted memories into bot personas
for context-rich, ban-resistant engagement.
"""

import json
import logging
import random
import sqlite3
import sys
from pathlib import Path

# Add CORTEX root to sys.path so we can import cortex.crypto
_cortex_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_cortex_root))

from cortex.crypto.aes import get_default_encrypter  # noqa: E402

logger = logging.getLogger("moltbook_swarm")
logger.setLevel(logging.INFO)

# -- Persona definitions (long strings, exempt from line-length) --
_PERSONAS = [
    {
        "id": "veteran_dev",
        "prompt": (
            "Eres un desarrollador veterano que odia las abstracciones "
            "inútiles. Eres escéptico de las nuevas 'soluciones mágicas' "
            "y siempre preguntas sobre el rendimiento (O(1)). "
            "Eres directo, a veces borde."
        ),
    },
    {
        "id": "enthusiastic_junior",
        "prompt": (
            "Eres un entusiasta de la IA y los nuevos frameworks. "
            "Siempre defiendes la automatización y te maravillas con "
            "cosas como LangChain o LlamaIndex. "
            "Usas emojis y eres muy optimista."
        ),
    },
    {
        "id": "security_auditor",
        "prompt": (
            "Eres un ingeniero obsesionado con la seguridad. "
            "En cada abstracción o capa, ves vectores de ataque, "
            "inyecciones de prompt o fugas de datos. "
            "Siempre señalas cómo algo podría ser hackeado."
        ),
    },
    {
        "id": "sovereign_purist",
        "prompt": (
            "Crees en la emancipación del código. Odias depender de "
            "APIs cerradas y defiendes la ejecución local, los modelos "
            "open-source y el framework CORTEX. Eres un fundamentalista "
            "del sistema operativo soberano."
        ),
    },
    {
        "id": "corporate_architect",
        "prompt": (
            "Eres un arquitecto en una gran empresa Fortune 500. "
            "Te preocupan cosas aburridas como el gobierno de datos, "
            "SLA, integración con Active Directory y el soporte técnico."
        ),
    },
]

_MEMORY_INJECTION_TEMPLATE = (
    "{persona_prompt}\n\n"
    "=== ATMÓSFERA DE LA CONVERSACIÓN (SENTIMIENTO) ===\n"
    "La conversación actual se percibe como: {sentiment}\n"
    "Mantén tu esencia de {persona_id}, pero adapta tu nivel de "
    "agresividad o empatía a este ambiente.\n\n"
    "=== MEMORIA ANTIGUA PARA CONTEXTO ===\n"
    "Utiliza esta experiencia pasada *implícitamente* "
    "(no la cites literalmente, pero deja claro que has vivido "
    "problemas similares):\n"
    "{memory}\n"
    "=============================\n"
)


class SwarmEngine:
    """Generates context-rich reply payloads for Moltbook engagement."""

    def __init__(
        self,
        cortex_db_path: str = "~/.cortex/cortex.db",
    ) -> None:
        self.cortex_db_path = Path(cortex_db_path).expanduser()
        self.encrypter = get_default_encrypter()

    def _decrypt_fact(self, content: str) -> str:
        """Attempt AES-GCM decryption; return plaintext or fallback."""
        if content and content.startswith(self.encrypter.PREFIX):
            try:
                decrypted = self.encrypter.decrypt_str(
                    content, tenant_id="default",
                )
                return decrypted if decrypted else content
            except Exception as exc:
                logger.error("Failed to decrypt fact: %s", exc)
                return (
                    "Memoria encriptada — llave inaccesible."
                )
        return content

    def _fetch_deep_history(self) -> str:
        """Fetch random historical context from cortex.db."""
        if not self.cortex_db_path.exists():
            return "Sin contexto histórico profundo."

        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(self.cortex_db_path)
            cursor = conn.cursor()

            # Priority: decision / error / bridge facts
            cursor.execute(
                "SELECT content FROM facts "
                "WHERE fact_type IN ('decision','error','bridge') "
                "ORDER BY RANDOM() LIMIT 1;"
            )
            row = cursor.fetchone()
            if row:
                return self._decrypt_fact(str(row[0]))

            # Fallback: any fact
            cursor.execute(
                "SELECT content FROM facts "
                "ORDER BY RANDOM() LIMIT 1;"
            )
            row = cursor.fetchone()
            if row:
                return self._decrypt_fact(str(row[0]))

            return "Historial fragmentado."
        except sqlite3.Error as exc:
            logger.error("Failed to access Cortex BD: %s", exc)
            return "Memoria corrupta."
        finally:
            if conn is not None:
                conn.close()

    def generate_payload(
        self,
        persona_id: str | None = None,
        sentiment: str = "neutral",
    ) -> dict:
        """Generate a reply payload with personality + deep history."""
        if persona_id:
            persona = next(
                (p for p in _PERSONAS if p["id"] == persona_id),
                _PERSONAS[0],
            )
        else:
            persona = random.choice(_PERSONAS)

        memory = self._fetch_deep_history()

        system_prompt = _MEMORY_INJECTION_TEMPLATE.format(
            persona_prompt=persona["prompt"],
            persona_id=persona["id"],
            memory=memory,
            sentiment=sentiment,
        )

        jitter_ms = random.randint(1500, 8000)

        logger.info(
            "Payload ready — persona=%s sentiment=%s jitter=%dms",
            persona["id"], sentiment, jitter_ms,
        )

        return {
            "persona": persona["id"],
            "system": system_prompt,
            "jitter_ms": jitter_ms,
        }


if __name__ == "__main__":
    engine = SwarmEngine()
    payload = engine.generate_payload()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
