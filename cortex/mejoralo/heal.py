"""Auto-Healing capability for MEJORAlo.

Detects the files that lowered the score, delegates refactoring to an LLM agent,
runs `pytest` to ensure 100% integrity, and automatically commits or rollbacks.
"""

import asyncio
import logging
import re
import subprocess
from pathlib import Path

from cortex.llm.provider import LLMProvider
from cortex.mejoralo.types import ScanResult

logger = logging.getLogger("cortex.mejoralo.heal")

HEAL_PROMPT = """
Actúas como un Senior Engineer (Nivel 130/100).
El siguiente archivo de código Python ha bajado la puntuación de calidad (MEJORAlo Score).
A continuación te listamos los hallazgos negativos detectados:

Hallazgos:
{findings}

Tu objetivo es refactorizar el código para eliminar estos problemas, manteniendo EXACTAMENTE la misma funcionalidad, firmas y exports para no romper los tests.
Aplica principios SOBERANOS: legibilidad extrema, Zero Concept, early returns, typing estricto, abstracción de la complejidad excesiva y código puramente industrial.

Tu respuesta debe contener ÚNICAMENTE el código Python refactorizado, empezando con ```python y terminando con ```. 
NO AÑADAS EXPLICACIONES, SALUDOS NI NINGÚN OTRO TEXTO.

Código original:
```python
{code}
```
"""


def _extract_issues_from_findings(scan_result: ScanResult) -> dict[str, list[str]]:
    """Mapea los hallazgos del scan a sus respectivos archivos."""
    file_issues: dict[str, list[str]] = {}

    for d in scan_result.dimensions:
        for f in d.findings:
            rel_path = None
            if " -> " in f:
                rel_path = f.split(":", 1)[0]
            elif " LOC)" in f:
                rel_path = f.split(" (", 1)[0]

            if rel_path:
                if rel_path not in file_issues:
                    file_issues[rel_path] = []
                file_issues[rel_path].append(f"({d.name}) {f}")

    return file_issues


async def _heal_file_async(file_path: Path, findings: list[str]) -> bool:
    """Invoca al LLM para refactorizar un archivo específico."""
    content = file_path.read_text(errors="replace")

    # Try gemini, fallback to anthropic if env missing, or let LLMProvider handle it
    # We will use 'gemini' if available, otherwise 'openai' or whatever is in env
    import os

    provider_name = os.environ.get("CORTEX_LLM_PROVIDER", "anthropic")

    try:
        provider = LLMProvider(provider=provider_name)
    except (ValueError, RuntimeError, OSError) as e:
        logger.error(f"Error instanciando LLMProvider: {e}")
        return False

    prompt = HEAL_PROMPT.format(findings="- " + "\n- ".join(findings), code=content)

    try:
        response = await provider.complete(
            prompt,
            system="Eres un Senior Core Dev de CORTEX. Analizas, mutas y devuelves solo código perfecto (130/100).",
            temperature=0.1,
            max_tokens=8192,
        )
    except (RuntimeError, OSError, ValueError) as e:
        logger.error(f"Error en complete(): {e}")
        await provider.close()
        return False

    await provider.close()

    match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
    if match:
        new_code = match.group(1)
    else:
        new_code = response.replace("```python", "").replace("```", "").strip()

    if not new_code.strip():
        logger.error("El modelo devolvió código vacío.")
        return False

    file_path.write_text(new_code.strip() + "\n")
    return True


def heal_project(
    project: str, path: str | Path, target_score: int, scan_result: ScanResult
) -> bool:
    """Orquesta la autosanación: detecta, reescribe, testea y comitea recursivamente."""
    from cortex.cli import console
    from cortex.mejoralo.scan import scan

    current_result = scan_result
    iteration = 0
    max_iterations = 5  # Seguridad contra bucles infinitos
    any_success = False

    while current_result.score < target_score and iteration < max_iterations:
        iteration += 1
        console.print(
            f"\n[bold blue]🤖 Auto-Heal Iteración {iteration}/{max_iterations}[/] ({project}) "
            f"→ Score actual: [bold]{current_result.score}[/] | Meta: [bold]{target_score}[/]"
        )

        file_issues = _extract_issues_from_findings(current_result)
        if not file_issues:
            console.print("[dim yellow]⚠️ Auto-Heal: No se encontraron fallos refactorizables.[/]")
            break

        # Elegir el archivo con más peso en la caída del score
        sorted_files = sorted(file_issues.items(), key=lambda x: len(x[1]), reverse=True)
        top_file_rel, top_issues = sorted_files[0]
        
        # Limitar issues para no saturar el contexto del LLM
        top_issues = top_issues[:15]

        abs_path = Path(path).resolve() / top_file_rel
        if not abs_path.exists() or not abs_path.is_file():
            console.print(f"[dim yellow]⚠️ Auto-Heal: {top_file_rel} no disponible. Saltando...[/]")
            # Eliminar de la lista para la próxima iteración si no avanzamos
            continue

        console.print(
            f"  Refactorizando [cyan]{top_file_rel}[/] ({len(file_issues[top_file_rel])} hallazgos)..."
        )

        success = asyncio.run(_heal_file_async(abs_path, top_issues))
        if not success:
            console.print(f"  [red]❌ Generación fallida para {top_file_rel}.[/]")
            subprocess.run(["git", "restore", str(abs_path)], cwd=path, capture_output=True)
            continue

        # 🔬 Integrity Check
        console.print("  [cyan]🔬 Verificando Integridad Bizantina (pytest)...[/]")
        res = subprocess.run(["pytest"], cwd=path, capture_output=True, text=True)
        
        if res.returncode != 0:
            console.print(f"  [bold red]💥 Regresión detectada en {top_file_rel}! Rollback.[/]")
            subprocess.run(["git", "restore", str(abs_path)], cwd=path, capture_output=True)
            continue

        # ✅ Valid and Safe to commit
        commit_msg = (
            f"[MEJORAlo Auto-Heal] Refactorizado {top_file_rel} (Score: {current_result.score}→?)"
        )
        console.print("  [bold green]✅ Integridad OK. Comiteando...[/]")

        subprocess.run(["git", "add", str(abs_path)], cwd=path, capture_output=True)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                commit_msg,
                "--author",
                "CORTEX MEJORAlo Auto-Heal <cortex@moskv.1>",
            ],
            cwd=path,
            capture_output=True,
        )
        
        any_success = True

        # 🔄 Re-scan para ver el progreso real
        console.print("  [cyan]🔄 Re-escaneando para verificar impacto...[/]")
        current_result = scan(project, path)
        
        if current_result.score >= target_score:
            console.print(
                f"[bold green]✨ META ALCANZADA! Score final: {current_result.score}/100[/]"
            )
            break

    if not any_success and current_result.score < target_score:
        return False

    return True
