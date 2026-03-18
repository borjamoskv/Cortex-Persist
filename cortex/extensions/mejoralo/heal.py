"""Auto-Healing capability for MEJORAlo.

Detects the files that lowered the score, delegates refactoring to an LLM agent,
runs `pytest` to ensure 100% integrity, and automatically commits or rollbacks.

v8.0 — Relentless Mode: no para hasta que sea INMEJORABLE.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from cortex.extensions.mejoralo.engine import MejoraloEngine

from cortex.extensions.mejoralo.chronos import calculate_chronos_yield
from cortex.extensions.mejoralo.constants import (
    ESCALATION_ITER_L2,
    ESCALATION_ITER_L3,
    HARD_ITERATION_CAP,
    MIN_PROGRESS,
    PYTEST_TIMEOUT_SECONDS,
    STAGNATION_LIMIT,
)
from cortex.extensions.mejoralo.deps import sort_by_topological_order
from cortex.extensions.mejoralo.heal_prompts import (
    get_files_per_iteration as _get_files_per_iteration,
)
from cortex.extensions.mejoralo.models import ScanResult
from cortex.extensions.mejoralo.taint import is_file_tainted, mark_file_tainted

__all__ = [
    "heal_project",
]

logger = logging.getLogger("cortex.extensions.mejoralo.heal")


def _extract_issues_from_findings(scan_result: ScanResult) -> dict[str, list[str]]:
    """Map scan findings to their respective files."""
    file_issues: dict[str, list[str]] = {}
    for d in scan_result.dimensions:
        for f in d.findings:
            _add_finding_to_issues(file_issues, d.name, f)
    return file_issues


def _add_finding_to_issues(file_issues: dict[str, list[str]], dim_name: str, finding: str) -> None:
    """Helper to register a finding for its target file."""
    rel_path = _extract_path_from_finding(finding)
    if rel_path:
        file_issues.setdefault(rel_path, []).append(f"({dim_name}) {finding}")


def _extract_path_from_finding(finding: str) -> Optional[str]:
    """Extract file relative path from typical MEJORAlo findings."""
    if " -> " in finding or " → " in finding:
        return finding.split(":", 1)[0].strip()
    if " LOC)" in finding:
        return finding.split(" (", 1)[0].strip()
    return None


# ── Healing Logic ───────────────────────────────────────────────────


async def _heal_file_async(
    file_path: Path,
    findings: list[str],
    level: int = 1,
    iteration: int = 0,
    engine: Optional[MejoraloEngine] = None,  # type: ignore[reportGeneralTypeIssues]
    project: Optional[str] = None,
) -> Optional[str]:
    """Invoke the Sovereign Swarm to refactor a specific file with escalating intensity.

    Returns the new code if successful, None otherwise.
    """
    from cortex.extensions.mejoralo.swarm import MejoraloSwarm

    swarm = MejoraloSwarm(level=level)
    return await swarm.refactor_file(
        file_path, findings, iteration=iteration, engine=engine, project=project
    )


def _calculate_total_complexity(source_code: str) -> int:
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return 0

    from cortex.extensions.mejoralo.scan import _COMPLEXITY_NODES

    comp = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            comp += 1
        if isinstance(node, _COMPLEXITY_NODES):
            comp += 1
    return comp


def _apply_and_verify(
    top_file_rel: str,
    new_code: str,
    path: str | Path,
    level: int,
    iteration: int,
    console: Any,
    current_score: int,
    engine: Optional[MejoraloEngine] = None,  # type: ignore[reportGeneralTypeIssues]
    project: Optional[str] = None,
) -> bool:
    """Apply the already generated refactor, test it, and commit/rollback."""
    abs_path = Path(path).resolve() / top_file_rel
    console.print(f"  [cyan]🔬 Verificando {top_file_rel} (Integridad Bizantina)...[/]")

    try:
        original_code = abs_path.read_text(errors="replace")
    except (OSError, UnicodeDecodeError):
        logger.exception("Failed to read original code for %s", top_file_rel)
        return False

    complexity_delta = 0
    if abs_path.suffix == ".py":
        old_comp = _calculate_total_complexity(original_code)
        new_comp = _calculate_total_complexity(new_code)
        complexity_delta = old_comp - new_comp

    if not _run_functional_inquisitor(
        new_code, original_code, top_file_rel, console, engine, project, abs_path
    ):
        return False

    abs_path.write_text(new_code)
    _apply_aesthetic_formatting(abs_path, console)

    if not _run_delta_testing(
        top_file_rel, path, original_code, abs_path, console, engine, project, level
    ):
        return False

    return _commit_healed_file(
        abs_path,
        path,
        top_file_rel,
        level,
        iteration,
        current_score,
        console,
        complexity_delta=complexity_delta,
        engine=engine,
        project=project,
    )


def _run_functional_inquisitor(
    new_code: str,
    original_code: str,
    top_file_rel: str,
    console: Any,
    engine: Optional[MejoraloEngine],  # type: ignore[reportGeneralTypeIssues]
    project: Optional[str],
    abs_path: Path,
) -> bool:
    if abs_path.suffix != ".py":
        return True

    try:
        old_tree = ast.parse(original_code)
        new_tree = ast.parse(new_code)

        old_funcs = {n.name for n in ast.walk(old_tree) if isinstance(n, ast.FunctionDef)}
        new_funcs = {n.name for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef)}

        deleted = [f for f in old_funcs if not f.startswith("_") and f not in new_funcs]
        if deleted:
            console.print(
                f"  [bold red]🚫 Inquisidor: Eliminación de funciones públicas "
                f"detectada ({', '.join(deleted)}). BLOQUED.[/]"
            )
            if engine and project:
                engine.record_scar(project, top_file_rel, f"Inquisidor: Eliminó {deleted}")
            return False
    except SyntaxError:
        pass
    return True


def _apply_aesthetic_formatting(abs_path: Path, console: Any) -> None:
    console.print("  [cyan]💅 Aplicando 130/100 Aesthetics (Ruff)...[/]")
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", str(abs_path)],
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--fix", str(abs_path)],
        capture_output=True,
    )


def _run_delta_testing(
    top_file_rel: str,
    path: str | Path,
    original_code: str,
    abs_path: Path,
    console: Any,
    engine: Optional[MejoraloEngine],  # type: ignore[reportGeneralTypeIssues]
    project: Optional[str],
    level: int = 1,
) -> bool:
    pytest_cmd = [sys.executable, "-m", "pytest"]
    rel_parts = Path(top_file_rel).parts

    if len(rel_parts) > 1 and rel_parts[0] == "cortex":
        inferred_test = Path(path) / "tests" / f"test_{Path(top_file_rel).stem}.py"
        if inferred_test.exists():
            console.print(f"  [cyan]🎯 Delta-Testing: {inferred_test.name}[/]")
            pytest_cmd.append(str(inferred_test))
        else:
            console.print("  [dim]⚠️ No direct test found, running full suite...[/]")

    try:
        res = subprocess.run(
            pytest_cmd,
            cwd=path,
            capture_output=True,
            text=True,
            timeout=PYTEST_TIMEOUT_SECONDS,
        )
        if res.returncode != 0:
            console.print(f"  [bold red]💥 Regresión en {top_file_rel}! Rollback.[/]")
            if engine and project:
                error_trace = (res.stdout + "\n" + res.stderr).strip()
                engine.record_scar(project, top_file_rel, error_trace)
                # ⛔ Taint Circuit Breaker: if L3 and still failing, mark as tainted
                if level >= 3:
                    console.print(
                        f"  [bold red]☠️ L3 CIRCUIT BREAKER: {top_file_rel} "
                        "marcado como TAINTED. Requiere ariadne-arch-omega.[/]"
                    )
                    mark_file_tainted(top_file_rel, project, engine)
            abs_path.write_text(original_code)
            return False
        return True
    except subprocess.TimeoutExpired as e:
        console.print(
            f"  [bold red]⏳ Timeout en {top_file_rel} tras {PYTEST_TIMEOUT_SECONDS}s! Rollback.[/]"
        )
        if engine and project:
            err_trace = (
                f"TimeoutExpired: pytest superó los {PYTEST_TIMEOUT_SECONDS} "
                f"segundos. stdout: {e.stdout}"
            )
            engine.record_scar(project, top_file_rel, err_trace)
        abs_path.write_text(original_code)
        return False


def _commit_healed_file(
    abs_path: Path,
    path: str | Path,
    top_file_rel: str,
    level: int,
    iteration: int,
    current_score: int,
    console: Any,
    complexity_delta: int = 0,
    engine: Optional[MejoraloEngine] = None,
    project: Optional[str] = None,
) -> bool:
    try:
        commit_msg = (
            f"[MEJORAlo Auto-Heal L{level}] "
            f"Refactorizado {top_file_rel} "
            f"(iter {iteration}, score {current_score})"
        )
        console.print(f"  [bold green]✅ {top_file_rel} OK. Comiteando...[/]")
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
        # Ω₁₁ CHRONOS-1: Emit compound yield for this healed file
        if engine and project:
            hours = calculate_chronos_yield(
                files_touched=1,
                codepaths_affected=max(1, complexity_delta),
                runtime_ms=0,
                cyclomatic_complexity_delta=complexity_delta,
            )
            try:
                engine.record_session(
                    project=project,
                    score_before=current_score,
                    score_after=current_score,  # Will be updated by caller on re-scan
                    actions=[
                        f"Healed {top_file_rel} (L{level}, iter {iteration})",
                        f"CHRONOS-1 yield: {hours}h saved",
                    ],
                )
                console.print(f"  [dim]⏱ CHRONOS-1: {hours}h saved recorded in ledger.[/]")
            except Exception:  # noqa: BLE001
                logger.exception("Failed to record CHRONOS-1 yield for %s", top_file_rel)
        return True
    except (OSError, subprocess.SubprocessError):
        logger.exception("Error aplicando commit a %s", top_file_rel)
        return False


def _detect_escalation_level(
    iteration: int,
    stagnation_count: int,
) -> int:
    """Determine the current escalation level based on progress history."""
    if stagnation_count >= STAGNATION_LIMIT * 2 or iteration > ESCALATION_ITER_L3:
        return 3
    if stagnation_count >= STAGNATION_LIMIT or iteration > ESCALATION_ITER_L2:
        return 2
    return 1


def heal_project(
    project: str,
    path: str | Path,
    target_score: int,
    scan_result: ScanResult,
    engine: Optional[MejoraloEngine] = None,  # type: ignore[reportGeneralTypeIssues]
) -> bool:
    """Orchestrate autonomous healing: detect, rewrite, test, commit — RELENTLESSLY."""
    from cortex.cli import console

    current_result = scan_result
    iteration = 0
    any_success = False
    score_history: list[int] = [current_result.score]
    stagnation_count = 0
    healed_files: set[str] = set()

    while current_result.score < target_score and iteration < HARD_ITERATION_CAP:
        iteration += 1

        level = _detect_escalation_level(iteration, stagnation_count)
        _print_iteration_header(
            console, iteration, level, project, current_result.score, target_score, stagnation_count
        )

        iteration_success, current_result = _run_healing_iteration(
            project, path, level, iteration, console, current_result, healed_files, engine=engine
        )

        any_success = any_success or iteration_success
        score_history.append(current_result.score)

        stagnation_count = _check_stagnation(
            console,
            score_history,
            stagnation_count,
            iteration_success,
        )

        if stagnation_count >= STAGNATION_LIMIT * 3 or current_result.score >= target_score:
            if stagnation_count >= STAGNATION_LIMIT * 3:
                console.print(f"\n[bold red]🛑 Estancamiento terminal ({stagnation_count}).[/]")
            break

    return _report_final_state(
        console, current_result, target_score, iteration, score_history, any_success
    )


def _run_healing_iteration(
    project: str,
    path: str | Path,
    level: int,
    iteration: int,
    console: Any,
    current_result: ScanResult,
    healed_files: set[str],
    engine: Optional[MejoraloEngine] = None,  # type: ignore[reportGeneralTypeIssues]
) -> tuple[bool, ScanResult]:
    """Execute a single multi-file healing pass with re-scan."""
    from cortex.extensions.mejoralo.scan import scan

    file_issues = _extract_issues_from_findings(current_result)
    if not file_issues:
        return False, current_result

    # 🔗 Topological Sort: Prioritize leaf nodes (dependencies) to avoid cascading failures
    sorted_files = sort_by_topological_order(file_issues, path)

    # Within the topological layer, prioritize unhealed files with most issues
    # Note: _sort_by_topological_order currently returns a simple list,
    # but we can refine it if we want parallel layers.
    targets = sorted_files[: _get_files_per_iteration(level)]

    # 🚀 Sequential Generation (avoid rate-limits)
    async def _run_generations():
        results = []
        for f, iss in targets:
            result = await _heal_file_async(
                Path(path).resolve() / f,
                iss,
                level=level,
                iteration=iteration,
                engine=engine,
                project=project,
            )
            results.append(result)
        return results

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # If we are in an async context, we can't block.
            # This is a sync-to-async boundary. For now, we use a thread-safe
            # approach or nest sparingly.
            # In a sovereign environment, we prefer to run on a separate thread
            # to block properly if sync.
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                generation_results = executor.submit(
                    lambda: asyncio.run(_run_generations())
                ).result()
        else:
            generation_results = asyncio.run(_run_generations())
    except RuntimeError:
        generation_results = asyncio.run(_run_generations())

    iteration_success = False
    for (top_file_rel, _), new_code in zip(targets, generation_results, strict=True):
        # ⛔ Skip permanently tainted files before attempting to apply
        if is_file_tainted(top_file_rel, project, engine):
            console.print(
                f"  [bold red]☠️ {top_file_rel} está TAINTED. "
                "Requiere ariadne-arch-omega. Saltando.[/]"
            )
            continue
        if new_code and _apply_and_verify(
            top_file_rel,
            new_code,
            path,
            level,
            iteration,
            console,
            current_result.score,
            engine=engine,
            project=project,
        ):
            iteration_success = True
            healed_files.add(top_file_rel)

    # Re-scan to see new score
    console.print("  [cyan]🔄 Re-escaneando para verificar impacto...[/]")
    new_result = scan(project, path)
    return iteration_success, new_result


def _print_iteration_header(
    console: Any,
    iteration: int,
    level: int,
    project: str,
    current_score: int,
    target_score: int,
    stagnation_count: int,
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
    """Evaluate whether the last iteration made progress."""
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
            console.print(f"  [green]📈 Progreso: Δ{delta:+d} → Score {score_history[-1]}[/]")

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
        prog_str = f"{score_history[0]} → {current_result.score} in {iteration} iters."
        console.print(f"\n[bold yellow]⚡ Progreso parcial: {prog_str}[/]")
        _print_journey(console, score_history)
        return True

    return False


def _print_journey(console: Any, score_history: list[int]) -> None:
    """Print a visual journey of the score progression."""
    if len(score_history) <= 1:
        return
    journey = " → ".join(str(s) for s in score_history)
    console.print(f"  [dim]Recorrido: {journey}[/]")
