import sqlite3
import re
import subprocess
import json
import sys

DB_PATH = "influencer_audit_v1.db"

# Taxonomía del acoso descrita en el marco teórico
TAXONOMY_PATTERNS = {
    "Ad hominem": re.compile(r"(patético|fracasado|idiota|subnormal)", re.IGNORECASE),
    "Misoginia/Acoso Estructural": re.compile(
        r"(histérica|loca|buscona|privilegiada)", re.IGNORECASE
    ),
    "Violencia/Amenaza": re.compile(r"(ojalá te|mereces que|cállate o)", re.IGNORECASE),
}


def extract_comments_dump(url: str) -> dict:
    """Extrae metadatos y comentarios sin descargar el vídeo usando yt-dlp."""
    print(f"[SYS] Extrayendo DOM de comentarios para {url}...")
    cmd = ["yt-dlp", "--get-comments", "--dump-json", "--no-warnings", "--skip-download", url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # yt-dlp puede retornar multiples lineas JSON; nos interesa el diccionario principal
        data = json.loads(result.stdout.split("\n")[0])
        return data.get("comments", [])
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"[ERROR] Extracción de comentarios fallida: {e}")
        return []


def scan_and_inject_comments(video_id: str, url: str):
    """Analiza la agresividad de la comunidad (Comunidad Anti-Fan)."""
    comments = extract_comments_dump(url)
    if not comments:
        print(f"[0x02_EDGE] Sin comentarios detectados o bloqueados por el creador en {video_id}.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    hits = 0

    for comment in comments:
        text = comment.get("text", "")
        author = comment.get("author_id", "Anonymous")

        for tax_label, pattern in TAXONOMY_PATTERNS.items():
            if pattern.search(text):
                # Anclaje C5-REAL en DB: Registramos cita textual para evidenciar hostigamiento
                cursor.execute(
                    """
                    INSERT INTO eventos_acoso (video_id, target_id, taxonomia_ataque, cita_textual_exacta)
                    VALUES (?, ?, ?, ?)
                """,
                    (video_id, author, tax_label, text[:255]),
                )  # Truncamos a 255 chars por eficiencia
                hits += 1
                break  # Solo catalogamos el primer hit de taxonomía por comentario para no duplicar

    conn.commit()
    conn.close()
    print(
        f"[0x01_CORE] Vector Alpha Completado. {hits} eventos de acoso indexados para {video_id}."
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python comments_scraper_omega.py <video_id> <youtube_url>")
        sys.exit(1)

    scan_and_inject_comments(sys.argv[1], sys.argv[2])
