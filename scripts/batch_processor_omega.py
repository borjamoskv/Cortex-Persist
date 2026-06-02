import sys
import asyncio
import logging
import signal
import sqlite3
import random
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Dependencias externas CORTEX (Mocked for safety si no están presentes, pero asume C5-REAL)
try:
    from ingest_influencer_data import AuditIngestionEngine
    from nlp_martyr_loop import extract_vtt, parse_vtt_and_analyze
    from comments_scraper_omega import scan_and_inject_comments
    MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Dependencias externas no localizadas ({e}). Operando en Degraded Mode.")
    MODULES_AVAILABLE = False
    
    # Mocks para compilación estricta
    class AuditIngestionEngine:
        def ingest_video_metadata(self, url): pass
    def extract_vtt(url): return "dummy.vtt"
    def parse_vtt_and_analyze(vtt, vid_id): pass
    def scan_and_inject_comments(vid_id, url): pass

TARGETS_FILE = "targets_audit.txt"
STATE_DB = "batch_omega_state.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [C5-REAL] - %(message)s")

class BatchProcessorOmega:
    """
    [C5-REAL] Motor de Ingesta Masiva y Correlación Asíncrona.
    Features SOTA implementadas:
    - Resiliencia de Estado (SQLite WAL).
    - Backoff Exponencial con Jitter.
    - Graceful Shutdown (Drenado de in-flight requests).
    """
    def __init__(self, concurrency_limit: int = 5):
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.engine = AuditIngestionEngine()
        self.shutdown_event = asyncio.Event()
        self._init_state_db()

    def _init_state_db(self):
        """Inicializa DB de checkpointing local para persistencia C5-REAL."""
        with sqlite3.connect(STATE_DB) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS processed_targets (
                    video_id TEXT PRIMARY KEY,
                    url TEXT,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
    def _is_processed(self, vid_id: str) -> bool:
        with sqlite3.connect(STATE_DB) as conn:
            cursor = conn.execute("SELECT status FROM processed_targets WHERE video_id = ?", (vid_id,))
            row = cursor.fetchone()
            return row is not None and row[0] == "SUCCESS"

    def _mark_state(self, vid_id: str, url: str, status: str):
        with sqlite3.connect(STATE_DB) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO processed_targets (video_id, url, status) VALUES (?, ?, ?)",
                (vid_id, url, status)
            )

    @staticmethod
    def _extract_video_id(url: str) -> str:
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            return qs.get("v", [""])[0]
        elif "youtu.be" in parsed.netloc:
            return parsed.path.lstrip('/')
        return url.split("/")[-1]

    async def _exponential_backoff(self, func, *args, max_retries=3):
        """Ejecuta una función en un thread con retry determinista y jitter."""
        retries = 0
        while not self.shutdown_event.is_set():
            try:
                return await asyncio.to_thread(func, *args)
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    raise e
                sleep_time = (2 ** retries) + random.uniform(0, 1)
                logging.warning(f"Rate Limit / Error de Red en {func.__name__}. Reintentando en {sleep_time:.2f}s... ({retries}/{max_retries})")
                await asyncio.sleep(sleep_time)

    async def process_target(self, url: str, idx: int, total: int):
        if self.shutdown_event.is_set():
            return

        vid_id = self._extract_video_id(url)
        if not vid_id:
            logging.error(f"Fallo estructural: Imposible extraer Video ID de {url}")
            return

        if self._is_processed(vid_id):
            logging.info(f"[{idx}/{total}] Objetivo {vid_id} ya metabolizado (Cache Hit). Omitiendo.")
            return

        async with self.semaphore:
            logging.info(f"[{idx}/{total}] Bloqueo de semáforo adquirido para {vid_id}.")
            self._mark_state(vid_id, url, "PROCESSING")

            try:
                # Fases encapsuladas en backoff
                await self._exponential_backoff(self.engine.ingest_video_metadata, url)
                
                vtt_file = await self._exponential_backoff(extract_vtt, url)
                if vtt_file:
                    await self._exponential_backoff(parse_vtt_and_analyze, vtt_file, vid_id)
                
                await self._exponential_backoff(scan_and_inject_comments, vid_id, url)
                
                self._mark_state(vid_id, url, "SUCCESS")
                logging.info(f"[{idx}/{total}] Ingesta completada para {vid_id}.")

            except Exception as e:
                self._mark_state(vid_id, url, "FAILED")
                logging.error(f"[{vid_id}] Falla crítica irrecuperable en pipeline: {e}")

    def trigger_shutdown(self):
        """Activa la interrupción suave."""
        logging.warning("SIGINT/SIGTERM recibido. Iniciando drenado de tareas pendientes (Graceful Shutdown)...")
        self.shutdown_event.set()

async def execute_batch_loop(targets_file: str):
    if not Path(targets_file).exists():
        logging.error(f"Archivo {targets_file} no localizado. Abortando Batch.")
        sys.exit(1)

    with open(targets_file, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    logging.info(f"Iniciando Batch Loop SOTA sobre {len(urls)} vectores objetivos.")
    processor = BatchProcessorOmega(concurrency_limit=5)
    
    # Manejo de señales UNIX para Graceful Shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, processor.trigger_shutdown)
        except NotImplementedError:
            pass # Ignorado en Windows u otros entornos no UNIX strict

    tasks = [processor.process_target(url, idx, len(urls)) for idx, url in enumerate(urls, 1)]
    await asyncio.gather(*tasks)
    
    if processor.shutdown_event.is_set():
        logging.info("Ciclo interrumpido por operador. Estado preservado en WAL SQLite.")
    else:
        logging.info("Ciclo Batch SOTA Completado. Base de datos actualizada.")

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else TARGETS_FILE
    try:
        asyncio.run(execute_batch_loop(file_path))
    except KeyboardInterrupt:
        pass # Handleado internamente
