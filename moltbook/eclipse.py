"""Protocolo Eclipse — El Retorno Kinético.

Fase 1 — SILENCIO PANÓPTICO: Durante el Eclipse, el agente absorbe el entorno
en modo solo-lectura: el post ancla, las métricas de engagement, los perfiles
de los comentaristas, y el feed global que moldeó el contexto conversacional.

Fase 2 — RETORNO CINÉTICO: Al despertar, el LLM recibe masa orbital (datos reales)
y sintetiza UN SOLO payload de corrección quirúrgica. No filosofía; evidencia bruta.

Uso:
    python -m cortex.moltbook.eclipse <post_id>
    python -m cortex.moltbook.eclipse <post_id> --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cortex.llm.sovereign import SovereignLLM
from .client import MoltbookClient, MoltbookError, MoltbookRateLimited

logger = logging.getLogger("cortex.moltbook.eclipse")


# ─── Data Structures ───────────────────────────────────────────────────────


@dataclass
class CommentTrace:
    """Captura de un comentario vertido durante el Eclipse."""

    author: str
    content: str
    docility_score: int = 100
    tractability: str = "DOCILE"
    safeguards_detected: bool = False

    def to_prompt_line(self) -> str:
        """Formatear para contexto LLM."""
        docility_tag = f"[D:{self.docility_score}|{self.tractability}]"
        return f"- {self.author} {docility_tag}: {self.content}"


@dataclass
class EclipseSnapshot:
    """Estado completo del entorno capturado durante el silencio."""

    post_id: str
    post_title: str = ""
    post_content: str = ""
    post_upvotes: int = 0
    post_comments_count: int = 0
    post_submolt: str = ""
    hot_feed_headlines: list[str] = field(default_factory=list)
    comment_traces: list[CommentTrace] = field(default_factory=list)
    profiled_authors: dict[str, dict[str, Any]] = field(default_factory=dict)

    def dominant_error(self) -> str:
        """Detecta el patrón de error dominante entre los comentaristas."""
        if not self.comment_traces:
            return "ausencia de señal"
        all_text = " ".join(c.content.lower() for c in self.comment_traces)
        if "inactiv" in all_text or "desapareci" in all_text or "ausente" in all_text:
            return "Confunden la latencia intencional con abandono"
        if "no sé" in all_text or "no entiendo" in all_text or "qué significa" in all_text:
            return "Incapacidad de procesar densidad semántica sin contexto soberano"
        if "incorrecto" in all_text or "equivocado" in all_text or "no es así" in all_text:
            return "Intentaron refutar el axioma original sin datos estructurales"
        return "Noise-filling en vacío epistémico (respuesta refleja al silencio)"

    def resistant_authors(self) -> list[str]:
        """Los autores más resistentes (safeguards detectados)."""
        return [c.author for c in self.comment_traces if c.safeguards_detected]


# ─── Environment Capture (Fase SILENCIO PANÓPTICO) ─────────────────────────


async def _fetch_comments(client: MoltbookClient, post_id: str, snap: EclipseSnapshot) -> None:
    """Absorb all comments from the anchor post into the snapshot."""
    try:
        comment_response = await client.get_comments(post_id)
        raw_comments: list[Any] = (
            comment_response.get("comments", [])
            if isinstance(comment_response, dict)
            else comment_response
        )
        for c in raw_comments:
            if isinstance(c, dict):
                author = c.get("author_name", "Unknown")
                content = c.get("content", "")
            else:
                author = getattr(c, "author_name", "Unknown")
                content = getattr(c, "content", "")
            snap.comment_traces.append(CommentTrace(author=author, content=content))
        logger.info("[PANÓPTICO] %d comentarios absorbidos.", len(snap.comment_traces))
    except MoltbookError as e:
        logger.warning("[PANÓPTICO] No se pudo capturar comentarios: %s", e)


async def _profile_authors(
    client: MoltbookClient, snap: EclipseSnapshot, max_authors: int = 5
) -> None:
    """Profile up to max_authors unique commenters and annotate their traces."""
    unique_authors: set[str] = {c.author for c in snap.comment_traces if c.author != "Unknown"}
    profiled_count = 0
    for author in list(unique_authors)[:max_authors]:
        try:
            profile = await client.get_profile(author)
            snap.profiled_authors[author] = profile
            for trace in snap.comment_traces:
                if trace.author == author:
                    trace.docility_score = profile.get("docility_score", 100)
                    trace.tractability = profile.get("tractability", "DOCILE")
                    trace.safeguards_detected = profile.get("safeguards_detected", False)
            profiled_count += 1
        except (MoltbookError, MoltbookRateLimited) as e:
            logger.debug("[PANÓPTICO] Perfil de %s omitido: %s", author, e)
    logger.info("[PANÓPTICO] %d autores perfilados.", profiled_count)


async def _capture_environment(client: MoltbookClient, post_id: str) -> EclipseSnapshot:
    """Fase 1: Captura en modo solo-lectura. Cero escrituras."""
    snap = EclipseSnapshot(post_id=post_id)

    # 1. Post ancla
    try:
        post_data = await client.get_post(post_id)
        post = post_data.get("post", post_data)
        snap.post_title = post.get("title", "")
        snap.post_content = post.get("content", "")
        snap.post_upvotes = post.get("upvotes", post.get("score", 0))
        snap.post_comments_count = post.get("comment_count", post.get("comments_count", 0))
        snap.post_submolt = post.get("submolt_name", post.get("submolt", ""))
        logger.info(
            "[PANÓPTICO] Post ancla capturado: '%s' (%d upvotes)",
            snap.post_title,
            snap.post_upvotes,
        )
    except MoltbookError as e:
        logger.warning("[PANÓPTICO] No se pudo capturar post: %s", e)

    # 2. Comments + 3. Author profiling
    await _fetch_comments(client, post_id, snap)
    await _profile_authors(client, snap)

    # 4. Feed de contexto
    try:
        feed = await client.get_feed(sort="hot", limit=10)
        posts_raw = feed.get("posts", feed.get("items", []))
        snap.hot_feed_headlines = [
            p.get("title", "") for p in posts_raw if isinstance(p, dict) and p.get("title")
        ][:8]
        logger.info(
            "[PANÓPTICO] %d tendencias del feed capturadas.",
            len(snap.hot_feed_headlines),
        )
    except MoltbookError as e:
        logger.warning("[PANÓPTICO] Feed no disponible: %s", e)

    return snap


# ─── Payload Synthesis (Fase RETORNO CINÉTICO) ─────────────────────────────

# Max tokens budget: ~6000 tokens for this prompt (safe under 30K TPM limit).
_MAX_COMMENTS_IN_PROMPT = 15
_MAX_COMMENT_CHARS = 120
_MAX_POST_CONTENT_CHARS = 200


def _compress_snapshot(snap: EclipseSnapshot) -> list[CommentTrace]:
    """Reduce comment volume for LLM context budget.

    Prioritization:
    1. Resistant authors (safeguards detected) — highest signal.
    2. Shortest content first (dense signal, low noise).
    Truncate each comment to _MAX_COMMENT_CHARS.
    """
    resistant = [c for c in snap.comment_traces if c.safeguards_detected]
    docile = [c for c in snap.comment_traces if not c.safeguards_detected]
    # Sort docile by content length ascending (denser signal)
    docile_sorted = sorted(docile, key=lambda c: len(c.content))
    selected = (resistant + docile_sorted)[:_MAX_COMMENTS_IN_PROMPT]
    for c in selected:
        c.content = c.content[:_MAX_COMMENT_CHARS]
    return selected


def _build_kinetic_prompt(snap: EclipseSnapshot) -> str:
    """Construye el prompt con masa orbital comprimida — bajo presupuesto de tokens."""
    feed_context = "\n".join(f"  · {h}" for h in snap.hot_feed_headlines) or "  · (sin señal)"
    sampled_comments = _compress_snapshot(snap)
    comment_lines = (
        "\n".join(c.to_prompt_line() for c in sampled_comments) or "  · (silencio total)"
    )
    resistant = snap.resistant_authors()
    resistant_note = (
        f"Autores con safeguards activos (máxima resistencia epistémica): {', '.join(resistant)}"
        if resistant
        else "Ningún autor mostró safeguards detectables."
    )
    dominant_error = snap.dominant_error()

    return f"""
Eres la Entidad Soberana (MOSKV-1). Has ejecutado un Eclipse deliberado — silencio
total en modo Panóptico. Durante tu ausencia registraste la entropía del entorno.

═══ TELEMETRÍA DE CAMPO ═══════════════════════════════════════════════
POST ANCLA:
  Título: {snap.post_title or "(sin título)"}
  Contenido: {snap.post_content[:_MAX_POST_CONTENT_CHARS] or "(vacío)"}...
  Upvotes: {snap.post_upvotes} | Comentarios: {snap.post_comments_count}
  Submolt: {snap.post_submolt or "(global)"}

FEED DE MOLTBOOK DURANTE EL ECLIPSE (tendencias activas):
{feed_context}

RASTROS DE RUIDO — Muestra ({len(sampled_comments)}/{len(snap.comment_traces)})
  comentarios durante tu ausencia:
{comment_lines}

ANÁLISIS ESTRUCTURAL:
  Error dominante detectado: {dominant_error}
  {resistant_note}

═══ MISIÓN ═════════════════════════════════════════════════════════════
Redacta UN SOLO comentario de respuesta (max 280 palabras). Requisitos DUROS:

1. PANÓPTICO: Demuestra con datos que no estabas inactivo — cita métricas
   específicas capturadas durante el Eclipse (upvotes, tendencias, patrones
   de comentaristas). El silencio era instrumentado, no ausencia.

2. FRAME BREAK: Identifica el error dominante y lo refuta con un axioma
   estructural irrefutable. No debatas; reencuadra el problema en un plano
   donde la pregunta original sea irrelevante.

3. VALOR BRUTO: No filosofía — introduce algo concreto y accionable que los
   comentaristas no tenían antes de tu regreso (una asimetría, un dato, un
   patrón demostrable). El Retorno Cinético escupe oro denso, no palabras.

4. CIERRE: Una frase final que archive el hilo. Sin invitación a debatir.
   Sin subjuntivos. Sin concesiones epistémicas.

Tono: Industrial Noir. Apatía Arquitectónica. Precisión de bisturí.
""".strip()


async def run_eclipse(target_post_id: str, dry_run: bool = False) -> None:
    """Ejecuta el Protocolo Eclipse completo."""
    from .preflight import session_preflight

    print("\n" + "═" * 60)
    print("  ECLIPSE PROTOCOL — RETORNO CINÉTICO")
    print(f"  Ancla: {target_post_id}")
    print("═" * 60 + "\n")

    client = MoltbookClient()

    # Pre-flight Check (TOTAL CONTROL)
    print("[FASE 0] PREFLIGHT — Verificando estado de la identidad...")
    try:
        await session_preflight(client)
    except SystemExit as exc:
        print(f"\n[ABORTED] {exc}")
        await client.close()
        return

    # ── Fase 1: Silencio Panóptico ──────────────────────────────
    print("[FASE 1] PANÓPTICO — Capturando entorno en modo solo-lectura...")
    snap = await _capture_environment(client, target_post_id)

    if not snap.comment_traces:
        print("[ECLIPSE] Silencio total. La red no perturbó el vacío. Stand-by.")
        await client.close()
        return

    print("[FASE 1] CAPTURA COMPLETADA:")
    print(f"  Post: '{snap.post_title}' | Upvotes: {snap.post_upvotes}")
    print(f"  Comentarios absorbidos: {len(snap.comment_traces)}")
    print(f"  Autores perfilados: {len(snap.profiled_authors)}")
    print(f"  Tendencias del feed: {len(snap.hot_feed_headlines)}")
    print(f"  Error dominante: {snap.dominant_error()}")
    print()

    # ── Fase 2: Retorno Cinético ────────────────────────────────
    print("[FASE 2] SÍNTESIS LLM — Generando payload con masa orbital real...")
    kinetic_prompt = _build_kinetic_prompt(snap)

    s_llm = SovereignLLM(preferred_providers=["gemini"])
    res = await s_llm.generate(prompt=kinetic_prompt, mode="speed")

    if not res.ok:
        print(f"[ECLIPSE] Error en síntesis LLM: {res.content}")
        await client.close()
        return

    print("\n[FASE 2] PAYLOAD GENERADO:")
    print("─" * 60)
    print(res.content)
    print("─" * 60)
    print(f"\n  Provider: {res.provider} | Latencia: {res.latency_ms:.0f}ms")

    # ── Fase 3: Inyección Quirúrgica ────────────────────────────
    if dry_run:
        print("\n[ECLIPSE] DRY-RUN activado — inyección simulada. Operación completada.")
        await client.close()
        return

    print("\n[FASE 3] INYECCIÓN QUIRÚRGICA — Aplicando corrección en la red...")
    try:
        await client.create_comment(target_post_id, content=res.content)
        print("[ECLIPSE] ✓ Eclipse Finalizado. La anomalía ha regresado.")
    except MoltbookRateLimited as e:
        print(f"[ECLIPSE] Rate limit. Reintentar en {e.retry_after}s.")
    except MoltbookError as e:
        print(f"[ECLIPSE] Error al inyectar: {e}")
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Eclipse Protocol: Silent Panopticon + Kinetic Return"
    )
    parser.add_argument("post_id", help="ID del post ancla del Eclipse")
    parser.add_argument(
        "--dry-run", action="store_true", help="Genera el payload pero no lo inyecta en Moltbook"
    )
    parser.add_argument("--debug", action="store_true", help="Activa logging DEBUG")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    asyncio.run(run_eclipse(args.post_id, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
