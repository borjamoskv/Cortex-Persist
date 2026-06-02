import sys
import asyncio
import logging
from urllib.parse import urlparse, parse_qs
from typing import List

# Importaciones asumidas como sincrónicas de bibliotecas externas
from ingest_influencer_data import AuditIngestionEngine
from nlp_martyr_loop import extract_vtt, parse_vtt_and_analyze
from comments_scraper_omega import scan_and_inject_comments

TARGETS_FILE = "targets_audit.txt"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [C5-REAL] - %(message)s")

class BatchProcessorOmega:
    """
    [C5-REAL] Motor de Ingesta Masiva y Correlación Asíncrona.
    Reemplaza la falsa concurrencia (time.sleep) por un event loop real con semáforos de rate limiting.
    """
    def __init__(self, concurrency_limit: int = 3):
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.engine = AuditIngestionEngine()

    @staticmethod
    def _extract_video_id(url: str) -> str:
        """Validación estricta de URL en lugar de .split('v=') frágil."""
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            return qs.get("v", [""])[0]
        elif "youtu.be" in parsed.netloc:
            return parsed.path.lstrip('/')
        return url.split("/")[-1]

    async def process_target(self, url: str, idx: int, total: int):
        """Pipeline asíncrono para un objetivo individual."""
        vid_id = self._extract_video_id(url)
        if not vid_id:
            logging.error(f"Fallo estructural: Imposible extraer Video ID de {url}")
            return

        async with self.semaphore:
            logging.info(f"[{idx}/{total}] Bloqueo de semáforo adquirido para {vid_id}. Iniciando ingesta.")

            try:
                # Fase 1: Ingesta Estructural (I/O Sincrónico envuelto en thread)
                await asyncio.to_thread(self.engine.ingest_video_metadata, url)
                
                # Fase 2: Mapeo de Disonancia VTT
                vtt_file = await asyncio.to_thread(extract_vtt, url)
                if vtt_file:
                    await asyncio.to_thread(parse_vtt_and_analyze, vtt_file, vid_id)
                else:
                    logging.warning(f"[{vid_id}] 0x02_EDGE: Imposible extraer VTT (Rate Limit o Sin CC).")

                # Fase 3: Minería de Caja de Comentarios
                await asyncio.to_thread(scan_and_inject_comments, vid_id, url)
                
                logging.info(f"[{idx}/{total}] Ingesta completada para {vid_id}.")

            except Exception as e:
                logging.error(f"[{vid_id}] Falla crítica en pipeline: {e}")

async def execute_batch_loop(targets_file: str):
    try:
        with open(targets_file, encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        logging.error(f"Archivo {targets_file} no localizado. Abortando Batch.")
        sys.exit(1)

    logging.info(f"Iniciando Batch Loop Asíncrono sobre {len(urls)} vectores objetivos.")
    processor = BatchProcessorOmega(concurrency_limit=3)
    
    tasks = [processor.process_target(url, idx, len(urls)) for idx, url in enumerate(urls, 1)]
    await asyncio.gather(*tasks)
    
    logging.info("Ciclo Batch Asíncrono Completado. Base de datos actualizada.")

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else TARGETS_FILE
    asyncio.run(execute_batch_loop(file_path))
