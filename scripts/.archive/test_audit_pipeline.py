import os
import sqlite3
import unittest
from unittest.mock import patch

from comments_scraper_omega import scan_and_inject_comments
from generate_report import generate_html_report
from ingest_influencer_data import AuditIngestionEngine

# Importar los componentes del pipeline
from init_influencer_audit_db import init_db
from nlp_martyr_loop import parse_vtt_and_analyze

TEST_DB = "influencer_audit_test.db"
MOCK_VTT = "test_subs.es.vtt"


class TestInfluencerAuditPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Asegurar aislamiento del entorno de pruebas
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        # Redireccionar el DB_PATH de los modulos importados
        import comments_scraper_omega
        import generate_report
        import ingest_influencer_data
        import init_influencer_audit_db
        import nlp_martyr_loop

        init_influencer_audit_db.DB_PATH = TEST_DB
        ingest_influencer_data.DB_PATH = TEST_DB
        nlp_martyr_loop.DB_PATH = TEST_DB
        comments_scraper_omega.DB_PATH = TEST_DB
        generate_report.DB_PATH = TEST_DB

    def setUp(self):
        init_db()

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        if os.path.exists(MOCK_VTT):
            os.remove(MOCK_VTT)
        if os.path.exists("report_influencer_audit.html"):
            os.remove("report_influencer_audit.html")

    @patch("ingest_influencer_data.AuditIngestionEngine._execute_yt_dlp")
    @patch("comments_scraper_omega.extract_comments_dump")
    def test_pipeline_integracion_total(self, mock_comments, mock_yt_dlp):
        """
        [C5-REAL] Test de integración del pipeline: ingesta -> NLP -> acoso -> reporte.
        """
        # 1. Mock de yt-dlp metadata
        mock_yt_dlp.return_value = {
            "id": "test_vid_123",
            "uploader_id": "creador_polarizado_1",
            "upload_date": "20260531",
            "webpage_url": "https://youtube.com/watch?v=test_vid_123",
            "duration": 600,
        }

        # 2. Mock de caja de comentarios
        mock_comments.return_value = [
            {"author_id": "usr_1", "text": "Este canal es patético e idiota"},  # Ad hominem
            {"author_id": "usr_2", "text": "Eres una loca histérica total"},  # Misoginia
            {"author_id": "usr_3", "text": "Ojalá te metan una paliza"},  # Violencia
            {"author_id": "usr_4", "text": "Buen vídeo, de acuerdo con el análisis."},  # Neutral
        ]

        # Escribir VTT temporal de prueba para simular la transcripción
        with open(MOCK_VTT, "w", encoding="utf-8") as f:
            f.write(
                "00:00:10.000 --> 00:00:15.000\nMe desmonetizan el canal constantemente. Es censura pura.\n\n"
            )
            f.write(
                "00:00:45.000 --> 00:00:50.000\nApoya el canal en mi Patreon, el enlace está en la descripción.\n"
            )

        # --- EJECUCIÓN ---
        # Fase I: Ingesta de metadatos
        engine = AuditIngestionEngine(db_path=TEST_DB)
        engine.ingest_video_metadata("https://youtube.com/watch?v=test_vid_123")

        # Fase II: NLP de victimismo/CTA
        parse_vtt_and_analyze(MOCK_VTT, "test_vid_123")

        # Fase III: Scraper de acoso de la comunidad
        scan_and_inject_comments("test_vid_123", "https://youtube.com/watch?v=test_vid_123")

        # --- ASERCIONES ---
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()

        # Verificar Videos Fuente
        cursor.execute("SELECT creador_id FROM videos_fuente WHERE video_id = 'test_vid_123'")
        self.assertEqual(cursor.fetchone()[0], "creador_polarizado_1")

        # Verificar Acoso (Debe catalogar 3 ataques según taxonomías mock)
        cursor.execute("SELECT COUNT(*) FROM eventos_acoso")
        self.assertEqual(cursor.fetchone()[0], 3)

        # Verificar Victimismo
        cursor.execute(
            "SELECT call_to_action_economica FROM eventos_victimismo WHERE video_id = 'test_vid_123'"
        )
        self.assertTrue(cursor.fetchone()[0])

        conn.close()

        # Fase IV: Generar Reporte HTML para validar que no rompa
        generate_html_report()
        self.assertTrue(os.path.exists("report_influencer_audit.html"))


if __name__ == "__main__":
    unittest.main()
