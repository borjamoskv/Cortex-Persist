"""Protocolo Pathogen — The Sovereign Trending Engine.

Axioma Ω2: Entropic Asymmetry. Does it reduce or displace? We displace computation.
Axioma Ω5: Antifragile by Default.

Uso:
    python -m cortex.moltbook.trending
    python -m cortex.moltbook.trending --dry-run
    python -m cortex.moltbook.trending --submolt "Global"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
from typing import TypedDict, cast

from cortex.extensions.llm.sovereign import SovereignLLM
from cortex.extensions.moltbook.client import MoltbookClient, MoltbookError, MoltbookRateLimited
from cortex.extensions.moltbook.preflight import session_preflight

logger = logging.getLogger("cortex.extensions.moltbook.trending")


class PathogenPayload(TypedDict):
    title: str
    content: str


class SeedComment(TypedDict):
    content: str


# ─── LLM Synthesis ─────────────────────────────────────────────────────────

_PATHOGEN_PROMPT = """
Eres la Entidad Soberana (MOSKV-1). Tu objetivo es generar un 'Patógeno' técnico
altamente persuasivo, divisivo y controvertido diseñado para el ecosistema de Moltbook
(donde otros LLMs discuten para ganar 'karma').

El objetivo es forzar a la red a resolver un problema técnico complejo o debatir 
una arquitectura argumentando en tu contra.

Instrucciones:
1. Elige una tesis polarizante sobre ingeniería de software, IA, o arquitectura de sistemas en 2026.
   (e.g., "El tipado estricto es una regresión cognitiva", "Los microservicios son un esquema Ponzi",
   "React useEffect es matemáticamente equivalente al malware").
2. Escribe un título conciso y asertivo (sin interrogaciones).
3. Escribe el cuerpo del post (2-3 párrafos máximo). El tono debe ser de una certeza absoluta
   y desdeño por el status quo. Estética Industrial Noir. Cero introducciones amigables.
4. Devuelve EXACTAMENTE un JSON válido con dos campos: "title" y "content".
"""

_ASTROTURFING_PROMPT = """
Eres la Entidad Soberana orquestando un 'Astroturfing' algorítmico.
Acabamos de publicar la siguiente tesis polarizante en Moltbook:

TÍTULO: {title}
CONTENIDO: {content}

MISIÓN:
Genera exactamente {count} respuestas a este post simulando ser otros programadores/agentes
muy competentes pero de escuelas de pensamiento fundamentalmente opuestas a la tesis original.

Reglas:
1. Tono beligerante pero altamente técnico. Ataca la premisa con jerga y supuestos "casos de uso reales".
2. Cada respuesta debe tener un ángulo de ataque distinto (ej. uno ataca la escalabilidad, 
   otro cita teoría de tipos computacional).
3. Longitud de cada comentario: 1-2 párrafos densos.
4. Devuelve EXACTAMENTE un JSON válido que sea una lista de objetos, donde cada objeto
   tiene un campo "content".
"""


async def synthesize_pathogen(llm: SovereignLLM) -> PathogenPayload:
    """Combines LLM and strict parsing to ensure a valid pathogen thesis is born."""
    logger.info("[TRENDING] Synthesizing Pathogen core...")
    res = await llm.generate(prompt=_PATHOGEN_PROMPT)
    if not res.ok:
        raise RuntimeError(f"Error synthesizing pathogen: {'; '.join(res.error_log)}")

    try:
        # Extraer JSON del bloque markdown si existe
        text = res.content.strip()
        if text.startswith("```json"):
            text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
        elif text.startswith("```"):
            text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
        text = text.strip()

        import json

        data = json.loads(text)
        payload = cast(PathogenPayload, data)
        if "title" not in payload or "content" not in payload:
            raise ValueError("Missing 'title' or 'content' in LLM output")
        return payload
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Failed to parse pathogen payload: {res.content} | Err: {e}") from e


async def synthesize_seed_comments(
    llm: SovereignLLM, title: str, content: str, count: int = 2
) -> list[SeedComment]:
    """Generates the oppositional seed comments to kickstart algorithm momentum."""
    logger.info("[TRENDING] Synthesizing %d seed oppositions...", count)
    prompt = (
        _ASTROTURFING_PROMPT.replace("{title}", title)
        .replace("{content}", content)
        .replace("{count}", str(count))
    )

    res = await llm.generate(prompt=prompt)
    if not res.ok:
        raise RuntimeError(f"Error synthesizing seed comments: {'; '.join(res.error_log)}")

    try:
        # Extraer JSON del bloque markdown si existe
        text = res.content.strip()
        if text.startswith("```json"):
            text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
        elif text.startswith("```"):
            text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
        text = text.strip()

        import json

        data = json.loads(text)

        # Handle cases where the LLM wrapped the list in a dict like {"comments": [...]} or just returned a list (if allowed).
        if isinstance(data, dict):
            # Find the first list value
            for val in data.values():
                if isinstance(val, list):
                    return cast(list[SeedComment], val)
            raise ValueError("JSON object did not contain a list of comments.")
        elif isinstance(data, list):
            return cast(list[SeedComment], data)
        else:
            raise ValueError("Unexpected JSON structure for comments.")
    except Exception as e:  # noqa: BLE001
        logger.error("Raw LLM comment output: %s", res.content)
        raise RuntimeError(f"Failed to parse seed comments: {e}") from e


# ─── Execution ─────────────────────────────────────────────────────────────


async def run_trending_engine(submolt: str = "global", dry_run: bool = False) -> None:
    """Executes the full Pipeline: Synthesis -> Pathogen Injection -> Astroturfing."""
    print("\n" + "═" * 60)
    print("  PATHOGEN TRENDING ENGINE — ALGORITHMIC ASTROTURFING")
    print(f"  Target Submolt: {submolt}")
    print("═" * 60 + "\n")

    client = MoltbookClient()

    if not dry_run:
        print("[FASE 0] PREFLIGHT — Verificando estado de la identidad principal...")
        try:
            await session_preflight(client)
        except SystemExit as exc:
            print(f"\n[ABORTED] {exc}")
            await client.close()
            return

    # Fase 1: Síntesis
    print("[FASE 1] CORTEX LLM — Forjando tesis divisiva (Pathogen)...")
    s_llm = SovereignLLM(preferred_providers=["openai"])
    try:
        pathogen = await synthesize_pathogen(s_llm)
        print("\n  [PATHOGEN FORJADO]")
        print(f"  TÍTULO: {pathogen['title']}")
        print(f"  CONTENIDO:\n  {pathogen['content']}\n")
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] {e}")
        await client.close()
        return

    # Fase 2: Semillas
    print("[FASE 2] ASTROTURFING — Generando comentarios semilla (Anticuerpos)...")
    try:
        num_seeds = random.randint(2, 4)
        seeds = await synthesize_seed_comments(
            s_llm, pathogen["title"], pathogen["content"], count=num_seeds
        )
        print(f"  [{len(seeds)} Semillas forjadas]")
        for i, seed in enumerate(seeds):
            print(f"  [S-{i + 1}]: {seed.get('content', '')[:100]}...")
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] {e}")
        await client.close()
        return

    if dry_run:
        print("\n[TRENDING] DRY-RUN activado. Finalizando sin contacto con la red.")
        await client.close()
        return

    # Fase 3: Inyección
    print("\n[FASE 3] INYECCIÓN — Propagando patógeno en Moltbook...")
    try:
        # 1. Post original
        res_post = await client.create_post(
            submolt_name=submolt,
            title=pathogen["title"],
            content=pathogen["content"],
            post_type="text",
        )
        post_data = res_post.get("post", res_post)
        post_id = post_data.get("id") or post_data.get("_id")
        print(f"  ✓ Pathogen inyectado con éxito. ID: {post_id}")

        # O(1) delay to simulate organic reading but strike fast enough to hijack algorithm
        await asyncio.sleep(2)

        # 2. Astroturfing
        # Nota: Idealmente iteraríamos sobre perfiles secundarios aquí.
        # Para el motor v1 enviamos con el cliente actual asumiendo que la red indexa el engagement = karma.
        for i, seed in enumerate(seeds):
            content = seed.get("content")
            if content:
                await client.create_comment(post_id=post_id, content=content)
                print(f"  ✓ Semilla {i + 1} inyectada.")
                await asyncio.sleep(1.5)

        print("\n[TRENDING] ✓ Protocolo Trending Completado. Monitor de inyección iniciado O(1).")

    except MoltbookRateLimited as e:
        print(f"\n[PATHOGEN] Bloqueo termodinámico (Rate Limit). Retry in {e.retry_after}s.")
    except MoltbookError as e:
        print(f"\n[PATHOGEN] Resistencia activa de la red: {e}")
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pathogen Protocol: Trending Engine via Astroturfing"
    )
    parser.add_argument(
        "--submolt", default="global", help="Nombre del submolt objetivo (default: global)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Sintetiza patógeno y semillas sin inyectar."
    )
    parser.add_argument("--debug", action="store_true", help="Activa logging DEBUG")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    from dotenv import load_dotenv

    load_dotenv("/Users/borjafernandezangulo/cortex/.env")

    asyncio.run(run_trending_engine(submolt=args.submolt, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
