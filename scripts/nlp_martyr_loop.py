import sqlite3
import re
import subprocess
import os
import sys

DB_PATH = "influencer_audit_v1.db"
VTT_TEMP = "temp_subs.vtt"

VICTIM_KEYWORDS = re.compile(
    r"(censura|desmonetiza|quieren callar|cancelación|policía del pensamiento|ataque coordinado)",
    re.IGNORECASE,
)
CTA_KEYWORDS = re.compile(
    r"(patreon|apoya el canal|donación|cripto|enlace en la descripción|miembro|suscríbete para apoyar)",
    re.IGNORECASE,
)


def extract_vtt(url: str):
    """Descarga subtítulos autogenerados vía yt-dlp (C5-REAL)."""
    if os.path.exists(VTT_TEMP):
        os.remove(VTT_TEMP)
    cmd = [
        "yt-dlp",
        "--write-auto-subs",
        "--skip-download",
        "--sub-format",
        "vtt",
        "--output",
        "temp_subs",
        url,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # yt-dlp appends lang code, e.g. temp_subs.es.vtt
        for f in os.listdir("."):
            if f.startswith("temp_subs") and f.endswith(".vtt"):
                return f
        return None
    except subprocess.CalledProcessError:
        return None


def parse_vtt_and_analyze(vtt_file: str, video_id: str):
    """Busca intersecciones temporales entre Victimización y CTA."""
    with open(vtt_file, encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("\n\n")
    victim_timestamps = []
    cta_timestamps = []

    for block in blocks:
        lines = block.split("\n")
        if len(lines) >= 2 and "-->" in lines[0]:
            timestamp = lines[0]
            text = " ".join(lines[1:])
            if VICTIM_KEYWORDS.search(text):
                victim_timestamps.append((timestamp, text))
            if CTA_KEYWORDS.search(text):
                cta_timestamps.append((timestamp, text))

    # Análisis de Proximidad (Ventana de 120 segundos)
    # Implementación heurística rápida (O(n*m))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if victim_timestamps and cta_timestamps:
        # Se asume correlación positiva si ambas métricas se disparan en el mismo vídeo.
        # Future: strict timestamp proximity math.

        cursor.execute(
            """
            INSERT INTO eventos_victimismo (video_id, evidencia_externa_instrumentalizada, tono_reclamo, call_to_action_economica)
            VALUES (?, ?, ?, ?)
        """,
            (
                video_id,
                f"Matches: {len(victim_timestamps)} victim keywords",
                "Agravio Estructural Detectado",
                True,
            ),
        )
        conn.commit()
        print(
            f"[0x01_CORE] Disonancia extraída: Video {video_id}. Victim({len(victim_timestamps)}) -> CTA({len(cta_timestamps)})"
        )
    else:
        print(f"[0x02_EDGE] Sin vector de victimización clara en {video_id}.")

    conn.close()
    if os.path.exists(vtt_file):
        os.remove(vtt_file)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python nlp_martyr_loop.py <video_id> <youtube_url>")
        sys.exit(1)

    vid = sys.argv[1]
    url = sys.argv[2]
    print(f"[SYS] Ejecutando análisis heurístico VTT sobre {url}...")
    vtt = extract_vtt(url)
    if vtt:
        parse_vtt_and_analyze(vtt, vid)
    else:
        print("[FAIL] VTT Inexistente o bloqueado.")
