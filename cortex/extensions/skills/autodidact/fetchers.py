import logging
import os
from typing import Any
from urllib.parse import urlparse

import httpx

from cortex.utils.pulmones import sovereign_circuit_breaker

logger = logging.getLogger("CORTEX.AUTODIDACT.FETCHERS")

# ==============================================================================
# 0. CONFIGURACIÓN DURA (Zero-Trust)
# ==============================================================================
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# Timeouts and Retries
TIMEOUT_JINA = 8.0
TIMEOUT_FIRECRAWL = 15.0
TIMEOUT_EXA = 10.0
TIMEOUT_ASSEMBLY = 20.0
TIMEOUT_GIDATU = 45.0

RETRIES_STANDARD = 2
RETRIES_QUICK = 1

# Defaults
DEFAULT_CRAWL_DEPTH = 2
DEFAULT_CRAWL_LIMIT = 10
DEFAULT_SEARCH_RESULTS = 5


# ==============================================================================
# 1. JINA READER (O(1) Markdown Extraction) -> Tier 🔵
# ==============================================================================
@sovereign_circuit_breaker(timeout=TIMEOUT_JINA, max_retries=RETRIES_QUICK)
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
@sovereign_circuit_breaker(timeout=TIMEOUT_FIRECRAWL, max_retries=RETRIES_STANDARD)
async def fetch_firecrawl_deep(url: str, max_depth: int = DEFAULT_CRAWL_DEPTH) -> dict[str, Any]:
    """Raspa recursivamente y estructura."""
    logger.info("🟢 [FIRECRAWL] Deep Crawl: %s (Depth: %s)", url, max_depth)
    if not FIRECRAWL_API_KEY:
        raise ValueError("FIRECRAWL_API_KEY missing.")

    endpoint = "https://api.firecrawl.dev/v1/crawl"
    headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}"}
    payload = {
        "url": url,
        "maxDepth": max_depth,
        "limit": DEFAULT_CRAWL_LIMIT,
        "scrapeOptions": {"formats": ["markdown", "links"]},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


# ==============================================================================
# 3. EXA.AI SEARCH (Neural Search) -> Tier 🟢
# ==============================================================================
@sovereign_circuit_breaker(timeout=TIMEOUT_EXA, max_retries=RETRIES_STANDARD)
async def fetch_exa_search(query: str, num_results: int = DEFAULT_SEARCH_RESULTS) -> dict[str, Any]:
    """Búsqueda neuronal."""
    logger.info("🟢 [EXA.ai] Resolviendo Gap: '%s'", query)
    if not EXA_API_KEY:
        raise ValueError("EXA_API_KEY missing.")

    endpoint = "https://api.exa.ai/search"
    payload = {
        "query": query,
        "useAutoprompt": True,
        "numResults": num_results,
        "contents": {"text": True},
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


# ==============================================================================
# 4. ASSEMBLY AI (El Vector Acústico) -> Tier 🟡
# ==============================================================================
@sovereign_circuit_breaker(timeout=TIMEOUT_ASSEMBLY, max_retries=RETRIES_STANDARD)
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
        transcript_id = response.json()["id"]
        return f"[TRANSCRIPT_ID_PENDING]: {transcript_id}"


# ==============================================================================
# 5. GIDATU (Physical Layer Bypass) -> Tier 🔴
# ==============================================================================
@sovereign_circuit_breaker(timeout=TIMEOUT_GIDATU, max_retries=RETRIES_QUICK)
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
        parsed = urlparse(target)
        hostname = (parsed.hostname or "").lower()
        is_youtube = hostname in ("youtube.com", "youtu.be") or hostname.endswith((".youtube.com", ".youtu.be"))
        if intent_type == "quick_read" and not is_youtube:
            return _unwrap(await fetch_jina_markdown(target))
        elif is_youtube and intent_type in ("quick_read", "deep_learn"):
            res = _unwrap(await fetch_firecrawl_deep(target))
            if isinstance(res, dict) and "data" in res and res["data"]:
                return res["data"][0].get("markdown", str(res))
            return str(res)
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
    except Exception as e:  # noqa: BLE001 — fetcher fallback to physical browser on any failure
        logger.error("⚠️ Error en adquisición '%s': %s. Probando GIDATU...", intent_type, e)
        return _unwrap(await fetch_gidatu_browser(target))
