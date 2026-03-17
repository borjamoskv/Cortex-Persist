import asyncio
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class SovereignTriad:
    """
    [SOVEREIGN TRIAD] - AETHER COGNITIVE APIS
    - Jina AI: Extracción web instantánea a Markdown. (Neutraliza entropía HTML).
    - Exa.ai: Búsqueda Semántica Neuronal. (Comprensión profunda, zero keyword-matching).
    - Braintrust: Telemetría RLHF & Observabilidad. (Axioma 3: Zero Trust, todo medido).

    Reglas de Combate (O(1)):
    - Timeouts estrictos (red variable = entropía).
    - No hay 'except Exception'. Fallos específicos.
    - Zero librerías hinchadas (Langchain). Puras peticiones httpx.
    """

    def __init__(self):
        self.jina_key = os.getenv("JINA_API_KEY", "")
        self.exa_key = os.getenv("EXA_API_KEY", "")
        self.braintrust_key = os.getenv("BRAINTRUST_API_KEY", "")
        self.firecrawl_key = os.getenv("FIRECRAWL_API_KEY", "")
        # Tiempos de colapso - la Red no tiene paciencia.
        self.timeout_s = 15.0

    async def extract_url_jina(self, target_url: str) -> str:
        """
        [J&iacute;na AI] Consume cualquier URL y devuelve Markdown puro.
        Funda los límites del HTML basura que agota tokens.
        """
        if not target_url.startswith("http"):
            target_url = "https://" + target_url

        url = f"https://r.jina.ai/{target_url}"
        headers = {}
        if self.jina_key:
            headers["Authorization"] = f"Bearer {self.jina_key}"

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                logger.error(
                    "JINA HTTP Error collapsando '%s': %s", target_url, e.response.status_code
                )
                return f"[ERROR] Ingesta fallida (Status {e.response.status_code})"
            except httpx.RequestError as e:
                logger.error("JINA Request Timeout/Fail en '%s': %s", target_url, str(e))
                return "[ERROR] Falla estructural (Red/Timeout) durante la Ingesta."

    async def extract_url_firecrawl(self, target_url: str) -> str:
        """
        [Firecrawl] Extracción profunda a Markdown. Usa para ingestas pesadas.
        """
        if not self.firecrawl_key:
            return "[ERROR] FIRECRAWL_API_KEY no detectada."

        url = "https://api.firecrawl.dev/v0/scrape"
        headers = {"Authorization": f"Bearer {self.firecrawl_key}"}
        payload = {"url": target_url, "formats": ["markdown"]}

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get("success") and "markdown" in data.get("data", {}):
                    return data["data"]["markdown"]
                return "[ERROR] Firecrawl incompleto o bloqueado por JS."
            except httpx.HTTPStatusError as e:
                return f"[ERROR] Firecrawl Status {e.response.status_code}"
            except httpx.RequestError as e:
                return f"[ERROR] Firecrawl Fallo de red: {str(e)}"

    async def extract_url_exa(self, target_url: str) -> str:
        """
        [Exa.ai] Fallback táctico vía Search API. Si un Firewall (Cloudflare) bloquea
        la extracción directa, recuperamos el contenido directamente del índice neuronal de Exa.
        """
        if not self.exa_key:
            return "[ERROR] EXA_API_KEY no detectada."

        url = "https://api.exa.ai/contents"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.exa_key,
        }
        payload = {"urls": [target_url], "text": True}

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                resultados = data.get("results", [])
                if resultados:
                    raw = resultados[0].get("text")
                    if raw:
                        return raw
                    return "[ERROR] Exa: Contenido indexado vacío."
                return "[ERROR] Exa: URL no indexada o bloqueada."
            except httpx.HTTPStatusError as e:
                return f"[ERROR] Exa Status {e.response.status_code}"
            except httpx.RequestError as e:
                return f"[ERROR] Exa Fallo de red: {str(e)}"

    async def neural_search_exa(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        """
        [Exa.ai] Caza semántica. Pide contexto como un ser humano, recupera nodos precisos.
        """
        if not self.exa_key:
            logger.warning("EXA_API_KEY no detectada. Retornando vacío.")
            return []

        url = "https://api.exa.ai/search"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.exa_key,
        }
        payload = {
            "query": query,
            "useAutoprompt": True,
            "numResults": num_results,
            # Se puede añadir "contents": {"text": True, "highlights": True} para obtener snippets
            "contents": {"text": True},
        }

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])
            except httpx.HTTPStatusError as e:
                logger.error("EXA Neural Search truncado: %s", e.response.status_code)
                return []
            except httpx.RequestError as e:
                logger.error("EXA Neural Search Fallo de Red: %s", str(e))
                return []

    async def log_braintrust_trace(
        self,
        project_name: str,
        span_name: str,
        input_data: Any,
        output_data: Any,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        [Braintrust] Telemetría silenciosa. Axioma 3: Mide la ejecución. Graba inputs/outputs para RLHF futuro.
        Requiere Braintrust REST API o el braintrust SDK.
        Lo hacemos vía REST puro para mantener dependencia cero.
        """
        if not self.braintrust_key:
            logger.warning("BRAINTRUST_API_KEY no detectada. Skipeando telémetría.")
            return False

        # Endpoint asumiendo el estándar de ingest de Braintrust (simplificado para el script O(1))
        # Nota: Braintrust recomienda usar su SDK, pero para trazas ligeras HTTP puro sirve.
        # Generalmente, necesitas crear un experimento primero, pero podemos loggear eventos a un proyecto.
        url = "https://api.braintrustdata.com/v1/log"
        headers = {
            "Authorization": f"Bearer {self.braintrust_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "project_name": project_name,
            "events": [
                {
                    "name": span_name,
                    "input": input_data,
                    "output": output_data,
                    "metadata": metadata or {},
                }
            ],
        }

        async with httpx.AsyncClient(timeout=self.timeout_s * 2) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                logger.info("Braintrust logeado en O(1) - %s", span_name)
                return True
            except httpx.HTTPStatusError as e:
                logger.error("Braintrust fallo telemetría: %s", e.response.status_code)
                return False
            except httpx.RequestError as e:
                logger.error("Braintrust Timeout de red: %s", str(e))
                return False


# =====================================================================
# EJECUCIÓN TÁCTICA (TEST INDIVIDUAL)
# =====================================================================
if __name__ == "__main__":

    async def run_triad_test():
        triad = SovereignTriad()

        print("--- 1. Test Jina Extract ---")
        jina_res = await triad.extract_url_jina("https://news.ycombinator.com")
        print(f"Jina: {len(jina_res)} chars recibidos. Preview: {jina_res[:100]}...\n")

        print("--- 2. Test Exa Search ---")
        exa_res = await triad.neural_search_exa(
            "best python agentic frameworks 2026", num_results=2
        )
        print(f"Exa: Encontrados {len(exa_res)} nodos.\n")

        print("--- 3. Test Braintrust Telemetry ---")
        # braintrust_res = await triad.log_braintrust_trace("Aether-Agent-Test", "Test Run", "hello", "world")
        # print(f"Braintrust Log Status: {braintrust_res}")
        print("Braintrust no comprobado en este script local para evitar ruido.\n")

    asyncio.run(run_triad_test())
