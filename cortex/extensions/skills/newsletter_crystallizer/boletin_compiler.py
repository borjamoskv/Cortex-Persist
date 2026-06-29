import os
import subprocess
import datetime
from pathlib import Path

# C5-REAL: SOTA-Vector-Engine-Omega Execution
HOME_DIR = Path(os.path.expanduser('~'))
CORTEX_ROOT = HOME_DIR / "30_CORTEX"
SKILL_DIR = CORTEX_ROOT / "cortex/extensions/skills/newsletter_crystallizer"
BOCETOS_DIR = HOME_DIR / "BOCETOS"

def get_cortex_commits():
    try:
        # Extraemos los commits de los últimos 3 días (72h)
        res = subprocess.run(["git", "log", "--since=3 days ago", "--oneline"], cwd=CORTEX_ROOT, capture_output=True, text=True, check=True)
        commits = res.stdout.strip()
        if not commits:
            return "- [SYSTEM] Sin mutaciones en las últimas 72h."
        return "\n".join([f"- `{c.split(' ', 1)[0]}` {c.split(' ', 1)[1]}" for c in commits.split("\n") if c])
    except Exception as e:
        return f"- [ERROR] Fallo al extraer Sentinel Logs: {e}"

def generate_newsletter():
    # En un entorno C5 completo, aquí inyectamos `cortex autodidact` o firecrawl
    # Para el Issue #1, usaremos el SOTA Crystal ya generado como fallback.
    
    # 1. Leer Template
    template_path = SKILL_DIR / "newsletter_template.md"
    if not template_path.exists():
        print("Falta el template.")
        return
        
    template = template_path.read_text()
    
    # 2. CORTEX Commits
    cortex_commits = get_cortex_commits()
    
    # 3. SOTA Vectors (Mockup para la prueba, en prod se extrae vía LLM)
    sota_vectors = """### 1. Vector Open-Weight & Foundation Models
- **GPT-5.5 Cyber / GPT-5.6:** Frecuencia de despliegue acelerada.
- **Claude Fable 5 & Opus 4.8:** Iteraciones en Test Time Compute.

### 2. Vector Infraestructura & Hardware
- **SpaceX Colossus Deal:** Datacenters satelitales masivos.
- **Nvidia N1X:** Nueva arquitectura de red superando B200.

### 3. Vector Agentic & Tooling
- **Codex as Workspace:** Entorno de desarrollo nativo.
- **Loop Engineering:** Swarm Architecture desplazando al prompt engineering."""
    
    # 4. Compilar
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    issue_num = 1
    
    compiled = template.replace("{ISSUE_NUMBER}", str(issue_num))
    compiled = compiled.replace("{DATE}", date_str)
    compiled = compiled.replace("{SOTA_VECTORS}", sota_vectors)
    compiled = compiled.replace("{CORTEX_COMMITS}", cortex_commits)
    
    # 5. Escribir en BOCETOS
    output_path = BOCETOS_DIR / f"SOTA_CRYSTAL_Issue_{issue_num}.md"
    output_path.write_text(compiled)
    print(f"[C5-REAL] Boletín compilado exitosamente en: {output_path}")

if __name__ == "__main__":
    generate_newsletter()
