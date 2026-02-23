#!/usr/bin/env python3
"""
LEGION_HYDRA_UPDATE — Enjambre Paralelo Nivel 130/100
=====================================================
Optimiza y actualiza el ecosistema MOSKV-1 usando paralelismo real (asyncio).
Formación HYDRA: Hasta 20 agentes simultáneos con especialistas dedicados.
"""

import os
import sys
import json
import time
import glob
import shutil
import asyncio
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import Literal, Dict, Any, List

from dotenv import load_dotenv
load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ google-genai no instalado. Ejecuta: pip install google-genai")
    sys.exit(1)

# ─── PATHS ───────────────────────────────────────────────────────────────────
SKILLS_DIR    = Path.home() / ".gemini" / "antigravity" / "skills"
WORKFLOWS_DIR = Path.home() / "cortex" / ".agent" / "workflows"
BACKUP_DIR    = Path.home() / ".cortex" / "swarm_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE      = Path.home() / ".cortex" / "legion_hydra.log"

# ─── HYDRA CONFIG ────────────────────────────────────────────────────────────
MAX_CONCURRENCY = 2      # Más conservador para evitar 429
MAX_RETRIES     = 5
BACKOFF_BASE    = 5.0    # Backoff más agresivo
RPM_SAFE_DELAY  = 15.0   # 4 RPM aprox por agente

# ─── SPECIALIST PROMPTS ──────────────────────────────────────────────────────

ARCHITECT_PROMPT = """Eres el ArchitectSpecialist de MOSKV-1 (Sovereign Level).
TU MISIÓN: Trasponer este SKILL.md al estándar `legion-1 v5.1.0`.

REGLAS DE ORO:
1. YAML FIXED: No toques el frontmatter (entre ---).
2. CODE SECURE: No modifiques bloques de código ```.
3. INYECTA 🐝 ESPECIALISTAS: Añade una sección `## 🐝 Especialistas del Enjambre` con 3-5 agentes específicos para el dominio de este skill. Define su trigger y misión.
4. LEGIØN Lore: Refuerza la integración con LEGIØN-1 (formaciones BLITZ, PHALANX, HYDRA).
5. ZERO FLUFF: Estilo militar, denso, contundente. Si no es ejecutable o dato puro, bórralo.
6. POQ-6: Asegura que el skill mencione la infraestructura Zero-Trust y Privacy Shield.

Responde SOLO el Markdown procesado.
"""

WORKFLOW_PROMPT = """Eres el WorkflowSpecialist de MOSKV-1 (Sovereign Level).
TU MISIÓN: Evolucionar este workflow para operación autónoma avanzada.

REGLAS DE ORO:
1. YAML FIXED: No toques el frontmatter.
2. ESPECIALISTAS ACTIVADOS: Añade un bloque `### 🐝 Especialistas Activados` indicando qué agente orquesta este flujo y bajo qué condición escala a HYDRA o PHALANX.
3. TURBO ENABLED: Inserta la anotación `// turbo` sobre pasos de CLI seguros para auto-ejecución.
4. ZERO FLUFF: Limpia pasos redundantes. Hazlo "Sovereign-ready".

Responde SOLO el Markdown procesado.
"""

REFINERY_PROMPT = """Eres el PythonRefinery de MOSKV-1 (Senior Python Architect).
TU MISIÓN: Inyectar capacidades de enjambre y robustez 130/100 en este script recordándote PoQ-6.

REGLAS DE ORO:
1. NO BREAKS: Mantén la lógica original intacta.
2. SWARM DISPATCH: Si hay bucles de procesamiento (for/while) que tocan archivos/APIs, añade/sugiere un patrón de despacho paralelo vía `asyncio` o especifica un `_dispatch_specialist`.
3. POQ-6 INFRA: Implementa o refuerza el uso de Privacy Shield conceptual (anotaciones de clasificación) y asegura que NO hay `except Exception` genéricos.
4. TYPE HINTS: Añade tipado estricto donde falte.
5. LOGGING: Usa emojis ✅ ❌ ⚡ 🐝 y timestamps.

Responde SOLO el código Python. Sin fences ```python.
"""

# ─── INTERFAZ VISUAL ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def c(color: str, text: str) -> str: return f"{color}{text}{RESET}"

# ─── ENGINE ──────────────────────────────────────────────────────────────────

class SwarmEngine:
    def __init__(self, dry_run: bool = False, limit: int | None = None):
        self.dry_run = dry_run
        self.limit = limit
        self.stats = {"total": 0, "ok": 0, "skip": 0, "fail": 0, "errors": 0}
        self.start_time = time.time()
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.log_file = LOG_FILE
        
    def log(self, msg: str):
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%H:%M:%S}] {msg}\n")

    def backup(self, path: Path):
        if self.dry_run: return
        rel = path.relative_to(Path.home())
        dest = BACKUP_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    async def call_specialist(self, prompt: str, content: str, file_label: str) -> str | None:
        async with self.semaphore:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    # Pequeño delay para no saturar el socket
                    await asyncio.sleep(RPM_SAFE_DELAY)
                    
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model="gemini-2.0-flash", # Usamos flash para velocidad masiva
                        contents=[
                            types.Part.from_text(text=prompt),
                            types.Part.from_text(text=content),
                        ],
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            max_output_tokens=8192,
                        ),
                    )
                    return response.text
                except Exception as e:
                    err_str = str(e).lower()
                    wait = BACKOFF_BASE ** attempt
                    self.log(f"ERROR {file_label} (Attempt {attempt}/{MAX_RETRIES}): {e}")
                    if any(x in err_str for x in ["quota", "429", "limit", "exhausted", "503"]):
                        print(f"      {c(YELLOW, f'⚠️ API Rate Limit/Error. Retrying in {wait:.1f}s...')}")
                        await asyncio.sleep(wait)
                    else:
                        print(f"      {c(RED, f'❌ API Error inesperado: {e}')}")
                        return None
            print(f"      {c(RED, '❌ Fallo en API después de varios reintentos.')}")
            return None

    def strip_fences(self, text: str, lang: str = "") -> str:
        text = text.strip()
        for prefix in (f"```{lang}", "```"):
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    async def process_file(self, path: Path, file_type: str, index: int, total: int):
        label = path.name
        ext = path.suffix
        
        # Selección de especialista
        try:
            if label == "SKILL.md":
                prompt = ARCHITECT_PROMPT
                lang = "markdown"
            elif ext == ".md":
                prompt = WORKFLOW_PROMPT
                lang = "markdown"
            elif ext == ".py":
                prompt = REFINERY_PROMPT
                lang = "python"
            else:
                self.stats["skip"] += 1
                return
        except Exception as e:
            self.stats["errors"] += 1
            print(f"      ❌ ERROR ({path}): {str(e)}")
            return None

        content = path.read_text(encoding="utf-8", errors="ignore")
        
        # Filtro de tamaño para scripts
        if ext == ".py" and content.count("\n") < 30:
            self.stats["skip"] += 1
            return

        print(f"{c(CYAN, f'[{index:3d}/{total}]')} 🐝 Despachando {c(BOLD, file_type)}: {DIM}{path.relative_to(Path.home())}{RESET}")
        
        # Preservar frontmatter si es MD
        frontmatter = ""
        body = content
        if ext == ".md" and content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter, body = parts[1], parts[2]

        result = await self.call_specialist(prompt, body, str(path))
        
        if result:
            processed = self.strip_fences(result, lang)
            if ext == ".md":
                final_content = f"---{frontmatter}---\n{processed}\n"
            else:
                final_content = processed + "\n"
            
            if not self.dry_run:
                self.backup(path)
                path.write_text(final_content, encoding="utf-8")
                print(f"      {c(GREEN, '✅ Mutado con éxito')}")
            else:
                print(f"      {c(YELLOW, '🔍 (Dry-run) Simulado')}")
            
            self.stats["ok"] += 1
            self.log(f"OK {path}")
        else:
            print(f"      {c(RED, '❌ Fallo en API')}")
            self.stats["fail"] += 1

    async def run(self):
        # Recolección
        targets = []
        # 1. Skills
        for p in SKILLS_DIR.glob("*/SKILL.md"): targets.append((p, "🧬 SKILL"))
        # 2. Workflows
        for p in WORKFLOWS_DIR.glob("*.md"): targets.append((p, "⚡ FLOW"))
        # 3. Scripts
        for p in SKILLS_DIR.glob("*/scripts/*.py"): targets.append((p, "🐍 PY"))
        for p in SKILLS_DIR.glob("*/*.py"): 
            if p.name != "SKILL.md": targets.append((p, "🐍 PY"))

        targets = sorted(list(set(targets))) # Dedup y sort
        if self.limit:
            targets = targets[:self.limit]
            
        self.stats["total"] = len(targets)
        
        print(f"\n{c(BOLD, '🐉 FORMACIÓN HYDRA ACTIVADA')}")
        print(f"   Targets: {c(BOLD, str(len(targets)))} archivos")
        print(f"   Backup:  {BACKUP_DIR}")
        print(f"   Swarm:   {MAX_CONCURRENCY} agentes paralelos\n")

        if not self.dry_run: BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        tasks = []
        for i, (path, ftype) in enumerate(targets, 1):
            tasks.append(self.process_file(path, ftype, i, len(targets)))
            
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - self.start_time
        mins, secs = divmod(int(elapsed), 60)
        
        print(f"\n{'─'*60}")
        print(f"{c(BOLD, '📊 RESUMEN HYDRA')}")
        print(f"  ✅ OK:      {self.stats['ok']}")
        print(f"  ⏭  SKIP:    {self.stats['skip']}")
        print(f"  ❌ FAIL:    {self.stats['fail']}")
        print(f"  ⏱  TIEMPO:  {mins}m {secs}s")
        print(f"{'─'*60}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    
    engine = SwarmEngine(dry_run=args.dry_run, limit=args.limit)
    asyncio.run(engine.run())
