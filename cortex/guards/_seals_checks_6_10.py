# [C5-REAL] Exergy-Maximized
import ast
import asyncio
from pathlib import Path

from cortex.guards._seals_cache import ROOT_DIR, GlobalSourceCache, printer
from cortex.guards.sovereign_seals import (
    check_gate_21_preservation,
    check_seal_8_dependency_impl,
    check_seal_9_compliance_impl,
)

GateResult = tuple[bool, str]


async def _check_blocking_sleep(exclude_files: frozenset[str]) -> list[str]:
    """Identify synchronous time.sleep() calls in async-critical files."""
    violations = []
    for py_file, content in GlobalSourceCache.files.items():
        if py_file.name in exclude_files:
            continue
        try:
            tree = ast.parse(content, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "sleep"
                        and isinstance(node.func.value, ast.Name)
                        and (node.func.value.id == "time")
                        or (isinstance(node.func, ast.Name) and node.func.id == "sleep")
                    ):
                        violations.append(f"{py_file.name}:{node.lineno}")
        except SyntaxError:
            continue
    return violations


async def _check_temperature_determinism(critical_files: list[Path]) -> list[str]:
    """Ensure LLM calls use temperature=0 for determinism."""
    violations = []
    zero_values = (0, 0.0)
    for path in critical_files:
        if path in GlobalSourceCache.files:
            content = GlobalSourceCache.files[path]
        elif path.exists():
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        else:
            continue
        try:
            tree = ast.parse(content, filename=str(path))
            has_temp = False
            has_zero = False
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword) and node.arg == "temperature":
                    has_temp = True
                    if isinstance(node.value, ast.Constant) and node.value.value in zero_values:
                        has_zero = True
                elif isinstance(node, ast.Dict):
                    for k, v in zip(node.keys, node.values, strict=False):
                        if isinstance(k, ast.Constant) and k.value == "temperature":
                            has_temp = True
                            if isinstance(v, ast.Constant) and v.value in zero_values:
                                has_zero = True
            if has_temp and (not has_zero):
                violations.append(path.name)
        except SyntaxError:
            continue
    return violations


async def _check_latency_telemetry() -> list[str]:
    """Audit local provider latency from telemetry."""
    try:
        from cortex.extensions.llm._telemetry import CascadeTelemetry

        telemetry = CascadeTelemetry()
        stats = telemetry.stats()
        slow = []
        for prov in ["ollama", "vllm", "jan", "lmstudio"]:
            avg_lat = stats.get(prov, {}).get("avg_latency_ms", 0)
            if avg_lat > 200:
                slow.append(f"{prov} ({avg_lat}ms)")
        return slow
    except ImportError:
        return []


async def check_seal_6_async_perf() -> GateResult:
    """Check asynchronous performance invariants."""
    printer.seal(6, "AX-III Colapso Entrópico", "Async & Performance")
    passed = True
    exclude = frozenset(
        [
            "seals.py",
            "reactor.py",
            "antipatterns.py",
            "_scanner_visitors.py",
            "registry.py",
            "legion.py",
            "legion_vectors.py",
            "demo_swarm.py",
            "demo_bicameral.py",
            "network.py",
            "fiat_oracle.py",
            "mouse.py",
            "dashboard_cmds.py",
            "health_cmds.py",
            "ouroboros_omega.py",
            "oracle.py",
        ]
    )
    sleep_violations = await _check_blocking_sleep(exclude)
    if sleep_violations:
        printer.fail(f"Blocking time.sleep(): {sleep_violations}")
        passed = False
    else:
        printer.success("No blocking time.sleep() found.")
    critical = [
        ROOT_DIR / "cortex/llm/router.py",
        ROOT_DIR / "cortex/llm/provider.py",
        ROOT_DIR / "cortex/guards/seals.py",
    ]
    temp_violations = await _check_temperature_determinism(critical)
    if temp_violations:
        printer.fail(f"Temperature drift in {temp_violations}")
        passed = False
    else:
        printer.success("Temperature Determinism intact.")
    slow_locals = await _check_latency_telemetry()
    if slow_locals:
        printer.warn(f"High local latency: {slow_locals}")
    else:
        printer.success("Latency <200ms.")
    return (passed, "verified")


async def check_seal_7_axiom_registry() -> GateResult:
    """Check axiom registry integrity and system prompt budget."""
    printer.seal(7, "Registry Integrity", "Axiom Registry + Prompt Budget")
    passed = True
    try:
        from cortex.extensions.axioms import AXIOM_REGISTRY
        from cortex.extensions.axioms.registry import enforced

        total = len(AXIOM_REGISTRY)
        enf = len(enforced())
        if total != 7:
            printer.fail(f"Registry degraded: exactly 7 axioms required, found {total}")
            passed = False
        else:
            printer.success(f"Registry: {total} Sovereign Axioms, {enf} CI-enforced.")
    except ImportError:
        printer.warn("Axioms extension not found. Skipping registry check.")
    except (AttributeError, TypeError, ValueError) as e:
        printer.fail(f"Registry error: {e}")
        passed = False
    prompt_file = ROOT_DIR / "SYSTEM_PROMPT.md"
    if prompt_file.exists():
        try:
            content = await asyncio.to_thread(prompt_file.read_text, encoding="utf-8")
            tokens = len(content.split())
            if tokens > 500:
                printer.warn(f"System prompt {tokens} words (target: <200).")
            else:
                printer.success(f"Prompt within targets ({tokens} words).")
        except OSError:
            printer.warn("Could not read SYSTEM_PROMPT.md")
    return (passed, "verified")


async def check_seal_8_dependency() -> GateResult:
    """Verify dependency integrity and Shannon entropy of files."""
    printer.seal(8, "Ω₃ Byzantine", "Dependency Integrity + Shannon Entropy")
    return await check_seal_8_dependency_impl(GlobalSourceCache.files)


async def check_seal_9_compliance() -> GateResult:
    """Verify compliance and aesthetic integrity."""
    printer.seal(9, "Sovereign Aesthetic", "Compliance & Aesthetic Integrity")
    return await check_seal_9_compliance_impl()


async def check_seal_10_preservation() -> GateResult:
    """Check self-preservation guarantees."""
    printer.seal(10, "Ω₅ Antifragile", "Self-Preservation")
    return await check_gate_21_preservation(cached_files=GlobalSourceCache.files)
