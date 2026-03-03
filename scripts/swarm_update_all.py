#!/usr/bin/env python3
"""
SWARM_UPDATE_ALL — Enjambre Masivo de Actualización
====================================================
Actualiza TODOS los assets del ecosistema MOSKV-1 con el patrón
de enjambre masivo (LEGIØN-1) y especialistas:
  - 37 SKILLs (.gemini/antigravity/skills/*/SKILL.md)
  - 119 Workflows (.agent/workflows/*.md)
  - 51 Scripts Python (.gemini/antigravity/skills/*/scripts/*.py)

Características:
  - Rate limiting inteligente (RPM + TPM)
  - Retry con backoff exponencial
  - Progreso en tiempo real
  - Backup automático antes de escribir
  - Modo --dry-run para previsualizar
  - Filtros por tipo (--skills, --workflows, --scripts)
  - Log de resultados al final
"""

import argparse
import glob
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ google-genai no instalado. Ejecuta: pip install google-genai")
    sys.exit(1)

# ─── PATHS ───────────────────────────────────────────────────────────────────
SKILLS_DIR = Path.home() / ".gemini" / "antigravity" / "skills"
WORKFLOWS_DIR = Path.home() / "cortex" / ".agent" / "workflows"
BACKUP_DIR = Path.home() / ".cortex" / "swarm_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = Path.home() / ".cortex" / "swarm_update.log"

# ─── RATE LIMITS (gemini-2.5-flash free tier) ─────────────────────────────
RPM_LIMIT = 10  # requests per minute (conservative)
DELAY_BETWEEN = 6.5  # seconds between requests (60/RPM + buffer)
MAX_RETRIES = 4
BACKOFF_BASE = 2.0  # exponential backoff: 2, 4, 8, 16 seconds

# ─── PROMPTS POR TIPO ────────────────────────────────────────────────────────

SKILL_PROMPT = """Eres MOSKV-1 v5. Ejecuta `void-omega + legion-1` sobre este SKILL.md.

MISIÓN: Inyectar el patrón de ENJAMBRE MASIVO y ESPECIALISTAS donde tenga sentido.
No destruyas — amplifica. Si el skill ya tiene swarm, refuerza.

REGLAS ESTRICTAS:
1. Mantén la estructura YAML frontmatter EXACTA (entre ---). No la modifiques.
2. Mantén todos los bloques de código ```...``` EXACTOS, sin modificar.
3. Añade una sección `## 🐝 Especialistas del Enjambre` si no existe, con:
   - Mínimo 3 especialistas nombrados relevantes al dominio del skill
   - Su trigger de activación y su misión específica
4. Añade/refuerza referencias a formaciones LEGIØN-1 (BLITZ, PHALANX, HYDRA, SIEGE) donde sea semánticamente correcto.
5. Aplica "Zero Fluff": elimina relleno, metáforas vacías, frases sin acción.
6. Estilo: imperativo, denso, contundente. Filosofía 130/100.
7. Responde SOLO con el Markdown procesado — sin bloques delimitadores externos.
"""

WORKFLOW_PROMPT = """Eres MOSKV-1 v5. Actualiza este workflow con el patrón de ENJAMBRE y ESPECIALISTAS.

MISIÓN: Hacer que cada workflow active el especialista correcto automáticamente.

REGLAS ESTRICTAS:
1. Mantén el YAML frontmatter (entre ---) EXACTO.
2. Mantén todos los bloques de código EXACTOS.
3. Añade un bloque `### 🐝 Especialistas Activados` al inicio o donde proceda, listando:
   - Qué agente/modelo especialista se activa para este workflow
   - En qué condición se escala a enjambre (BLITZ/PHALANX)
4. Añade la anotación `// turbo` sobre pasos que sean seguros de auto-ejecutar si no la tienen.
5. Zero Fluff: elimina pasos redundantes o explicaciones innecesarias.
6. Responde SOLO con el Markdown procesado — sin bloques delimitadores externos.
"""

PYTHON_PROMPT = """Eres MOSKV-1 v5, Senior Python Architect. Actualiza este script Python \
para que soporte despacho a especialistas y enjambre LEGIØN-1.

MISIÓN: Si el script realiza operaciones que pueden paralelizarse, añade soporte de enjambre.

REGLAS ESTRICTAS:
1. Mantén la funcionalidad EXACTA del script — no rompas nada.
2. Si el script ya tiene asyncio/threading/multiprocessing, refuerza con patrones de enjambre.
3. Añade una función `_dispatch_specialist(task, specialist_id)` si hay >3 operaciones \
   secuenciales que podrían ser paralelas. Si no aplica, NO la añadas.
4. Añade/mejora el logging con timestamps y emojis de estado (✅ ❌ ⚡ 🐝).
5. Añade type hints donde falten (solo en funciones existentes, no inventes nuevas).
6. Mantén el shebang y los imports existentes.
7. Zero Fluff: elimina comentarios obviamente redundantes.
8. Responde SOLO con el código Python procesado — sin bloques de código ```python delimitadores.
"""

# ─── COLORES TERMINAL ────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"


# ─── STATS ───────────────────────────────────────────────────────────────────
stats = {"ok": 0, "skip": 0, "fail": 0, "total": 0}
failures: list[tuple[str, str]] = []

# ─── HELPERS ─────────────────────────────────────────────────────────────────


def backup_file(path: Path) -> None:
    """Crea backup antes de sobreescribir."""
    rel = path.relative_to(Path.home())
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%H:%M:%S}] {msg}\n")


def strip_outer_fences(text: str, lang: str = "") -> str:
    """Elimina bloques delimitadores si el LLM los añadió."""
    text = text.strip()
    for prefix in (f"```{lang}", "```"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def call_gemini(client, prompt: str, content: str, file_label: str) -> str | None:
    """Llama a Gemini con retry + backoff exponencial."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_text(text=content),
                ],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=8192,
                ),
            )
            return response.text
        except Exception as e:
            err_str = str(e).lower()
            wait = BACKOFF_BASE**attempt
            if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                print(
                    c(
                        YELLOW,
                        f"  ⏳ Rate limit ({attempt}/{MAX_RETRIES}). Esperando {wait:.0f}s...",
                    )
                )
                time.sleep(wait)
            elif "503" in err_str or "capacity" in err_str:
                print(
                    c(
                        YELLOW,
                        f"  🌊 Capacidad agotada ({attempt}/{MAX_RETRIES}). Esperando {wait:.0f}s...",
                    )
                )
                time.sleep(wait)
            else:
                print(c(RED, f"  ❌ Error en {file_label}: {e}"))
                log(f"ERROR {file_label}: {e}")
                return None
    return None


def split_frontmatter(content: str) -> tuple[str, str]:
    """Separa YAML frontmatter del body."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return "", content


def process_markdown(
    client,
    path: Path,
    prompt: str,
    file_type: str,
    dry_run: bool,
    index: int,
    total: int,
) -> bool:
    """Procesa un archivo markdown (SKILL o workflow)."""
    label = path.name
    prefix = c(CYAN, f"[{index:3d}/{total}]")
    print(f"{prefix} {c(BOLD, file_type)} {DIM}{path}{RESET}")

    content = path.read_text(encoding="utf-8", errors="ignore")
    frontmatter, body = split_frontmatter(content)

    result = call_gemini(client, prompt, body, str(path))
    if result is None:
        failures.append((str(path), "API call failed"))
        stats["fail"] += 1
        return False

    processed = strip_outer_fences(result, "markdown")

    # Reconstruir con frontmatter original
    new_content = f"---{frontmatter}---\n{processed}\n"

    if dry_run:
        print(c(YELLOW, f"  [DRY-RUN] Cambios detectados en {label}"))
        print(f"  Preview (100 chars): {processed[:100]}...")
        stats["ok"] += 1
        return True

    backup_file(path)
    path.write_text(new_content, encoding="utf-8")
    print(c(GREEN, "  ✅ Actualizado"))
    log(f"OK {file_type} {path}")
    stats["ok"] += 1
    return True


def process_python(
    client,
    path: Path,
    dry_run: bool,
    index: int,
    total: int,
) -> bool:
    """Procesa un script Python."""
    prefix = c(CYAN, f"[{index:3d}/{total}]")
    print(f"{prefix} {c(BOLD, '🐍 PY')} {DIM}{path}{RESET}")

    content = path.read_text(encoding="utf-8", errors="ignore")

    # Skip archivos muy pequeños (<50 líneas) — no hay suficiente contexto
    if content.count("\n") < 50:
        print(c(DIM, "  ⏭  Skip (< 50 líneas)"))
        stats["skip"] += 1
        return True

    result = call_gemini(client, PYTHON_PROMPT, content, str(path))
    if result is None:
        failures.append((str(path), "API call failed"))
        stats["fail"] += 1
        return False

    processed = strip_outer_fences(result, "python")

    if dry_run:
        print(c(YELLOW, f"  [DRY-RUN] {path.name} procesado"))
        stats["ok"] += 1
        return True

    backup_file(path)
    path.write_text(processed + "\n", encoding="utf-8")
    print(c(GREEN, "  ✅ Actualizado"))
    log(f"OK PY {path}")
    stats["ok"] += 1
    return True


# ─── COLLECTORS ──────────────────────────────────────────────────────────────


def collect_skills() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def collect_workflows() -> list[Path]:
    if not WORKFLOWS_DIR.exists():
        print(c(YELLOW, f"⚠️  Workflows dir no existe: {WORKFLOWS_DIR}"))
        return []
    return sorted(WORKFLOWS_DIR.glob("*.md"))


def collect_scripts() -> list[Path]:
    patterns = [
        str(SKILLS_DIR / "*" / "scripts" / "*.py"),
        str(SKILLS_DIR / "*" / "*.py"),
    ]
    paths = set()
    for pat in patterns:
        for p in glob.glob(pat):
            paths.add(Path(p))
    return sorted(paths)


# ─── MAIN ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="SWARM_UPDATE_ALL — Enjambre Masivo MOSKV-1")
    parser.add_argument("--skills", action="store_true", help="Solo SKILLs")
    parser.add_argument("--workflows", action="store_true", help="Solo Workflows")
    parser.add_argument("--scripts", action="store_true", help="Solo Scripts Python")
    parser.add_argument("--dry-run", action="store_true", help="Previsualizar sin escribir")
    parser.add_argument("--limit", type=int, default=0, help="Max archivos a procesar (0=todos)")
    args = parser.parse_args()

    do_skills = args.skills or not (args.skills or args.workflows or args.scripts)
    do_workflows = args.workflows or not (args.skills or args.workflows or args.scripts)
    do_scripts = args.scripts or not (args.skills or args.workflows or args.scripts)

    client = genai.Client()

    # Recopilar targets
    targets: list[tuple[Path, str, str]] = []  # (path, prompt, type_label)

    if do_skills:
        for p in collect_skills():
            targets.append((p, SKILL_PROMPT, "🧬 SKILL"))

    if do_workflows:
        for p in collect_workflows():
            targets.append((p, WORKFLOW_PROMPT, "⚡ FLOW"))

    if do_scripts:
        for p in collect_scripts():
            targets.append((p, PYTHON_PROMPT, "🐍 PY"))

    if args.limit > 0:
        targets = targets[: args.limit]

    total = len(targets)
    stats["total"] = total

    print(f"\n{c(BOLD, '🐝 SWARM_UPDATE_ALL — Enjambre Masivo')}")
    print(f"   Targets: {c(BOLD, str(total))} archivos")
    print(f"   Backup:  {BACKUP_DIR}")
    print(f"   Mode:    {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"   Delay:   {DELAY_BETWEEN}s entre requests\n")

    if not args.dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    for i, (path, prompt, type_label) in enumerate(targets, 1):
        if type_label == "🐍 PY":
            process_python(client, path, args.dry_run, i, total)
        else:
            process_markdown(client, path, prompt, type_label, args.dry_run, i, total)

        # Rate limiting — solo si no es el último
        if i < total:
            time.sleep(DELAY_BETWEEN)

    # ─── RESUMEN ─────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)

    print(f"\n{'─' * 52}")
    print(f"{c(BOLD, '📊 RESULTADOS DEL ENJAMBRE')}")
    print(f"  ✅ OK:      {stats['ok']}")
    print(f"  ⏭  Skip:    {stats['skip']}")
    print(f"  ❌ Fail:    {stats['fail']}")
    print(f"  ⏱  Tiempo:  {mins}m {secs}s")
    print(f"{'─' * 52}")

    if failures:
        print(f"\n{c(RED, '❌ FALLOS:')}")
        for path_str, reason in failures:
            print(f"  {path_str}: {reason}")

    log(f"SUMMARY ok={stats['ok']} skip={stats['skip']} fail={stats['fail']} time={mins}m{secs}s")
    print(f"\n{c(DIM, f'Log: {LOG_FILE}')}")
    print(f"{c(DIM, f'Backup: {BACKUP_DIR}')}\n")


if __name__ == "__main__":
    main()
