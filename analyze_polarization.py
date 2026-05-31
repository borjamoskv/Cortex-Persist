import sqlite3
import sys

DB_PATH = "influencer_audit_v1.db"


def run_analytical_suite():
    """
    [C5-REAL] Motor de consulta relacional para auditar dinámicas de polarización y agravio.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print(" CORTEX PERSISTENCE AUDIT: ANALYTICS SUITE (C5-REAL)")
    print("=" * 60)

    # Query 1: Rage-to-Revenue Ratio (Conversión del Agravio)
    print("\n[0x01_ANALYSIS] Ratio de Conversión del Agravio (Rage-to-Revenue):")
    try:
        cursor.execute("""
            SELECT 
                v.creador_id,
                COUNT(DISTINCT v.video_id) as total_videos,
                SUM(CASE WHEN ev.victim_id IS NOT NULL THEN 1 ELSE 0 END) as videos_con_victimismo,
                SUM(CASE WHEN ev.victim_id IS NOT NULL AND ev.call_to_action_economica = 1 THEN 1 ELSE 0 END) as victimismo_con_cta,
                ROUND(
                    (CAST(SUM(CASE WHEN ev.victim_id IS NOT NULL AND ev.call_to_action_economica = 1 THEN 1 ELSE 0 END) AS REAL) / 
                     COALESCE(NULLIF(SUM(CASE WHEN ev.victim_id IS NOT NULL THEN 1 ELSE 0 END), 0), 1)) * 100, 2
                ) as conversion_rate
            FROM videos_fuente v
            LEFT JOIN eventos_victimismo ev ON v.video_id = ev.video_id
            GROUP BY v.creador_id;
        """)
        rows = cursor.fetchall()
        for r in rows:
            print(f"  - Creador: {r['creador_id']}")
            print(
                f"    Videos Totales: {r['total_videos']} | Con Victimismo: {r['videos_con_victimismo']}"
            )
            print(f"    Víctima -> Monetización (CTA): {r['victimismo_con_cta']}")
            print(f"    Tasa de Conversión: {r['conversion_rate']}%")
    except Exception as e:
        print(f"  [FAIL] Query 1 fallida: {e}")

    # Query 2: Induced Toxicity Index (Índice de Toxicidad Inducida)
    print("\n[0x02_ANALYSIS] Índice de Toxicidad Inducida (Acoso en comentarios vs Victimismo):")
    try:
        cursor.execute("""
            SELECT 
                CASE WHEN ev.victim_id IS NOT NULL THEN 'Vídeo con Victimismo/Queja' ELSE 'Vídeo Neutral/Otros' END as tipo_video,
                COUNT(DISTINCT v.video_id) as total_videos,
                COUNT(ea.acoso_id) as total_eventos_acoso,
                ROUND(CAST(COUNT(ea.acoso_id) AS REAL) / COUNT(DISTINCT v.video_id), 2) as media_acoso_por_video
            FROM videos_fuente v
            LEFT JOIN eventos_victimismo ev ON v.video_id = ev.video_id
            LEFT JOIN eventos_acoso ea ON v.video_id = ea.video_id
            GROUP BY tipo_video;
        """)
        rows = cursor.fetchall()
        for r in rows:
            print(f"  - [{r['tipo_video']}]:")
            print(f"    Vídeos: {r['total_videos']} | Total Acoso: {r['total_eventos_acoso']}")
            print(f"    Ratio Acoso/Vídeo: {r['media_acoso_por_video']}")
    except Exception as e:
        print(f"  [FAIL] Query 2 fallida: {e}")

    # Query 3: Disonancias Filosóficas Documentadas (Broicism Friction)
    print("\n[0x03_ANALYSIS] Fricción de Coherencia Intelectual (Disonancias):")
    try:
        cursor.execute("""
            SELECT COUNT(*) as total_contradicciones FROM contradicciones_documentadas;
        """)
        total = cursor.fetchone()["total_contradicciones"]
        print(f"  - Total contradicciones documentadas en el Ledger: {total}")

        cursor.execute("""
            SELECT axioma_filosofico_declarado, accion_real_documentada, evidencia_url 
            FROM contradicciones_documentadas
            LIMIT 5;
        """)
        rows = cursor.fetchall()
        for idx, r in enumerate(rows, 1):
            print(f"    {idx}. Axioma: {r['axioma_filosofico_declarado']}")
            print(f"       Acción: {r['accion_real_documentada']}")
            print(f"       Evidencia: {r['evidencia_url']}")
    except Exception as e:
        print(f"  [FAIL] Query 3 fallida: {e}")

    print("=" * 60 + "\n")
    conn.close()


if __name__ == "__main__":
    run_analytical_suite()
