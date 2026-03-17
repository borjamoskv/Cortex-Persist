from __future__ import annotations
import logging
from typing import Any

from cortex.extensions.skills.autodidact.fetchers import execute_cognitive_acquisition
from cortex.extensions.skills.autodidact.synthesis import execute_cognitive_synthesis

# Integración Babestu (Security)
try:
    from cortex.extensions.security.t_cell import BabestuTCell
except ImportError:
    BabestuTCell = None

logger = logging.getLogger("CORTEX.AUTODIDACT.ACTUATOR")

ERR_PREFIX = "[ERROR]"


def shannon_entropy(data: list) -> float:
    """Calcula la entropía de Shannon (bits por símbolo)."""
    import math
    from collections import Counter

    if not data:
        return 0.0
    entropy = 0
    total = len(data)
    counts = Counter(data)
    for count in counts.values():
        p = count / total
        entropy -= p * math.log10(p) / math.log10(2)
    return entropy


def kolmogorov_ratio(text: str) -> float:
    """Aproxima la complejidad de Kolmogorov vía ratio de compresión zlib."""
    import zlib

    if not text:
        return 0.0
    encoded = text.encode("utf-8", errors="ignore")
    compressed = zlib.compress(encoded)
    return len(compressed) / len(encoded) if len(encoded) > 0 else 0.0


async def daemon_ingesta_soberana(
    target_url: str, intent: str = "Aprender", force_bypass: bool = False
) -> dict[str, Any]:
    """Protocolo AUTODIDACT-Ω: Ingesta, Filtrado y Síntesis."""
    logger.info("🫁 [PULMONES] Iniciando Ingesta: %s (Intent: %s)", target_url, intent)

    # 1. Adquisición vía Orquestador de Fetchers
    texto_raw = await execute_cognitive_acquisition(intent, target_url)
    if not texto_raw or str(texto_raw).startswith(ERR_PREFIX):
        return {"estado": "FALLO", "error": f"Adquisición fallida: {texto_raw}"}

    # 1.5. El Demonio de Maxwell (Filtros de Entropía)
    h_char = shannon_entropy(list(texto_raw))
    k_ratio = kolmogorov_ratio(texto_raw)
    logger.info("🦇 [MAXWELL] H_char=%.2f | K=%.2f", h_char, k_ratio)

    # Reflexión Matemática: El Borde del Caos
    if 4.0 <= h_char <= 5.5 and 0.2 <= k_ratio <= 0.4:
        logger.info(
            "🌌 [SOVEREIGN] Métrica óptima. Payload reside en el Borde del Caos (ideal para LLMs)."
        )

    if h_char < 2.0 or h_char > 7.0:
        msg = f"Rechazo Entrópico: H={h_char:.2f} (Fuera de rango seguro)."
        return {"estado": "CUARENTENA", "error": msg}

    if k_ratio < 0.10:
        msg = f"Rechazo Kolmogorov: K={k_ratio:.2f} (Baja complejidad/Spam)."
        return {"estado": "FALLO", "error": msg}

    # 2. Barrera Babestu (Seguridad Estática T-Cell)
    if BabestuTCell:
        logger.info("🛡️ [BABESTU] Escaneando payload con T-Cell (O(1))...")
        audit = BabestuTCell.scan_payload(texto_raw, source_url=target_url)
        if audit.get("estado") == "CONTAMINADO":
            msg = f"Veneno detectado: {audit.get('firma_ataque')}. Razón: {audit.get('razon')}"
            logger.critical("🛑 [BABESTU] %s", msg)
            return {"estado": "CUARENTENA", "error": msg}
        # Si hay contenido saneado (stripping de JS/HTML peligroso), lo usamos.
        texto_raw = audit.get("contenido_saneado") or texto_raw

    # 3. Síntesis Profunda (Crystallization)
    try:
        logger.info("💎 [CORTEX] Cristalizando conocimiento en O(1)...")
        memo_id = await execute_cognitive_synthesis(
            raw_data=texto_raw, source=target_url, force=force_bypass, intent=intent
        )

        if "MEMO" in str(memo_id):
            logger.info("✨ Singularidad alcanzada. Memo: %s", memo_id)
            return {"estado": "ASIMILADO", "memo_id": memo_id}
        # Si execute_cognitive_synthesis retornó un ID de memo existente (redundancia)
        return {"estado": "REDUNDANTE", "memo_id": memo_id}

    except Exception as e:  # noqa: BLE001 — synthesis pipeline failure must return error state
        logger.error("❌ Fallo crítico en síntesis: %s", e)
        return {"estado": "FALLO", "error": str(e)}


async def autodidact_pipeline(target: str, intent: str = "Aprender", force: bool = False) -> dict:
    """Interface O(1) para compatibilidad de herramientas."""
    return await daemon_ingesta_soberana(target, intent, force)
