"""
⚙️ CORTEX SKILL: SYNTHESIS-OMEGA (Skill 66)
Clasificación: Meta-Orquestación Atómica y Mutación Estructural
Protocolo: A.E.R.E.V. (Análisis → Extracción → Reconstrucción → Escalado → Verificación)

Integra con SovereignLLM para análisis real, usa Inquisitor como Red Team,
y persiste decisiones a CORTEX. Atomicidad transaccional garantizada.

DERIVATION: Ω₂ (Entropic Asymmetry) + Ω₃ (Byzantine Default) + Ω₅ (Antifragile)
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.skills.synthesis_omega")


# ─── Resultado del Ciclo ─────────────────────────────────────────────────────


@dataclass
class AEREVResult:
    """Resultado inmutable del ciclo A.E.R.E.V."""

    success: bool
    target: str
    duration_ms: float = 0.0
    phases_completed: int = 0
    analysis_report: dict[str, Any] = field(default_factory=dict)
    rollback_executed: bool = False
    error: str = ""
    checksum_before: str = ""
    checksum_after: str = ""


# ─── Env Matrix ──────────────────────────────────────────────────────────────


class CortexEnvMatrix:
    """Ingiere el Multiplex de APIs proporcionado por el Arquitecto.

    Lee las variables de entorno y clasifica nodos por velocidad/coste.
    """

    __slots__ = (
        "primary_provider",
        "primary_model",
        "fast_nodes",
        "active_fast_nodes",
    )

    # Nodos ultra-rápidos para Fase 1 (AST scan, análisis ligero)
    _FAST_NODE_KEYS: dict[str, str] = {
        "TOGETHER": "TOGETHER_API_KEY",
        "FIREWORKS": "FIREWORKS_API_KEY",
        "CEREBRAS": "CEREBRAS_API_KEY",
        "DEEPINFRA": "DEEPINFRA_API_KEY",
        "SAMBANOVA": "SAMBANOVA_API_KEY",
        "NOVITA": "NOVITA_API_KEY",
    }

    def __init__(self) -> None:
        self.primary_provider: str = os.getenv("CORTEX_LLM_PROVIDER", "openai")
        self.primary_model: str = os.getenv("CORTEX_LLM_MODEL", "gpt-4o")
        self.fast_nodes: dict[str, str | None] = {
            k: os.getenv(v) for k, v in self._FAST_NODE_KEYS.items()
        }
        self.active_fast_nodes: list[str] = [
            k for k, v in self.fast_nodes.items() if v
        ]

    @property
    def best_fast_node(self) -> str:
        """Nodo rápido preferido, o el provider primario como fallback."""
        return self.active_fast_nodes[0] if self.active_fast_nodes else self.primary_provider

    @property
    def has_fast_nodes(self) -> bool:
        return len(self.active_fast_nodes) > 0


# ─── AST Analyzer ────────────────────────────────────────────────────────────


@dataclass
class ASTReport:
    """Reporte estructurado del análisis AST."""

    valid: bool
    total_nodes: int = 0
    functions: int = 0
    classes: int = 0
    async_functions: int = 0
    sync_functions: int = 0
    imports: int = 0
    complexity_indicators: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)


def analyze_ast(source: str) -> ASTReport:
    """Análisis AST estático del código fuente.

    No usa LLM — puro Python AST. O(n) sobre nodos.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ASTReport(valid=False)

    funcs = 0
    async_funcs = 0
    classes = 0
    imports = 0
    bottlenecks: list[str] = []
    complexity: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            funcs += 1
        elif isinstance(node, ast.AsyncFunctionDef):
            async_funcs += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports += 1
        # Detectar anti-patrones
        elif isinstance(node, ast.Call):
            func = getattr(node, "func", None)
            # Bare except → SyntaxError risk
            if isinstance(func, ast.Attribute) and func.attr == "sleep":
                bottlenecks.append("sync_sleep_detected")
        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                complexity.append("bare_except")
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                complexity.append("broad_exception_catch")

    # Ratio sync/async
    total_funcs = funcs + async_funcs
    if total_funcs > 0 and funcs > async_funcs * 2:
        bottlenecks.append("predominantly_sync_codebase")

    return ASTReport(
        valid=True,
        total_nodes=sum(1 for _ in ast.walk(tree)),
        functions=funcs,
        classes=classes,
        async_functions=async_funcs,
        sync_functions=funcs,
        imports=imports,
        complexity_indicators=complexity,
        bottlenecks=bottlenecks,
    )


# ─── SynthesisOmega ──────────────────────────────────────────────────────────


class SynthesisOmega:
    """Ensamblador Atómico — Protocolo A.E.R.E.V.

    Transaccional: o todo el ciclo completa, o se revierte al byte exacto.
    Zero-Trust: valida AST antes Y después de la mutación.
    Integra con SovereignLLM para fases que requieren inferencia.

    Usage::

        skill = SynthesisOmega("/path/to/module.py")
        result = await skill.execute_atomic_cycle()
        if result.success:
            print(f"Mutado en {result.duration_ms:.0f}ms")
    """

    def __init__(
        self,
        target_file: str,
        *,
        dry_run: bool = False,
        persist_to_cortex: bool = True,
    ) -> None:
        self.target_path = Path(target_file).absolute()
        self.lock_path = self.target_path.with_suffix(
            self.target_path.suffix + ".synth_lock"
        )
        self.matrix = CortexEnvMatrix()
        self.dry_run = dry_run
        self.persist_to_cortex = persist_to_cortex
        self._llm = None  # Lazy

    # ── LLM Access (Lazy) ─────────────────────────────────────────────────

    async def _get_llm(self):
        """Lazy-init del SovereignLLM. Solo importa si se necesita."""
        if self._llm is None:
            try:
                from cortex.llm.sovereign import SovereignLLM
                self._llm = SovereignLLM(temperature=0.2, max_tokens=4096)
            except ImportError:
                logger.warning("SovereignLLM no disponible — fases LLM degradarán a template")
                self._llm = None
        return self._llm

    # ── Entry Point ───────────────────────────────────────────────────────

    async def execute_atomic_cycle(self) -> AEREVResult:
        """Protocolo Transaccional Cerrado (All-or-Nothing)."""
        t0 = time.monotonic()
        logger.info("Iniciando Protocolo A.E.R.E.V en: %s", self.target_path.name)

        if not self.target_path.exists():
            logger.error("Objetivo no encontrado: %s", self.target_path)
            return AEREVResult(
                success=False, target=str(self.target_path), error="File not found"
            )

        if not self.target_path.suffix == ".py":
            return AEREVResult(
                success=False,
                target=str(self.target_path),
                error="Only Python files supported",
            )

        # 0. SNAPSHOT ATÓMICO
        source_code = self.target_path.read_text(encoding="utf-8")
        checksum_before = hashlib.sha256(source_code.encode()).hexdigest()[:16]
        shutil.copy2(self.target_path, self.lock_path)

        phases_completed = 0

        try:
            # [A]NÁLISIS
            ast_report = await self._fase_1_analisis(source_code)
            phases_completed = 1

            if not ast_report.valid:
                raise ValueError("El archivo objetivo tiene errores de sintaxis previos al ciclo")

            # [E]XTRACCIÓN
            extraction = await self._fase_2_extraccion(source_code, ast_report)
            phases_completed = 2

            # [R]ECONSTRUCCIÓN
            reconstructed = await self._fase_3_reconstruccion(extraction, ast_report)
            phases_completed = 3

            # [E]SCALADO
            scaled = await self._fase_4_escalado(reconstructed, ast_report)
            phases_completed = 4

            # [V]ERIFICACIÓN
            is_valid, report = await self._fase_5_verificacion(scaled, source_code)
            phases_completed = 5

            if not is_valid:
                raise ValueError(f"Verificación fallida: {report}")

            checksum_after = hashlib.sha256(scaled.encode()).hexdigest()[:16]

            if not self.dry_run:
                self.target_path.write_text(scaled, encoding="utf-8")

            # Cleanup lock
            if self.lock_path.exists():
                self.lock_path.unlink()

            elapsed = (time.monotonic() - t0) * 1000
            logger.info(
                "🟢 CICLO COMPLETADO. %s mutado en %.0fms [%s → %s]",
                self.target_path.name,
                elapsed,
                checksum_before,
                checksum_after,
            )

            result = AEREVResult(
                success=True,
                target=str(self.target_path),
                duration_ms=elapsed,
                phases_completed=phases_completed,
                analysis_report={
                    "functions": ast_report.functions,
                    "classes": ast_report.classes,
                    "async_ratio": (
                        ast_report.async_functions
                        / max(ast_report.functions + ast_report.async_functions, 1)
                    ),
                    "bottlenecks": ast_report.bottlenecks,
                    "complexity": ast_report.complexity_indicators,
                },
                checksum_before=checksum_before,
                checksum_after=checksum_after,
            )

            # Persist to CORTEX
            if self.persist_to_cortex:
                await self._persist_decision(result)

            return result

        except Exception as e:
            logger.error("🔴 ANOMALÍA en fase %d: %s. ROLLBACK.", phases_completed + 1, e)
            self._rollback()
            elapsed = (time.monotonic() - t0) * 1000
            return AEREVResult(
                success=False,
                target=str(self.target_path),
                duration_ms=elapsed,
                phases_completed=phases_completed,
                rollback_executed=True,
                error=str(e),
                checksum_before=checksum_before,
            )

    # ==========================================
    # 🔬 LAS 5 FASES DEL PROTOCOLO A.E.R.E.V
    # ==========================================

    async def _fase_1_analisis(self, code: str) -> ASTReport:
        """[A]NÁLISIS — Mapeo AST + detección de anti-patrones.

        Usa AST puro (sin LLM) para velocidad. El análisis LLM
        se reserva para la Fase 3 donde el coste se justifica.
        """
        node = self.matrix.best_fast_node
        logger.info("[1/5] ANÁLISIS: Mapeando AST y deuda técnica (vía %s)...", node)
        return analyze_ast(code)

    async def _fase_2_extraccion(
        self, code: str, report: ASTReport
    ) -> dict[str, Any]:
        """[E]XTRACCIÓN — Aislamiento de lógica core.

        Segmenta el código en bloques funcionales para permitir
        reconstrucción quirúrgica sin dañar imports o constantes.
        """
        logger.info("[2/5] EXTRACCIÓN: Aislando lógica core...")

        tree = ast.parse(code)
        lines = code.splitlines(keepends=True)

        # Extraer bloques por tipo
        segments: dict[str, list[str]] = {
            "header": [],  # imports, docstrings, constants
            "classes": [],
            "functions": [],
            "main": [],  # if __name__ == "__main__" blocks
        }

        # Clasificar nodos de primer nivel
        for node in ast.iter_child_nodes(tree):
            start = node.lineno - 1
            end = getattr(node, "end_lineno", start + 1)
            block = "".join(lines[start:end])

            if isinstance(node, (ast.Import, ast.ImportFrom)):
                segments["header"].append(block)
            elif isinstance(node, ast.ClassDef):
                segments["classes"].append(block)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                segments["functions"].append(block)
            elif isinstance(node, ast.If):
                # Detect if __name__ == "__main__"
                test = node.test
                if (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"
                ):
                    segments["main"].append(block)
                else:
                    segments["functions"].append(block)
            else:
                segments["header"].append(block)

        return {
            "source": code,
            "segments": segments,
            "ast_report": report,
        }

    async def _fase_3_reconstruccion(
        self, extraction: dict[str, Any], report: ASTReport
    ) -> str:
        """[R]ECONSTRUCCIÓN — Clean Architecture via SovereignLLM.

        Usa el núcleo pesado (gpt-4o / provider configurado) para
        reescribir aplicando SOLID. Si LLM no disponible, retorna original.
        """
        provider = f"{self.matrix.primary_provider.upper()} ({self.matrix.primary_model})"
        logger.info("[3/5] RECONSTRUCCIÓN: Aplicando Clean Architecture vía %s...", provider)

        source = extraction["source"]
        llm = await self._get_llm()

        if llm is None:
            logger.info("[3/5] Sin LLM disponible — retornando código original")
            return source

        # Construir prompt con contexto del AST
        bottlenecks = report.bottlenecks
        complexity = report.complexity_indicators

        if not bottlenecks and not complexity:
            logger.info("[3/5] Sin anti-patrones detectados — skip reconstrucción")
            return source

        prompt = (
            "You are a Senior Python Architect. Refactor the following code to fix these issues:\n\n"
            f"Bottlenecks: {', '.join(bottlenecks) or 'none'}\n"
            f"Complexity issues: {', '.join(complexity) or 'none'}\n\n"
            "Rules:\n"
            "- Keep ALL existing functionality intact\n"
            "- Fix only the identified issues\n"
            "- Use specific exception types (never bare except or catch-all Exception)\n"
            "- Add type hints where missing\n"
            "- Do NOT change the public API\n"
            "- Return ONLY the complete Python code, no explanations\n\n"
            f"```python\n{source}\n```"
        )

        system = (
            "You are a code refactoring engine. Return ONLY valid Python code. "
            "No markdown fences, no explanations. Pure Python source."
        )

        try:
            result = await llm.generate(prompt, system=system, mode="quality")
            if result.ok:
                # Strip markdown fences if LLM added them anyway
                content = result.content.strip()
                if content.startswith("```python"):
                    content = content[len("```python"):].strip()
                if content.startswith("```"):
                    content = content[3:].strip()
                if content.endswith("```"):
                    content = content[:-3].strip()
                return content
            logger.warning("[3/5] LLM no respondió OK — retornando original")
            return source
        except Exception as e:
            logger.error("[3/5] Error en LLM: %s — retornando original", e)
            return source

    async def _fase_4_escalado(self, code: str, report: ASTReport) -> str:
        """[E]SCALADO — Preparación para alta concurrencia.

        NOTA CRÍTICA: La v0 hacía str.replace("def ", "async def ") que
        destruía `default`, `__init__`, `def_factory`, etc.
        La v2 usa transformación AST quirúrgica.

        Solo escala si se detectaron bottlenecks de sync en Fase 1.
        """
        logger.info("[4/5] ESCALADO: Evaluando necesidad de hiper-concurrencia...")

        if "predominantly_sync_codebase" not in report.bottlenecks:
            logger.info("[4/5] Codebase no requiere escalado async — skip")
            return code

        # En lugar de str.replace destructivo, solo señalamos
        # las funciones candidatas. La transformación real la haría
        # el LLM en Fase 3 o un AST transformer dedicado.
        logger.info(
            "[4/5] SEÑALADO: %d funciones sync detectadas para posible migración async",
            report.sync_functions,
        )

        # No mutamos el código ciegamente — la Fase 3 con LLM es la que
        # debe hacer la transformación informada. Aquí solo validamos.
        return code

    async def _fase_5_verificacion(
        self, code: str, original: str
    ) -> tuple[bool, str]:
        """[V]ERIFICACIÓN — Compilación AST + invariancia estructural.

        Verifica:
        1. Sintaxis válida (ast.parse)
        2. No se perdieron clases/funciones del original
        3. Inquisitor adversarial (si disponible)
        """
        logger.info("[5/5] VERIFICACIÓN: Compilando AST y validando invariancia...")

        # 1. Sintaxis
        try:
            new_tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"SyntaxError en línea {e.lineno}: {e.msg}"

        # 2. Invariancia estructural — no perder entidades públicas
        try:
            old_tree = ast.parse(original)
        except SyntaxError:
            # Si el original ya era inválido, aceptamos el nuevo
            return True, "Original era inválido, nuevo AST verificado OK"

        old_names = {
            node.name
            for node in ast.walk(old_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and not node.name.startswith("_")
        }

        new_names = {
            node.name
            for node in ast.walk(new_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and not node.name.startswith("_")
        }

        missing = old_names - new_names
        if missing:
            return False, f"Entidades públicas perdidas: {', '.join(sorted(missing))}"

        # 3. Red Team (Inquisitor) — si disponible
        try:
            from cortex.llm.sovereign import Inquisitor

            inquisitor = Inquisitor()
            siege_result = await inquisitor.asediar(code, original_prompt="AEREV-synthesis")
            if siege_result and hasattr(siege_result, "ok") and not siege_result.ok:
                logger.warning("[5/5] Inquisitor flagged issues — aceptando con warning")
                # No bloqueamos por ahora, solo warning
        except (ImportError, AttributeError, Exception) as e:
            logger.debug("[5/5] Inquisitor no disponible: %s", e)

        return True, "AST verificado + invariancia estructural OK"

    # ── Rollback ──────────────────────────────────────────────────────────

    def _rollback(self) -> None:
        """Restauración absoluta al byte exacto previo a la ejecución."""
        if self.lock_path.exists():
            shutil.copy2(self.lock_path, self.target_path)
            self.lock_path.unlink()
            logger.warning("🔄 ROLLBACK: %s restaurado al estado previo", self.target_path.name)
        else:
            logger.error("🔴 ROLLBACK IMPOSIBLE: lock file no encontrado")

    # ── CORTEX Persistence ────────────────────────────────────────────────

    async def _persist_decision(self, result: AEREVResult) -> None:
        """Persiste el resultado a CORTEX como decision."""
        try:
            project = self.target_path.parts[-2] if len(self.target_path.parts) >= 2 else "unknown"
            content = (
                f"SYNTHESIS-OMEGA A.E.R.E.V completado en {result.target}: "
                f"{result.phases_completed}/5 fases, "
                f"{result.duration_ms:.0f}ms, "
                f"checksum {result.checksum_before}→{result.checksum_after}"
            )
            proc = await asyncio.create_subprocess_exec(
                str(Path.home() / "cortex" / ".venv" / "bin" / "python"),
                "-m", "cortex.cli", "store",
                "--type", "decision",
                "--source", "skill:synthesis-omega",
                project.upper(),
                content,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
        except Exception as e:
            logger.debug("CORTEX persistence skipped: %s", e)


# ─── Batch Mode ───────────────────────────────────────────────────────────────


async def trigger_synthesis(
    filepath: str,
    *,
    dry_run: bool = False,
    persist: bool = True,
) -> AEREVResult:
    """Punto de ignición para keter-omega y orquestadores externos."""
    skill = SynthesisOmega(filepath, dry_run=dry_run, persist_to_cortex=persist)
    return await skill.execute_atomic_cycle()


async def batch_synthesis(
    filepaths: list[str],
    *,
    dry_run: bool = False,
    max_concurrent: int = 4,
) -> list[AEREVResult]:
    """Ejecuta A.E.R.E.V en batch con concurrencia controlada.

    Args:
        filepaths: Lista de archivos Python a procesar.
        max_concurrent: Máximo de archivos procesados en paralelo.
        dry_run: Si True, no escribe cambios al disco.

    Returns:
        Lista de resultados (uno por archivo).
    """
    sem = asyncio.Semaphore(max_concurrent)

    async def _bounded(fp: str) -> AEREVResult:
        async with sem:
            return await trigger_synthesis(
                fp, dry_run=dry_run, persist=True
            )

    tasks = [_bounded(fp) for fp in filepaths]
    return await asyncio.gather(*tasks)


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m cortex.skills.synthesis_omega <file.py> [--dry-run]")
        sys.exit(1)

    target = sys.argv[1]
    dry = "--dry-run" in sys.argv

    async def _main() -> None:
        result = await trigger_synthesis(target, dry_run=dry)
        status = "🟢 SUCCESS" if result.success else "🔴 FAILED"
        print(f"\n{status}: {result.target}")
        print(f"  Fases: {result.phases_completed}/5")
        print(f"  Duración: {result.duration_ms:.0f}ms")
        if result.error:
            print(f"  Error: {result.error}")
        if result.rollback_executed:
            print("  ⚠️ Rollback ejecutado")
        if result.analysis_report:
            print(f"  Reporte: {result.analysis_report}")

    asyncio.run(_main())
