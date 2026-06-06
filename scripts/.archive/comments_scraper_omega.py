import asyncio
import json
import sqlite3
import sys
from typing import Any

DB_PATH = "influencer_audit_v1.db"

# We replace static regex with the SovereignLLM import for semantic analysis
try:
    from cortex.extensions.llm.sovereign import SovereignLLM
except ImportError:
    SovereignLLM = None
    print(
        "[WARNING] SovereignLLM not found in path, falling back to basic extraction without semantic tagging."
    )


async def extract_comments_dump(url: str) -> list[dict[str, Any]]:
    """Extrae metadatos y comentarios de forma asíncrona usando yt-dlp."""
    print(f"[SYS] Extrayendo DOM de comentarios asíncronamente para {url}...")
    cmd = ["yt-dlp", "--get-comments", "--dump-json", "--no-warnings", "--skip-download", url]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print(f"[ERROR] yt-dlp failed: {stderr.decode()}")
            return []

        # Parse the first JSON line
        lines = stdout.decode().strip().split("\n")
        if not lines or not lines[0]:
            return []

        data = json.loads(lines[0])
        return data.get("comments", [])
    except Exception as e:
        print(f"[ERROR] Extracción de comentarios fallida: {e}")
        return []


async def analyze_with_llm(comments: list[str]) -> dict[str, str]:
    """Usa el LLM Soberano para categorizar la toxicidad de los comentarios en lote."""
    if not SovereignLLM:
        return {}

    system_prompt = (
        "Eres un auditor C5-REAL de toxicidad. "
        "Dada una lista de comentarios, identifica cuáles contienen: Ad hominem, Misoginia, o Violencia/Amenaza.\n"
        "Devuelve un JSON estricto donde la clave es el texto exacto del comentario y el valor es la categoría de toxicidad.\n"
        "Solo incluye comentarios que sean genuinamente tóxicos."
    )

    prompt = "COMENTARIOS:\n" + "\n".join(f"- {c}" for c in comments[:50])  # Batch size limit

    llm = SovereignLLM(temperature=0.0)
    try:
        res = await llm.generate(prompt=prompt, system=system_prompt)
        if res.ok:
            content = res.content.strip()
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            return json.loads(content)
    except Exception as e:
        print(f"[ERROR LLM] Falla en auditoría semántica: {e}")
    finally:
        await llm.close()

    return {}


async def scan_and_inject_comments(video_id: str, url: str):
    """Analiza la agresividad de la comunidad (Comunidad Anti-Fan) de forma asíncrona."""
    comments = await extract_comments_dump(url)
    if not comments:
        print(f"[0x02_EDGE] Sin comentarios detectados o bloqueados por el creador en {video_id}.")
        return

    # Extract raw texts for LLM batching
    raw_texts = [c.get("text", "") for c in comments if c.get("text")]
    toxic_map = await analyze_with_llm(raw_texts) if raw_texts else {}

    # Si no hay SovereignLLM, simulamos guardado crudo sin taxonomia
    hits = 0

    # SQLite connection inside executor or just sync since SQLite is fast for inserts
    # For a fully async system, we should use aiosqlite, but standard sqlite3 is fine for small batches.
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos_acoso (
            video_id TEXT,
            target_id TEXT,
            taxonomia_ataque TEXT,
            cita_textual_exacta TEXT
        )
    """)

    for comment in comments:
        text = comment.get("text", "")
        author = comment.get("author_id", "Anonymous")

        if text in toxic_map:
            tax_label = toxic_map[text]
            cursor.execute(
                """
                INSERT INTO eventos_acoso (video_id, target_id, taxonomia_ataque, cita_textual_exacta)
                VALUES (?, ?, ?, ?)
                """,
                (video_id, author, tax_label, text[:255]),
            )
            hits += 1

    conn.commit()
    conn.close()
    print(
        f"[0x01_CORE] Vector Alpha Completado. {hits} eventos de acoso indexados para {video_id} mediante LLM."
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python comments_scraper_omega.py <video_id> <youtube_url>")
        sys.exit(1)

    asyncio.run(scan_and_inject_comments(sys.argv[1], sys.argv[2]))
