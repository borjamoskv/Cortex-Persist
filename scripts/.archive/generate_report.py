import json
import os
import sqlite3

DB_PATH = "influencer_audit_v1.db"
OUTPUT_HTML = "report_influencer_audit.html"


def get_analytics_data():
    """Recupera los datos de la base de datos y los retorna en formato estructurado para JS."""
    if not os.path.exists(DB_PATH):
        return {"creadores": [], "toxicidad": [], "contradicciones": []}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Rage-to-Revenue data
    creadores = []
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
        creadores = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[ERROR] Query 1 fallida: {e}")

    # 2. Toxicidad Data
    toxicidad = []
    try:
        cursor.execute("""
            SELECT taxonomia_ataque, COUNT(*) as count 
            FROM eventos_acoso 
            GROUP BY taxonomia_ataque;
        """)
        toxicidad = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[ERROR] Query 2 fallida: {e}")

    # 3. Contradicciones
    contradicciones = []
    try:
        cursor.execute("""
            SELECT axioma_filosofico_declarado, accion_real_documentada, evidencia_url 
            FROM contradicciones_documentadas;
        """)
        contradicciones = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[ERROR] Query 3 fallida: {e}")

    conn.close()
    return {"creadores": creadores, "toxicidad": toxicidad, "contradicciones": contradicciones}


def generate_html_report():
    """Genera el dashboard HTML interactivo bajo la estética Industrial Noir 2026."""
    data = get_analytics_data()

    html_content = f"""<!DOCTYPE html>
<html lang="es" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ecosistema de Influencia Digital - Análisis Estructural</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Outfit:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        body {{
            background-color: #0A0A0A;
            color: #E5E5E5;
            font-family: 'Inter', sans-serif;
        }}
        .font-title {{
            font-family: 'Outfit', sans-serif;
        }}
        .border-neon {{
            border-color: #2B3BE5;
        }}
        .text-neon {{
            color: #2B3BE5;
        }}
        .bg-card {{
            background-color: #121212;
            border: 1px solid #1E1E1E;
        }}
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between py-8 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto w-full">
        <!-- Header -->
        <header class="border-b border-1e1e1e pb-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center">
            <div>
                <span class="text-xs font-semibold tracking-widest text-neon uppercase">C5-REAL // REPORT ENGINE</span>
                <h1 class="text-4xl font-bold font-title mt-1 tracking-tight text-white">Mercantilización del Agravio</h1>
                <p class="text-sm text-gray-500 mt-1">Análisis estructural y empírico del ecosistema de polarización digital.</p>
            </div>
            <div class="mt-4 md:mt-0 bg-card px-4 py-2 rounded text-xs text-gray-400">
                Ledger State: <span class="text-green-500 font-mono">SYNCHRONIZED</span>
            </div>
        </header>

        <!-- Grid de Métricas Principales -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-card p-6 rounded-lg">
                <span class="text-xs text-gray-500 uppercase tracking-wider">Creadores Auditados</span>
                <div class="text-3xl font-bold font-title text-white mt-2">{
        len(data["creadores"])
    }</div>
            </div>
            <div class="bg-card p-6 rounded-lg">
                <span class="text-xs text-gray-500 uppercase tracking-wider">Ataques Catalogados</span>
                <div class="text-3xl font-bold font-title text-white mt-2">{
        sum(t["count"] for t in data["toxicidad"])
    }</div>
            </div>
            <div class="bg-card p-6 rounded-lg">
                <span class="text-xs text-gray-500 uppercase tracking-wider">Disonancias Discursivas</span>
                <div class="text-3xl font-bold font-title text-white mt-2">{
        len(data["contradicciones"])
    }</div>
            </div>
        </section>

        <!-- Gráficos -->
        <section class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            <div class="bg-card p-6 rounded-lg">
                <h2 class="text-lg font-bold font-title text-white mb-4">Conversión Rage-to-Revenue (%)</h2>
                <div class="h-64 relative">
                    <canvas id="conversionChart"></canvas>
                </div>
            </div>
            <div class="bg-card p-6 rounded-lg">
                <h2 class="text-lg font-bold font-title text-white mb-4">Taxonomía del Agresor</h2>
                <div class="h-64 relative">
                    <canvas id="taxonomyChart"></canvas>
                </div>
            </div>
        </section>

        <!-- Tabla de Contradicciones -->
        <section class="bg-card p-6 rounded-lg mb-8">
            <h2 class="text-xl font-bold font-title text-white mb-4 border-b border-neutral-800 pb-2">Disonancia Discursiva (Contradicciones Documentadas)</h2>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-neutral-800">
                    <thead>
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Axioma Declarado</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Acción Real Documentada</th>
                            <th class="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Evidencia / URL</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-neutral-800">
                        <!-- Inyección dinámica de contradicciones -->
                        {
        "".join(
            f'''
                        <tr>
                            <td class="px-6 py-4 text-sm font-semibold text-white">{c["axioma_filosofico_declarado"]}</td>
                            <td class="px-6 py-4 text-sm text-gray-300">{c["accion_real_documentada"]}</td>
                            <td class="px-6 py-4 text-sm text-neon font-mono"><a href="{c["evidencia_url"]}" target="_blank" class="hover:underline">{c["evidencia_url"]}</a></td>
                        </tr>
                        '''
            for c in data["contradicciones"]
        )
    }
                    </tbody>
                </table>
            </div>
        </section>
    </div>

    <!-- Footer -->
    <footer class="max-w-7xl mx-auto w-full border-t border-neutral-900 pt-6 text-center text-xs text-gray-600">
        <p>Aesthetic Engine: Industrial Noir 2026 | Operator: borjamoskv</p>
    </footer>

    <!-- Chart Configuration -->
    <script>
        const rawData = {json.dumps(data)};
        
        // Render Rage-to-Revenue Chart
        const ctxConv = document.getElementById('conversionChart').getContext('2d');
        new Chart(ctxConv, {{
            type: 'bar',
            data: {{
                labels: rawData.creadores.map(c => c.creador_id),
                datasets: [{{
                    label: 'Ratio de Conversión (%)',
                    data: rawData.creadores.map(c => c.conversion_rate),
                    backgroundColor: '#2B3BE5',
                    borderColor: '#2B3BE5',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: '#1E1E1E' }},
                        ticks: {{ color: '#888' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#888' }}
                    }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});

        // Render Taxonomy Chart
        const ctxTax = document.getElementById('taxonomyChart').getContext('2d');
        new Chart(ctxTax, {{
            type: 'doughnut',
            data: {{
                labels: rawData.toxicidad.map(t => t.taxonomia_ataque),
                datasets: [{{
                    data: rawData.toxicidad.map(t => t.count),
                    backgroundColor: ['#2B3BE5', '#1E1E1E', '#3E3E3E'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: '#888', font: {{ family: 'Inter' }} }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[C5-REAL] Dashboard HTML exitosamente generado en: {OUTPUT_HTML}")


if __name__ == "__main__":
    generate_html_report()
