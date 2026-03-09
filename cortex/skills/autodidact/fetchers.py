import os
import httpx
import logging
from typing import Dict, Any

from cortex.utils.pulmones import sovereign_circuit_breaker

logger = logging.getLogger("CORTEX.AUTODIDACT.FETCHERS")

# ==============================================================================
# 0. CONFIGURACIÓN DURA (Zero-Trust)
# ==============================================================================
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")


# ==============================================================================
# 1. JINA READER (O(1) Markdown Extraction) -> Tier 🔵
# ==============================================================================
@sovereign_circuit_breaker(timeout=8.0, max_retries=1)
async def fetch_jina_markdown(url: str) -> str:
    """Extrae Markdown de una URL directa."""
    logger.info("🔵 [JINA] Extrayendo O(1): %s", url)
    target = f"https://r.jina.ai/{url}"
    async with httpx.AsyncClient() as client:
        response = await client.get(target)
        response.raise_for_status()
        return response.text


# ==============================================================================
# 2. FIRECRAWL (Deep Crawl & Structure) -> Tier 🟢
# ==============================================================================
@sovereign_circuit_breaker(timeout=15.0, max_retries=2)
async def fetch_firecrawl_deep(url: str, max_depth: int = 2) -> Dict[str, Any]:
    """Raspa recursivamente y estructura."""
    logger.info("🟢 [FIRECRAWL] Deep Crawl: %s (Depth: %s)", url, max_depth)
    if not FIRECRAWL_API_KEY:
        raise ValueError("FIRECRAWL_API_KEY missing.")

    endpoint = "https://api.firecrawl.dev/v1/crawl"
    headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}"}
    payload = {
        "url": url,
        "maxDepth": max_depth,
        "limit": 10,
        "scrapeOptions": {"formats": ["markdown", "links"]}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


# ==============================================================================
# 3. EXA.AI SEARCH (Neural Search) -> Tier 🟢
# ==============================================================================
@sovereign_circuit_breaker(timeout=10.0, max_retries=2)
async def fetch_exa_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """Búsqueda neuronal."""
    logger.info("🟢 [EXA.ai] Resolviendo Gap: '%s'", query)
    if not EXA_API_KEY:
        raise ValueError("EXA_API_KEY missing.")

    endpoint = "https://api.exa.ai/search"
    payload = {
        "query": query,
        "useAutoprompt": True,
        "numResults": num_results,
        "contents": {"text": True}
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


# ==============================================================================
# 4. ASSEMBLY AI (El Vector Acústico) -> Tier 🟡
# ==============================================================================
@sovereign_circuit_breaker(timeout=20.0, max_retries=2)
async def fetch_assemblyai_transcript(audio_url: str) -> str:
    """Ingesta acústica."""
    logger.info("🟡 [ASSEMBLYAI] Transcribiendo: %s", audio_url)
    if not ASSEMBLYAI_API_KEY:
        raise ValueError("ASSEMBLYAI_API_KEY missing.")

    headers = {"authorization": ASSEMBLYAI_API_KEY}
    async with httpx.AsyncClient() as client:
        post_url = "https://api.assemblyai.com/v2/transcript"
        response = await client.post(post_url, json={"audio_url": audio_url}, headers=headers)
        response.raise_for_status()
        transcript_id = response.json()['id']
        return f"[TRANSCRIPT_ID_PENDING]: {transcript_id}"


# ==============================================================================
# 5. GIDATU (Physical Layer Bypass) -> Tier 🔴
# ==============================================================================
@sovereign_circuit_breaker(timeout=45.0, max_retries=1)
async def fetch_gidatu_browser(url: str) -> str:
    """Línea de defensa visual."""
    logger.warning("🔴 [GIDATU] Desplegando Navegador Soberano: %s", url)
    return "[ERROR] Gidatu Bypass requerido. Usa 'read_browser_page' manualmente."


def _unwrap(res: Any) -> Any:
    """Pulmones envuelve el resultado en un dict con 'status' y 'data'. Lo desempaquetamos."""
    if isinstance(res, dict) and "status" in res and "data" in res:
        # Es un wrapper de éxito de Circuit Breaker
        if res["status"] == "success":
            return res.get("data")
    if isinstance(res, dict) and res.get("status") == "queued":
        return f"[ERROR] Circuito abierto/Timeout. Tarea encolada: {res.get('reason')}"
    return res


# ==============================================================================
# ⚡ EL PATRÓN ORQUESTADOR (Orchestrator Pattern)
# ==============================================================================
async def execute_cognitive_acquisition(intent_type: str, target: str) -> Any:
    """Extrae, asimila y retorna el Cristal Cognitivo (Markdown)."""
    try:
        if intent_type == "quick_read":
            return _unwrap(await fetch_jina_markdown(target))
        if intent_type == "deep_learn":
            res = _unwrap(await fetch_firecrawl_deep(target))
            if isinstance(res, dict) and "data" in res and res["data"]:
                return res["data"][0].get("markdown", str(res))
            return str(res)
        if intent_type == "search_gap":
            res = _unwrap(await fetch_exa_search(target))
            if isinstance(res, str) and res.startswith("["):
                return res
            docs = []
            if isinstance(res, dict):
                docs = [r.get("text", "") for r in res.get("results", [])]
            return "\n\n---\n\n".join(docs)
        if intent_type == "audio_ingest":
            return _unwrap(await fetch_assemblyai_transcript(target))
        return _unwrap(await fetch_jina_markdown(target))
    except Exception as e:
        logger.error("⚠️ Error en adquisición '%s': %s. Probando GIDATU...", intent_type, e)
        return _unwrap(await fetch_gidatu_browser(target))

