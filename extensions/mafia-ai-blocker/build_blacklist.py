# [C5-REAL] Exergy-Maximized
import csv
import json
from pathlib import Path

# Script para inyectar el Smoke Index dentro de la extensión del navegador
CSV_PATH = Path("data/reputation_graph/smoke_index_report.csv")
JS_OUTPUT = Path("extensions/mafia-ai-blocker/blacklist.js")
THRESHOLD = 10.0


def build():
    if not CSV_PATH.exists():
        print("[!] CSV no encontrado.")
        return

    blocked_nodes = []

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if float(row["Smoke_Index"]) > THRESHOLD:
                blocked_nodes.append(row["Node"].lower())

    js_content = f"// AUTO-GENERATED C5-REAL BLACKLIST\nconst MAFIA_AI_BLACKLIST = {json.dumps(blocked_nodes)};\n"

    with open(JS_OUTPUT, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"[*] Blacklist JS generada con {len(blocked_nodes)} nodos bloqueados.")


if __name__ == "__main__":
    build()
