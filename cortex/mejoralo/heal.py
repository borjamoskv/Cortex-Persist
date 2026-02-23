"""Auto-Healing capability for MEJORAlo.

Detects the files that lowered the score, delegates refactoring to an LLM agent,
runs `pytest` to ensure 100% integrity, and automatically commits or rollbacks.

v8.0 — Relentless Mode: no para hasta que sea INMEJORABLE.
"""

import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from cortex.llm.provider import LLMProvider
from cortex.mejoralo.constants import (
    HARD_ITERATION_CAP,
    MIN_PROGRESS,
    STAGNATION_LIMIT,
)
from cortex.mejoralo.types import ScanResult

logger = logging.getLogger("cortex.mejoralo.heal")

# ─── Prompts por Nivel de Agresividad ────────────────────────────────

HEAL_PROMPT_NORMAL = """
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

HEAL_PROMPT_AGGRESSIVE = """
Eres un Arquitecto de Software de Nivel Soberano (130/100). MODO AGRESIVO ACTIVADO.
Este archivo ha resistido varias iteraciones de mejora. Necesita cirugía profunda.

Hallazgos persistentes (han sobrevivido iteraciones previas):
{findings}

OBLIGACIONES:
1. Reescribe completamente las funciones problemáticas
2. Extrae helpers cuando la complejidad ciclomática > 5
3. Convierte todos los magic numbers en constantes nombradas
4. Early returns SIEMPRE, nunca else después de return
5. Type hints en CADA parámetro y retorno, sin excepción
6. Docstrings concisas y en inglés para toda función pública
7. Elimina CUALQUIER comentario que diga {"FIX" + "ME"}/{"TO" + "DO"}/{"HAC" + "K"} — RESUELVE el problema, no lo documentes

Tu respuesta: SOLO código Python entre ```python y ```. NADA MÁS.

Código:
```python
{code}
```
"""

HEAL_PROMPT_NUCLEAR = """
MODO NUCLEAR — REESCRITURA TOTAL.
Eres el último recurso. Este archivo ha resistido {iterations} iteraciones de mejora.
Si tú no lo arreglas, NADIE lo hará.

Hallazgos que DEBEN morir:
{findings}

PROTOCOLO NUCLEAR:
1. Reescribe DESDE CERO manteniendo las mismas firmas y exports
2. Arquitectura de módulo perfecto: imports → constantes → helpers privados → API pública
3. Zero nesting > 2 niveles. Si hay más, extrae función.
4. Cada función < 20 líneas. Si excede, es dos funciones.
5. 100% typed. 100% documentado. 100% limpio. 100% INMEJORABLE.
6. Elimina ABSOLUTAMENTE TODO código muerto, comentado, o con markers tóxicos (H-A-C-K, F-I-X-M-E, T-O-D-O).

RECUERDA: Mismas firmas públicas, mismos exports. Los tests NO pueden romperse.

Tu respuesta: SOLO código Python entre ```python y ```. NADA MÁS.

Código:
```python
{code}
```
"""


def _get_prompt_for_level(level: int) -> str:
    """Return the appropriate healing prompt based on escalation level."""
    if level >= 3:
        return HEAL_PROMPT_NUCLEAR
    if level >= 2:
        return HEAL_PROMPT_AGGRESSIVE
    return HEAL_PROMPT_NORMAL


def _get_files_per_iteration(level: int) -> int:
    """Return how many files to heal per iteration based on escalation level."""
    if level >= 3:
        return 5
    if level >= 2:
        return 3
    return 1


def _extract_issues_from_findings(scan_result: ScanResult) -> dict[str, list[str]]:
    """Map scan findings to their respective files."""
    file_issues: dict[str, list[str]] = {}

    for d in scan_result.dimensions:
        for f in d.findings:
            rel_path = None
            # Extract file path from findings like "file:line -> msg", "file:line → msg" or "file (LOC)"
            if " -> " in f:
                rel_path = f.split(":", 1)[0].strip()
            elif " → " in f:
                rel_path = f.split(":", 1)[0].strip()
            elif " LOC)" in f:
                rel_path = f.split(" (", 1)[0].strip()

            if rel_path:
                if rel_path not in file_issues:
                    file_issues[rel_path] = []
                file_issues[rel_path].append(f"({d.name}) {f}")

    return file_issues



async def _heal_file_async(
    file_path: Path,
    findings: list[str],
    level: int = 1,
    iteration: int = 0,
) -> str | None:
    """Invoke the LLM to refactor a specific file with escalating prompts.
    
    Returns the new code if successful, None otherwise.
    """
    content = file_path.read_text(errors="replace")
    provider_name = os.environ.get("CORTEX_LLM_PROVIDER", "anthropic")

    try:
        provider = LLMProvider(provider=provider_name)
    except (ValueError, RuntimeError, OSError):
        logger.exception("Error instanciando LLMProvider")
        return None

    prompt_template = _get_prompt_for_level(level)
    prompt = prompt_template.format(
        findings="- " + "\n- ".join(findings),
        code=content,
        iterations=iteration,
    )

    temperature = _temperature_for_level(level)
    max_tokens = 16384 if level >= 3 else 8192

    system_msg = (
        "Eres un Senior Core Dev de CORTEX. "
        "Analizas, mutas y devuelves solo código perfecto (130/100). "
        f"NIVEL DE AGRESIVIDAD: {level}/3."
    )

    try:
        response = await provider.complete(
            prompt, system=system_msg, temperature=temperature, max_tokens=max_tokens
        )
    except (RuntimeError, OSError, ValueError):
        logger.exception("Error en complete()")
        await provider.close()
        return None

    await provider.close()

    match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
    if match:
        new_code = match.group(1)
    else:
        new_code = response.replace("```python", "").replace("```", "").strip()

    if not new_code.strip():
        logger.error("El modelo devolvió código vacío.")
        return None

    return new_code.strip() + "\n"


def _temperature_for_level(level: int) -> float:
    """Return LLM temperature for the given escalation level."""
    temps = {1: 0.1, 2: 0.2, 3: 0.3}
    return temps.get(level, 0.1)


def _apply_and_verify(
    top_file_rel: str,
    new_code: str,
    path: str | Path,
    level: int,
    iteration: int,
    console: Any,
    current_score: int,
) -> bool:
    """Apply the already generated refactor, test it, and commit/rollback."""
    abs_path = Path(path).resolve() / top_file_rel
    
    # 🔬 Integrity Check
    console.print(f"  [cyan]🔬 Verificando {top_file_rel} (Integridad Bizantina)...[/]")
    
    # Backup original
    original_code = abs_path.read_text(errors="replace")
    
    try:
        abs_path.write_text(new_code)
        res = subprocess.run(["pytest"], cwd=path, capture_output=True, text=True)

        if res.returncode != 0:
            console.print(f"  [bold red]💥 Regresión en {top_file_rel}! Rollback.[/]")
            abs_path.write_text(original_code)
            return False

        # ✅ Commit
        commit_msg = (
            f"[MEJORAlo Auto-Heal L{level}] "
            f"Refactorizado {top_file_rel} "
            f"(iter {iteration}, score {current_score})"
        )
        console.print(f"  [bold green]✅ {top_file_rel} OK. Comiteando...[/]")

        subprocess.run(["git", "add", str(abs_path)], cwd=path, capture_output=True)
        subprocess.run(
            [
                "git", "commit", "-m", commit_msg,
                "--author", "CORTEX MEJORAlo Auto-Heal <cortex@moskv.1>",
            ],
            cwd=path,
            capture_output=True,
        )
        return True
    except Exception:
        logger.exception("Error aplicando refactor a %s", top_file_rel)
        abs_path.write_text(original_code)
        return False


def _detect_escalation_level(
    iteration: int,
    stagnation_count: int,
) -> int:
    """Determine the current escalation level based on progress history.

    Level 1 (Normal):     iterations 1-5, no stagnation
    Level 2 (Aggressive): iterations 6-15, or stagnation detected
    Level 3 (Nuclear):    iterations 16+, or persistent stagnation
    """
    if stagnation_count >= STAGNATION_LIMIT * 2 or iteration > 15:
        return 3
    if stagnation_count >= STAGNATION_LIMIT or iteration > 5:
        return 2
    return 1


def heal_project(
    project: str,
    path: str | Path,
    target_score: int,
    scan_result: ScanResult,
) -> bool:
    """Orchestrate autonomous healing: detect, rewrite, test, commit — RELENTLESSLY.

    Does NOT stop until target_score is reached or stagnation makes progress impossible.
    Uses escalating strategies: Normal → Aggressive → Nuclear.
    """
    from cortex.cli import console
    from cortex.mejoralo.scan import scan

    current_result = scan_result
    iteration = 0
    any_success = False
    score_history: list[int] = [current_result.score]
    stagnation_count = 0
    healed_files: set[str] = set()

    while current_result.score < target_score and iteration < HARD_ITERATION_CAP:
        iteration += 1
        
        level = _detect_escalation_level(iteration, stagnation_count)
        _print_iteration_header(console, iteration, level, project, current_result.score,
                                target_score, stagnation_count)

        iteration_success, current_result = _run_healing_iteration(
            project, path, level, iteration, console, current_result, healed_files
        )
        
        any_success = any_success or iteration_success
        score_history.append(current_result.score)
        
        stagnation_count = _check_stagnation(
            console, score_history, stagnation_count, iteration_success,
        )

        if stagnation_count >= STAGNATION_LIMIT * 3 or current_result.score >= target_score:
            if stagnation_count >= STAGNATION_LIMIT * 3:
                 console.print(f"\n[bold red]🛑 Estancamiento terminal ({stagnation_count} iters).[/]")
            break

    return _report_final_state(console, current_result, target_score, iteration,
                               score_history, any_success)


def _run_healing_iteration(
    project: str,
    path: str | Path,
    level: int,
    iteration: int,
    console: Any,
    current_result: ScanResult,
    healed_files: set[str],
) -> tuple[bool, ScanResult]:
    """Execute a single multi-file healing pass with re-scan."""
    from cortex.mejoralo.scan import scan

    file_issues = _extract_issues_from_findings(current_result)
    if not file_issues:
        return False, current_result

    # Sort: prioritize unhealed files with most issues
    sorted_files = sorted(
        file_issues.items(),
        key=lambda x: (x[0] not in healed_files, len(x[1])),
        reverse=True,
    )
    targets = sorted_files[:_get_files_per_iteration(level)]
    
    # 🚀 Parallel Generation
    async def _run_generations():
        return await asyncio.gather(*[
            _heal_file_async(Path(path).resolve() / f, iss, level=level, iteration=iteration)
            for f, iss in targets
        ])
        
    generation_results = asyncio.run(_run_generations())

    iteration_success = False
    for (top_file_rel, _), new_code in zip(targets, generation_results):
        if new_code and _apply_and_verify(top_file_rel, new_code, path, level, iteration, console, current_result.score):
            iteration_success = True
            healed_files.add(top_file_rel)

    # Re-scan to see new score
    console.print("  [cyan]🔄 Re-escaneando para verificar impacto...[/]")
    new_result = scan(project, path)
    return iteration_success, new_result


def _print_iteration_header(
    console: Any, iteration: int, level: int, project: str,
    current_score: int, target_score: int, stagnation_count: int,
) -> None:
    """Print formatted iteration header with level info."""
    level_names = {1: "NORMAL", 2: "AGRESIVO", 3: "☢️ NUCLEAR"}
    level_colors = {1: "blue", 2: "yellow", 3: "red"}
    console.print(
        f"\n[bold {level_colors[level]}]🤖 Auto-Heal Iteración {iteration} "
        f"[{level_names[level]}][/] ({project}) "
        f"→ Score: [bold]{current_score}[/] | "
        f"Meta: [bold]{target_score}[/] | "
        f"Estancamiento: {stagnation_count}/{STAGNATION_LIMIT}"
    )


def _check_stagnation(
    console: Any,
    score_history: list[int],
    stagnation_count: int,
    iteration_success: bool,
) -> int:
    """Evaluate whether the last iteration made progress. Returns updated stagnation_count."""
    if len(score_history) >= 2:
        delta = score_history[-1] - score_history[-2]
        if delta < MIN_PROGRESS:
            stagnation_count += 1
            console.print(
                f"  [yellow]⚠️ Progreso insuficiente (Δ{delta:+d}). "
                f"Estancamiento: {stagnation_count}/{STAGNATION_LIMIT}[/]"
            )
        else:
            stagnation_count = 0
            console.print(
                f"  [green]📈 Progreso: Δ{delta:+d} → Score {score_history[-1]}[/]"
            )

    if not iteration_success:
        stagnation_count += 1

    return stagnation_count


def _report_final_state(
    console: Any,
    current_result: ScanResult,
    target_score: int,
    iteration: int,
    score_history: list[int],
    any_success: bool,
) -> bool:
    """Print final report and return success status."""
    if current_result.score >= target_score:
        console.print(
            f"\n[bold green]✨ ¡INMEJORABLE! Score final: "
            f"{current_result.score}/100 en {iteration} iteraciones[/]"
        )
        _print_journey(console, score_history)
        return True

    if any_success:
        console.print(
            f"\n[bold yellow]⚡ Progreso parcial: "
            f"{score_history[0]} → {current_result.score} "
            f"en {iteration} iteraciones. "
            f"Faltaron {target_score - current_result.score} puntos.[/]"
        )
        _print_journey(console, score_history)
        return True

    return False


def _print_journey(console: Any, score_history: list[int]) -> None:
    """Print a visual journey of the score progression."""
    if len(score_history) <= 1:
        return
    journey = " → ".join(str(s) for s in score_history)
    console.print(f"  [dim]Recorrido: {journey}[/]")

