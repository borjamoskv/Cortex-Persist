import sys
import time
from ingest_influencer_data import AuditIngestionEngine
from nlp_martyr_loop import extract_vtt, parse_vtt_and_analyze

TARGETS_FILE = "targets_audit.txt"


def execute_batch_loop(targets_file: str):
    """
    [C5-REAL] Motor Vector Gamma: Ingesta Masiva y Correlación Asíncrona.
    """
    try:
        with open(targets_file, encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        print(f"[ERROR] Archivo {targets_file} no localizado. Abortando Batch.")
        sys.exit(1)

    print(f"[SYS] Iniciando Batch Loop sobre {len(urls)} vectores objetivos.")

    engine = AuditIngestionEngine()

    for idx, url in enumerate(urls, 1):
        print(f"\n--- [Procesando Objetivo {idx}/{len(urls)}] ---")
        print(f"URL: {url}")

        # Fase 1: Ingesta Estructural (videos_fuente)
        try:
            engine.ingest_video_metadata(url)
        except Exception as e:
            print(f"[FAIL] Fase 1 caída en {url}: {e}")
            continue

        # Extraer Video_ID asumiendo formato youtube watch?v= o shortlink
        # Simplificación rápida para el pipeline (en un entorno real se extraería directamente del engine)
        vid_id = url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1]

        # Fase 2: Mapeo de Disonancia VTT (eventos_victimismo)
        print(f"[SYS] Lanzando Crawler VTT para {vid_id}...")
        vtt_file = extract_vtt(url)
        if vtt_file:
            parse_vtt_and_analyze(vtt_file, vid_id)
        else:
            print(
                f"[0x02_EDGE] Imposible extraer subtítulos para {vid_id} (API Rate Limit o Ausencia de CC)."
            )

        # Fase 3: Minería de Caja de Comentarios (eventos_acoso)
        from comments_scraper_omega import scan_and_inject_comments

        print(f"[SYS] Iniciando barrido de comunidad (Vector Alpha) para {vid_id}...")
        scan_and_inject_comments(vid_id, url)

        # Evasión de Throttling (Anti-Ban)
        time.sleep(2)

    print("\n[C5-REAL] Ciclo Batch Completado. Base de datos actualizada.")


if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else TARGETS_FILE
    execute_batch_loop(file_path)
